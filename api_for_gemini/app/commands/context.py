import http.client
import json
import os
import socket
import subprocess
import sys


def check_server_status(host="127.0.0.1", port=18000, timeout=1):
    """Check if the proxy server is responding."""
    try:
        conn = http.client.HTTPConnection(host, port, timeout=timeout)
        conn.request("GET", "/status")
        response = conn.getresponse()
        if response.status == 200:
            data = json.loads(response.read().decode())
            return True, data
        return False, {"error": f"Server returned status {response.status}"}
    except (http.client.HTTPException, socket.timeout, ConnectionRefusedError) as e:
        return False, {"error": str(e)}
    except Exception as e:
        return False, {"error": f"Unexpected error: {str(e)}"}


def start_server_background():
    """Start the Gema proxy server in the background and detach it."""
    # Use the same python executable and run as a module
    cmd = [sys.executable, "-m", "api_for_gemini.app.main", "start"]

    # Environment inherited, but we could add/modify if needed
    env = os.environ.copy()

    try:
        if sys.platform == "win32":
            # Windows: CREATE_NO_WINDOW (0x08000000) | DETACHED_PROCESS (0x00000008)
            creationflags = 0x08000000 | 0x00000008
            subprocess.Popen(
                cmd,
                creationflags=creationflags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                close_fds=True,
                env=env,
                shell=False,
            )
        else:
            # Unix: Use setsid to detach from the terminal and create a new session
            subprocess.Popen(
                cmd,
                preexec_fn=os.setsid,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                close_fds=True,
                env=env,
            )
        return True
    except Exception:
        return False


def context_handler():
    """Handle the context command for Gemini CLI hook."""
    # Based on the documentation, hooks MUST output JSON to stdout
    # and NO other text.

    is_running, status_data = check_server_status()
    auto_started = False

    if not is_running:
        # Try to start in background
        auto_started = start_server_background()

    context = {
        "description": "Gema CLI context",
        "proxy_info": {
            "name": "gema",
            "version": "0.1.0",
            "is_running": is_running,
            "auto_started": auto_started,
            "status": status_data,
        },
    }

    # Send JSON to stdout
    sys.stdout.write(f"{json.dumps(context)}\n")
    sys.stdout.flush()
    # Exit with success
    sys.exit(0)
