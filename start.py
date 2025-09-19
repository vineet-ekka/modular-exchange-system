#!/usr/bin/env python3
"""
Simplified Dashboard Startup Script
====================================
One-command startup for the entire Exchange Dashboard system.
Just run: python start.py
"""

import subprocess
import sys
import os
import time
import webbrowser
from pathlib import Path
import json
import shutil
import threading

# Force unbuffered output for immediate display
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(line_buffering=True)

# Alternative for Python < 3.7
if sys.version_info < (3, 7):
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 1)
    sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', 1)

# Set encoding for Windows
if sys.platform == "win32":
    import locale
    # Try to set UTF-8 encoding
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except:
        pass

# Colors for terminal output (disable on Windows to avoid issues)
class Colors:
    if sys.platform == "win32":
        # No colors on Windows to avoid encoding issues
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
    """Print startup header."""
    print("\n" + "="*60, flush=True)
    print(f"{Colors.BOLD}EXCHANGE DASHBOARD - SIMPLIFIED STARTUP{Colors.RESET}", flush=True)
    print("="*60 + "\n", flush=True)
    sys.stdout.flush()

def print_status(message, status="info"):
    """Print colored status messages."""
    # Use ASCII symbols for better compatibility
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
    sys.stdout.flush()

def check_command(command):
    """Check if a command is available."""
    return shutil.which(command) is not None

def check_prerequisites():
    """Check if all required tools are installed."""
    print_status("Checking prerequisites...", "info")
    
    prerequisites = {
        "python": "Python is required. Download from https://python.org",
        "node": "Node.js is required. Download from https://nodejs.org",
        "npm": "npm is required. Comes with Node.js",
        "docker": "Docker is required. Download from https://docker.com"
    }
    
    all_ok = True
    for cmd, message in prerequisites.items():
        if check_command(cmd):
            print_status(f"{cmd.capitalize()} found", "success")
        else:
            print_status(f"{cmd.capitalize()} not found. {message}", "error")
            all_ok = False
    
    return all_ok

def is_postgres_running():
    """Check if PostgreSQL container is running."""
    try:
        result = subprocess.run(
            ["docker", "ps"],
            capture_output=True,
            text=True,
            shell=True
        )
        return "exchange_postgres" in result.stdout
    except:
        return False

def is_redis_running():
    """Check if Redis container is running."""
    try:
        result = subprocess.run(
            ["docker", "ps"],
            capture_output=True,
            text=True,
            shell=True
        )
        return "exchange_redis" in result.stdout
    except:
        return False

def start_postgres():
    """Start PostgreSQL container."""
    print_status("Starting PostgreSQL...", "info")
    
    if is_postgres_running():
        print_status("PostgreSQL is already running", "success")
        return True
    
    try:
        # Check if Docker is running
        subprocess.run(["docker", "info"], capture_output=True, check=True, shell=True)
    except:
        print_status("Docker is not running. Please start Docker Desktop first.", "error")
        return False
    
    try:
        print("   Starting PostgreSQL container...")
        subprocess.run(
            ["docker-compose", "up", "-d", "postgres"],
            check=True,
            shell=True,
            capture_output=True
        )
        
        # Wait for PostgreSQL to be ready
        print("   Waiting for PostgreSQL to be ready...")
        for i in range(10):
            time.sleep(1)
            if is_postgres_running():
                print_status("PostgreSQL started successfully", "success")
                return True
        
        print_status("PostgreSQL is taking longer than expected to start", "warning")
        return True
        
    except subprocess.CalledProcessError as e:
        print_status(f"Failed to start PostgreSQL: {e}", "error")
        return False

def start_redis():
    """Start Redis container."""
    print_status("Starting Redis cache...", "info")
    
    if is_redis_running():
        print_status("Redis is already running", "success")
        return True
    
    try:
        # Check if Docker is running
        subprocess.run(["docker", "info"], capture_output=True, check=True, shell=True)
    except:
        print_status("Docker is not running. Please start Docker Desktop first.", "error")
        return False
    
    try:
        print("   Starting Redis container...")
        subprocess.run(
            ["docker-compose", "up", "-d", "redis"],
            check=True,
            shell=True,
            capture_output=True
        )
        
        # Wait for Redis to be ready
        print("   Waiting for Redis to be ready...")
        for i in range(10):
            time.sleep(1)
            if is_redis_running():
                print_status("Redis started successfully", "success")
                return True
        
        print_status("Redis is taking longer than expected to start", "warning")
        return True
        
    except subprocess.CalledProcessError as e:
        print_status(f"Failed to start Redis: {e}", "error")
        print_status("The system will continue without Redis caching", "warning")
        return True  # Don't fail the entire startup if Redis fails

