from __future__ import annotations

import ctypes
import os
import socket
import subprocess
import time
from pathlib import Path


WORKSPACE = Path(r"C:\Users\gHOST\Downloads\New folder")
BACKEND_PYTHON = WORKSPACE / "backend_runtime" / "Scripts" / "python.exe"
BACKEND_DIR = WORKSPACE / "backend"
FRONTEND_DIR = WORKSPACE / "frontend" / "dist"
BROWSER_PROFILE_DIR = WORKSPACE / ".runtime" / "agent-browser-profile"
BACKEND_PORT = 8000
FRONTEND_PORT = 4173
FRONTEND_URL = f"http://127.0.0.1:{FRONTEND_PORT}"
DETACHED = 0x00000008 | 0x00000200

BROWSER_CANDIDATES = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
]


def port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


def terminate_pid(pid: int) -> None:
    try:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        pass


def wait_for_port_state(port: int, *, should_be_open: bool, timeout_seconds: int = 10) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        is_open = port_open(port)
        if is_open == should_be_open:
            return
        time.sleep(0.25)


def pids_for_port(port: int) -> list[int]:
    try:
        output = subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return []
    pids: list[int] = []
    for line in output.stdout.splitlines():
        line = line.strip()
        if line.isdigit():
            pid = int(line)
            if pid not in pids:
                pids.append(pid)
    return pids


def start_detached(command: list[str], cwd: Path, log_name: str) -> None:
    log_path = WORKSPACE / log_name
    handle = log_path.open("a", encoding="utf-8")
    subprocess.Popen(
        command,
        cwd=str(cwd),
        stdout=handle,
        stderr=subprocess.STDOUT,
        creationflags=DETACHED,
        close_fds=True,
    )


def ensure_backend() -> None:
    for pid in pids_for_port(BACKEND_PORT):
        terminate_pid(pid)
    wait_for_port_state(BACKEND_PORT, should_be_open=False)
    start_detached(
        [
            str(BACKEND_PYTHON),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(BACKEND_PORT),
        ],
        BACKEND_DIR,
        "workspace-backend.log",
    )


def ensure_frontend() -> None:
    for pid in pids_for_port(FRONTEND_PORT):
        terminate_pid(pid)
    wait_for_port_state(FRONTEND_PORT, should_be_open=False)
    start_detached(
        [
            str(BACKEND_PYTHON),
            "-m",
            "http.server",
            str(FRONTEND_PORT),
            "--bind",
            "127.0.0.1",
            "-d",
            str(FRONTEND_DIR),
        ],
        WORKSPACE,
        "workspace-frontend.log",
    )


def wait_for_port(port: int, timeout_seconds: int = 20) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if port_open(port):
            return
        time.sleep(0.5)
    raise TimeoutError(f"Port {port} did not become ready in time.")


def get_browser() -> Path | None:
    for browser in BROWSER_CANDIDATES:
        if browser.exists():
            return browser
    return None


def launch_agent_window() -> None:
    BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    for process_name in ("chrome.exe", "msedge.exe"):
        subprocess.run(
            [
                "taskkill",
                "/IM",
                process_name,
                "/FI",
                f"WINDOWTITLE eq Local 3D Agent*",
                "/T",
                "/F",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    time.sleep(1)
    browser = get_browser()
    if browser is None:
        return
    subprocess.Popen(
        [
            str(browser),
            f"--user-data-dir={BROWSER_PROFILE_DIR}",
            "--new-window",
            "--disable-application-cache",
            f"--app={FRONTEND_URL}",
        ],
        creationflags=DETACHED,
        close_fds=True,
    )


user32 = ctypes.windll.user32


def _window_text(hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def _find_window(title_fragment: str) -> int | None:
    matches: list[int] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def enum_proc(hwnd, _lparam):
        if user32.IsWindowVisible(hwnd):
            title = _window_text(hwnd)
            if title_fragment.lower() in title.lower():
                matches.append(hwnd)
        return True

    user32.EnumWindows(enum_proc, 0)
    return matches[0] if matches else None


def arrange_windows() -> None:
    screen_width = user32.GetSystemMetrics(0)
    screen_height = user32.GetSystemMetrics(1)
    blender_width = int(screen_width * 0.68)
    agent_width = screen_width - blender_width

    for _ in range(40):
        blender_hwnd = _find_window("Blender")
        agent_hwnd = _find_window("Local 3D Agent")
        if blender_hwnd and agent_hwnd:
            user32.ShowWindow(blender_hwnd, 9)
            user32.ShowWindow(agent_hwnd, 9)
            user32.MoveWindow(blender_hwnd, 0, 0, blender_width, screen_height, True)
            user32.MoveWindow(agent_hwnd, blender_width, 0, agent_width, screen_height, True)
            return
        time.sleep(1)


def main() -> None:
    ensure_backend()
    ensure_frontend()
    wait_for_port(BACKEND_PORT)
    wait_for_port(FRONTEND_PORT)
    launch_agent_window()
    arrange_windows()


if __name__ == "__main__":
    main()
