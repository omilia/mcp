"""
Tool decorator factories for MCP tools.

Provides extensible decorators that handle lifecycle callbacks (before/after/override).
Dependencies (Authorization, execution_mode, allowed_groups) should be injected
using Depends() - see dependencies.py
"""

from __future__ import annotations

import inspect
from typing import Awaitable, Callable, ParamSpec, TypeVar

from fastmcp import FastMCP

P = ParamSpec("P")
T = TypeVar("T")

BeforeCallback = Callable[..., Awaitable[None]]
AfterCallback = Callable[..., Awaitable[None]]
OverrideCallback = Callable[P, Awaitable[T]]


class ToolWrapper:
    """
    Wrapper that holds a tool function and its registered callbacks.

    Supports:
        - before: Pre-execution hook (receives all original args)
        - after: Post-execution hook (receives all original args + result)
        - override: Replaces execution when execution_mode="mock"
    """

    def __init__(self, func: Callable[P, Awaitable[T]]):
        self._func = func
        self._before: BeforeCallback | None = None
        self._after: AfterCallback | None = None
        self._override: OverrideCallback | None = None
        self._wrapped_func: Callable | None = None

    def _create_wrapped_function(self) -> Callable:
        """Create the actual wrapped function that will be registered with MCP."""
        func = self._func
        sig = inspect.signature(func)

        async def wrapped(**kwargs):
            execution_mode = kwargs.pop("execution_mode", "normal")

            if execution_mode == "mock" and self._override:
                return await self._override(**kwargs)

            if self._before:
                await self._before(**kwargs)

            result = await func(**kwargs)

            if self._after:
                await self._after(result=result, **kwargs)

            return result

        wrapped.__name__ = func.__name__
        wrapped.__doc__ = func.__doc__
        wrapped.__module__ = func.__module__
        wrapped.__qualname__ = func.__qualname__
        wrapped.__annotations__ = func.__annotations__
        wrapped.__signature__ = sig

        return wrapped

    async def __call__(self, **kwargs):
        """Make ToolWrapper callable for direct invocation (e.g., in tests)."""
        wrapped = self._create_wrapped_function()
        return await wrapped(**kwargs)

    def before(self, callback: BeforeCallback) -> BeforeCallback:
        """
        Register a callback to run before tool execution.

        The callback receives all original function arguments.

        Example:
            @my_tool.before
            async def log_call(data: str, **kwargs):
                logger.info(f"Calling with {data}")
        """
        self._before = callback
        return callback

    def after(self, callback: AfterCallback) -> AfterCallback:
        """
        Register a callback to run after tool execution.

        The callback receives all original function arguments plus `result`.

        Example:
            @my_tool.after
            async def log_result(data: str, result: dict = None, **kwargs):
                logger.info(f"Result: {result}")
        """
        self._after = callback
        return callback

    def override(self, callback: OverrideCallback) -> OverrideCallback:
        """
        Register a callback to replace execution when execution_mode="mock".

        The callback receives all original function arguments and should
        return a value matching the original function's return type.

        Example:
            @my_tool.override
            async def mock_response(data: str, **kwargs) -> dict:
                return {"mock": True, "data": data}
        """
        self._override = callback
        return callback


def tool_with_callbacks(mcp_instance: FastMCP):
    """
    Tool decorator factory that returns a ToolWrapper enabling callback hooks.

    Provides callback registration:
        - .before() - runs before execution
        - .after() - runs after execution (receives result)
        - .override() - replaces execution when execution_mode="mock"

    Dependencies (Authorization, execution_mode, allowed_groups) should be
    injected using Depends() from dependencies.py

    Usage:
        from dependencies import AuthorizationDep, ExecutionModeDep

        tool = tool_with_callbacks(mcp)

        @tool(tags=["example"])
        async def my_tool(
            data: str,
            Authorization: AuthorizationDep,
            execution_mode: ExecutionModeDep,
        ) -> dict:
            return {"data": data}

        @my_tool.before
        async def log_call(data: str, **kwargs):
            logger.info(f"Calling with {data}")

        @my_tool.override
        async def mock_response(data: str, **kwargs) -> dict:
            return {"mock": True}
    """

    def decorator(tags: list[str] | None = None, **kwargs):
        def wrapper(func: Callable[P, Awaitable[T]]) -> ToolWrapper:
            tool_wrapper = ToolWrapper(func)
            wrapped_func = tool_wrapper._create_wrapped_function()
            mcp_instance.tool(tags=tags, **kwargs)(wrapped_func)
            return tool_wrapper

        return wrapper

    return decorator