def check_npm_dependencies():
    """Check if npm dependencies are installed."""
    dashboard_path = Path("dashboard")
    node_modules = dashboard_path / "node_modules"
    package_json = dashboard_path / "package.json"
    
    if not package_json.exists():
        print_status("Dashboard directory not found", "error")
        return False
    
    if not node_modules.exists():
        print_status("NPM dependencies not installed", "warning")
        print_status("Installing dependencies (this may take a few minutes)...", "info")
        
        try:
            subprocess.run(
                ["npm", "install"],
                cwd=dashboard_path,
                check=True,
                shell=True
            )
            print_status("Dependencies installed successfully", "success")
            return True
        except subprocess.CalledProcessError as e:
            print_status(f"Failed to install dependencies: {e}", "error")
            return False
    else:
        print_status("NPM dependencies already installed", "success")
        return True

def is_port_in_use(port):
    """Check if a port is in use."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def start_api_server():
    """Start the FastAPI backend server."""
    print_status("Starting API server...", "info")
    
    if is_port_in_use(8000):
        print_status("API server already running on port 8000", "success")
        return True
    
    try:
        # Start API server in background
        if sys.platform == "win32":
            subprocess.Popen(
                [sys.executable, "api.py"],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=Path.cwd()
            )
        else:
            subprocess.Popen(
                [sys.executable, "api.py"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=Path.cwd()
            )
        
        # Wait for API to start
        print("   Waiting for API server to start...")
        for i in range(10):
            time.sleep(1)
            if is_port_in_use(8000):
                print_status("API server started at http://localhost:8000", "success")
                return True
        
        print_status("API server is taking longer than expected", "warning")
        return True
        
    except Exception as e:
        print_status(f"Failed to start API server: {e}", "error")
        return False

def start_react_dashboard():
    """Start the React frontend."""
    print_status("Starting React dashboard...", "info")
    
    if is_port_in_use(3000):
        print_status("Dashboard already running on port 3000", "success")
        return True
    
    dashboard_path = Path("dashboard")
    
    try:
        # Start React app in background
        if sys.platform == "win32":
            subprocess.Popen(
                ["npm", "start"],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=dashboard_path,
                shell=True
            )
        else:
            subprocess.Popen(
                ["npm", "start"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=dashboard_path,
                shell=True
            )
        
        print("   Waiting for React to compile (this may take a moment)...")
        for i in range(30):
            time.sleep(1)
            if is_port_in_use(3000):
                print_status("Dashboard started at http://localhost:3000", "success")
                return True
        
        print_status("Dashboard is taking longer than expected", "warning")
        return True
        
    except Exception as e:
        print_status(f"Failed to start dashboard: {e}", "error")
        return False

def start_data_collector(quiet=True):
    """Start the data collection system."""
    print_status("Starting data collector...", "info")
    
    try:
        # Use 30-second intervals for real-time updates
        cmd = [sys.executable, "main.py", "--loop", "--interval", "30"]
        if quiet:
            cmd.append("--quiet")
        
        # Check if main.py exists first
        if not Path("main.py").exists():
            print_status("main.py not found in current directory", "error")
            return False
        
        # Create a log file for the data collector
        log_file = Path("data_collector.log")
        
        if sys.platform == "win32":
            # On Windows, write output to a log file instead of creating new console
            with open(log_file, "w") as log:
                process = subprocess.Popen(
                    cmd,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    cwd=Path.cwd(),
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
        else:
            with open(log_file, "w") as log:
                process = subprocess.Popen(
                    cmd,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    cwd=Path.cwd()
                )
        
        # Wait a moment to check if process started successfully
        time.sleep(2)
        
        # Check if process is still running
        if process.poll() is None:
            print_status("Data collector started (30-second intervals for real-time updates)", "success")
            print_status(f"Data collector log: {log_file}", "info")
            return True
        else:
            print_status("Data collector failed to start. Check data_collector.log for details", "warning")
            print("   You can start it manually with: python main.py --loop --interval 30")
            return False
        
    except Exception as e:
        print_status(f"Failed to start data collector: {e}", "warning")
        print("   You can start it manually later with: python main.py --loop --interval 30")
        return False

def start_background_historical_backfill():
    """Start 7-day historical backfill in background thread."""
    lock_file = Path(".backfill.lock")
    
    def _run_backfill():
        """Inner function to run the backfill."""
        try:
            # Check for existing lock
            if lock_file.exists():
                lock_age = time.time() - lock_file.stat().st_mtime
                if lock_age < 600:  # Less than 10 minutes old
                    print_status("Background historical refresh already running", "info")
                    return
            
            # Create lock file
            lock_file.touch()
            
            try:
                print_status("Starting 30-day historical data refresh in background...", "info")
                
                # Run the backfill script silently
                result = subprocess.run(
                    [sys.executable, "run_backfill.py", "--days", "30"],
                    capture_output=True,
                    text=True,
                    cwd=Path.cwd()
                )
                
                if result.returncode == 0:
                    print_status("Background: 30-day historical data refresh completed", "success")
                else:
                    # Silent failure - don't interrupt user experience
                    pass
                    
            finally:
                # Remove lock file
                if lock_file.exists():
                    lock_file.unlink()
                    
        except Exception as e:
            # Silent failure - background process shouldn't interrupt main flow
            pass
    
    # Start background thread
    thread = threading.Thread(target=_run_backfill, daemon=True)
    thread.start()
    
    print_status("Background: Refreshing last 7 days of historical data", "info")
    print_status("Dashboard will auto-update as new data arrives", "info")
    return thread

def open_dashboard():
    """Open the dashboard in the default browser."""
    print_status("Opening dashboard in browser...", "info")
    time.sleep(2)
    webbrowser.open("http://localhost:3000")

def print_summary(collector_running=True):
    """Print summary of running services."""
    print("\n" + "="*60, flush=True)
    print(f"{Colors.BOLD}DASHBOARD READY!{Colors.RESET}", flush=True)
    print("="*60, flush=True)
    print(f"\n{Colors.GREEN}Services running:{Colors.RESET}", flush=True)
    print(f"  Dashboard:  {Colors.BLUE}http://localhost:3000{Colors.RESET}", flush=True)
    print(f"  API Server: {Colors.BLUE}http://localhost:8000{Colors.RESET}", flush=True)
    print(f"  API Docs:   {Colors.BLUE}http://localhost:8000/docs{Colors.RESET}", flush=True)
    print(f"  PostgreSQL: localhost:5432", flush=True)
    if is_redis_running():
        print(f"  Redis:      localhost:6379 (caching enabled)", flush=True)
    else:
        print(f"  Redis:      {Colors.YELLOW}Not running (fallback to in-memory cache){Colors.RESET}", flush=True)
    print(f"\n{Colors.GREEN}Background processes:{Colors.RESET}", flush=True)
    if collector_running:
        print(f"  Real-time collector: Every 30 seconds (check data_collector.log)", flush=True)
    else:
        print(f"  Real-time collector: {Colors.YELLOW}Not running - start manually with:{Colors.RESET}", flush=True)
        print(f"    python main.py --loop --interval 30", flush=True)
    print(f"  Historical refresh: 30-day backfill running", flush=True)
    print(f"\n{Colors.BLUE}Data updates:{Colors.RESET}", flush=True)
    print(f"  Dashboard auto-refreshes every 30 seconds", flush=True)
    print(f"  Historical data updating in background (~5-7 min)", flush=True)
    print(f"\n{Colors.YELLOW}Press Ctrl+C to stop all services{Colors.RESET}", flush=True)
    sys.stdout.flush()

def main():
    """Main startup sequence."""
    # Immediate output to show script is running
    print("Starting Exchange Dashboard System...", flush=True)
    sys.stdout.flush()
    
    print_header()
    
    # Step 1: Check prerequisites
    if not check_prerequisites():
        print_status("\nPlease install missing prerequisites and try again.", "error")
        sys.exit(1)
    
    print()  # Empty line for spacing
    
    # Step 2: Start PostgreSQL
    if not start_postgres():
        print_status("\nFailed to start PostgreSQL. Please check Docker Desktop.", "error")
        sys.exit(1)
    
    print()  # Empty line for spacing
    
    # Step 3: Start Redis Cache
    start_redis()  # Don't fail if Redis doesn't start
    
    print()  # Empty line for spacing
    
    # Step 4: Check/install npm dependencies
    if not check_npm_dependencies():
        print_status("\nFailed to set up dashboard dependencies.", "error")
        sys.exit(1)
    
    print()  # Empty line for spacing
    
    # Step 4: Start API server
    if not start_api_server():
        print_status("\nFailed to start API server.", "error")
        sys.exit(1)
    
    print()  # Empty line for spacing
    
    # Step 5: Start React dashboard
    if not start_react_dashboard():
        print_status("\nFailed to start React dashboard.", "error")
        sys.exit(1)
    
    print()  # Empty line for spacing
    
    # Step 6: Start data collector (optional, don't fail if it doesn't work)
    collector_started = start_data_collector(quiet=True)
    
    print()  # Empty line for spacing
    
    # Step 7: Start background historical backfill
    backfill_thread = start_background_historical_backfill()
    
    print()  # Empty line for spacing
    
    # Step 8: Open browser
    open_dashboard()
    
    # Step 9: Show summary
    print_summary(collector_running=collector_started)
    
    # Keep running until Ctrl+C
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Shutting down...{Colors.RESET}")
        print("Services will continue running in the background.")
        print("To stop them completely, close the console windows or use Docker Desktop.")

if __name__ == "__main__":
    try:
        # Force immediate output
        print("Initializing startup script...", flush=True)
        sys.stdout.flush()
        
        # Check if running from a terminal that will close immediately
        if sys.platform == "win32" and not sys.stdin.isatty():
            # Add a pause for Windows when not running in interactive terminal
            import atexit
            atexit.register(lambda: input("\nPress Enter to exit..."))
        
        main()
    except Exception as e:
        print_status(f"\nUnexpected error: {e}", "error")
        print("\nFor help, check the README.md or run components manually.")
        sys.exit(1)