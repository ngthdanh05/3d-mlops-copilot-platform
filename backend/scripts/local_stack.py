"""Throwaway backend and frontend for the smoke test and the benchmark.

They run on their own ports with a temporary database, so `mlops.db` and any dev server
the developer already has open are left alone.
"""

import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import httpx

BACKEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"
sys.path.insert(0, str(BACKEND_DIR))  # lets scripts import `app` when run from any directory
BACKEND_PORT = 18000
FRONTEND_PORT = 15173
BACKEND_URL = f"http://127.0.0.1:{BACKEND_PORT}"
FRONTEND_URL = f"http://localhost:{FRONTEND_PORT}"
_STARTUP_TIMEOUT_S = 60


class StackError(RuntimeError):
    """A server could not be started, or a tool it needs is missing."""


def use_utf8_output() -> None:
    """Windows consoles default to a code page that cannot print Vietnamese."""
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def database_url(path: Path) -> str:
    return f"sqlite+aiosqlite:///{path.as_posix()}"


def find_tool(name: str) -> str:
    candidates = [shutil.which(name)]
    if appdata := os.environ.get("APPDATA"):  # where `npm install -g pnpm` puts it on Windows
        candidates.append(shutil.which(name, path=str(Path(appdata) / "npm")))
    for candidate in candidates:
        if candidate:
            return candidate
    raise StackError(f"Không tìm thấy `{name}` trong PATH.")


def _require_free_port(port: int) -> None:
    with socket.socket() as probe:
        probe.settimeout(0.5)
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            raise StackError(f"Cổng {port} đang được dùng. Hãy tắt tiến trình đang giữ cổng này.")


def _stop(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True, check=False
        )
    else:
        os.killpg(process.pid, signal.SIGTERM)
    process.wait(timeout=15)


def _wait_until_up(url: str, process: subprocess.Popen, log_path: Path) -> None:
    deadline = time.monotonic() + _STARTUP_TIMEOUT_S
    while time.monotonic() < deadline:
        if process.poll() is not None:
            break
        try:
            if httpx.get(url, timeout=2).status_code < 500:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.25)
    log = log_path.read_text(encoding="utf-8", errors="replace")[-2000:]
    raise StackError(f"{url} không chạy được. Log cuối:\n{log}")


@contextmanager
def _server(
    command: list[str], cwd: Path, env: dict[str, str], port: int, url: str, log_path: Path
) -> Iterator[None]:
    _require_free_port(port)
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env={**os.environ, **env},
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=os.name != "nt",  # so that _stop can end its children too
        )
        try:
            _wait_until_up(url, process, log_path)
            yield
        finally:
            _stop(process)


@contextmanager
def running_backend(db_url: str, log_dir: Path, *, real_llm: bool = False) -> Iterator[None]:
    """`real_llm` uses the key in backend/.env, which spends quota. Otherwise the stand-in."""
    env = {"DATABASE_URL": db_url}
    if not real_llm:
        env["LLM_API_KEY"] = ""
    command = [
        str(find_python()),
        "-m",
        "uvicorn",
        "app.main:app",
        "--port",
        str(BACKEND_PORT),
        "--log-level",
        "warning",
    ]
    with _server(
        command,
        BACKEND_DIR,
        env,
        BACKEND_PORT,
        f"{BACKEND_URL}/api/health",
        log_dir / f"backend-{time.monotonic_ns()}.log",
    ):
        yield


def find_python() -> Path:
    scripts = "Scripts/python.exe" if os.name == "nt" else "bin/python"
    return BACKEND_DIR / ".venv" / scripts


@contextmanager
def running_frontend(log_dir: Path, *, production: bool = False) -> Iterator[None]:
    """Vite's dev server, or a production preview for measuring what users would really get."""
    pnpm = find_tool("pnpm")
    if production:
        subprocess.run([pnpm, "build"], cwd=FRONTEND_DIR, check=True, capture_output=True)
    mode = ["preview"] if production else []
    command = [pnpm, "exec", "vite", *mode, "--port", str(FRONTEND_PORT), "--strictPort"]
    with _server(
        command,
        FRONTEND_DIR,
        {"API_PROXY_TARGET": BACKEND_URL},
        FRONTEND_PORT,
        FRONTEND_URL,
        log_dir / f"frontend-{time.monotonic_ns()}.log",
    ):
        yield


def run_node_script(name: str, *arguments: str) -> None:
    script = FRONTEND_DIR / "scripts" / name
    subprocess.run([find_tool("node"), str(script), *arguments], cwd=FRONTEND_DIR, check=True)
