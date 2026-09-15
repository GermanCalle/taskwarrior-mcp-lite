import subprocess
import sys
import textwrap

# Blocks `mcp` at import time no matter where it is installed, so the isolation
# claim is tested even in an environment that has the server extra present.
_HIDE_MCP = textwrap.dedent("""
    import sys

    class _Blocker:
        def find_spec(self, name, path=None, target=None):
            if name == "mcp" or name.startswith("mcp."):
                raise ModuleNotFoundError(f"No module named {name!r}", name=name)
            return None

    sys.meta_path.insert(0, _Blocker())
""")


def _run_without_mcp(body: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", _HIDE_MCP + textwrap.dedent(body)],
        capture_output=True,
        timeout=60,
        check=False,
    )


def test_core_imports_without_the_mcp_sdk():
    proc = _run_without_mcp("""
        from taskwarrior_mcp_lite import TaskWarrior

        TaskWarrior("/tmp/nonexistent-taskrc")
        print("ok")
    """)

    assert proc.returncode == 0, proc.stderr.decode()
    assert b"ok" in proc.stdout


def test_importing_the_package_does_not_pull_in_the_sdk():
    proc = _run_without_mcp("""
        import sys

        import taskwarrior_mcp_lite  # noqa: F401

        print(any(name == "mcp" or name.startswith("mcp.") for name in sys.modules))
    """)

    assert proc.returncode == 0, proc.stderr.decode()
    assert proc.stdout.strip() == b"False"


def test_server_module_explains_the_missing_extra():
    proc = _run_without_mcp("""
        try:
            import taskwarrior_mcp_lite.server  # noqa: F401
        except ModuleNotFoundError as exc:
            print(exc)
    """)

    assert b"taskwarrior-mcp-lite[server]" in proc.stdout
