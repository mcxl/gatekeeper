import os
import sys
import subprocess

port = os.environ.get("PORT", "8080")
print(f"Starting on port {port}", flush=True)
print(f"Python: {sys.executable}", flush=True)

result = subprocess.run([
    sys.executable, "-m", "uvicorn",
    "api.main:app",
    "--host", "0.0.0.0",
    "--port", port,
    "--log-level", "info"
])
