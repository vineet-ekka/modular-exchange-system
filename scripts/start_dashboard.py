"""
Dashboard Startup Script (Enhanced)
====================================
Launches the complete dashboard system with better error handling.
For a simpler experience, use start.py instead.
"""

import subprocess
import time
import os
import sys
import webbrowser
from pathlib import Path
import shutil

def check_command(command):
    """Check if a command is available."""
    return shutil.which(command) is not None

def check_docker_running():
    """Check if Docker daemon is running."""
    try:
        subprocess.run(["docker", "info"], capture_output=True, check=True, shell=True)
        return True
    except:
        return False

def check_postgres():
    """Check if PostgreSQL is running via Docker."""
    if not check_docker_running():
        print("⚠️  Docker is not running. Please start Docker Desktop.")
        return False
    
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

def start_postgres():
    """Start PostgreSQL using docker-compose."""
    print("Starting PostgreSQL...")
    
    # Check if Docker is running first
    if not check_docker_running():
        print("❌ Docker is not running. Please start Docker Desktop first.")
        return False
    
    try:
        # Navigate to parent directory where docker-compose.yml is located
        parent_dir = Path(__file__).parent.parent
        subprocess.run(
            ["docker-compose", "up", "-d", "postgres"],
            shell=True,
            cwd=parent_dir,
            check=True,
            capture_output=True
        )
        time.sleep(5)  # Wait for PostgreSQL to be ready
        print("✅ PostgreSQL started")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start PostgreSQL: {e}")
        print("   Make sure docker-compose.yml exists in the project root.")
        return False
    except Exception as e:
        print(f"❌ Unexpected error starting PostgreSQL: {e}")
        return False
    return True

def start_api_server():
    """Start the FastAPI backend server."""
    print("Starting API server...")
    
    # Check if Python is available
    if not check_command("python"):
        print("❌ Python not found in PATH")
        return False
    
    try:
        # Navigate to parent directory where api.py is located
        parent_dir = Path(__file__).parent.parent
        
        # Check if api.py exists
        if not (parent_dir / "api.py").exists():
            print(f"❌ api.py not found in {parent_dir}")
            return False
        
        # Start API server in a new window
        if sys.platform == "win32":
            subprocess.Popen(
                ["start", "cmd", "/k", "python", "api.py"],
                shell=True,
                cwd=parent_dir
            )
        else:
            subprocess.Popen(
                ["python", "api.py"],
                cwd=parent_dir
            )
        time.sleep(3)  # Wait for server to start
        print("✅ API server started at http://localhost:8000")
        print("   API docs available at http://localhost:8000/docs")
    except Exception as e:
        print(f"❌ Failed to start API server: {e}")
        return False
    return True

def start_react_dashboard():
    """Start the React frontend dashboard."""
    print("Starting React dashboard...")
    
    # Check if npm is available
    if not check_command("npm"):
        print("❌ npm not found. Please install Node.js from https://nodejs.org")
        return False
    
    # Navigate to parent directory, then to dashboard
    dashboard_path = Path(__file__).parent.parent / "dashboard"
    
    if not dashboard_path.exists():
        print(f"❌ Dashboard directory not found at {dashboard_path}")
        return False
    
    # Check if node_modules exists
    if not (dashboard_path / "node_modules").exists():
        print("⚠️  Dependencies not installed. Installing now...")
        print("   This may take a few minutes on first run...")
        try:
            subprocess.run(
                ["npm", "install"],
                shell=True,
                cwd=dashboard_path,
                check=True
            )
            print("✅ Dependencies installed")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            return False
    
    try:
        # Start React app in a new window
        if sys.platform == "win32":
            subprocess.Popen(
                ["start", "cmd", "/k", "npm", "start"],
                shell=True,
                cwd=dashboard_path
            )
        else:
            subprocess.Popen(
                ["npm", "start"],
                cwd=dashboard_path
            )
        time.sleep(5)  # Wait for React to compile
        print("✅ React dashboard started at http://localhost:3000")
    except Exception as e:
        print(f"❌ Failed to start React dashboard: {e}")
        return False
    return True

def start_data_collector():
    """Start the data collection system."""
    print("Starting data collector...")
    
    # Navigate to parent directory where main.py is located
    parent_dir = Path(__file__).parent.parent
    
    # Check if main.py exists (the new name for the collector)
    if not (parent_dir / "main.py").exists():
        print("⚠️  main.py not found. Data collector may not be available.")
        return
    
    try:
        # Start data collector in a new window with 30-second intervals
        if sys.platform == "win32":
            subprocess.Popen(
                ["start", "cmd", "/k", "python", "main.py", "--loop", "--interval", "30", "--quiet"],
                shell=True,
                cwd=parent_dir
            )
        else:
            subprocess.Popen(
                ["python", "main.py", "--loop", "--interval", "30", "--quiet"],
                cwd=parent_dir
            )
        print("✅ Data collector started (30-second intervals for real-time updates)")
    except Exception as e:
        print(f"⚠️  Failed to start data collector: {e}")
        print("   You can start it manually: python main.py --loop --interval 30")

def main():
    """Main startup sequence."""
    print("="*60)
    print("EXCHANGE DASHBOARD STARTUP (Enhanced)")
    print("="*60)
    print("\n💡 For a simpler experience, use: python ../start.py\n")
    
    # Check prerequisites
    print("Checking prerequisites...")
    missing = []
    if not check_command("python"):
        missing.append("Python")
    if not check_command("node"):
        missing.append("Node.js")
    if not check_command("npm"):
        missing.append("npm")
    if not check_command("docker"):
        missing.append("Docker")
    
    if missing:
        print(f"❌ Missing requirements: {', '.join(missing)}")
        print("Please install the missing tools and try again.")
        return
    
    print("✅ All prerequisites found")
    
    # Check and start PostgreSQL
    if not check_postgres():
        print("\nPostgreSQL not running. Starting...")
        if not start_postgres():
            print("Failed to start PostgreSQL. Please start Docker Desktop and try again.")
            return
    else:
        print("\n✅ PostgreSQL is already running")
    
    # Start API server
    if not start_api_server():
        print("Failed to start API server. Please check the logs.")
        return
    
    # Start React dashboard
    if not start_react_dashboard():
        print("Failed to start React dashboard. Please check if npm dependencies are installed.")
        return
    
    # Optional: Start data collector
    start_data_collector()
    
    print("\n" + "="*60)
    print("DASHBOARD STARTUP COMPLETE")
    print("="*60)
    print("\nServices running:")
    print("  📊 API Server: http://localhost:8000")
    print("  📈 API Docs: http://localhost:8000/docs")
    print("  🎨 Dashboard: http://localhost:3000")
    print("  🗄️ PostgreSQL: localhost:5432")
    print("\nOpening dashboard in browser...")
    
    # Open dashboard in browser
    time.sleep(3)
    webbrowser.open("http://localhost:3000")
    
    print("\nPress Ctrl+C in this window to stop all services")
    
    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutting down services...")
        print("Please close the opened command windows manually.")

if __name__ == "__main__":
    main()