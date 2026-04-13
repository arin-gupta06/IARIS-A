"""
IARIS TUI Dashboard — Rich Terminal UI with Textual

Real-time terminal dashboard showing:
- System state panel (CPU, Memory, I/O, state indicator)
- Process list with behavior classification and scores
- Workload groups
- Reasoning panel with latest decisions
"""

from __future__ import annotations

import asyncio
import time
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.reactive import reactive
from textual.widgets import Header, Footer, Static, DataTable, Label, ProgressBar
from textual.timer import Timer
from rich.text import Text
from rich.table import Table
from rich.panel import Panel
from rich.console import Group

from iaris.engine import IARISEngine
from iaris.models import SystemState, BehaviorType, AllocationAction


# ─── Widgets ──────────────────────────────────────────────────────────────────

class SystemPanel(Static):
    """Shows system-wide metrics and state."""

    def render(self) -> Panel:
        app: IARISDashboard = self.app  # type: ignore
        system = app.engine.system

        state_colors = {
            SystemState.STABLE: "green",
            SystemState.PRESSURE: "yellow",
            SystemState.CRITICAL: "red",
        }
        state_color = state_colors.get(system.state, "white")

        # Build metrics display
        content = Text()
        content.append("CPU: ", style="bold")
        cpu_color = "green" if system.cpu_percent < 70 else "yellow" if system.cpu_percent < 90 else "red"
        content.append(f"{system.cpu_percent:.1f}%", style=cpu_color)
        content.append(f"  ({system.cpu_count} cores)\n")

        content.append("MEM: ", style="bold")
        mem_color = "green" if system.memory_percent < 75 else "yellow" if system.memory_percent < 90 else "red"
        content.append(f"{system.memory_percent:.1f}%", style=mem_color)
        content.append(f"  ({system.memory_available_gb:.1f} GB free)\n")

        content.append("I/O: ", style="bold")
        content.append(f"R:{system.disk_io_read_rate/1024:.0f} KB/s  W:{system.disk_io_write_rate/1024:.0f} KB/s\n")

        content.append("NET: ", style="bold")
        content.append(f"↑{system.net_io_send_rate/1024:.0f} KB/s  ↓{system.net_io_recv_rate/1024:.0f} KB/s\n")

        content.append("\nState: ", style="bold")
        content.append(f" {system.state.value.upper()} ", style=f"bold white on {state_color}")
        content.append(f"  ({system.behavior.value})\n")

        content.append("Processes: ", style="bold")
        content.append(f"{system.process_count}")

        return Panel(content, title="⚙ System", border_style=state_color)


class ProcessTable(Static):
    """Shows process list with behavior classification."""

    def render(self) -> Panel:
        app: IARISDashboard = self.app  # type: ignore
        profiles = app.engine.profiles

        table = Table(show_header=True, header_style="bold cyan", expand=True, box=None)
        table.add_column("PID", width=7)
        table.add_column("Name", width=22)
        table.add_column("Type", width=18)
        table.add_column("CPU%", width=7, justify="right")
        table.add_column("MEM%", width=7, justify="right")
        table.add_column("Score", width=7, justify="right")

        type_colors = {
            BehaviorType.CPU_HOG: "red",
            BehaviorType.LATENCY_SENSITIVE: "green",
            BehaviorType.BURSTY: "yellow",
            BehaviorType.BLOCKING: "magenta",
            BehaviorType.MEMORY_HEAVY: "blue",
            BehaviorType.IDLE: "dim",
            BehaviorType.UNKNOWN: "white",
        }

        # Sort by CPU and show top entries
        sorted_profiles = sorted(profiles.values(), key=lambda p: p.avg_cpu, reverse=True)
        for profile in sorted_profiles[:20]:
            color = type_colors.get(profile.behavior_type, "white")
            score_color = "green" if profile.allocation_score >= 0.6 else "yellow" if profile.allocation_score >= 0.3 else "red"
            table.add_row(
                str(profile.pid),
                profile.name[:22],
                Text(profile.behavior_type.value, style=color),
                f"{profile.avg_cpu:.1f}",
                f"{profile.avg_memory:.1f}",
                Text(f"{profile.allocation_score:.3f}", style=score_color),
            )

        return Panel(table, title=f"📊 Processes ({len(profiles)} tracked)", border_style="cyan")


