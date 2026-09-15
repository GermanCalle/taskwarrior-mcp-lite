# taskwarrior-mcp-lite

An MCP server that exposes [Taskwarrior](https://taskwarrior.org/) through 8
tools, plus `taskwarrior_mcp_lite.core` — a `TaskWarrior` class with **zero runtime
dependencies** (standard library only) that any Python project can import
directly, no MCP required.

## Install

Taskwarrior itself is a prerequisite — this package drives the `task` binary and
does not bundle it. Any release from 2.6 onwards works (`apt install taskwarrior`,
`pacman -S task`, `brew install task`); see [Compatibility](#compatibility).

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

The full test suite passes against Taskwarrior 2.6.2, 3.0.2, 3.1.0, 3.2.0,
3.3.0, 3.4.2 and 3.5.0 — the latest patch of every minor release from 2.6
onwards, each built from its official release tarball. This spans the 3.0
switch from flat files to SQLite, which the library is unaffected by: it only
ever talks to `task` over a subprocess and parses its JSON.

That matrix was run on Python 3.12. CI covers Python 3.12–3.14 against
Taskwarrior 2.6.x and 3.5.x.

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

## Using the Claude Code plugin

This repository is also a Claude Code plugin, which registers the MCP server and
installs a skill describing how to drive its tools. It ships its own marketplace
manifest, so installing points Claude Code straight at this repository — there is
no external registry in between:

```
/plugin marketplace add GermanCalle/taskwarrior-mcp-lite
/plugin install taskwarrior-mcp-lite@taskwarrior-mcp-lite
```

The plugin launches the server through `uvx` from PyPI, so there is nothing to
install by hand and no `claude mcp add` to run. It leaves `TASKRC` unset, which
means Taskwarrior reads your own `~/.taskrc`.

## Using the MCP server

For any other MCP client, register it directly:

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

That block is the same everywhere; only the file it goes in changes:

| Client | File |
|---|---|
| Claude Desktop | `claude_desktop_config.json` (Settings → Developer → Edit Config) |
| Cursor | `.cursor/mcp.json` in the project, or `~/.cursor/mcp.json` globally |
| VS Code (Copilot) | `.vscode/mcp.json` in the project |
| Claude Code (manual) | `.mcp.json` in the project, or `claude mcp add` for a user-wide server |

Zed reads the same command under a `context_servers` key in its `settings.json`
rather than `mcpServers`. Windsurf, Cline and other clients each have their own
path, but all of them launch the server the same way: a stdio process started
with that `command` and `args`.

Setting `TASKRC` is optional. Left unset, Taskwarrior falls back to its own
default of `~/.taskrc`.

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
