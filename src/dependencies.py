"""Dependency injection providers for FastMCP tools.

Provides injectable dependencies using FastMCP's Depends() pattern,
replacing the deprecated exclude_args approach.
"""

from typing import Annotated

from fastmcp.dependencies import Depends


async def get_authorization() -> str | None:
    """Provides Authorization header via dependency injection."""
    return None


async def get_execution_mode() -> str:
    """Provides execution mode (normal/mock) via dependency injection."""
    return "normal"


async def get_allowed_groups() -> list[str] | None:
    """Provides allowed groups for access control via dependency injection."""
    return None


AuthorizationDep = Annotated[str | None, Depends(get_authorization)]
ExecutionModeDep = Annotated[str, Depends(get_execution_mode)]
AllowedGroupsDep = Annotated[list[str] | None, Depends(get_allowed_groups)]

