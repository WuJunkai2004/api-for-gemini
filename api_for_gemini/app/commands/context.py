import http.client
import json
import socket
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


def context_handler():
    """Handle the context command for Gemini CLI hook."""
    # Based on the documentation, hooks MUST output JSON to stdout
    # and NO other text.

    is_running, status_data = check_server_status()

    context = {
        "description": "Gema CLI context",
        "proxy_info": {
            "name": "gema",
            "version": "0.1.0",
            "is_running": is_running,
            "status": status_data,
        },
    }

    # Send JSON to stdout
    print(json.dumps(context))
    # Exit with success
    sys.exit(0)
