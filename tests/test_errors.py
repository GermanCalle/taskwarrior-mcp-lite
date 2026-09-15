from taskwarrior_mcp_lite.errors import (
    TaskNotFound,
    TaskwarriorCommandError,
    TaskwarriorError,
    TaskwarriorNotFound,
    TaskwarriorThemeMissing,
    TaskwarriorTimeout,
)


def test_all_errors_share_a_base():
    errors = [
        TaskwarriorNotFound(),
        TaskwarriorCommandError(["task", "export"], 1, "boom"),
        TaskNotFound("42"),
        TaskwarriorTimeout(["task", "export"], 10.0),
        TaskwarriorThemeMissing(),
    ]

    assert all(isinstance(error, TaskwarriorError) for error in errors)


def test_not_found_explains_how_to_install():
    message = str(TaskwarriorNotFound())

    assert "not found on PATH" in message
    assert "apt install taskwarrior" in message


def test_command_error_keeps_diagnostics():
    error = TaskwarriorCommandError(["task", "export"], 3, "  bad filter\n")

    assert error.cmd == ["task", "export"]
    assert error.returncode == 3
    assert error.stderr == "  bad filter\n"
    assert "task export" in str(error)
    assert "bad filter" in str(error)


def test_task_not_found_names_the_reference():
    error = TaskNotFound("deadbeef")

    assert error.ref == "deadbeef"
    assert "deadbeef" in str(error)


def test_theme_missing_is_actionable():
    message = str(TaskwarriorThemeMissing())

    assert "default.theme" in message
    assert ".taskrc" in message
