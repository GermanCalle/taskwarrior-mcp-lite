---
name: taskwarrior
description: Use when managing Taskwarrior tasks — listing, creating, updating, starting/pausing, completing, or deleting tasks and browsing projects.
---

# Taskwarrior

Use `list_tasks` to find work before acting: it returns compact records with
the `uuid` the destructive tools require.

- Filter with the typed parameters (`status`, `project`, `tags`, `active`,
  `search`), not raw Taskwarrior syntax.
- `get_task` returns every field Taskwarrior has for that task — including
  annotations and dependencies when it has them — while `list_tasks` returns
  a compact subset. Use `get_task` when you need detail on one task.
- `complete_task` and `delete_task` require a UUID. Short IDs are recycled
  when tasks complete, so an ID can point at a different task than the user
  saw. Always resolve the UUID with `list_tasks` first.
- `set_task_timer` starts or pauses one task. Taskwarrior allows several
  tasks to be running at once; use `list_tasks` with `active: true` to see
  which ones are, and stop them explicitly rather than assuming a start
  stops whatever was running before.
- If a call reports a missing `default.theme`, the user is on Taskwarrior 3.x
  without theme files: creating an empty `default.theme` next to their
  `.taskrc` fixes it.
- Taskwarrior reads `~/.taskrc` by default. If a call reports that no
  configuration file could be found, or the tasks returned are not the ones the
  user expects, they can point the server at a specific one by setting `TASKRC`
  in their MCP client configuration.
