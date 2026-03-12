from typing import Any

from aidial_sdk.chat_completion import Message

from task.tools.deployment.base_agent_tool import BaseAgentTool
from task.tools.models import ToolCallParams

TOOL_DESCRIPTION = """
The Calculation Tool is built for efficient and accurate mathematical operations. 
It features a Python Code Interpreter (via MCP) for advanced computations and scripting, 
a Simple Calculator for quick arithmetic, and the ability to generate interactive Plotly 
graphics and bar charts. Ideal for data analysis, reporting, and visualization, this tool 
streamlines everything from basic calculations to complex data processing and visual insights—all in one place.
"""

class CalculationsAgentTool(BaseAgentTool):

    #TODO:
    # Provide implementations of deployment_name (in core config), name, description and parameters.
    # Don't forget to mark them as @property
    # Parameters:
    #   - prompt: string. Required.
    #   - propagate_history: boolean
    
    @property
    def deployment_name(self) -> str:
        return "calculations-agent"
    
    @property
    def name(self) -> str:
        return "calculations_tool"
    
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
                    "description": "The calculation query or instruction to be processed by the tool."
                },
                "propagate_history": {
                    "type": "boolean",
                    "default": False,
                    "description": "Indicates whether to include conversation history. Default 'false'."
                }
            },
            "required": ["prompt"]
        }
