#!/usr/bin/env python3
"""
Setup Verification Script
=========================
Verifies all components are correctly configured and running.
Run: python verify_setup.py
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

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


class CheckResult:
    def __init__(self, name, passed, message="", suggestion=""):
        self.name = name
        self.passed = passed
        self.warning = False
        self.message = message
        self.suggestion = suggestion


def print_header():
    print("\n" + "=" * 60, flush=True)
    print(f"{Colors.BOLD}SETUP VERIFICATION REPORT{Colors.RESET}", flush=True)
    print("=" * 60 + "\n", flush=True)


def check_env_files():
    root_dir = Path(__file__).parent
    results = []

    env_file = root_dir / ".env"
    if env_file.exists():
        with open(env_file) as f:
            content = f.read()
        if "your_password_here" in content or "POSTGRES_PASSWORD=\n" in content:
            result = CheckResult(
                "Environment file (.env)",
                False,
                "Password not configured",
                "Run: python setup.py"
            )
        else:
            result = CheckResult("Environment file (.env)", True)
        results.append(result)
    else:
        results.append(CheckResult(
            "Environment file (.env)",
            False,
            "File missing",
            "Run: python setup.py"
        ))

    dashboard_env = root_dir / "dashboard" / ".env"
    if dashboard_env.exists():
        results.append(CheckResult("Dashboard environment (dashboard/.env)", True))
    else:
        result = CheckResult(
            "Dashboard environment (dashboard/.env)",
            True,
            "File missing (optional)"
        )
        result.warning = True
        results.append(result)

    return results


def check_docker():
    if not shutil.which("docker"):
        return CheckResult(
            "Docker installed",
            False,
            "Docker not found",
            "Install from https://docker.com"
        )

    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            shell=(sys.platform == "win32")
        )
        if result.returncode == 0:
            return CheckResult("Docker running", True)
        else:
            return CheckResult(
                "Docker running",
                False,
                "Docker is not running",
                "Start Docker Desktop"
            )
    except Exception as e:
        return CheckResult(
            "Docker running",
            False,
            str(e),
            "Start Docker Desktop"
        )


def check_postgres_container():
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=exchange_postgres", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            shell=(sys.platform == "win32")
        )
        if result.stdout.strip() and "Up" in result.stdout:
            return CheckResult("PostgreSQL container", True)
        else:
            return CheckResult(
                "PostgreSQL container",
                False,
                "Container not running",
                "Run: docker compose up -d postgres"
            )
    except Exception as e:
        return CheckResult(
            "PostgreSQL container",
            False,
            str(e),
            "Run: docker compose up -d postgres"
        )


def check_redis_container():
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=exchange_redis", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            shell=(sys.platform == "win32")
        )
        if result.stdout.strip() and "Up" in result.stdout:
            return CheckResult("Redis container", True)
        else:
            result = CheckResult(
                "Redis container",
                True,
                "Not running (optional - falls back to in-memory cache)"
            )
            result.warning = True
            return result
    except Exception as e:
        result = CheckResult(
            "Redis container",
            True,
            f"Check failed: {e} (optional)"
        )
        result.warning = True
        return result


def check_database_connection():
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
            connect_timeout=5
        )

        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'exchange_data'")
        table_exists = cursor.fetchone()[0] > 0
        conn.close()

        if table_exists:
            return CheckResult("Database connection", True, "Schema exists")
        else:
            result = CheckResult(
                "Database connection",
                True,
                "Connected but schema not created yet"
            )
            result.warning = True
            return result
    except ImportError:
        return CheckResult(
            "Database connection",
            False,
            "psycopg2 not installed",
            "Run: pip install -r requirements.txt"
        )
    except Exception as e:
        return CheckResult(
            "Database connection",
            False,
            str(e)[:50],
            "Check password in .env matches docker-compose.yml"
        )


def check_api_server():
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:8000/api/health", method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                return CheckResult("API server (port 8000)", True)
            else:
                result = CheckResult(
                    "API server (port 8000)",
                    True,
                    f"Responded with status {response.status}"
                )
                result.warning = True
                return result
    except Exception as e:
        result = CheckResult(
            "API server (port 8000)",
            True,
            "Not running"
        )
        result.warning = True
        return result


def check_dashboard():
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:3000", method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                return CheckResult("Dashboard (port 3000)", True)
            else:
                result = CheckResult(
                    "Dashboard (port 3000)",
                    True,
                    f"Responded with status {response.status}"
                )
                result.warning = True
                return result
    except Exception:
        result = CheckResult(
            "Dashboard (port 3000)",
            True,
            "Not running (optional)"
        )
        result.warning = True
        return result


def check_python_packages():
    required_packages = [
        "fastapi",
        "uvicorn",
        "psycopg2",
        "pandas",
        "redis",
        "requests"
    ]

    missing = []
    for pkg in required_packages:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            missing.append(pkg)

    if missing:
        return CheckResult(
            "Python packages",
            False,
            f"Missing: {', '.join(missing)}",
            "Run: pip install -r requirements.txt"
        )
    else:
        return CheckResult("Python packages", True)


def print_result(result):
    if result.passed and not result.warning:
        status = f"{Colors.GREEN}[PASS]{Colors.RESET}"
    elif result.warning:
        status = f"{Colors.YELLOW}[WARN]{Colors.RESET}"
    else:
        status = f"{Colors.RED}[FAIL]{Colors.RESET}"

    line = f"{status} {result.name}"
    if result.message:
        line += f" - {result.message}"
    print(line, flush=True)

    if result.suggestion and not result.passed:
        print(f"       Suggestion: {result.suggestion}", flush=True)


def print_summary(results):
    passed = sum(1 for r in results if r.passed and not r.warning)
    warnings = sum(1 for r in results if r.warning)
    failed = sum(1 for r in results if not r.passed)
    total = len(results)

    print("\n" + "-" * 60, flush=True)

    if failed == 0 and warnings == 0:
        print(f"{Colors.GREEN}RESULT: All {total} checks passed{Colors.RESET}", flush=True)
    elif failed == 0:
        print(f"{Colors.GREEN}RESULT: {passed}/{total} checks passed, {warnings} warning(s){Colors.RESET}", flush=True)
    else:
        print(f"{Colors.RED}RESULT: {passed}/{total} checks passed, {failed} failed, {warnings} warning(s){Colors.RESET}", flush=True)

    if failed > 0:
        print("\nTo fix issues, run:", flush=True)
        print(f"  {Colors.BOLD}python setup.py{Colors.RESET}", flush=True)
    elif warnings > 0:
        print("\nNext steps:", flush=True)
        print(f"  {Colors.BOLD}python start.py{Colors.RESET}", flush=True)
    else:
        print("\nSystem is ready! Start with:", flush=True)
        print(f"  {Colors.BOLD}python start.py{Colors.RESET}", flush=True)

    print("-" * 60, flush=True)


def main():
    print_header()

    results = []

    results.extend(check_env_files())
    results.append(check_docker())
    results.append(check_postgres_container())
    results.append(check_redis_container())
    results.append(check_database_connection())
    results.append(check_python_packages())
    results.append(check_api_server())
    results.append(check_dashboard())

    for result in results:
        print_result(result)

    print_summary(results)

    failed = sum(1 for r in results if not r.passed)
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
