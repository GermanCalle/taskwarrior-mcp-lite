import asyncio

import pytest

from taskwarrior_mcp_lite import server


def _tools_by_name():
    return {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}


@pytest.fixture
def tools(taskrc, monkeypatch):
    # The tools build their own client per call from the environment, so pointing
    # TASKRC at the fixture database is what isolates them from the real one.
    monkeypatch.setenv("TASKRC", str(taskrc))
    return server


def test_the_server_exposes_exactly_eight_tools(tools):
    names = {
        "list_tasks",
        "get_task",
        "list_projects",
        "add_task",
        "update_task",
        "set_task_timer",
        "complete_task",
        "delete_task",
    }

    assert set(_tools_by_name()) == names


def test_read_tools_are_annotated_read_only(tools):
    by_name = _tools_by_name()

    for name in ("list_tasks", "get_task", "list_projects"):
        assert by_name[name].annotations.read_only_hint is True


def test_status_is_an_enum_in_the_schema(tools):
    status = _tools_by_name()["list_tasks"].input_schema["properties"]["status"]

    assert status["enum"] == ["pending", "completed", "deleted", "all"]


def test_list_tasks_is_empty_on_a_fresh_database(tools):
    assert tools.list_tasks() == {"tasks": [], "total": 0, "truncated": False}


def test_list_tasks_returns_compact_fields_only(tools, task_cli):
    task_cli("add", "compact me", "project:alpha")

    (task,) = tools.list_tasks()["tasks"]

    assert set(task) <= set(server.COMPACT_FIELDS)
    assert "entry" not in task


def test_list_tasks_filters_by_project(tools, task_cli):
    task_cli("add", "in scope", "project:alpha")
    task_cli("add", "out of scope", "project:beta")

    result = tools.list_tasks(project="alpha")

    assert [task["description"] for task in result["tasks"]] == ["in scope"]


def test_list_tasks_reports_truncation(tools, task_cli):
    for index in range(3):
        task_cli("add", f"task {index}")

    result = tools.list_tasks(limit=2)

    assert len(result["tasks"]) == 2
    assert result["total"] == 3
    assert result["truncated"] is True


def test_list_tasks_clamps_a_zero_limit_to_one(tools, task_cli):
    task_cli("add", "only one")
    task_cli("add", "and another")

    assert len(tools.list_tasks(limit=0)["tasks"]) == 1


def test_list_tasks_clamps_a_negative_limit_to_one(tools, task_cli):
    task_cli("add", "only one")
    task_cli("add", "and another")

    assert len(tools.list_tasks(limit=-5)["tasks"]) == 1


def test_get_task_returns_the_full_record(tools, task_cli):
    task_cli("add", "detailed", "project:alpha")

    task = tools.get_task("1")

    assert task["description"] == "detailed"
    assert "entry" in task


def test_get_task_accepts_a_short_id(tools, task_cli):
    task_cli("add", "by short id")

    assert tools.get_task("1")["description"] == "by short id"


def test_list_projects_lists_names_with_counts(tools, task_cli):
    task_cli("add", "pending one", "project:alpha")
    task_cli("add", "done one", "project:alpha")
    task_cli("2", "done")
    task_cli("add", "other", "project:beta")

    projects = tools.list_projects()["projects"]

    assert projects == [
        {"name": "alpha", "pending": 1, "completed": 1},
        {"name": "beta", "pending": 1, "completed": 0},
    ]
