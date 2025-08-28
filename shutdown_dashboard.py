#!/usr/bin/env python3
"""
Shutdown Script for Exchange Dashboard
======================================
Cleanly stops all dashboard processes.
"""

import subprocess
import sys
import os
import time
import psutil
import signal
from pathlib import Path

def find_and_kill_process(port=None, name_pattern=None):
    """Find and kill processes by port or name pattern."""
    killed_count = 0
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Check by port
            if port:
                connections = proc.connections(kind='inet')
                for conn in connections:
                    if conn.laddr.port == port:
                        print(f"  Stopping process on port {port}: {proc.info['name']} (PID: {proc.info['pid']})")
                        proc.terminate()
                        killed_count += 1
                        break
            
            # Check by name pattern
            if name_pattern and proc.info['cmdline']:
                cmdline = ' '.join(proc.info['cmdline'])
                if name_pattern in cmdline:
                    print(f"  Stopping {name_pattern}: {proc.info['name']} (PID: {proc.info['pid']})")
                    proc.terminate()
                    killed_count += 1
                    
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    return killed_count

def cleanup_files():
    """Remove lock and status files."""
    files_to_remove = [
        ".backfill.lock",
        ".backfill.status",
        ".shutdown.lock"
    ]
    
    for file_path in files_to_remove:
        path = Path(file_path)
        if path.exists():
            try:
                path.unlink()
                print(f"  Removed {file_path}")
            except:
                pass

def shutdown_dashboard():
    """Main shutdown function."""
    print("\n" + "="*60)
    print("SHUTTING DOWN EXCHANGE DASHBOARD")
    print("="*60 + "\n")
    
    # Create shutdown lock to signal other processes
    shutdown_lock = Path(".shutdown.lock")
    shutdown_lock.touch()
    
    try:
        # 1. Stop React development server (port 3000)
        print("1. Stopping React dashboard...")
        killed = find_and_kill_process(port=3000)
        if killed > 0:
            print("   ✓ React dashboard stopped")
        else:
            print("   - React dashboard not running")
        
        # 2. Stop FastAPI server (port 8000)
        print("\n2. Stopping API server...")
        killed = find_and_kill_process(port=8000)
        if killed > 0:
            print("   ✓ API server stopped")
        else:
            print("   - API server not running")
        
        # 3. Stop data collector (main.py)
        print("\n3. Stopping data collector...")
        killed = find_and_kill_process(name_pattern="main.py")
        if killed > 0:
            print("   ✓ Data collector stopped")
        else:
            print("   - Data collector not running")
        
        # 4. Stop any backfill processes
        print("\n4. Stopping backfill processes...")
        killed = find_and_kill_process(name_pattern="backfill")
        if killed > 0:
            print("   ✓ Backfill processes stopped")
        else:
            print("   - No backfill processes running")
        
        # 5. PostgreSQL (just notify, don't stop)
        print("\n5. PostgreSQL database...")
        print("   ℹ PostgreSQL will continue running in Docker")
        print("   To stop it manually: docker-compose down")
        
        # 6. Clean up files
        print("\n6. Cleaning up temporary files...")
        cleanup_files()
        print("   ✓ Cleanup complete")
        
        # Wait a moment for processes to terminate
        time.sleep(2)
        
        # Final status
        print("\n" + "="*60)
        print("✓ DASHBOARD SHUTDOWN COMPLETE")
        print("="*60)
        print("\nAll dashboard processes have been stopped.")
        print("PostgreSQL remains running for data persistence.")
        print("\nTo restart the dashboard, run: python start.py")
        
    except Exception as e:
        print(f"\n✗ Error during shutdown: {e}")
        print("Some processes may need to be stopped manually.")
    
    finally:
        # Remove shutdown lock
        if shutdown_lock.exists():
            shutdown_lock.unlink()

if __name__ == "__main__":
    # Check if psutil is installed
    try:
        import psutil
    except ImportError:
        print("Installing required package: psutil...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
        import psutil
    
    shutdown_dashboard()