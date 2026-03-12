from typing import Any

from task.tools.deployment.base_agent_tool import BaseAgentTool

TOOL_DESCRIPTION = """
The WEB Search Agent specializes in conducting online research based on user requests. 
Equipped with a powerful WEB search capability (using DuckDuckGo via MCP), it can efficiently 
retrieve and summarize information from the internet. Additionally, it is able to fetch and 
extract content directly from web pages, making it ideal for gathering up-to-date facts, news, 
and insights from a wide range of online sources.
"""

class WebSearchAgentTool(BaseAgentTool):

    #TODO:
    # Provide implementations of deployment_name (in core config), name, description and parameters.
    # Don't forget to mark them as @property
    # Parameters:
    #   - prompt: string. Required.
    #   - propagate_history: boolean
    @property
    def deployment_name(self) -> str:
        return "web-search-agent"
    
    @property
    def name(self) -> str:
        return "web_search_tool"
    
    @property
    def description(self) -> str:
        return TOOL_DESCRIPTION
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The web search query or instruction to be processed by the tool."
                },
                "propagate_history": {
                    "type": "boolean",
                    "default": False,
                    "description": "Indicates whether to include conversation history. Default 'false'."
                }
            },
            "required": ["prompt"]
        }

