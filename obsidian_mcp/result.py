"""
Result type for consistent return values across the codebase.

This module provides a generic Result type that can be used to wrap
function return values, indicating success or failure along with
data or error information.

Usage:
    from obsidian_mcp.result import Result

    def my_function() -> Result[str]:
        if something_wrong:
            return Result.fail("Something went wrong")
        return Result.ok("Success data")

    # Consumer:
    result = my_function()
    if result.success:
        print(result.data)
    else:
        print(f"Error: {result.error}")
"""

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Result(Generic[T]):
    """
    A generic result type for operations that can succeed or fail.

    Attributes:
        success: Whether the operation succeeded.
        data: The result data if successful, None otherwise.
        error: The error message if failed, None otherwise.
    """

    success: bool
    data: T | None = None
    error: str | None = None

    @classmethod
    def ok(cls, data: T) -> "Result[T]":
        """Create a successful result with data.

        Args:
            data: The success data to wrap.

        Returns:
            A Result instance with success=True and the provided data.
        """
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, error: str) -> "Result[T]":
        """Create a failed result with an error message.

        Args:
            error: The error message describing what went wrong.

        Returns:
            A Result instance with success=False and the provided error.
        """
        return cls(success=False, error=error)

    def __bool__(self) -> bool:
        """Allow using Result in boolean context (truthy if successful)."""
        return self.success

    def unwrap(self) -> T:
        """Get the data, raising ValueError if the result is a failure.

        Returns:
            The wrapped data.

        Raises:
            ValueError: If the result is a failure.
        """
        if not self.success:
            raise ValueError(f"Cannot unwrap failed Result: {self.error}")
        return self.data  # type: ignore[return-value]

    def unwrap_or(self, default: T) -> T:
        """Get the data or a default value if the result is a failure.

        Args:
            default: The default value to return if failed.

        Returns:
            The wrapped data if successful, otherwise the default.
        """
        if self.success and self.data is not None:
            return self.data
        return default

    def map_error(self, prefix: str = "❌") -> str:
        """Format the error for display with an optional prefix.

        Args:
            prefix: The prefix to add before the error message.

        Returns:
            Formatted error string, or empty string if successful.
        """
        if self.success or not self.error:
            return ""
        return f"{prefix} {self.error}"

    def to_display(self, error_prefix: str = "❌", success_prefix: str = "") -> str:
        """Convert result to display string (data on success, error on failure).

        This method is type-safe and always returns str, making it suitable
        for MCP tool return values.

        Args:
            error_prefix: Prefix to add before error messages.
            success_prefix: Prefix to add before success data (e.g., "✅").

        Returns:
            The data as string if successful, formatted error otherwise.
        """
        if self.success and self.data is not None:
            if success_prefix:
                return f"{success_prefix} {self.data}"
            return str(self.data)
        return f"{error_prefix} {self.error or 'Unknown error'}"
