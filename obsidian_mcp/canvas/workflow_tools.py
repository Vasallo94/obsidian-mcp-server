"""
Kanvas workflow MCP tools.

Provides task lifecycle management tools for project kanban boards
backed by .canvas files. Handles state transitions, dependency tracking,
and project initialization.
"""

from fastmcp import FastMCP

from ..tools.registry import register_tool
from ..utils import get_logger
from .workflow_tool_logic import (
    add_dependency,
    approve_task,
    complete_task,
    edit_task,
    finish_task,
    get_blocked_tasks,
    get_ready_tasks,
    get_status,
    init_project,
    pause_task,
    propose_group,
    propose_task,
    show_task,
    start_task,
)

logger = get_logger(__name__)


def register_workflow_tools(mcp: FastMCP) -> None:
    """Register kanvas workflow tools with the MCP server."""

    @register_tool(mcp, "kanvas_status")
    def kanvas_status(canvas_path: str) -> str:
        """Get a board overview: task counts by state, groups, total tasks.

        Args:
            canvas_path: Path to the .canvas project file

        Returns:
            Board summary with tasks grouped by state
        """
        try:
            return get_status(canvas_path).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error getting status: {e}"

    @register_tool(mcp, "kanvas_task")
    def kanvas_task(canvas_path: str, task_id: str) -> str:
        """Show details for a specific task: state, group, description, dependencies.

        Args:
            canvas_path: Path to the .canvas project file
            task_id: Task identifier (e.g. 'DEV-01')

        Returns:
            Task details
        """
        try:
            return show_task(canvas_path, task_id).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error showing task: {e}"

    @register_tool(mcp, "kanvas_ready")
    def kanvas_ready(canvas_path: str) -> str:
        """List tasks that are ready to start (red/To Do with all dependencies met).

        Args:
            canvas_path: Path to the .canvas project file

        Returns:
            List of ready tasks
        """
        try:
            return get_ready_tasks(canvas_path).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error getting ready tasks: {e}"

    @register_tool(mcp, "kanvas_blocked")
    def kanvas_blocked(canvas_path: str) -> str:
        """List tasks that are blocked and what is blocking them.

        Args:
            canvas_path: Path to the .canvas project file

        Returns:
            List of blocked tasks with their blockers
        """
        try:
            return get_blocked_tasks(canvas_path).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error getting blocked tasks: {e}"

    @register_tool(mcp, "kanvas_start")
    def kanvas_start(canvas_path: str, task_id: str) -> str:
        """Start a task: red (To Do) → orange (Doing). Validates dependencies are met.

        Args:
            canvas_path: Path to the .canvas project file
            task_id: Task identifier (e.g. 'DEV-01')

        Returns:
            Confirmation of state change
        """
        try:
            return start_task(canvas_path, task_id).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error starting task: {e}"

    @register_tool(mcp, "kanvas_finish")
    def kanvas_finish(canvas_path: str, task_id: str) -> str:
        """Finish a task: orange (Doing) → cyan (Review).

        Args:
            canvas_path: Path to the .canvas project file
            task_id: Task identifier

        Returns:
            Confirmation of state change
        """
        try:
            return finish_task(canvas_path, task_id).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error finishing task: {e}"

    @register_tool(mcp, "kanvas_pause")
    def kanvas_pause(canvas_path: str, task_id: str) -> str:
        """Pause a task: orange (Doing) → red (To Do).

        Args:
            canvas_path: Path to the .canvas project file
            task_id: Task identifier

        Returns:
            Confirmation of state change
        """
        try:
            return pause_task(canvas_path, task_id).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error pausing task: {e}"

    @register_tool(mcp, "kanvas_approve")
    def kanvas_approve(canvas_path: str, task_id: str) -> str:
        """Approve a proposed task: purple (Proposed) → red (To Do). RELAXED mode only.

        Args:
            canvas_path: Path to the .canvas project file
            task_id: Task identifier

        Returns:
            Confirmation of state change
        """
        try:
            return approve_task(canvas_path, task_id).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error approving task: {e}"

    @register_tool(mcp, "kanvas_complete")
    def kanvas_complete(canvas_path: str, task_id: str) -> str:
        """Mark a task as done: cyan (Review) → green (Done). RELAXED mode only.

        Args:
            canvas_path: Path to the .canvas project file
            task_id: Task identifier

        Returns:
            Confirmation of state change
        """
        try:
            return complete_task(canvas_path, task_id).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error completing task: {e}"

    @register_tool(mcp, "kanvas_edit_task")
    def kanvas_edit_task(canvas_path: str, task_id: str, text: str) -> str:
        """Update a task's description body. Task must be orange (or cyan in RELAXED mode).

        Args:
            canvas_path: Path to the .canvas project file
            task_id: Task identifier
            text: New description text (replaces the body below the title line)

        Returns:
            Confirmation of update
        """
        try:
            return edit_task(canvas_path, task_id, text).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error editing task: {e}"

    @register_tool(mcp, "kanvas_add_dependency")
    def kanvas_add_dependency(canvas_path: str, from_task: str, to_task: str) -> str:
        """Add a dependency: from_task blocks to_task. Rejects cycles.

        Args:
            canvas_path: Path to the .canvas project file
            from_task: Task ID that must complete first
            to_task: Task ID that depends on from_task

        Returns:
            Confirmation of dependency added
        """
        try:
            return add_dependency(canvas_path, from_task, to_task).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error adding dependency: {e}"

    @register_tool(mcp, "kanvas_propose_task")
    def kanvas_propose_task(
        canvas_path: str,
        group: str,
        title: str,
        description: str,
        depends_on: list[str] | None = None,
    ) -> str:
        """Propose a new task (creates purple card). Auto-assigns the next task ID.

        Args:
            canvas_path: Path to the .canvas project file
            group: Name of the group/phase to place the task in
            title: Short task title
            description: Task description body
            depends_on: List of task IDs this task depends on (optional)

        Returns:
            Confirmation with the new task ID
        """
        try:
            return propose_task(
                canvas_path, group, title, description, depends_on
            ).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error proposing task: {e}"

    @register_tool(mcp, "kanvas_propose_group")
    def kanvas_propose_group(canvas_path: str, label: str) -> str:
        """Add a new group/phase to the project canvas.

        Args:
            canvas_path: Path to the .canvas project file
            label: Group label text

        Returns:
            Confirmation of group creation
        """
        try:
            return propose_group(canvas_path, label).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error proposing group: {e}"

    @register_tool(mcp, "kanvas_init")
    def kanvas_init(
        canvas_path: str,
        groups: list[str],
        tasks: list[dict] | None = None,
        mode: str = "strict",
    ) -> str:
        """Initialize a new project canvas with groups, legend, and optional tasks.

        Args:
            canvas_path: Path for the new .canvas file (must not exist)
            groups: List of group/phase names (e.g. ['Planning', 'Development', 'Testing'])
            tasks: Optional list of task defs: {group, title, desc, depends_on: [titles]}
            mode: Workflow mode: 'strict' (default) or 'relaxed'

        Returns:
            Summary of what was created
        """
        try:
            return init_project(canvas_path, groups, tasks, mode).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error initializing project: {e}"
