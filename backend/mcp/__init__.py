"""MCP external tools — live FX (BoC), currency conversion, live market quotes."""

from mcp.currency import convert_currency
from mcp.market import get_market_quote
from mcp.registry import MCP_TOOL_DEFINITIONS, execute_mcp_tool, register_mcp_tools

__all__ = [
    "MCP_TOOL_DEFINITIONS",
    "convert_currency",
    "get_market_quote",
    "execute_mcp_tool",
    "register_mcp_tools",
]
