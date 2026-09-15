import os
from importlib.metadata import PackageNotFoundError, version
from typing import Literal

try:
    from mcp.server.mcpserver import MCPServer
    from mcp.server.mcpserver.exceptions import ToolError
    from mcp.types import ToolAnnotations
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "The MCP server needs the 'mcp' SDK, which is an optional extra. "
        "Install it with: pip install 'taskwarrior-mcp-lite[server]'"
    ) from exc

from taskwarrior_mcp_lite.core import TaskWarrior
from taskwarrior_mcp_lite.errors import TaskwarriorError

try:
    __version__ = version("taskwarrior-mcp-lite")
except PackageNotFoundError:
    __version__ = "0.0.0.dev0"

mcp = MCPServer(
    name="taskwarrior",
    version=__version__,
    instructions=(
        "Manage Taskwarrior tasks. Use list_tasks to find work, get_task for "
        "full detail on one task, and set_task_timer to start or pause. "
        "complete_task and delete_task need a UUID from list_tasks or get_task."
    ),
)

COMPACT_FIELDS = (
    "uuid",
    "id",
    "description",
    "status",
    "project",
    "tags",
    "due",
    "urgency",
    "start",
)

READ_ONLY = ToolAnnotations(read_only_hint=True)


def _client() -> TaskWarrior:
    return TaskWarrior(
        os.environ.get("TASKRC"),
        hooks=os.environ.get("TASKWARRIOR_MCP_HOOKS") == "1",
        timeout=float(os.environ.get("TASKWARRIOR_MCP_TIMEOUT", "10")),
    )


def _compact(task: dict) -> dict:
    return {k: task[k] for k in COMPACT_FIELDS if task.get(k) not in (None, [], "")}


@mcp.tool(annotations=READ_ONLY)
def list_tasks(
    status: Literal["pending", "completed", "deleted", "all"] = "pending",
    project: str | None = None,
    tags: list[str] | None = None,
    active: bool = False,
    search: str | None = None,
    limit: int = 50,
) -> dict:
    """List tasks, filtered. Returns compact records; use get_task for full detail."""
    limit = max(1, limit)
    filters = []
    if status != "all":
        filters.append(f"status:{status}")
    if project:
        filters.append(f"project:{project}")
    for tag in tags or []:
        filters.append(f"+{tag}")
    if search:
        filters.append(f"description.contains:{search}")

    try:
        tasks = _client().export(*filters)
    except (TaskwarriorError, ValueError) as exc:
        raise ToolError(str(exc)) from exc

    if active:
        tasks = [t for t in tasks if t.get("start")]

    return {
        "tasks": [_compact(t) for t in tasks[:limit]],
        "total": len(tasks),
        "truncated": len(tasks) > limit,
    }


@mcp.tool(annotations=READ_ONLY)
def get_task(ref: str) -> dict:
    """Get every field of one task, by short ID or UUID (prefix accepted)."""
    try:
        return _client().get(ref)
    except (TaskwarriorError, ValueError) as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool(annotations=READ_ONLY)
def list_projects() -> dict:
    """List project names with their pending and completed counts."""
    try:
        tasks = _client().export()
    except (TaskwarriorError, ValueError) as exc:
        raise ToolError(str(exc)) from exc

    counts: dict[str, dict[str, int]] = {}
    for task in tasks:
        name = task.get("project")
        if not name:
            continue
        entry = counts.setdefault(name, {"pending": 0, "completed": 0})
        if task["status"] in entry:
            entry[task["status"]] += 1

    return {"projects": [{"name": name, **entry} for name, entry in sorted(counts.items())]}


MUTATING = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True)
CREATING = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False)
DESTRUCTIVE = ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=True)


@mcp.tool(annotations=CREATING)
def add_task(
    description: str,
    project: str | None = None,
    tags: list[str] | None = None,
    priority: Literal["H", "M", "L"] | None = None,
    due: str | None = None,
) -> dict:
    """Create a task. `due` takes Taskwarrior date syntax, e.g. 'tomorrow' or '2026-09-30'."""
    try:
        return _client().add(description, project=project, tags=tags, priority=priority, due=due)
    except (TaskwarriorError, ValueError) as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool(annotations=MUTATING)
def update_task(
    ref: str,
    description: str | None = None,
    project: str | None = None,
    priority: Literal["H", "M", "L"] | None = None,
    due: str | None = None,
) -> dict:
    """Change fields on an existing task, by short ID or UUID. Only given fields change."""
    try:
        return _client().modify(
            ref, description=description, project=project, priority=priority, due=due
        )
    except (TaskwarriorError, ValueError) as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool(annotations=MUTATING)
def set_task_timer(ref: str, action: Literal["start", "stop"]) -> dict:
    """Start or pause the timer on a task, by short ID or UUID."""
    client = _client()
    try:
        return client.start(ref) if action == "start" else client.stop(ref)
    except (TaskwarriorError, ValueError) as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool(annotations=DESTRUCTIVE)
def complete_task(uuid: str) -> dict:
    """Mark a task done. Needs a UUID: short IDs are recycled and can point elsewhere."""
    client = _client()
    try:
        previous = client.get(uuid)["status"]
        return {"task": client.done(uuid), "previous_status": previous}
    except (TaskwarriorError, ValueError) as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool(annotations=DESTRUCTIVE)
def delete_task(uuid: str) -> dict:
    """Delete a task. Needs a UUID: short IDs are recycled and can point elsewhere."""
    client = _client()
    try:
        previous = client.get(uuid)["status"]
        return {"task": client.delete(uuid), "previous_status": previous}
    except (TaskwarriorError, ValueError) as exc:
        raise ToolError(str(exc)) from exc


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
