#!/usr/bin/env python3
"""
First-Time Setup Script
=======================
One-command setup for new users cloning the repository.
Run: python setup.py
"""

import subprocess
import sys
import os
import time
import shutil
from pathlib import Path

# Force unbuffered output for immediate display
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(line_buffering=True)

# Set encoding for Windows
if sys.platform == "win32":
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except:
        pass


class Colors:
    if sys.platform == "win32":
        GREEN = ''
        YELLOW = ''
        RED = ''
        BLUE = ''
        RESET = ''
        BOLD = ''
    else:
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        BLUE = '\033[94m'
        RESET = '\033[0m'
        BOLD = '\033[1m'


def print_header():
    print("\n" + "=" * 60, flush=True)
    print(f"{Colors.BOLD}EXCHANGE DASHBOARD - FIRST-TIME SETUP{Colors.RESET}", flush=True)
    print("=" * 60 + "\n", flush=True)


def print_status(message, status="info"):
    if status == "success":
        print(f"{Colors.GREEN}[OK] {message}{Colors.RESET}", flush=True)
    elif status == "error":
        print(f"{Colors.RED}[ERROR] {message}{Colors.RESET}", flush=True)
    elif status == "warning":
        print(f"{Colors.YELLOW}[WARN] {message}{Colors.RESET}", flush=True)
    elif status == "info":
        print(f"{Colors.BLUE}[INFO] {message}{Colors.RESET}", flush=True)
    else:
        print(f"   {message}", flush=True)


def print_step(step_num, total_steps, message):
    print(f"\n{Colors.BOLD}[{step_num}/{total_steps}] {message}{Colors.RESET}", flush=True)


def check_command(command):
    if shutil.which(command) is not None:
        return True
    if command in ["node", "npm"]:
        try:
            nvm_dir = os.path.expanduser("~/.nvm")
            nvm_versions = os.path.join(nvm_dir, "versions", "node")
            if os.path.exists(nvm_versions):
                for version_dir in os.listdir(nvm_versions):
                    version_path = os.path.join(nvm_versions, version_dir)
                    if os.path.isdir(version_path):
                        bin_path = os.path.join(version_path, "bin", command)
                        if os.path.exists(bin_path):
                            return True
        except:
            pass
    return False


def get_npm_command():
    if shutil.which("npm"):
        return "npm"
    try:
        nvm_dir = os.path.expanduser("~/.nvm")
        nvm_versions = os.path.join(nvm_dir, "versions", "node")
        if os.path.exists(nvm_versions):
            for version_dir in sorted(os.listdir(nvm_versions), reverse=True):
                npm_path = os.path.join(nvm_versions, version_dir, "bin", "npm")
                if os.path.exists(npm_path):
                    return npm_path
    except:
        pass
    return None


def check_python_version():
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print_status(f"Python {version.major}.{version.minor}.{version.micro} found", "success")
        return True
    else:
        print_status(f"Python 3.8+ required, found {version.major}.{version.minor}", "error")
        return False


def check_docker_running():
    if not shutil.which("docker"):
        print_status("Docker not found. Install from https://docker.com", "error")
        return False
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            shell=(sys.platform == "win32")
        )
        if result.returncode == 0:
            print_status("Docker is running", "success")
            return True
        else:
            print_status("Docker is installed but not running", "error")
            print_status("Please start Docker Desktop and try again", "info")
            return False
    except Exception as e:
        print_status(f"Error checking Docker: {e}", "error")
        return False


def check_prerequisites():
    print_step(1, 7, "Checking prerequisites")

    all_ok = True

    if not check_python_version():
        all_ok = False

    if not check_docker_running():
        all_ok = False

    if check_command("node"):
        print_status("Node.js found", "success")
    else:
        print_status("Node.js not found (optional - dashboard will be skipped)", "warning")

    if check_command("npm"):
        print_status("npm found", "success")
    else:
        print_status("npm not found (optional - dashboard will be skipped)", "warning")

    return all_ok


def setup_env_files():
    print_step(2, 7, "Setting up environment files")

    root_dir = Path(__file__).parent

    env_file = root_dir / ".env"
    env_example = root_dir / ".env.example"

    if env_file.exists():
        print_status(".env already exists, skipping", "info")
    elif env_example.exists():
        shutil.copy2(env_example, env_file)
        print_status("Created .env from .env.example", "success")
    else:
        print_status(".env.example not found", "error")
        return False

    dashboard_env = root_dir / "dashboard" / ".env"
    dashboard_env_example = root_dir / "dashboard" / ".env.example"

    if dashboard_env.exists():
        print_status("dashboard/.env already exists, skipping", "info")
    elif dashboard_env_example.exists():
        shutil.copy2(dashboard_env_example, dashboard_env)
        print_status("Created dashboard/.env from dashboard/.env.example", "success")
    else:
        print_status("dashboard/.env.example not found (skipping)", "warning")

    return True


def install_python_dependencies():
    print_step(3, 7, "Installing Python dependencies")

    requirements_file = Path(__file__).parent / "requirements.txt"
    if not requirements_file.exists():
        print_status("requirements.txt not found", "error")
        return False

    print_status("Running pip install (this may take a minute)...", "info")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_file), "-q"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print_status("Python dependencies installed successfully", "success")
            return True
        else:
            print_status("pip install failed", "error")
            if result.stderr:
                print(f"   {result.stderr[:500]}")
            return False
    except Exception as e:
        print_status(f"Error installing dependencies: {e}", "error")
        return False


