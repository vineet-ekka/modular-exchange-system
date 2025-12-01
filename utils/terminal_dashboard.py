"""
Terminal Dashboard for Exchange Data System
===========================================
Live monitoring dashboard showing real-time system metrics with backfill monitoring
and admin control capabilities.
"""

import json
import time
import requests
import sys
import threading
import subprocess
import logging
import atexit
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Optional, List
from queue import Queue, Empty
from dataclasses import dataclass, field
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich import box

try:
    import msvcrt
    WINDOWS = True
except ImportError:
    import select
    import tty
    import termios
    WINDOWS = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('terminal_dashboard.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

console = Console()

MAX_BACKFILL_EXCHANGES = 15
BACKFILL_PANEL_SIZE = 22


@dataclass
class DashboardConfig:
    """
    Configuration for terminal dashboard.
    Provides sensible defaults for all tunable parameters.
    """

    api_url: str = "http://localhost:8000"
    api_read_timeout: int = 5
    api_write_timeout: int = 10

    react_dashboard_url: str = "http://localhost:3000"
    react_dashboard_timeout: int = 2

    update_interval: int = 30
    refresh_rate: float = 1.0

    max_backfill_exchanges: int = 15
    backfill_panel_size: int = 22

    log_level: str = "INFO"
    log_file: str = "terminal_dashboard.log"

    input_poll_interval: float = 0.1
    keyboard_sleep_interval: float = 0.05

    thread_join_timeout: float = 2.0

    metrics_file: Optional[Path] = None
    backfill_status_file: Optional[Path] = None

    def __post_init__(self) -> None:
        """Set default paths if not provided."""
        if self.metrics_file is None:
            self.metrics_file = Path(__file__).parent.parent / '.collection_metrics.json'
        if self.backfill_status_file is None:
            self.backfill_status_file = Path(__file__).parent.parent / '.unified_backfill.status'


class DashboardDataSource:
    """
    Data source layer for terminal dashboard.
    Handles all file I/O and API communication.
    """

    def __init__(
        self,
        api_url: str,
        metrics_file: Path,
        backfill_status_file: Path,
        session: requests.Session = None,
        read_timeout: int = 5,
        write_timeout: int = 10,
        react_dashboard_url: str = "http://localhost:3000",
        react_dashboard_timeout: int = 2
    ):
        """
        Initialize data source.

        Args:
            api_url: Base URL for API server
            metrics_file: Path to collection metrics JSON file
            backfill_status_file: Path to backfill status JSON file
            session: Optional requests.Session for connection pooling
            read_timeout: Timeout for GET requests in seconds
            write_timeout: Timeout for POST requests in seconds
            react_dashboard_url: URL for React dashboard health check
            react_dashboard_timeout: Timeout for dashboard health check
        """
        self.api_url = api_url
        self.metrics_file = metrics_file
        self.backfill_status_file = backfill_status_file
        self.session = session or requests.Session()
        self.read_timeout = read_timeout
        self.write_timeout = write_timeout
        self.react_dashboard_url = react_dashboard_url
        self.react_dashboard_timeout = react_dashboard_timeout
        logger.info(f"DashboardDataSource initialized with API: {api_url}")

    def get_collection_metrics(self) -> Optional[Dict]:
        """
        Get collection metrics from JSON file.

        Returns:
            Dict containing metrics if successful, None otherwise
        """
        try:
            with open(self.metrics_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.debug(f"Metrics file not found: {self.metrics_file}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse metrics JSON: {e}")
            return None
        except PermissionError as e:
            logger.error(f"Permission denied reading metrics file: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error reading metrics: {e}")
            return None

    def get_api_data(self, endpoint: str) -> Optional[Dict]:
        """
        Fetch data from API endpoint.

        Args:
            endpoint: API endpoint path (e.g., "/api/health")

        Returns:
            JSON response as dict if successful, None otherwise
        """
        try:
            response = self.session.get(f"{self.api_url}{endpoint}", timeout=self.read_timeout)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"API endpoint {endpoint} returned status {response.status_code}")
                return None
        except requests.exceptions.ConnectionError as e:
            logger.debug(f"Connection error for {endpoint}: {e}")
            return None
        except requests.exceptions.Timeout as e:
            logger.warning(f"Timeout fetching {endpoint}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from {endpoint}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {endpoint}: {e}")
            return None

    def get_backfill_status(self) -> Optional[Dict]:
        """
        Get backfill status from API first, fallback to file.

        Returns:
            Dict containing backfill status if available, None otherwise
        """
        api_data = self.get_api_data("/api/backfill/status")
        if api_data:
            return api_data

        try:
            with open(self.backfill_status_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.debug(f"Backfill status file not found: {self.backfill_status_file}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse backfill status JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error reading backfill status: {e}")
            return None

    def execute_api_call(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """
        Execute API call and return result.

        Args:
            method: HTTP method (GET or POST)
            endpoint: API endpoint path
            data: Optional JSON data for POST requests

        Returns:
            Dict with 'success' key and either 'data' or 'error' key
        """
        try:
            url = f"{self.api_url}{endpoint}"
            logger.info(f"API call: {method} {endpoint}")

            if method.upper() == "POST":
                response = self.session.post(url, json=data, timeout=self.write_timeout)
            else:
                response = self.session.get(url, timeout=self.read_timeout)

            if response.status_code == 200:
                result_data = response.json()
                logger.info(f"API call successful: {endpoint}")
                return {"success": True, "data": result_data}
            else:
                error_msg = f"HTTP {response.status_code}"
                logger.warning(f"API call failed: {endpoint} - {error_msg}")
                return {"success": False, "error": error_msg}
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout calling {endpoint}: {e}")
            logger.info(f"Hint: Is the API server running on {self.api_url}?")
            return {"success": False, "error": "Request timeout"}
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error calling {endpoint}: {e}")
            logger.info(f"Hint: Check if API server is accessible at {self.api_url}")
            return {"success": False, "error": "Connection failed"}
        except Exception as e:
            logger.error(f"Unexpected error calling {endpoint}: {e}")
            return {"success": False, "error": str(e)}

    def delete_backfill_status_file(self) -> bool:
        """
        Delete backfill status file.

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.backfill_status_file.exists():
                self.backfill_status_file.unlink()
                logger.info(f"Deleted backfill status file: {self.backfill_status_file}")
                return True
            return False
        except PermissionError as e:
            logger.error(f"Permission denied deleting backfill status file: {e}")
            return False
        except OSError as e:
            logger.error(f"OS error deleting backfill status file: {e}")
            return False

    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()
        logger.debug("Data source session closed")


class TerminalDashboard:
    """
    Interactive terminal dashboard for monitoring exchange data system.
    """

    def __init__(
        self,
        config: DashboardConfig = None,
        data_source: DashboardDataSource = None,
        interactive: bool = True
    ):
        """
        Initialize the terminal dashboard.

        Args:
            config: Optional DashboardConfig instance (uses defaults if None)
            data_source: Optional DashboardDataSource instance (for dependency injection/testing)
            interactive: Enable interactive keyboard controls
        """
        self.config = config or DashboardConfig()
        self.api_url = self.config.api_url
        self.update_interval = self.config.update_interval
        self.interactive = interactive
        self.start_time = datetime.now(timezone.utc)
        self.last_update = None
        self.last_command = None
        self.command_result = None
        self.running = True
        self.key_queue = Queue()
        self.input_thread = None
        self.old_terminal_settings = None
        self.pending_threads = []

        if data_source is None:
            session = requests.Session()
            self.data_source = DashboardDataSource(
                api_url=self.config.api_url,
                metrics_file=self.config.metrics_file,
                backfill_status_file=self.config.backfill_status_file,
                session=session,
                read_timeout=self.config.api_read_timeout,
                write_timeout=self.config.api_write_timeout,
                react_dashboard_url=self.config.react_dashboard_url,
                react_dashboard_timeout=self.config.react_dashboard_timeout
            )
            self._owns_data_source = True
        else:
            self.data_source = data_source
            self._owns_data_source = False

        atexit.register(self._cleanup)

    def _cleanup(self) -> None:
        """Cleanup resources on exit."""
        try:
            logger.info("Starting cleanup process")
            self.running = False

            if not WINDOWS and self.old_terminal_settings is not None:
                try:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_terminal_settings)
                    logger.info("Terminal settings restored")
                except Exception as e:
                    logger.error(f"Failed to restore terminal settings: {e}")

            for thread in self.pending_threads:
                if thread.is_alive():
                    thread.join(timeout=self.config.thread_join_timeout)
                    if thread.is_alive():
                        logger.warning(f"Thread {thread.name} did not terminate in time")

            if self._owns_data_source:
                self.data_source.close()

            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def create_service_status_panel(self) -> Panel:
        """Create panel showing service status."""
        table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
        table.add_column("Service", style="cyan", width=25)
        table.add_column("Status", width=30)

        health_data = self.data_source.get_api_data("/api/health")

        if health_data and health_data.get("status") == "healthy":
            db_status = "[green]✓ UP[/green]"
        else:
            db_status = "[red]✗ DOWN[/red]"

        table.add_row("PostgreSQL (5432)", db_status)

        cache_data = self.data_source.get_api_data("/api/health/cache")
        if cache_data and cache_data.get("status") == "healthy":
            redis_status = f"[green]✓ UP[/green] ({cache_data.get('redis', {}).get('type', 'Unknown')})"
        else:
            redis_status = "[yellow]⚠ Fallback[/yellow] (SimpleCache)"

        table.add_row("Redis (6379)", redis_status)

        if health_data:
            api_status = "[green]✓ UP[/green]"
        else:
            api_status = "[yellow]⚠ STARTING[/yellow]"

        table.add_row("API Server (8000)", api_status)

        try:
            dashboard_check = self.data_source.session.get(
                self.data_source.react_dashboard_url,
                timeout=self.data_source.react_dashboard_timeout
            )
            dashboard_status = "[green]✓ UP[/green]"
        except requests.exceptions.RequestException as e:
            logger.debug(f"React dashboard check failed: {e}")
            dashboard_status = "[yellow]⚠ DOWN[/yellow]"

        react_port = self.data_source.react_dashboard_url.split(':')[-1] if ':' in self.data_source.react_dashboard_url else "3000"
        table.add_row(f"React Dashboard ({react_port})", dashboard_status)

        uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        uptime_str = self._format_duration(uptime)
        table.add_row("", "")
        table.add_row("System Uptime", f"[dim]{uptime_str}[/dim]")

        return Panel(table, title="[bold cyan]Service Status[/bold cyan]", border_style="cyan")

    def create_collection_timing_panel(self) -> Panel:
        """Create panel showing collection timing information."""
        metrics = self.data_source.get_collection_metrics()

        if not metrics:
            text = Text("Waiting for first collection cycle...", style="yellow italic")
            return Panel(text, title="[bold green]Collection Timing[/bold green]", border_style="green")

        table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
        table.add_column("Metric", style="cyan", width=20)
        table.add_column("Value", width=35)

        total_duration_ms = metrics.get('total_duration_ms', 0)
        total_contracts = sum(
            ex.get('record_count', 0)
            for ex in metrics.get('exchanges', {}).values()
        )

        speed = (
            (total_contracts / total_duration_ms) * 1000
            if total_duration_ms > 0
            else 0
        )

        table.add_row("Last Run Duration", f"[bold]{total_duration_ms/1000:.2f}s[/bold]")
        table.add_row("Contracts Collected", f"[bold]{total_contracts:,}[/bold]")
        table.add_row("Collection Speed", f"[bold]{speed:.1f}[/bold] contracts/sec")

        success_count = metrics.get('success_count', 0)
        failure_count = metrics.get('failure_count', 0)
        total_exchanges = success_count + failure_count

        if failure_count > 0:
            success_text = f"[yellow]{success_count}/{total_exchanges}[/yellow]"
        else:
            success_text = f"[green]{success_count}/{total_exchanges}[/green]"

        table.add_row("Exchange Success", success_text)

        batch_timestamp = metrics.get('batch_timestamp')
        if batch_timestamp:
            try:
                batch_time = datetime.fromisoformat(batch_timestamp)
                time_ago = (datetime.now(timezone.utc) - batch_time).total_seconds()
                table.add_row("Last Collection", f"[dim]{self._format_duration(time_ago)} ago[/dim]")

                next_run = self.update_interval - (time_ago % self.update_interval)
                if next_run > 0:
                    table.add_row("Next Collection", f"[dim]in {int(next_run)}s[/dim]")
            except ValueError as e:
                logger.error(f"Failed to parse batch timestamp '{batch_timestamp}': {e}")
            except Exception as e:
                logger.error(f"Unexpected error processing batch timestamp: {e}")

        return Panel(table, title="[bold green]Collection Timing[/bold green]", border_style="green")

    def create_exchange_health_panel(self) -> Panel:
        """Create panel showing exchange health scores."""
        metrics = self.data_source.get_collection_metrics()

        if not metrics or not metrics.get('exchanges'):
            text = Text("No exchange data available yet", style="yellow italic")
            return Panel(text, title="[bold magenta]Exchange Health (All Exchanges)[/bold magenta]", border_style="magenta")

        table = Table(show_header=True, box=box.SIMPLE_HEAD, padding=(0, 1))
        table.add_column("Exchange", style="cyan", width=12)
        table.add_column("Contracts", justify="right", width=9)
        table.add_column("Time", justify="right", width=9)
        table.add_column("Speed", justify="right", width=10)
        table.add_column("Status", width=8)

        exchanges = metrics.get('exchanges', {})
        exchange_list = sorted(exchanges.items(), key=lambda x: x[0].lower())

        for exchange_name, exchange_data in exchange_list:
            duration_ms = exchange_data.get('duration_ms', 0)
            record_count = exchange_data.get('record_count', 0)
            status = exchange_data.get('status', 'unknown')

            if record_count > 0 and duration_ms > 0:
                speed = (record_count / duration_ms) * 1000
                speed_str = f"{speed:.1f} c/s"
            else:
                speed_str = "N/A"

            duration_str = f"{duration_ms/1000:.2f}s"

            if status == 'success':
                if duration_ms >= 10000:
                    status_display = "[red]SLOW[/red]"
                    duration_str = f"[red]{duration_str}[/red]"
                elif duration_ms >= 5000:
                    status_display = "[yellow]OK[/yellow]"
                    duration_str = f"[yellow]{duration_str}[/yellow]"
                else:
                    status_display = "[green]✓[/green]"
            elif status == 'timeout':
                status_display = "[yellow]TIMEOUT[/yellow]"
            elif status == 'error':
                status_display = "[red]ERROR[/red]"
            else:
                status_display = "[dim]?[/dim]"

            table.add_row(
                exchange_name,
                f"{record_count:,}",
                duration_str,
                speed_str,
                status_display
            )

        return Panel(table, title="[bold magenta]Exchange Health (All Exchanges)[/bold magenta]", border_style="magenta")

    def create_system_statistics_panel(self) -> Panel:
        """Create panel showing system statistics."""
        table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
        table.add_column("Metric", style="cyan", width=25)
        table.add_column("Value", width=30)

        stats_data = self.data_source.get_api_data("/api/statistics/summary")

        if stats_data:
            total_contracts = stats_data.get('total_contracts', 0)
            total_exchanges = stats_data.get('total_exchanges', 0)
            unique_assets = stats_data.get('unique_assets', 0)

            table.add_row("Total Contracts", f"[bold]{total_contracts:,}[/bold]")
            table.add_row("Active Exchanges", f"[bold]{total_exchanges}[/bold]")
            table.add_row("Unique Assets", f"[bold]{unique_assets}[/bold]")
        else:
            table.add_row("Status", "[yellow]Fetching data...[/yellow]")

        cache_data = self.data_source.get_api_data("/api/health/cache")
        if cache_data:
            cache_type = cache_data.get('redis', {}).get('type', 'Unknown')
            if cache_type == 'Redis':
                cache_entries = cache_data.get('redis', {}).get('keys', 0)
                cache_memory = cache_data.get('redis', {}).get('used_memory_human', 'N/A')
                table.add_row("", "")
                table.add_row("Cache Type", f"[green]Redis[/green]")
                table.add_row("Cache Entries", f"{cache_entries:,}")
                table.add_row("Cache Memory", cache_memory)
            else:
                cache_entries = cache_data.get('fallback', {}).get('entries', 0)
                table.add_row("", "")
                table.add_row("Cache Type", f"[yellow]Fallback[/yellow]")
                table.add_row("Cache Entries", f"{cache_entries}")

        return Panel(table, title="[bold yellow]System Statistics[/bold yellow]", border_style="yellow")

    def create_backfill_progress_panel(self) -> Panel:
        """Create panel showing backfill progress."""
        backfill_data = self.data_source.get_backfill_status()

        if not backfill_data or not backfill_data.get('running'):
            if backfill_data and backfill_data.get('completed'):
                return self.create_backfill_completion_summary(backfill_data)
            elif backfill_data and backfill_data.get('message'):
                text = Text(backfill_data.get('message', 'No backfill running'), style="dim")
            else:
                text = Text("No backfill operation currently running", style="dim")
            return Panel(text, title="[bold blue]Backfill Progress[/bold blue]", border_style="blue")

        table = Table(show_header=True, box=box.SIMPLE_HEAD, padding=(0, 1))
        table.add_column("Exchange", style="cyan", width=12)
        table.add_column("Progress", width=30)
        table.add_column("Time/Speed", width=18)
        table.add_column("Status", width=12)

        overall_progress = backfill_data.get('overall_progress', 0)
        total_records = backfill_data.get('total_records', 0)
        exchanges_data = backfill_data.get('exchanges', {})
        completeness_data = backfill_data.get('completeness', {})

        completed_exchanges = sum(
            1 for ex in exchanges_data.values()
            if ex.get('status') == 'completed'
        )
        total_exchanges = len(exchanges_data)

        header_text = Text()
        header_text.append(f"Overall: ", style="bold")
        header_text.append(f"{overall_progress:.1f}%", style="bold green" if overall_progress >= 90 else "bold yellow")
        header_text.append(f" | ", style="dim")
        header_text.append(f"{completed_exchanges}/{total_exchanges} exchanges", style="bold")
        header_text.append(f" | ", style="dim")
        header_text.append(f"{total_records:,} records", style="bold cyan")

        sorted_exchanges = sorted(
            exchanges_data.items(),
            key=lambda x: x[1].get('progress', 0),
            reverse=True
        )

        for exchange_name, exchange_info in sorted_exchanges[:self.config.max_backfill_exchanges]:
            progress = exchange_info.get('progress', 0)
            status = exchange_info.get('status', 'unknown')
            symbols_processed = exchange_info.get('symbols_processed', 0)
            total_symbols = exchange_info.get('total_symbols', 0)
            records_fetched = exchange_info.get('records_fetched', 0)
            elapsed_time = exchange_info.get('elapsed_time', 0)
            estimated_remaining = exchange_info.get('estimated_remaining', 0)

            bar_width = 20
            filled = int((progress / 100) * bar_width)
            bar = "▓" * filled + "░" * (bar_width - filled)

            progress_text = f"{bar} {progress:.0f}%"

            # Format timing/speed display
            if elapsed_time > 0:
                time_str = self._format_duration(elapsed_time)
                if status == 'completed' and symbols_processed > 0:
                    speed = symbols_processed / elapsed_time
                    timing_display = f"{time_str} ({speed:.1f}c/s)"
                elif status == 'processing' and estimated_remaining > 0:
                    est_str = self._format_duration(estimated_remaining)
                    timing_display = f"{time_str} (~{est_str})"
                else:
                    timing_display = time_str
            else:
                timing_display = "[dim]--[/dim]"

            if status == 'completed':
                status_display = "[green]✓ DONE[/green]"
                completeness = completeness_data.get(exchange_name, {})
                complete_count = completeness.get('complete', 0)
                total_count = completeness.get('total', 0)
                if total_count > 0:
                    status_display = f"[green]✓ {complete_count}/{total_count}[/green]"
            elif status == 'processing':
                status_display = f"[yellow]{symbols_processed}/{total_symbols}[/yellow]"
            elif status == 'error':
                status_display = "[red]✗ ERROR[/red]"
            elif status == 'no_data':
                status_display = "[dim]NO DATA[/dim]"
            else:
                status_display = "[dim]PENDING[/dim]"

            table.add_row(exchange_name, progress_text, timing_display, status_display)

        if len(exchanges_data) > self.config.max_backfill_exchanges:
            table.add_row("[dim]...[/dim]", f"[dim]({len(exchanges_data) - self.config.max_backfill_exchanges} more)[/dim]", "", "")

        panel_content = Table.grid(padding=(0, 0))
        panel_content.add_row(header_text)
        panel_content.add_row("")
        panel_content.add_row(table)

        return Panel(panel_content, title="[bold blue]Backfill Progress[/bold blue]", border_style="blue")

    def create_backfill_completion_summary(self, backfill_data: dict) -> Panel:
        """Create detailed summary of completed backfill."""
        from rich.console import Group

        table = Table(show_header=True, box=box.SIMPLE_HEAD, padding=(0, 1))
        table.add_column("Exchange", style="cyan", width=12)
        table.add_column("Status", width=12)
        table.add_column("Symbols", justify="right", width=10)
        table.add_column("Records", justify="right", width=12)
        table.add_column("Time", justify="right", width=10)

        exchanges_data = backfill_data.get('exchanges', {})
        total_records = sum(ex.get('records_fetched', 0) for ex in exchanges_data.values())
        total_time = backfill_data.get('total_time', 0)

        success_count = sum(1 for ex in exchanges_data.values() if ex.get('status') == 'completed')
        failed_count = sum(1 for ex in exchanges_data.values() if ex.get('status') == 'failed')
        total_count = len(exchanges_data)

        header = Text()
        header.append("COMPLETED: ", style="bold green")
        header.append(f"{success_count}/{total_count} exchanges", style="bold")
        if failed_count > 0:
            header.append(f" ({failed_count} failed)", style="bold red")
        header.append(" | ", style="dim")
        header.append(f"{total_records:,} records", style="bold cyan")
        header.append(" | ", style="dim")
        header.append(f"{int(total_time)}s", style="bold yellow")

        for exchange_name, exchange_info in sorted(exchanges_data.items()):
            status = exchange_info.get('status', 'unknown')
            symbols = exchange_info.get('symbols_processed', 0)
            records = exchange_info.get('records_fetched', 0)
            elapsed = exchange_info.get('elapsed_time', 0)

            status_display = "[OK]" if status == "completed" else "[FAIL]"
            status_style = "green" if status == "completed" else "red"

            table.add_row(
                exchange_name,
                Text(status_display + " " + status, style=status_style),
                f"{symbols:,}",
                f"{records:,}",
                f"{int(elapsed)}s"
            )

        return Panel(
            Group(header, Text(""), table),
            title="[bold green]Backfill Completed[/bold green]",
            border_style="green",
            padding=(1, 2)
        )

    def _setup_terminal(self) -> None:
        """Setup terminal for non-blocking input (Unix only)."""
        if not WINDOWS:
            try:
                self.old_terminal_settings = termios.tcgetattr(sys.stdin)
                tty.setcbreak(sys.stdin.fileno())
                logger.info("Terminal configured for non-blocking input")
            except Exception as e:
                logger.error(f"Failed to configure terminal: {e}")
                raise

    def _input_reader_thread(self) -> None:
        """Background thread that reads keyboard input and puts it in queue."""
        logger.info("Input reader thread started")
        try:
            while self.running:
                try:
                    if WINDOWS:
                        if msvcrt.kbhit():
                            key = msvcrt.getch()
                            try:
                                decoded = key.decode('utf-8').lower()
                                if len(decoded) == 1 and decoded.isprintable():
                                    self.key_queue.put(decoded)
                                    logger.debug(f"Key pressed: {decoded}")
                            except UnicodeDecodeError as e:
                                logger.warning(f"Failed to decode key: {e}")
                        else:
                            time.sleep(self.config.keyboard_sleep_interval)
                    else:
                        rlist, _, _ = select.select([sys.stdin], [], [], self.config.input_poll_interval)
                        if rlist:
                            key = sys.stdin.read(1).lower()
                            if len(key) == 1 and (key.isprintable() or key.isspace()):
                                self.key_queue.put(key)
                                logger.debug(f"Key pressed: {key}")
                            else:
                                logger.debug(f"Ignoring non-printable key: {repr(key)}")
                except OSError as e:
                    logger.error(f"OS error in input thread: {e}")
                    time.sleep(0.1)
                except Exception as e:
                    logger.error(f"Unexpected error in input thread: {e}")
                    time.sleep(0.1)
        except Exception as e:
            logger.error(f"Fatal error in input thread: {e}")
        finally:
            logger.info("Input reader thread stopped")

    def get_keypress(self) -> Optional[str]:
        """Get a single keypress without blocking (non-blocking input)."""
        try:
            return self.key_queue.get_nowait()
        except Empty:
            return None

    def clear_cache_action(self) -> None:
        """Clear Redis/fallback cache."""
        self.last_command = "Clearing cache..."
        result = self.data_source.execute_api_call("POST", "/api/cache/clear")
        if result["success"]:
            entries = result["data"].get("entries_cleared", 0)
            self.command_result = f"Cache cleared: {entries} entries removed"
        else:
            self.command_result = f"Failed to clear cache: {result.get('error', 'Unknown error')}"

    def start_backfill_action(self) -> None:
        """Start historical backfill."""
        self.last_command = "Starting backfill..."
        result = self.data_source.execute_api_call("POST", "/api/backfill/start", {"days": 30, "parallel": True})
        if result["success"]:
            self.command_result = "Backfill started successfully (30 days, parallel mode)"
        else:
            self.command_result = f"Failed to start backfill: {result.get('error', 'Unknown error')}"

    def stop_backfill_action(self) -> None:
        """Stop running backfill."""
        self.last_command = "Stopping backfill..."
        result = self.data_source.execute_api_call("POST", "/api/backfill/stop")
        if result["success"]:
            self.command_result = "Backfill stopped successfully"
            self.data_source.delete_backfill_status_file()
        else:
            self.command_result = f"Failed to stop backfill: {result.get('error', 'Unknown error')}"

    def shutdown_system_action(self) -> None:
        """Shutdown all services."""
        self.last_command = "Initiating system shutdown..."
        result = self.data_source.execute_api_call("POST", "/api/shutdown")
        if result["success"]:
            self.command_result = "System shutdown initiated. Exiting monitor..."
            self.running = False
        else:
            self.command_result = f"Failed to shutdown: {result.get('error', 'Unknown error')}"

    def show_help(self) -> None:
        """Display help information."""
        self.last_command = "Help"
        self.command_result = (
            "Keyboard Shortcuts: "
            "[C]ache clear | [B]ackfill start | [X]top backfill | "
            "[Q]uit monitor | [S]hutdown system | [H]elp"
        )

    def _start_action_thread(self, target, name: str) -> None:
        """Start a non-daemon action thread and track it."""
        thread = threading.Thread(target=target, daemon=False, name=name)
        self.pending_threads.append(thread)
        thread.start()
        logger.info(f"Started action thread: {name}")

        self.pending_threads = [t for t in self.pending_threads if t.is_alive()]

    def handle_keypress(self, key: str) -> None:
        """Handle keyboard input and execute commands."""
        logger.debug(f"Handling keypress: {key}")

        if key == 'c':
            self._start_action_thread(self.clear_cache_action, "clear_cache")
        elif key == 'b':
            self._start_action_thread(self.start_backfill_action, "start_backfill")
        elif key == 'x':
            self._start_action_thread(self.stop_backfill_action, "stop_backfill")
        elif key == 's':
            self._start_action_thread(self.shutdown_system_action, "shutdown_system")
        elif key == 'h':
            self.show_help()
        elif key == 'q':
            logger.info("User requested quit")
            self.running = False

    def create_controls_panel(self) -> Panel:
        """Create panel showing keyboard controls and command status."""
        table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
        table.add_column("Controls", style="white", width=100)

        controls_text = Text()
        controls_text.append("[C]ache ", style="bold magenta")
        controls_text.append("[B]ackfill ", style="bold blue")
        controls_text.append("[X]top ", style="bold red")
        controls_text.append("[S]hutdown ", style="bold yellow")
        controls_text.append("[H]elp ", style="bold cyan")
        controls_text.append("[Q]uit", style="bold red")

        table.add_row(controls_text)

        if self.last_command:
            status_text = Text()
            status_text.append("Last: ", style="dim")
            status_text.append(self.last_command, style="yellow bold")
            if self.command_result:
                status_text.append(" | ", style="dim")
                style = "green" if "success" in self.command_result.lower() or "cleared" in self.command_result.lower() else "red"
                status_text.append(self.command_result, style=style)
            table.add_row(status_text)

        title = "[bold white]Interactive Admin Controls[/bold white]" if self.interactive else "[bold white]Admin Controls (Read-Only)[/bold white]"
        return Panel(table, title=title, border_style="white")

    def create_layout(self) -> Layout:
        """Create the dashboard layout."""
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="backfill_section", size=self.config.backfill_panel_size),
            Layout(name="controls", size=5),
            Layout(name="footer", size=3)
        )

        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )

        layout["left"].split_column(
            Layout(name="services"),
            Layout(name="timing")
        )

        layout["right"].split_column(
            Layout(name="health"),
            Layout(name="stats")
        )

        header_text = Text.assemble(
            ("EXCHANGE DATA SYSTEM", "bold cyan"),
            " - ",
            ("Live Monitoring Dashboard", "bold white"),
            " | ",
            ("Enhanced Edition", "bold green")
        )
        layout["header"].update(Panel(header_text, style="bold cyan"))

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        if self.interactive:
            footer_text = f"Last Update: {now} | Interactive Mode | Press Q to quit, H for help | Update: {self.update_interval}s"
        else:
            footer_text = f"Last Update: {now} | Press Ctrl+C to exit | Update Interval: {self.update_interval}s"
        layout["footer"].update(Panel(footer_text, style="dim"))

        return layout

    def update_layout(self, layout: Layout, full_update: bool = True) -> None:
        """Update all panels in the layout."""
        if full_update:
            layout["services"].update(self.create_service_status_panel())
            layout["timing"].update(self.create_collection_timing_panel())
            layout["health"].update(self.create_exchange_health_panel())
            layout["stats"].update(self.create_system_statistics_panel())
            layout["backfill_section"].update(self.create_backfill_progress_panel())

        layout["controls"].update(self.create_controls_panel())

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        if self.interactive:
            footer_text = f"Last Update: {now} | Interactive Mode | Press Q to quit, H for help | Update: {self.update_interval}s"
        else:
            footer_text = f"Last Update: {now} | Press Ctrl+C to exit | Update Interval: {self.update_interval}s"
        layout["footer"].update(Panel(footer_text, style="dim"))

    def run(self) -> None:
        """Run the dashboard in live mode with interactive controls."""
        logger.info("Starting terminal dashboard")

        if self.interactive:
            console.print("\n[bold cyan]Starting Interactive Monitoring Dashboard...[/bold cyan]")
            console.print("[yellow]Press H for help, Q to quit[/yellow]\n")

            try:
                self._setup_terminal()
            except Exception as e:
                console.print(f"[red]Failed to setup terminal: {e}[/red]")
                logger.error(f"Terminal setup failed: {e}")
                return

            self.input_thread = threading.Thread(
                target=self._input_reader_thread,
                daemon=False,
                name="input_reader"
            )
            self.input_thread.start()
            logger.info("Input thread started")
        else:
            console.print("\n[bold cyan]Starting Live Monitoring Dashboard...[/bold cyan]\n")

        time.sleep(1)

        layout = self.create_layout()
        self.update_layout(layout)

        try:
            with Live(layout, console=console, refresh_per_second=self.config.refresh_rate, screen=False) as live:
                last_update_time = time.time()

                while self.running:
                    keys_processed = False

                    if self.interactive:
                        while True:
                            key = self.get_keypress()
                            if not key:
                                break
                            self.handle_keypress(key)
                            keys_processed = True
                            if not self.running:
                                break

                        if keys_processed:
                            self.update_layout(layout, full_update=False)
                            live.update(layout)

                    if not self.running:
                        break

                    current_time = time.time()
                    if current_time - last_update_time >= self.update_interval:
                        self.update_layout(layout, full_update=True)
                        live.update(layout)
                        last_update_time = current_time

                    sleep_time = min(self.config.input_poll_interval, max(0.01, self.update_interval - (time.time() - last_update_time)))
                    time.sleep(sleep_time)

            if self.command_result and "shutdown" in self.command_result.lower():
                console.print("\n\n[yellow]System shutdown in progress...[/yellow]")
            else:
                console.print("\n\n[yellow]Dashboard stopped by user[/yellow]")

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Dashboard stopped by user[/yellow]")
            logger.info("Dashboard stopped by KeyboardInterrupt")
        finally:
            if self.input_thread and self.input_thread.is_alive():
                logger.info("Waiting for input thread to terminate...")
                self.input_thread.join(timeout=2.0)
            logger.info("Terminal dashboard stopped")

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """
        Format duration in seconds to human-readable string.

        Args:
            seconds: Duration in seconds (can be negative)

        Returns:
            Formatted string like "2d 3h 45m" or "1h 23m 45s"
        """
        if seconds < 0:
            return f"-{TerminalDashboard._format_duration(-seconds)}"

        days, remainder = divmod(int(seconds), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, secs = divmod(remainder, 60)

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if secs > 0 or not parts:
            parts.append(f"{secs}s")

        return " ".join(parts)

def main():
    """Main entry point for standalone testing."""
    dashboard = TerminalDashboard()
    dashboard.run()

if __name__ == "__main__":
    main()
