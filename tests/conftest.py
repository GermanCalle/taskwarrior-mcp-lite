import os
import subprocess
from pathlib import Path

import pytest

from taskwarrior_mcp_lite import TaskWarrior


@pytest.fixture
def taskrc(tmp_path: Path) -> Path:
    data_dir = tmp_path / "task"
    data_dir.mkdir()
    rc = tmp_path / "taskrc"
    rc.write_text(f"data.location={data_dir}\nconfirmation=no\nhooks=off\n")

    # Taskwarrior 3.x aborts every command, export included, when it cannot find
    # default.theme, resolving the name against the process's CWD. The library
    # runs `task` from the taskrc's directory, so placing it here covers both.
    (tmp_path / "default.theme").touch()
    return rc


@pytest.fixture
def tw(taskrc: Path) -> TaskWarrior:
    return TaskWarrior(taskrc)


@pytest.fixture
def task_cli(taskrc: Path):
    def run(*args: str) -> str:
        # Taskwarrior 2.6.x segfaults outright when HOME is unset, before it ever
        # reads TASKRC, so the environment is inherited rather than built fresh.
        env = dict(os.environ, TASKRC=str(taskrc))
        proc = subprocess.run(
            ["task", "rc.verbose=nothing", "rc.confirmation=no", "rc.hooks=off", *args],
            env=env,
            cwd=str(taskrc.parent),
            capture_output=True,
            timeout=10,
            check=True,
        )
        return proc.stdout.decode()

    return run
