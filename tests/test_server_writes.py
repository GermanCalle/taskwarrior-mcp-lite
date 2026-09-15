import asyncio

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from taskwarrior_mcp_lite import server


def _tools_by_name():
    return {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}


@pytest.fixture
def tools(taskrc, monkeypatch):
    monkeypatch.setenv("TASKRC", str(taskrc))
    return server


def test_write_tools_are_not_marked_read_only():
    by_name = _tools_by_name()

    for name in ("add_task", "update_task", "set_task_timer"):
        assert by_name[name].annotations.read_only_hint is False


def test_destructive_tools_are_annotated():
    by_name = _tools_by_name()

    for name in ("complete_task", "delete_task"):
        assert by_name[name].annotations.destructive_hint is True


def test_add_task_creates_and_returns_it(tools):
    task = tools.add_task("buy milk", project="home", tags=["errand"])

    assert task["description"] == "buy milk"
    assert task["project"] == "home"
    assert task["tags"] == ["errand"]


def test_add_task_rejects_a_description_starting_with_rc(tools):
    with pytest.raises(ToolError, match="rc\\."):
        tools.add_task("rc.data.location=/tmp/elsewhere")


def test_update_task_changes_a_field(tools):
    created = tools.add_task("original", project="alpha")

    updated = tools.update_task(created["uuid"], description="renamed")

    assert updated["description"] == "renamed"
    assert updated["project"] == "alpha"


def test_set_task_timer_starts_and_stops(tools):
    created = tools.add_task("timed")

    assert tools.set_task_timer(created["uuid"], "start").get("start")
    assert not tools.set_task_timer(created["uuid"], "stop").get("start")


def test_complete_task_reports_before_and_after(tools):
    created = tools.add_task("finish me")

    result = tools.complete_task(created["uuid"])

    assert result["previous_status"] == "pending"
    assert result["task"]["status"] == "completed"


def test_delete_task_reports_before_and_after(tools):
    created = tools.add_task("remove me")

    result = tools.delete_task(created["uuid"])

    assert result["previous_status"] == "pending"
    assert result["task"]["status"] == "deleted"


def test_complete_task_refuses_a_short_id(tools):
    tools.add_task("some task")

    with pytest.raises(ToolError, match="not a UUID"):
        tools.complete_task("1")


def test_delete_task_refuses_a_short_id(tools):
    tools.add_task("some task")

    with pytest.raises(ToolError, match="not a UUID"):
        tools.delete_task("1")


def test_delete_task_refuses_a_wildcard_that_would_match_every_task(tools):
    tools.add_task("innocent bystander")

    with pytest.raises(ToolError):
        tools.delete_task("--------")

    assert tools.list_tasks()["total"] == 1


def test_unknown_reference_gives_a_readable_error(tools):
    with pytest.raises(ToolError, match="No task matches"):
        tools.get_task("99999")
