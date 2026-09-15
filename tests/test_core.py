import os

import pytest

from taskwarrior_mcp_lite import TaskWarrior
from taskwarrior_mcp_lite.errors import (
    TaskwarriorCommandError,
    TaskwarriorNotFound,
    TaskwarriorThemeMissing,
    TaskwarriorTimeout,
)


def test_export_is_empty_on_a_fresh_database(tw):
    assert tw.export() == []


def test_export_returns_dicts(tw, task_cli):
    task_cli("add", "write the docs")

    (task,) = tw.export()

    assert task["description"] == "write the docs"
    assert task["status"] == "pending"
    assert "uuid" in task


def test_export_accepts_native_filters(tw, task_cli):
    task_cli("add", "in scope", "project:alpha")
    task_cli("add", "out of scope", "project:beta")

    descriptions = [task["description"] for task in tw.export("project:alpha")]

    assert descriptions == ["in scope"]


def test_export_includes_deleted_tasks(tw, task_cli):
    task_cli("add", "doomed")
    task_cli("1", "delete")

    statuses = [task["status"] for task in tw.export("status:deleted")]

    assert statuses == ["deleted"]


def test_unicode_and_control_characters_survive(tw, task_cli):
    description = "reunión — café\tdespués"
    task_cli("add", description)

    (task,) = tw.export()

    assert task["description"] == description


def test_a_filter_containing_a_semicolon_does_not_reach_a_shell(tw, task_cli):
    task_cli("add", "still here")

    with pytest.raises(TaskwarriorCommandError):
        tw.export("; rm -rf /")

    assert len(tw.export()) == 1


def test_rc_overrides_are_rejected(tw):
    with pytest.raises(ValueError, match="rc\\."):
        tw.export("rc.data.location=/tmp/elsewhere")


def test_works_regardless_of_the_caller_s_current_directory(tw, task_cli, tmp_path, monkeypatch):
    task_cli("add", "findable from anywhere")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    assert len(tw.export()) == 1


def test_command_failure_carries_stderr(tw):
    with pytest.raises(TaskwarriorCommandError) as excinfo:
        tw.export("(((")

    assert excinfo.value.returncode != 0
    assert excinfo.value.cmd[0] == "task"


def test_missing_binary_raises_a_clear_error(tw, monkeypatch):
    monkeypatch.setenv("PATH", "/nonexistent")

    with pytest.raises(TaskwarriorNotFound):
        TaskWarrior.version()


def test_a_slow_task_binary_raises_timeout(taskrc, tmp_path, monkeypatch):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    slow_task = fake_bin / "task"
    slow_task.write_text("#!/bin/sh\nsleep 30\n")
    slow_task.chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake_bin}:{os.environ['PATH']}")

    with pytest.raises(TaskwarriorTimeout):
        TaskWarrior(taskrc, timeout=0.2).export()


def test_a_real_missing_theme_failure_raises_theme_missing(taskrc, tmp_path, monkeypatch):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    failing_task = fake_bin / "task"
    failing_task.write_text(
        "#!/bin/sh\n"
        'echo "Could not find file in CWD, directory of config file or "\n'
        "echo \"search paths 'default.theme'\" >&2\n"
        "exit 1\n"
    )
    failing_task.chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake_bin}:{os.environ['PATH']}")

    with pytest.raises(TaskwarriorThemeMissing):
        TaskWarrior(taskrc).export()


def test_a_task_description_mentioning_the_theme_file_does_not_break_export(tw, task_cli):
    task_cli("add", "regenerate default.theme")

    (task,) = tw.export()

    assert task["description"] == "regenerate default.theme"


def test_version_reports_the_installed_binary():
    assert TaskWarrior.version()
