"""
IARIS CLI — Command-line interface using Typer

Provides commands for:
- Starting the IARIS server
- Running the TUI dashboard
- Managing dummy processes
- Viewing system status
"""

from __future__ import annotations

import asyncio
import logging
import sys

import typer

app = typer.Typer(
    name="iaris",
    help="IARIS — Intent-Aware Adaptive Resource Intelligence System",
    add_completion=False,
)


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to listen on"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
):
    """Start the IARIS API server."""
    setup_logging(verbose)

    import uvicorn
    typer.echo(f"🧠 Starting IARIS server on {host}:{port}")
    typer.echo(f"   Dashboard: http://localhost:{port}")
    typer.echo(f"   API docs:  http://localhost:{port}/docs")
    typer.echo(f"   WebSocket: ws://localhost:{port}/ws")
    typer.echo()

    uvicorn.run(
        "iaris.api:app",
        host=host,
        port=port,
        log_level="debug" if verbose else "info",
        reload=False,
    )


@app.command()
def dashboard(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
):
    """Launch the terminal (TUI) dashboard."""
    setup_logging(verbose)

    try:
        from iaris.tui import IARISDashboard
        dashboard_app = IARISDashboard()
        dashboard_app.run()
    except ImportError as e:
        typer.echo(f"Error: Textual not installed. Run: pip install textual\n{e}", err=True)
        raise typer.Exit(1)


@app.command()
def demo(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
):
    """Run the full IARIS demo (server + dummy processes)."""
    setup_logging(verbose)

    async def run_demo():
        from iaris.engine import IARISEngine

        engine = IARISEngine()
        engine.initialize()

        typer.echo("🧠 IARIS Demo — Intent-Aware Resource Intelligence")
        typer.echo("=" * 55)
        typer.echo()

        # Start monitoring
        typer.echo("▶ Starting process monitor...")
        engine.monitor.sample_once()
        typer.echo(f"  Found {engine.system.process_count} processes")
        typer.echo(f"  CPU: {engine.system.cpu_percent:.1f}% | Memory: {engine.system.memory_percent:.1f}%")
        typer.echo()

        # Spawn dummy processes
        typer.echo("▶ Spawning dummy processes...")
        dummies = engine.simulator.spawn_demo_set()
        for d in dummies:
            typer.echo(f"  ◆ {d.behavior_type} (PID: {d.pid})")
        typer.echo()

        # Run several ticks
        typer.echo("▶ Observing behavior (10 seconds)...")
        for i in range(10):
            system, processes = engine.monitor.sample_once()
            engine._process_tick(system, processes)
            typer.echo(f"  Tick {i+1}: CPU={system.cpu_percent:.1f}% | "
                       f"State={system.state.value} | "
                       f"Profiles={len(engine.profiles)}")
            await asyncio.sleep(1)

        typer.echo()

        # Show results
        typer.echo("▶ Analysis Results:")
        typer.echo("-" * 55)
        for profile in sorted(engine.profiles.values(), key=lambda p: p.avg_cpu, reverse=True)[:15]:
            typer.echo(
                f"  {profile.name[:25]:<25} | "
                f"Type: {profile.behavior_type.value:<20} | "
                f"CPU: {profile.avg_cpu:>5.1f}% | "
                f"Score: {profile.allocation_score:.3f}"
            )

        typer.echo()
        typer.echo("▶ Recent Decisions:")
        typer.echo("-" * 55)
        for decision in engine.decisions[-10:]:
            typer.echo(f"  [{decision.action.value:>8}] {decision.process_name}: {decision.reason[:80]}")

        # Cleanup
        typer.echo()
        typer.echo("▶ Cleaning up dummy processes...")
        engine.stop()
        typer.echo("✓ Demo complete")

    asyncio.run(run_demo())


@app.command()
def spawn(
    behavior_type: str = typer.Argument(help="Type: cpu_hog, latency_sensitive, bursty, blocking, memory_heavy"),
    count: int = typer.Option(1, help="Number of processes to spawn"),
):
    """Spawn dummy processes for testing."""
    from iaris.simulator import ProcessSimulator

    sim = ProcessSimulator()
    for _ in range(min(count, 10)):
        dummy = sim.spawn(behavior_type)
        if dummy and dummy.pid:
            typer.echo(f"◆ Spawned {behavior_type} (PID: {dummy.pid})")

    typer.echo(f"\nSpawned {count} dummy process(es). Press Ctrl+C to stop.")
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        sim.stop_all()
        typer.echo("\n✓ All dummy processes stopped")


@app.command()
def status():
    """Show current system status (one-shot)."""
    import psutil

    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/") if sys.platform != "win32" else psutil.disk_usage("C:\\")

    typer.echo("🧠 IARIS System Status")
    typer.echo("=" * 40)
    typer.echo(f"  CPU:    {cpu:.1f}%")
    typer.echo(f"  Memory: {mem.percent:.1f}% ({mem.used / (1024**3):.1f} / {mem.total / (1024**3):.1f} GB)")
    typer.echo(f"  Disk:   {disk.percent:.1f}%")
    typer.echo(f"  Processes: {len(psutil.pids())}")
    typer.echo(f"  Platform: {sys.platform}")


if __name__ == "__main__":
    app()
