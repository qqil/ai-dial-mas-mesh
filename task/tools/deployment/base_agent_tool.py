import json
from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Any

from aidial_client import AsyncDial
from aidial_sdk.chat_completion import Message, Role, CustomContent, Stage, Attachment
from pydantic import StrictStr

from task.tools.base_tool import BaseTool
from task.tools.models import ToolCallParams
from task.utils.stage import StageProcessor


class BaseAgentTool(BaseTool, ABC):

    def __init__(self, endpoint: str):
        self.endpoint = endpoint

    @property
    @abstractmethod
    def deployment_name(self) -> str:
        pass

    async def _execute(self, tool_call_params: ToolCallParams) -> str | Message:
        #TODO:
        # 1. All the agents that will used as tools will have two parameters in request:
        #   - `prompt` (the request to agent)
        #   - `propagate_history`, boolean whether we need to propagate the history of communication with called agent
        # 2. Use AsyncDial (api_version='2025-01-01-preview'), call the agent with steaming option.
        #    Here, actually, you can find one of the most powerful features of DIAL - Unified protocol. All the
        #    applications that provide `/chat/completions` endpoint and following Unified protocol - can `communicate`
        #    between each other though Unified protocol (that is OpenAI compatible), in other words, applications can
        #    `communicate` between each other like they communication with OpenAI models (Unified protocol is OpenAI compatible).
        #    The second powerful feature is that the application that makes the call provides with whole context and
        #    responsible to manage this context. So, like we calling the model and provide it with the whole history in
        #    the same way we are working with applications, the application that makes a call provide the conversation history.
        #    ⚠️ To provide proper message history you need to implement the `_prepare_messages` method!
        #    ⚠️ Don't forget to include as extra_headers `x-conversation-id`!
        # 3. Prepare:
        #   - `content` variable, here we will collect the streamed content
        #   - `custom_content: CustomContent` variable, here we will collect variable CustomContent from agent response
        #   - `stages_map: dict[int, Stage]` variable, here will be persisted propagated stages
        # 4. Iterate through chunks and:
        #   - Stream content to the Stage (from tool_call_params) for this tool call
        #   - For custom_content:
        #       - set `state` from response CustomContent to the `custom_content`
        #       - in attachments are found propagate them to choice
        #       - Optional:
        #           Stages propagation: convert response CustomContent to dict and if stages are present:
        #           - each Stage has it is `index`, it will be returned in each chunk. If stage by such index is present
        #             in `stages_map` then you need to propagate content, otherwise you need to create stage
        #           - propagate stage name from response to propagated stage name, the same story for `content` and `attachments`
        #           - if response stage has `status = completed` - we need to close such stage
        # 5. Ensure that stages are closed (just iterate through them and close safely with StageProcessor)
        # 6. Return Tool message
        #    ⚠️ Remember, tool message must have tool call id, also don't forget to add `custom_content` since we need
        #       to save properly tool history to choice state later
        dial_client = AsyncDial(
            api_version='2025-01-01-preview', 
            base_url=self.endpoint,
            api_key=tool_call_params.api_key,
        )

        arguments = json.loads(tool_call_params.tool_call.function.arguments)
        print(f"Tool call arguments: {arguments}")
        stage = tool_call_params.stage
        stage.append_name(f": {arguments.get("prompt")}")

        conversation_id = tool_call_params.conversation_id
        messages = self._prepare_messages(tool_call_params=tool_call_params)

        content = ""
        custom_content = CustomContent(attachments=[])
        stages_map: dict[int, Stage] = {}

        response = await dial_client.chat.completions.create(
            deployment_name=self.deployment_name,
            messages=messages, # type: ignore
            extra_headers={
                "x-conversation-id": conversation_id
            },
            # extra_body={
            #     "custom_fields": { **arguments }
            # },
            stream=True
        )

        async for chunk in response:
            if not chunk.choices or len(chunk.choices) == 0:
                continue

            delta = chunk.choices[0].delta

            if not delta:
                continue

            if delta.content:
                stage.append_content(delta.content)
                content += delta.content
            
            if delta.custom_content:
                if delta.custom_content.attachments:
                    custom_content.attachments.extend(delta.custom_content.attachments) # type: ignore
                
                if delta.custom_content.state:
                    custom_content.state = delta.custom_content.state

                delta_custom_content_dict = delta.custom_content.dict(exclude_none=True)
                stages = delta_custom_content_dict.get("stages")
                
                if not stages:
                    continue

                for delta_custom_content_stage in stages:
                    idx = delta_custom_content_stage["index"]
                    opened_stage = stages_map.get(idx)
                    if opened_stage:
                        if stg_name := delta_custom_content_stage.get("name"):
                            opened_stage.append_name(stg_name)
                        if stg_content := delta_custom_content_stage.get("content"):
                            opened_stage.append_content(stg_content)
                        if stg_attachments := delta_custom_content_stage.get("attachments"):
                            for att in stg_attachments:
                                opened_stage.add_attachment(Attachment(**att))
                        if delta_custom_content_stage.get('status') == 'completed':
                            StageProcessor.close_stage_safely(opened_stage)
                    else:
                        stages_map[idx] = StageProcessor.open_stage(tool_call_params.choice, delta_custom_content_stage.get("name"))
        
        for stage in stages_map.values():
            StageProcessor.close_stage_safely(stage)


        for attachment in custom_content.attachments: # type: ignore
            tool_call_params.choice.add_attachment(attachment=attachment)

        return Message(
            role=Role.TOOL,
            content=content,
            custom_content=custom_content,
            tool_call_id=tool_call_params.tool_call.id
        )

        

    def _prepare_messages(self, tool_call_params: ToolCallParams) -> list[dict[str, Any]]:
        #TODO:
        # In here we will manage the context for the agent that we are going to call.
        # We support two modes:
        #   - One-shot: only one user message to the Agent with prompt
        #   - Propagate whole Per-To-Per history between this Agent and the Agent that we are calling
        # ---
        # 1. Get: `prompt` and `propagate_history` params from tool call
        # 2. Prepare empty `messages` array, here we will collect history with Per-To-Per communication between this
        #    agent and the agent that we are colling
        # 3. Collect the proper history, iterate through messages and:
        #   - In Assistant messages presented the state with tool_call_history, we need to properly unpack it. If message
        #   from assistant and in custom content present state and in this state present history for this `self.name`
        #   (self.name is the key in state to get tool_call_history from the agent that we are going to call), then
        #   firstly add to `messages` user message that is going before the assistant message and then add assistant
        #   message. For assistant message you need to make a deepcopy and refactor the state for copied message, instead
        #   of the whole state you need to get from the state value by `self.name`
        # 4. Lastly, add the user message with `prompt` and don't forget about the custom_content
        arguments = json.loads(tool_call_params.tool_call.function.arguments)

        prompt = arguments.get("prompt")
        propagate_history = bool(arguments.get("propagate_history", False))

        messages = []

        if propagate_history:
            for msg_idx in range(len(tool_call_params.messages)):
                msg = tool_call_params.messages[msg_idx]

                # Process only assistant messages, user message (that is always before assistant message)
                # will be added later during processing
                if msg.role != Role.ASSISTANT:
                    continue

                # Skip assistant messages without custom_content and state
                if not msg.custom_content or not msg.custom_content.state:
                    continue

                msg_state = msg.custom_content.state
                # Skip if in assistant message state does not exist our tool name
                if not msg_state.get(self.name):
                    continue

                # Add user message (that is before assistant message)
                messages.append(tool_call_params.messages[msg_idx - 1].model_dump(exclude_none=True))

                # Add assistant message with updated state that contains only current tool state
                msg_copy = deepcopy(msg)
                msg_copy.custom_content.state = msg_state.get(self.name) # type: ignore
                messages.append(msg_copy.model_dump(exclude_none=True))



        last_message = tool_call_params.messages[-1]
        custom_content = last_message.custom_content.dict(exclude_none=True) if last_message.custom_content else None
        messages.append({
            "role": Role.USER,
            "content": prompt,
            "custom_content": custom_content
        })

        return messages