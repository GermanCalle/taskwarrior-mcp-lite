class TaskwarriorError(Exception):
    pass


class TaskwarriorNotFound(TaskwarriorError):
    def __init__(self) -> None:
        super().__init__(
            "The 'task' command-line tool was not found on PATH. "
            "Install Taskwarrior 2.6.x or 3.5.x "
            "(Debian/Ubuntu: apt install taskwarrior; Arch: pacman -S task)."
        )


class TaskwarriorCommandError(TaskwarriorError):
    def __init__(self, cmd: list[str], returncode: int, stderr: str) -> None:
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"`{' '.join(cmd)}` exited with {returncode}: {stderr.strip()}")


class TaskNotFound(TaskwarriorError):
    def __init__(self, ref: str) -> None:
        self.ref = ref
        super().__init__(f"No task matches reference {ref!r}.")


class TaskwarriorTimeout(TaskwarriorError):
    def __init__(self, cmd: list[str], timeout: float) -> None:
        self.cmd = cmd
        self.timeout = timeout
        super().__init__(f"`{' '.join(cmd)}` exceeded {timeout}s.")


class TaskwarriorThemeMissing(TaskwarriorError):
    def __init__(self) -> None:
        super().__init__(
            "Taskwarrior 3.x aborted because it could not find 'default.theme'. "
            "Create an empty file named default.theme next to your .taskrc, "
            "or install a Taskwarrior build that ships its theme files."
        )
