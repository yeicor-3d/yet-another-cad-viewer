#!/usr/bin/env python3
"""
yacv-server launcher for e2e tests.
The module-level YACV instance auto-starts on import.
This script waits for the server to be ready and then blocks until signaled.
Also provides a control endpoint at PORT+1 for pushing models during tests.
Also builds and serves a local yacv_server wheel for playground tests.
"""

import json
import os
import shutil
import signal
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path

# Don't prevent auto-start - we want the server to start on import
os.environ.setdefault("YACV_GRACEFUL_SECS_CONNECT", "0")
os.environ.setdefault("YACV_GRACEFUL_SECS_WORK", "10")

# Build the local yacv_server wheel and place it in the frontend directory
# so the playground can install from it instead of PyPI during e2e tests
_script_dir = Path(__file__).resolve().parent
_project_root = _script_dir.parent
_frontend_dir = _project_root / "yacv_server" / "frontend"
_wheel_dir = _frontend_dir / "yacv_wheel"
_wheel_dir.mkdir(parents=True, exist_ok=True)


def _ensure_wheel():
    """Ensure a local yacv_server wheel is available in the frontend directory.

    Tries (in order):
    1. Uses already-copied wheel in frontend/yacv_wheel/
    2. Copies from dist/ (pre-built wheel)
    3. Builds from source via uv build

    Copies the wheel to both frontend/yacv_wheel/ (for when the server serves from
    the yacv_server package directory) and dist/yacv_wheel/ (for when the server
    falls back to the project-level dist/ directory).
    """
    _dist_wheel_dir = _project_root / "dist" / "yacv_wheel"

    def _copy_wheel_to(target_dir: Path, wheel_path: Path):
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(wheel_path), str(target_dir / wheel_path.name))
        target_dir.joinpath("current.txt").write_text(wheel_path.name, encoding="utf-8")

    if not list(_wheel_dir.glob("*.whl")):
        # Try to copy from dist/ first (fastest)
        dist_dir = _project_root / "dist"
        wheels = list(dist_dir.glob("*.whl"))
        if wheels:
            print(f"Copying existing wheel from {wheels[0]}", flush=True)
            _copy_wheel_to(_wheel_dir, wheels[0])
        else:
            # Try to build the wheel
            print("No pre-built wheel found, building...", flush=True)
            env = os.environ.copy()
            env["YACV_SKIP_FRONTEND_BUILD"] = "true"
            try:
                result = subprocess.run(
                    ["uv", "build"],
                    cwd=str(_project_root),
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode != 0:
                    print(f"WARN: Failed to build wheel: {result.stderr}", flush=True)
                else:
                    wheels = list(dist_dir.glob("*.whl"))
                    if wheels:
                        _copy_wheel_to(_wheel_dir, wheels[0])
            except Exception as e:
                print(f"WARN: Could not build wheel: {e}", flush=True)

    # Also copy to dist/yacv_wheel/ so the server fallback can serve it
    wheel_files = list(_wheel_dir.glob("*.whl"))
    if wheel_files:
        print(f"Wheel ready: {wheel_files[0].name}", flush=True)
        if _dist_wheel_dir != _wheel_dir:
            _copy_wheel_to(_dist_wheel_dir, wheel_files[0])
    else:
        print(
            "WARN: No yacv_server wheel available. Playground URL tests may fail.",
            flush=True,
        )


_ensure_wheel()

# Import triggers __init__.py which auto-starts the server daemon thread
from yacv_server import yacv

# Wait for the server to be fully started
yacv.startup_complete.wait()
port = yacv.server.server_port
print(f"yacv-server ready on http://localhost:{port}", flush=True)


# ---- Control endpoint for e2e tests ----
# A simple TCP server that accepts JSON commands to control the server.
# Runs on port+1 by default.
CONTROL_PORT = int(os.getenv("YACV_CONTROL_PORT", str(port + 1)))


class ControlHandler(socketserver.StreamRequestHandler):
    def handle(self):
        try:
            data = self.rfile.readline().strip()
            if not data:
                return
            cmd = json.loads(data.decode("utf-8"))
            action = cmd.get("action")
            if action == "show":
                self._handle_show(cmd)
            elif action == "remove":
                self._handle_remove(cmd)
            elif action == "clear":
                from yacv_server import clear

                clear()
                self.wfile.write(b'{"ok": true}\n')
            elif action == "ping":
                self.wfile.write(b'{"ok": true}\n')
            else:
                self.wfile.write(
                    json.dumps({"error": f"Unknown action: {action}"}).encode() + b"\n"
                )
        except Exception as e:
            self.wfile.write(json.dumps({"error": str(e)}).encode() + b"\n")

    def _handle_show(self, cmd):
        from build123d import Box, Cylinder, Sphere

        from yacv_server import show

        shape_type = cmd.get("type", "box")
        name = cmd.get("name", "test_model")
        auto_clear = cmd.get("auto_clear", False)
        if shape_type == "box":
            w = cmd.get("width", 10)
            h = cmd.get("height", 10)
            d = cmd.get("depth", 10)
            obj = Box(w, h, d)
        elif shape_type == "sphere":
            r = cmd.get("radius", 10)
            obj = Sphere(r)
        elif shape_type == "cylinder":
            r = cmd.get("radius", 10)
            h = cmd.get("height", 20)
            obj = Cylinder(r, h)
        else:
            self.wfile.write(
                json.dumps({"error": f"Unknown shape type: {shape_type}"}).encode()
                + b"\n"
            )
            return
        show(obj, names=[name], auto_clear=auto_clear)
        self.wfile.write(json.dumps({"ok": True, "name": name}).encode() + b"\n")

    def _handle_remove(self, cmd):
        name = cmd.get("name", "")
        from yacv_server import remove

        remove(name)
        self.wfile.write(json.dumps({"ok": True}).encode() + b"\n")


control_server = None
for cp in range(CONTROL_PORT, CONTROL_PORT + 100):
    try:
        control_server = socketserver.ThreadingTCPServer(
            ("localhost", cp), ControlHandler
        )
        CONTROL_PORT = cp
        break
    except OSError:
        continue
if control_server is None:
    print("Failed to bind control port", flush=True)
    sys.exit(1)
control_thread = threading.Thread(target=control_server.serve_forever, daemon=True)
control_thread.start()
print(f"Control endpoint ready on tcp://localhost:{CONTROL_PORT}", flush=True)

# Write control port to a file for the test to discover
with open(".e2e_control_port", "w") as f:
    f.write(str(CONTROL_PORT))

# Signal handling for graceful shutdown
shutdown_event = threading.Event()


def handle_signal(signum, frame):
    if not shutdown_event.is_set():
        shutdown_event.set()
        # Remove port file
        try:
            os.unlink(".e2e_control_port")
        except Exception:
            pass
        control_server.shutdown()
        # Force exit after timeout
        threading.Thread(
            target=lambda: (time.sleep(5), os._exit(1)), daemon=True
        ).start()
        try:
            yacv.stop()
        except Exception:
            pass
        os._exit(0)


signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

# Block until signaled
try:
    shutdown_event.wait()
except KeyboardInterrupt:
    handle_signal(None, None)
