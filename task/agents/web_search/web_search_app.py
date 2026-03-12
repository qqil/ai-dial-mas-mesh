import os

import uvicorn
from aidial_sdk import DIALApp
from aidial_sdk.chat_completion import ChatCompletion, Request, Response

from task.agents.web_search.web_search_agent import WebSearchAgent
from task.tools.base_tool import BaseTool
from task.tools.deployment.calculations_agent_tool import CalculationsAgentTool
from task.tools.deployment.content_management_agent_tool import ContentManagementAgentTool
from task.tools.mcp.mcp_client import MCPClient
from task.tools.mcp.mcp_tool import MCPTool
from task.utils.constants import DIAL_ENDPOINT, DEPLOYMENT_NAME

_DDG_MCP_URL = os.getenv('DDG_MCP_URL', "http://localhost:8051/mcp")

#TODO:
# 1. Create WebSearchApplication class and extend ChatCompletion
# 2. As a tools for WebSearchAgent you need to provide:
#   - MCP tools by _DDG_MCP_URL
#   - CalculationsAgentTool (MAS Mesh)
#   - ContentManagementAgentTool (MAS Mesh)
# 3. Override the chat_completion method of ChatCompletion, create Choice and call WebSearchAgent
# ---
# 4. Create DIALApp with deployment_name `web-search-agent` (the same as in the core config) and impl is instance
#    of the WebSearchApplication
# 5. Add starter with DIALApp, port is 5003 (see core config)

class WebSearchApplication(ChatCompletion):
    def __init__(self) -> None:
        self.tools: list[BaseTool] | None = None

    async def chat_completion(self, request: Request, response: Response) -> None:
        if not self.tools:
            self.tools = await self._get_tools()

        with response.create_single_choice() as choice:
            await WebSearchAgent(
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
            CalculationsAgentTool(DIAL_ENDPOINT),
            ContentManagementAgentTool(DIAL_ENDPOINT)
        ]

        tools.extend(await self._get_mcp_tools(url=_DDG_MCP_URL))
    
        return tools
    
    async def _get_mcp_tools(self, url: str) -> list[BaseTool]: 
        tools: list[BaseTool] = []
    
        mcp_client = await MCPClient.create(mcp_server_url=url)
        tool_models = await mcp_client.get_tools()
        
        if len(tool_models) > 0:
            tools.extend([
                MCPTool(client=mcp_client, mcp_tool_model=tool_model) for tool_model in tool_models
            ])

        return tools


dial_app = DIALApp()
websearch_app = WebSearchApplication()

dial_app.add_chat_completion("web-search-agent", impl=websearch_app)

uvicorn.run(app=dial_app, port=5003, host="0.0.0.0", log_level="info")