def install_npm_dependencies():
    print_step(4, 7, "Installing npm dependencies")

    npm_cmd = get_npm_command()
    if not npm_cmd:
        print_status("npm not available - skipping dashboard setup", "warning")
        return True

    dashboard_path = Path(__file__).parent / "dashboard"
    node_modules = dashboard_path / "node_modules"

    if node_modules.exists() and any(node_modules.iterdir()):
        print_status("node_modules already exists, skipping install", "info")
        return True

    print_status("Running npm install (this may take a few minutes)...", "info")

    try:
        result = subprocess.run(
            [npm_cmd, "install"],
            cwd=str(dashboard_path),
            capture_output=True,
            text=True,
            shell=(sys.platform == "win32")
        )
        if result.returncode == 0:
            print_status("npm dependencies installed successfully", "success")
            return True
        else:
            print_status("npm install failed", "error")
            if result.stderr:
                print(f"   {result.stderr[:500]}")
            return False
    except Exception as e:
        print_status(f"Error installing npm dependencies: {e}", "error")
        return False


def pull_docker_images():
    print_step(5, 7, "Pulling Docker images")

    print_status("Pulling images (this may take a few minutes on first run)...", "info")

    try:
        result = subprocess.run(
            ["docker", "compose", "pull"],
            capture_output=True,
            text=True,
            shell=(sys.platform == "win32")
        )
        if result.returncode == 0:
            print_status("Docker images pulled successfully", "success")
            return True
        else:
            print_status("docker compose pull had issues (may still work)", "warning")
            return True
    except Exception as e:
        print_status(f"Error pulling images: {e}", "error")
        return False


def check_container_running(container_name):
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            shell=(sys.platform == "win32")
        )
        return container_name in result.stdout
    except:
        return False


def start_docker_containers():
    print_step(6, 7, "Starting Docker containers")

    postgres_running = check_container_running("exchange_postgres")
    redis_running = check_container_running("exchange_redis")

    if postgres_running and redis_running:
        print_status("PostgreSQL container already running", "success")
        print_status("Redis container already running", "success")
        return True

    print_status("Starting PostgreSQL and Redis containers...", "info")

    try:
        result = subprocess.run(
            ["docker", "compose", "up", "-d", "postgres", "redis"],
            capture_output=True,
            text=True,
            shell=(sys.platform == "win32")
        )

        if result.returncode != 0 and "already in use" in result.stderr:
            print_status("Containers exist, attempting to start them...", "info")
            subprocess.run(
                ["docker", "start", "exchange_postgres", "exchange_redis"],
                capture_output=True,
                shell=(sys.platform == "win32")
            )
        elif result.returncode != 0:
            print_status("docker compose up failed", "error")
            if result.stderr:
                print(f"   {result.stderr[:500]}")
            return False

        print_status("Waiting for containers to be ready...", "info")
        for i in range(15):
            time.sleep(1)
            postgres_running = check_container_running("exchange_postgres")
            redis_running = check_container_running("exchange_redis")

            if postgres_running and redis_running:
                print_status("PostgreSQL container is running", "success")
                print_status("Redis container is running", "success")
                return True
            elif postgres_running:
                print_status("PostgreSQL is running, Redis still starting...", "info")

        print_status("Containers are taking longer than expected", "warning")
        return True
    except Exception as e:
        print_status(f"Error starting containers: {e}", "error")
        return False


def verify_database_connection():
    print_step(7, 7, "Verifying database connection")

    print_status("Waiting for database to accept connections...", "info")
    time.sleep(3)

    try:
        import psycopg2
        from dotenv import load_dotenv
        load_dotenv()

        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            database=os.getenv("POSTGRES_DATABASE", "exchange_data"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres123"),
            connect_timeout=10
        )
        conn.close()
        print_status("Database connection successful", "success")
        return True
    except ImportError:
        print_status("psycopg2 not installed yet - will verify on first run", "warning")
        return True
    except Exception as e:
        print_status(f"Database connection failed: {e}", "warning")
        print_status("This may be normal if the database is still initializing", "info")
        return True


def print_summary(success):
    print("\n" + "=" * 60, flush=True)
    if success:
        print(f"{Colors.GREEN}{Colors.BOLD}SETUP COMPLETE{Colors.RESET}", flush=True)
    else:
        print(f"{Colors.YELLOW}{Colors.BOLD}SETUP COMPLETED WITH WARNINGS{Colors.RESET}", flush=True)
    print("=" * 60, flush=True)

    print("\nNext steps:", flush=True)
    print(f"  1. Start the system:     {Colors.BOLD}python start.py{Colors.RESET}", flush=True)
    print(f"  2. Verify installation:  {Colors.BOLD}python verify_setup.py{Colors.RESET}", flush=True)

    print("\nAccess points:", flush=True)
    print("  Dashboard:  http://localhost:3000", flush=True)
    print("  API:        http://localhost:8000", flush=True)
    print("  API Docs:   http://localhost:8000/docs", flush=True)
    print("", flush=True)


def main():
    print_header()

    all_success = True

    if not check_prerequisites():
        print("\n" + "=" * 60, flush=True)
        print(f"{Colors.RED}Prerequisites check failed. Please fix the issues above and try again.{Colors.RESET}", flush=True)
        print("=" * 60, flush=True)
        sys.exit(1)

    if not setup_env_files():
        all_success = False

    if not install_python_dependencies():
        all_success = False

    install_npm_dependencies()

    if not pull_docker_images():
        all_success = False

    if not start_docker_containers():
        all_success = False

    verify_database_connection()

    print_summary(all_success)

    return 0 if all_success else 1


if __name__ == "__main__":
    sys.exit(main())
