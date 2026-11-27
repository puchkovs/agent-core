"""Host-owned policy decisions, independent of prompts and observations."""

from dataclasses import dataclass
from enum import StrEnum

from .contracts import Effect, digest
from .tools import Tool


class Decision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    APPROVAL = "approval"


@dataclass(frozen=True)
class Policy:
    allowed_tools: frozenset[str] = frozenset()
    permissions: frozenset[str] = frozenset()
    approval_tools: frozenset[str] = frozenset()
    approve_writes: bool = True
    scope: str = "local"
    version: str = "1"

    def decide(self, tool: Tool) -> Decision:
        if tool.name not in self.allowed_tools or not tool.permissions <= self.permissions:
            return Decision.DENY
        if tool.name in self.approval_tools or (self.approve_writes and tool.effect != Effect.READ):
            return Decision.APPROVAL
        return Decision.ALLOW

    @property
    def identity(self) -> str:
        return digest(
            {
                "tools": sorted(self.allowed_tools),
                "permissions": sorted(self.permissions),
                "approval": sorted(self.approval_tools),
                "writes": self.approve_writes,
                "scope": self.scope,
                "version": self.version,
            }
        )
