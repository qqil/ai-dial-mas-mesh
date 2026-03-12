from typing import Any

from task.tools.deployment.base_agent_tool import BaseAgentTool

TOOL_DESCRIPTION = """
The Content Management Agent is designed to streamline document handling and information retrieval. 
It features a robust files content extractor and RAG (Retrieval-Augmented Generation) search, 
supporting PDF, TXT, and CSV files. This agent enables users to efficiently extract, search, and analyze 
content from various document formats.
"""

class ContentManagementAgentTool(BaseAgentTool):

    #TODO:
    # Provide implementations of deployment_name (in core config), name, description and parameters.
    # Don't forget to mark them as @property
    # Parameters:
    #   - prompt: string. Required.
    #   - propagate_history: boolean
    @property
    def deployment_name(self) -> str:
        return "content-management-agent"
    
    @property
    def name(self) -> str:
        return "content_management_tool"
    
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
                    "description": "The content management query or instruction to be processed by the tool."
                },
                "propagate_history": {
                    "type": "boolean",
                    "default": False,
                    "description": "Indicates whether to include conversation history. Default 'false'."
                }
            },
            "required": ["prompt"]
        }

