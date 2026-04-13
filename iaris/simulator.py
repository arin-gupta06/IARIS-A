"""
IARIS Dummy Process Simulator

Spawns synthetic processes that exhibit distinct resource usage patterns:
- CPU hog: sustained high CPU usage
- Latency sensitive: short bursts, fast response
- Bursty: periodic CPU spikes
- Blocking: simulates I/O wait
- Memory heavy: growing memory consumption

All dummies are managed as subprocesses and can be started/stopped via CLI or API.
"""

from __future__ import annotations

import logging
import multiprocessing
import os
import signal
import sys
import time
import math
import random
from typing import Optional

logger = logging.getLogger("iaris.simulator")


# ─── Dummy Process Worker Functions ──────────────────────────────────────────

def _cpu_hog_worker(intensity: float = 0.9):
    """Burn CPU continuously. Intensity controls duty cycle (0-1)."""
    while True:
        start = time.time()
        # Spin for intensity portion of each second
        while time.time() - start < intensity:
            _ = sum(i * i for i in range(1000))
        # Sleep for the remainder
        time.sleep(max(0, 1.0 - intensity))


def _latency_sensitive_worker(burst_ms: int = 50, interval_ms: int = 200):
    """Short CPU bursts simulating request handling."""
    while True:
        start = time.time()
        # Quick burst of computation
        duration = burst_ms / 1000.0
        while time.time() - start < duration:
            _ = math.sqrt(random.random()) * math.pi
        # Wait between bursts
        time.sleep(interval_ms / 1000.0)


def _bursty_worker(burst_duration: float = 2.0, idle_duration: float = 5.0):
    """Periodic CPU spikes — burst then idle."""
    while True:
        # Burst phase — high CPU
        burst_end = time.time() + burst_duration
        while time.time() < burst_end:
            _ = sum(i * i for i in range(5000))
        # Idle phase — almost no CPU
        time.sleep(idle_duration)


def _blocking_worker(block_duration: float = 0.5, work_duration: float = 0.1):
    """Simulates I/O-bound process that spends most time waiting."""
    while True:
        # Simulate I/O wait (sleep mimics blocking on I/O)
        time.sleep(block_duration)
        # Brief computation between waits
        start = time.time()
        while time.time() - start < work_duration:
            _ = [random.random() for _ in range(100)]


def _memory_heavy_worker(growth_mb_per_sec: float = 5.0, max_mb: float = 200.0):
    """Steadily grow memory usage up to a cap."""
    data = []
    chunk_size = int(growth_mb_per_sec * 1024 * 1024)  # bytes per second
    current_mb = 0.0

    while True:
        if current_mb < max_mb:
            data.append(bytearray(chunk_size))
            current_mb += growth_mb_per_sec
        else:
            # Hold at max, do light work
            _ = sum(1 for _ in range(1000))
        time.sleep(1.0)


# ─── Worker Dispatch ─────────────────────────────────────────────────────────

WORKER_MAP = {
    "cpu_hog": _cpu_hog_worker,
    "latency_sensitive": _latency_sensitive_worker,
    "bursty": _bursty_worker,
    "blocking": _blocking_worker,
    "memory_heavy": _memory_heavy_worker,
}


def _run_worker(behavior_type: str, **kwargs):
    """Entry point for spawned dummy processes."""
    # Set process title for identification (best-effort)
    try:
        import setproctitle
        setproctitle.setproctitle(f"iaris-dummy-{behavior_type}")
    except ImportError:
        pass

    worker_fn = WORKER_MAP.get(behavior_type)
    if worker_fn:
        worker_fn(**kwargs)


# ─── Dummy Process Manager ───────────────────────────────────────────────────

class DummyProcess:
    """Represents a running dummy process."""

    def __init__(self, behavior_type: str, process: multiprocessing.Process):
        self.behavior_type = behavior_type
        self.process = process
        self.pid: Optional[int] = None
        self.started_at: float = time.time()

    @property
    def is_alive(self) -> bool:
        return self.process.is_alive()


class ProcessSimulator:
    """
    Manages synthetic dummy processes for development and demo.

    Can spawn processes of various behavior types and track/stop them.
    """

    def __init__(self):
        self._dummies: dict[int, DummyProcess] = {}  # pid -> DummyProcess
        self._next_id = 1

    @property
    def active_processes(self) -> dict[int, DummyProcess]:
        """Get currently running dummy processes."""
        # Clean up dead processes
        dead_pids = [pid for pid, d in self._dummies.items() if not d.is_alive]
        for pid in dead_pids:
            del self._dummies[pid]
        return self._dummies.copy()

    @property
    def available_types(self) -> list[str]:
        """List available dummy process behavior types."""
        return list(WORKER_MAP.keys())

    def spawn(self, behavior_type: str, **kwargs) -> Optional[DummyProcess]:
        """
        Spawn a new dummy process of the given behavior type.

        Args:
            behavior_type: One of 'cpu_hog', 'latency_sensitive', 'bursty', 'blocking', 'memory_heavy'
            **kwargs: Additional arguments passed to the worker function

        Returns:
            DummyProcess instance, or None if behavior_type is invalid
        """
        if behavior_type not in WORKER_MAP:
            logger.error(f"Unknown behavior type: {behavior_type}. Available: {list(WORKER_MAP.keys())}")
            return None

        proc = multiprocessing.Process(
            target=_run_worker,
            args=(behavior_type,),
            kwargs=kwargs,
            name=f"iaris-dummy-{behavior_type}-{self._next_id}",
            daemon=True,
        )
        proc.start()
        self._next_id += 1

        dummy = DummyProcess(behavior_type=behavior_type, process=proc)
        dummy.pid = proc.pid

        if proc.pid:
            self._dummies[proc.pid] = dummy
            logger.info(f"Spawned dummy process: type={behavior_type}, pid={proc.pid}")

        return dummy

    def stop(self, pid: int) -> bool:
        """Stop a specific dummy process by PID."""
        dummy = self._dummies.get(pid)
        if not dummy:
            logger.warning(f"No dummy process found with pid={pid}")
            return False

        try:
            dummy.process.terminate()
            dummy.process.join(timeout=3)
            if dummy.process.is_alive():
                dummy.process.kill()
                dummy.process.join(timeout=2)
        except Exception as e:
            logger.error(f"Error stopping process {pid}: {e}")
            return False

        del self._dummies[pid]
        logger.info(f"Stopped dummy process: pid={pid}")
        return True

    def stop_all(self) -> int:
        """Stop all dummy processes. Returns count of stopped processes."""
        pids = list(self._dummies.keys())
        count = 0
        for pid in pids:
            if self.stop(pid):
                count += 1
        logger.info(f"Stopped {count} dummy processes")
        return count

    def spawn_demo_set(self) -> list[DummyProcess]:
        """Spawn one of each behavior type for demo purposes."""
        spawned = []
        for btype in WORKER_MAP:
            dummy = self.spawn(btype)
            if dummy:
                spawned.append(dummy)
        return spawned

    def get_status(self) -> list[dict]:
        """Get status of all dummy processes."""
        result = []
        for pid, dummy in self.active_processes.items():
            result.append({
                "pid": pid,
                "behavior_type": dummy.behavior_type,
                "is_alive": dummy.is_alive,
                "uptime_seconds": round(time.time() - dummy.started_at, 1),
            })
        return result
