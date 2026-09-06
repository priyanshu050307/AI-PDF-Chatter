#!/usr/bin/env python
import os
import sys
import time
import subprocess

# Reconfigure stdout to use UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

# Virtual environment python binary
VENV_PYTHON_WIN = os.path.join(BACKEND_DIR, "venv", "Scripts", "python.exe")
VENV_PYTHON_UNIX = os.path.join(BACKEND_DIR, "venv", "bin", "python")

if os.path.exists(VENV_PYTHON_WIN):
    PYTHON_BIN = VENV_PYTHON_WIN
elif os.path.exists(VENV_PYTHON_UNIX):
    PYTHON_BIN = VENV_PYTHON_UNIX
else:
    PYTHON_BIN = sys.executable


def ensure_backend_env():
    """Ensure backend/.env file exists."""
    env_path = os.path.join(BACKEND_DIR, ".env")
    if not os.path.exists(env_path):
        print("[+] Creating backend/.env configuration...")
        env_content = (
            'APP_NAME="AI PDF Chatter"\n'
            'APP_ENV="development"\n'
            'DEBUG=false\n'
            'PORT=8000\n'
            'HOST="0.0.0.0"\n'
            'CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"\n'
            'DATABASE_URL="sqlite+aiosqlite:///./pdfchatter.db"\n'
            'JWT_SECRET="development_secret_key_32_bytes_minimum_length_spec"\n'
            'JWT_ALGORITHM="HS256"\n'
            'ACCESS_TOKEN_EXPIRE_MINUTES=1440\n'
            'STORAGE_BACKEND="local"\n'
            'LOCAL_STORAGE_DIR="./storage_data"\n'
            'EMBEDDING_PROVIDER="mock"\n'
            'LLM_PROVIDER="mock"\n'
        )
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(env_content)


def main():
    print("=" * 65)
    print(" AI PDF Chatter -- Unified Application Launcher ")
    print("=" * 65)

    ensure_backend_env()

    processes = []

    try:
        # 1. Start Backend FastAPI Server
        print("\n[+] Starting Backend API server on http://127.0.0.1:8000 ...")
        backend_cmd = [
            PYTHON_BIN, "-m", "uvicorn", "app.main:app",
            "--host", "127.0.0.1", "--port", "8000"
        ]
        backend_proc = subprocess.Popen(
            backend_cmd,
            cwd=BACKEND_DIR,
            env=os.environ.copy()
        )
        processes.append(backend_proc)

        # 2. Start Frontend Next.js Server (Dev Mode)
        print("[+] Starting Frontend Next.js server on http://localhost:3000 ...")
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
        frontend_proc = subprocess.Popen(
            [npm_cmd, "run", "dev"],
            cwd=FRONTEND_DIR,
            env=os.environ.copy()
        )
        processes.append(frontend_proc)

        print("\n" + "=" * 65)
        print(" [SUCCESS] Both services are running concurrently!")
        print("   * Web Application : http://localhost:3000")
        print("   * Backend API Docs: http://127.0.0.1:8000/docs")
        print("   * Health Check    : http://127.0.0.1:8000/api/v1/health")
        print("=" * 65)
        print("\nPress Ctrl+C at any time to stop all services.\n")

        # Keep parent process alive while children run
        while True:
            time.sleep(2)
            all_dead = True
            for p in processes:
                if p.poll() is None:
                    all_dead = False
                else:
                    print(f"[!] Process {p.pid} exited with code {p.returncode}.")
            if all_dead:
                print("[!] All sub-processes have terminated.")
                break

    except KeyboardInterrupt:
        print("\n[*] Stopping all services...")
        for p in processes:
            try:
                p.terminate()
                p.wait(timeout=3)
            except Exception:
                p.kill()
        print("[+] All services stopped successfully.")


if __name__ == "__main__":
    main()