class WorkloadPanel(Static):
    """Shows workload group status."""

    def render(self) -> Panel:
        app: IARISDashboard = self.app  # type: ignore
        workloads = app.engine.workload.get_status()

        content = Text()
        for wg in workloads:
            members = wg["member_count"]
            if members > 0:
                content.append(f"● {wg['name']}", style="bold")
                content.append(f" ({members} procs)\n")
                content.append(f"  CPU: {wg['total_cpu']:.1f}%  MEM: {wg['total_memory']:.1f}%")
                content.append(f"  Priority: {wg['priority']:.1f}\n\n")
            else:
                content.append(f"○ {wg['name']}", style="dim")
                content.append(f" (empty)\n")

        if not content.plain.strip():
            content.append("No workloads configured", style="dim")

        return Panel(content, title="🔗 Workloads", border_style="blue")


class ReasoningPanel(Static):
    """Shows recent allocation decisions with reasoning."""

    def render(self) -> Panel:
        app: IARISDashboard = self.app  # type: ignore
        decisions = app.engine.decisions

        content = Text()
        action_styles = {
            AllocationAction.BOOST: "bold green",
            AllocationAction.MAINTAIN: "white",
            AllocationAction.THROTTLE: "yellow",
            AllocationAction.PAUSE: "bold red",
        }

        for decision in decisions[-8:]:
            style = action_styles.get(decision.action, "white")
            content.append(f"[{decision.action.value:>8}] ", style=style)
            content.append(f"{decision.process_name}: ", style="bold")
            # Truncate reason for display
            reason = decision.reason[:100]
            content.append(f"{reason}\n", style="dim")

        if not content.plain.strip():
            content.append("No decisions yet — observing...", style="dim italic")

        return Panel(content, title="🧠 Reasoning", border_style="yellow")


class DummyPanel(Static):
    """Shows dummy process status."""

    def render(self) -> Panel:
        app: IARISDashboard = self.app  # type: ignore
        dummies = app.engine.simulator.get_status()

        content = Text()
        for d in dummies:
            status = "●" if d["is_alive"] else "✗"
            color = "green" if d["is_alive"] else "red"
            content.append(f"  {status} ", style=color)
            content.append(f"PID {d['pid']} — {d['behavior_type']}")
            content.append(f" ({d['uptime_seconds']:.0f}s)\n")

        if not dummies:
            content.append("  No dummy processes running\n", style="dim")

        content.append(f"\n  Press 'd' to spawn demo set, 'x' to stop all", style="dim italic")

        return Panel(content, title="🎯 Dummy Processes", border_style="magenta")


# ─── Main Dashboard App ──────────────────────────────────────────────────────

class IARISDashboard(App):
    """IARIS Terminal Dashboard — Real-time system intelligence."""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 2 3;
        grid-gutter: 1;
        padding: 1;
    }

    #system-panel {
        column-span: 1;
    }

    #dummy-panel {
        column-span: 1;
    }

    #process-table {
        column-span: 2;
    }

    #workload-panel {
        column-span: 1;
    }

    #reasoning-panel {
        column-span: 1;
    }
    """

    TITLE = "IARIS — Intent-Aware Adaptive Resource Intelligence"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "spawn_demo", "Spawn Demo"),
        ("x", "stop_all", "Stop All"),
        ("r", "refresh", "Refresh"),
    ]

    def __init__(self):
        super().__init__()
        self.engine = IARISEngine()

    def compose(self) -> ComposeResult:
        yield Header()
        yield SystemPanel(id="system-panel")
        yield DummyPanel(id="dummy-panel")
        yield ProcessTable(id="process-table")
        yield WorkloadPanel(id="workload-panel")
        yield ReasoningPanel(id="reasoning-panel")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize engine and start refresh timer."""
        self.engine.initialize()
        # Do initial sample
        self.engine.monitor.sample_once()
        self.engine._process_tick(self.engine.system, self.engine.monitor.processes)
        # Refresh every second
        self.set_interval(1.0, self._tick)

    def _tick(self) -> None:
        """Called every second to update monitoring."""
        system, processes = self.engine.monitor.sample_once()
        self.engine._process_tick(system, processes)
        self._refresh_panels()

    def _refresh_panels(self) -> None:
        """Refresh all dashboard panels."""
        for widget_id in ["system-panel", "process-table", "workload-panel",
                          "reasoning-panel", "dummy-panel"]:
            try:
                self.query_one(f"#{widget_id}").refresh()
            except Exception:
                pass

    def action_spawn_demo(self) -> None:
        """Spawn demo dummy processes."""
        self.engine.simulator.spawn_demo_set()
        self._refresh_panels()

    def action_stop_all(self) -> None:
        """Stop all dummy processes."""
        self.engine.simulator.stop_all()
        self._refresh_panels()

    def action_refresh(self) -> None:
        """Force refresh."""
        self._tick()

    def on_unmount(self) -> None:
        """Cleanup on exit."""
        self.engine.stop()
