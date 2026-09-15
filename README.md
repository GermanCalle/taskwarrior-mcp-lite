# taskwarrior-mcp-lite

An MCP server that exposes [Taskwarrior](https://taskwarrior.org/) through 8
tools, plus `taskwarrior_mcp_lite.core` — a `TaskWarrior` class with **zero runtime
dependencies** (standard library only) that any Python project can import
directly, no MCP required.

## Install

To run the MCP server:

```bash
pip install "taskwarrior-mcp-lite[server]"
```

The `[server]` suffix pulls in the `mcp` SDK and its transitive dependencies
(pydantic, httpx and around 25 others). Most MCP clients launch the server
through `uvx`, which resolves the extra for you — see
[Using the MCP server](#using-the-mcp-server) below, where you don't install
anything by hand at all.

The server requires **`mcp` 2.0 or newer** and will not install alongside a
package that pins `mcp<2`. See [MCP SDK version](#mcp-sdk-version).

To use only the Python library, with no MCP server:

```bash
pip install taskwarrior-mcp-lite
```

That installs exactly one package and **no dependencies at all** — the core is
standard library only. Keeping the SDK behind an extra means importing
`TaskWarrior` never adds pydantic, httpx or a version constraint to your
project. See [Using the core library directly](#using-the-core-library-directly).

## Compatibility

Verified against Taskwarrior 2.6.x and 3.5.x on Python 3.12–3.14. Taskwarrior
versions 3.0–3.4 are untested.

### MCP SDK version

The `[server]` extra requires `mcp>=2.0,<3`. The lower bound is not negotiable:
the server is built on `mcp.server.mcpserver.MCPServer`, which does not exist in
the 1.x series — that line only ships `FastMCP`.

Because the 1.x and 2.x series overlapped, much of the MCP ecosystem still pins
`mcp<2`. Installing this package into an environment that already holds such a
package fails to resolve:

```
× No solution found when resolving dependencies
```

There is no version range that avoids this — it follows from the SDK's own
split. If you hit it, run the server through `uvx` as shown below, which gives
it an isolated environment and leaves your project's own `mcp` pin untouched.

The core library is unaffected: it has no dependencies and never imports `mcp`.

### Taskwarrior 3.x and `default.theme`


Taskwarrior 3.x aborts every command — including `export` — if it can't find
a file named `default.theme`. It looks for that file relative to the
process's current working directory, not the taskrc's directory, regardless
of what its own error message implies. This package works around it by
running `task` with its working directory set to the taskrc's directory, so
this normally isn't something you need to think about.

If you still see an error like:

```
Could not find file in CWD, directory of config file or search paths 'default.theme'
```

create an empty file named `default.theme` next to your `.taskrc`.

## Using the MCP server

Register it with your MCP client:

```json
{
  "mcpServers": {
    "taskwarrior": {
      "command": "uvx",
      "args": ["--from", "taskwarrior-mcp-lite[server]", "taskwarrior-mcp-lite"],
      "env": { "TASKRC": "/home/you/.taskrc" }
    }
  }
}
```

### Tools

| Tool | Destructive | Description |
|---|---|---|
| `list_tasks` | no | List tasks with typed filters (status, project, tags, active, search, limit) |
| `get_task` | no | Fetch one task with every field, by short ID or UUID |
| `add_task` | no | Create a task |
| `update_task` | no | Change fields on a task; only the fields you give are modified |
| `set_task_timer` | no | Start or pause the timer on a task (single tool, `action` parameter) |
| `complete_task` | **yes** | Mark a task done — requires a UUID |
| `delete_task` | **yes** | Delete a task — requires a UUID |
| `list_projects` | no | List project names with pending/completed task counts |

`complete_task` and `delete_task` require a UUID rather than a short ID.
Taskwarrior recycles short IDs as tasks complete, so an ID like `3` can point
at a different task a minute later. Requiring a UUID means an agent cannot
delete or complete the wrong task after the list it was working from went
stale. Resolve the UUID first with `list_tasks` or `get_task`.

## Using the core library directly

`taskwarrior_mcp_lite.core.TaskWarrior` has no runtime dependencies — it shells
out to the `task` binary and parses its output with the standard library
only. A backend or script can import it without pulling in the MCP SDK:

```python
from taskwarrior_mcp_lite import TaskWarrior

tw = TaskWarrior("~/.taskrc")
for task in tw.export("status:pending"):
    print(task["description"])
```

## Configuration

Environment variables:

| Variable | Purpose |
|---|---|
| `TASKRC` | Path to the taskrc file to use |
| `TASKDATA` | Path to the Taskwarrior data directory |
| `TASKWARRIOR_MCP_HOOKS` | Set to `1` to allow Taskwarrior hooks to run (default: off) |
| `TASKWARRIOR_MCP_TIMEOUT` | Timeout in seconds for `task` invocations (default: `10`) |

## License

MIT
