import os

import uvicorn
from aidial_sdk import DIALApp
from aidial_sdk.chat_completion import ChatCompletion, Request, Response

from task.agents.calculations.calculations_agent import CalculationsAgent
from task.agents.calculations.tools.simple_calculator_tool import SimpleCalculatorTool
from task.tools.base_tool import BaseTool
from task.agents.calculations.tools.py_interpreter.python_code_interpreter_tool import PythonCodeInterpreterTool
from task.tools.deployment.content_management_agent_tool import ContentManagementAgentTool
from task.tools.deployment.web_search_agent_tool import WebSearchAgentTool
from task.utils.constants import DIAL_ENDPOINT, DEPLOYMENT_NAME


#TODO:
# 1. Create CalculationsApplication class and extend ChatCompletion
# 2. As a tools for CalculationsAgent you need to provide:
#   - SimpleCalculatorTool
#   - PythonCodeInterpreterTool
#   - ContentManagementAgentTool (MAS Mesh)
#   - WebSearchAgentTool (MAS Mesh)
# 3. Override the chat_completion method of ChatCompletion, create Choice and call CalculationsAgent
# ---
# 4. Create DIALApp with deployment_name `calculations-agent` (the same as in the core config) and impl is instance of
#    the CalculationsApplication
# 5. Add starter with DIALApp, port is 5001 (see core config)

class CalculationsApplication(ChatCompletion):
    def __init__(self) -> None:
        self.tools: list[BaseTool] | None = None

    async def chat_completion(self, request: Request, response: Response) -> None:
        if not self.tools:
            self.tools = await self._get_tools()

        with response.create_single_choice() as choice:
            await CalculationsAgent(
                endpoint=DIAL_ENDPOINT,
                tools=self.tools
            ).handle_request(
                deployment_name=DEPLOYMENT_NAME,
                choice=choice,
                request=request,
                response=response
            )
    
    async def _get_tools(self) -> list[BaseTool]:
        tools: list[BaseTool] = [
            SimpleCalculatorTool(),
            ContentManagementAgentTool(DIAL_ENDPOINT),
            WebSearchAgentTool(DIAL_ENDPOINT),
            await PythonCodeInterpreterTool.create(
                mcp_url=os.getenv("PYINTERPRETER_MCP_URL", "http://localhost:8050/mcp"),
                tool_name="execute_code",
                dial_endpoint=DIAL_ENDPOINT
            )
        ]

        return tools


dial_app = DIALApp()
calculations_app = CalculationsApplication()

dial_app.add_chat_completion("calculations-agent", impl=calculations_app)

uvicorn.run(app=dial_app, port=5001, host="0.0.0.0", log_level="info")