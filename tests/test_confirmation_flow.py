"""Tests for elicit-based confirmation flow.

Issue #1: cancellation must surface a specific reason instead of opaque
"Operation cancelled.", and the unsupported-client path must be distinct
from the user-declined / user-dismissed paths.
"""

from obsidian_mcp.messages import ERRORS
from obsidian_mcp.tools.creation import _cancellation_reason


class TestCancellationReason:
    def test_decline_returns_explicit_rejection_message(self):
        msg = _cancellation_reason("decline")
        assert msg == ERRORS.OPERATION_DECLINED
        assert "rechazo" in msg

    def test_cancel_returns_dismissed_message(self):
        msg = _cancellation_reason("cancel")
        assert msg == ERRORS.OPERATION_DISMISSED
        assert "cerro" in msg

    def test_unknown_action_falls_back_to_decline(self):
        msg = _cancellation_reason("weirdo_value")
        assert msg == ERRORS.OPERATION_DECLINED

    def test_messages_are_all_in_spanish(self):
        """Issue #13: no English in confirmation errors."""
        for msg in (
            ERRORS.OPERATION_DECLINED,
            ERRORS.OPERATION_DISMISSED,
            ERRORS.OPERATION_CANCELLED_NO_CONFIRM,
        ):
            assert "cancelled" not in msg.lower()
            assert "operation" not in msg.lower()

    def test_unsupported_host_message_hints_at_workaround(self):
        """Agents should know they can fall back to preview_replace_in_notes."""
        assert "preview_replace_in_notes" in ERRORS.OPERATION_CANCELLED_NO_CONFIRM
