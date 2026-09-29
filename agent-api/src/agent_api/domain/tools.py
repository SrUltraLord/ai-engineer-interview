MCP_SEARCH_TOOL = "mcp_search_documents"

DEFAULT_TOOL_ALLOWLIST: dict[str, frozenset[str]] = {
    "comercial": frozenset({MCP_SEARCH_TOOL}),
    "analista_riesgos": frozenset({MCP_SEARCH_TOOL}),
    "tesorero": frozenset({MCP_SEARCH_TOOL}),
    "practicante": frozenset({MCP_SEARCH_TOOL}),
}


class ToolAllowlist:
    """Tools permitidas por rol. Un rol desconocido no puede ejecutar ninguna."""

    def __init__(self, by_role: dict[str, frozenset[str]] | None = None) -> None:
        self._by_role = DEFAULT_TOOL_ALLOWLIST if by_role is None else by_role

    def for_role(self, role: str) -> frozenset[str]:
        return self._by_role.get(role, frozenset())

    def allows(self, role: str, tool: str) -> bool:
        return tool in self.for_role(role)
