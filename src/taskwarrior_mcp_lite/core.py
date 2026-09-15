import json
import os
import re
import subprocess
from pathlib import Path

from taskwarrior_mcp_lite.errors import (
    TaskNotFound,
    TaskwarriorCommandError,
    TaskwarriorNotFound,
    TaskwarriorThemeMissing,
    TaskwarriorTimeout,
)

_THEME_MARKER = "default.theme"
_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def _check_for_missing_theme(returncode: int, stdout: str, stderr: str) -> None:
    # Task content (e.g. a description mentioning "default.theme") can put the
    # marker in stdout on a successful run, so the marker alone is not enough
    # signal — only a failing process indicates a genuine missing-theme abort.
    # Some Taskwarrior 3.x builds report it on stdout rather than stderr, so
    # both streams are still checked once returncode confirms real failure.
    if returncode != 0 and (_THEME_MARKER in stderr or _THEME_MARKER in stdout):
        raise TaskwarriorThemeMissing()


class TaskWarrior:
    def __init__(self, taskrc=None, *, hooks: bool = False, timeout: float = 10.0) -> None:
        self.taskrc = str(Path(taskrc).expanduser()) if taskrc else None
        self.hooks = hooks
        self.timeout = timeout

    def _cwd(self):
        # Taskwarrior 3.x resolves default.theme against the process's CWD,
        # not the taskrc's directory, despite what its own error message says
        # ("directory of config file" does not actually work). Running with
        # cwd=taskrc's directory keeps callers free to invoke us from anywhere.
        return str(Path(self.taskrc).parent) if self.taskrc else None

    def _argv(self, filters, command, args):
        overrides = ["rc.verbose=nothing", "rc.confirmation=no"]
        if not self.hooks:
            overrides.append("rc.hooks=off")
        return ["task", *overrides, *filters, command, *args]

    @staticmethod
    def _reject_rc_overrides(values):
        for value in values:
            if str(value).startswith("rc."):
                raise ValueError(
                    f"Refusing to pass {value!r}: rc. overrides would reconfigure "
                    "Taskwarrior for this invocation."
                )

    def _run(self, *, filters=(), command, args=()):
        self._reject_rc_overrides(filters)
        self._reject_rc_overrides(args)
        argv = self._argv([str(f) for f in filters], command, [str(a) for a in args])

        env = dict(os.environ)
        if self.taskrc:
            env["TASKRC"] = self.taskrc

        try:
            proc = subprocess.run(
                argv,
                env=env,
                cwd=self._cwd(),
                capture_output=True,
                timeout=self.timeout,
                check=False,
            )
        except FileNotFoundError:
            raise TaskwarriorNotFound() from None
        except subprocess.TimeoutExpired:
            raise TaskwarriorTimeout(argv, self.timeout) from None

        stdout = proc.stdout.decode("utf-8", errors="replace")
        stderr = proc.stderr.decode("utf-8", errors="replace")

        _check_for_missing_theme(proc.returncode, stdout, stderr)
        if proc.returncode != 0:
            raise TaskwarriorCommandError(argv, proc.returncode, stderr)
        return stdout

    def export(self, *filters) -> list[dict]:
        stdout = self._run(filters=filters, command="export").strip()
        return json.loads(stdout) if stdout else []

    @staticmethod
    def _attrs_to_args(attrs):
        args = []
        for key, value in attrs.items():
            if value is None:
                continue
            if key == "tags":
                args.extend(f"+{tag}" for tag in value)
            else:
                args.append(f"{key}:{value}")
        return args

    @staticmethod
    def _require_uuid(uuid):
        text = str(uuid)
        if not re.fullmatch(r"[0-9a-f]{8}[0-9a-f-]{0,28}", text):
            raise ValueError(
                f"{text!r} is not a UUID. Destructive operations require a UUID "
                "because Taskwarrior recycles short IDs when tasks complete."
            )
        return text

    def get(self, ref) -> dict:
        tasks = self.export(str(ref))
        if not tasks:
            raise TaskNotFound(str(ref))
        return tasks[0]

    def _resolve_exactly_one(self, ref) -> dict:
        tasks = self.export(str(ref))
        if not tasks:
            raise TaskNotFound(str(ref))
        if len(tasks) > 1:
            raise ValueError(
                f"{str(ref)!r} matches {len(tasks)} tasks; refusing to act on one "
                "of several matches. Use a full UUID to identify a single task."
            )
        return tasks[0]

    def add(self, description: str, **attrs) -> dict:
        overrides = ["rc.verbose=new-uuid", "rc.confirmation=no"]
        if not self.hooks:
            overrides.append("rc.hooks=off")
        args = self._attrs_to_args(attrs)
        self._reject_rc_overrides([description])
        self._reject_rc_overrides(args)

        env = dict(os.environ)
        if self.taskrc:
            env["TASKRC"] = self.taskrc
        argv = ["task", *overrides, "add", description, *args]

        try:
            proc = subprocess.run(
                argv,
                env=env,
                cwd=self._cwd(),
                capture_output=True,
                timeout=self.timeout,
                check=False,
            )
        except FileNotFoundError:
            raise TaskwarriorNotFound() from None
        except subprocess.TimeoutExpired:
            raise TaskwarriorTimeout(argv, self.timeout) from None

        stdout = proc.stdout.decode("utf-8", errors="replace")
        stderr = proc.stderr.decode("utf-8", errors="replace")
        _check_for_missing_theme(proc.returncode, stdout, stderr)
        if proc.returncode != 0:
            raise TaskwarriorCommandError(argv, proc.returncode, stderr)

        match = _UUID_RE.search(stdout)
        if not match:
            raise TaskwarriorCommandError(argv, proc.returncode, stdout)
        return self.get(match.group(0))

    def modify(self, ref, **attrs) -> dict:
        task = self.get(ref)
        args = self._attrs_to_args(attrs)
        self._run(filters=[task["uuid"]], command="modify", args=args)
        return self.get(task["uuid"])

    def start(self, ref) -> dict:
        task = self.get(ref)
        self._run(filters=[task["uuid"]], command="start")
        return self.get(task["uuid"])

    def stop(self, ref) -> dict:
        task = self.get(ref)
        self._run(filters=[task["uuid"]], command="stop")
        return self.get(task["uuid"])

    def done(self, uuid) -> dict:
        checked = self._require_uuid(uuid)
        task = self._resolve_exactly_one(checked)
        self._run(filters=[task["uuid"]], command="done")
        return self.get(task["uuid"])

    def delete(self, uuid) -> dict:
        checked = self._require_uuid(uuid)
        task = self._resolve_exactly_one(checked)
        self._run(filters=[task["uuid"]], command="delete")
        return self.get(task["uuid"])

    def projects(self) -> list[str]:
        names = {task["project"] for task in self.export() if task.get("project")}
        return sorted(names)

    @staticmethod
    def version() -> str:
        try:
            proc = subprocess.run(
                ["task", "--version"], capture_output=True, timeout=10, check=False
            )
        except FileNotFoundError:
            raise TaskwarriorNotFound() from None
        return proc.stdout.decode("utf-8", errors="replace").strip()
