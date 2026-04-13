"""
IARIS Engine — Central Orchestrator

Ties together all IARIS layers: Monitor → Classifier → Scorer → Knowledge → Workload → Reasoning.
This is the main entry point for the IARIS system.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections import deque
from typing import Callable, Optional

from iaris.models import (
    AllocationDecision,
    BehaviorProfile,
    IARISConfig,
    ProcessMetrics,
    SystemSnapshot,
    WorkloadGroup,
)
from iaris.monitor import ProcessMonitor
from iaris.classifier import BehaviorClassifier
from iaris.scorer import ScoringEngine
from iaris.knowledge import KnowledgeBase, RecipeLoader
from iaris.workload import WorkloadCoordinator
from iaris.simulator import ProcessSimulator

logger = logging.getLogger("iaris.engine")


class IARISEngine:
    """
    Central orchestrator for the IARIS system.

    Coordinates all layers:
    1. Monitor — collects process and system metrics
    2. Classifier — classifies process behavior
    3. Scorer — computes allocation scores and decisions
    4. Knowledge — persists and retrieves learned profiles
    5. Workload — coordinates workload groups
    6. Simulator — manages dummy processes
    """

    def __init__(self, config: Optional[IARISConfig] = None, db_path: Optional[str] = None):
        self.config = config or IARISConfig()

        # Core layers
        self.monitor = ProcessMonitor(self.config)
        self.classifier = BehaviorClassifier(self.config)
        self.scorer = ScoringEngine(self.config)
        self.knowledge = KnowledgeBase(db_path)
        self.workload = WorkloadCoordinator(self.config)
        self.simulator = ProcessSimulator()

        # Recipe loader
        self.recipe_loader = RecipeLoader()

        # State
        self._running = False
        self._decisions: deque[AllocationDecision] = deque(maxlen=200)
        self._profiles: dict[int, BehaviorProfile] = {}
        self._system: SystemSnapshot = SystemSnapshot()
        self._tick_count = 0
        self._callbacks: list[Callable] = []

        # Track only IARIS-related processes for detailed analysis
        self._iaris_pids: set[int] = set()

    @property
    def decisions(self) -> list[AllocationDecision]:
        """Recent allocation decisions."""
        return list(self._decisions)

    @property
    def profiles(self) -> dict[int, BehaviorProfile]:
        """Current behavior profiles."""
        return self._profiles.copy()

    @property
    def system(self) -> SystemSnapshot:
        """Current system snapshot."""
        return self._system

    def on_tick(self, callback: Callable) -> None:
        """Register a callback for each engine tick."""
        self._callbacks.append(callback)

    def initialize(self) -> None:
        """Initialize all subsystems."""
        logger.info("Initializing IARIS Engine...")

        # Initialize knowledge base
        self.knowledge.initialize()

        # Load cold-start recipes
        self.recipe_loader.load()

        # Load workload definitions
        workload_config = os.path.join(os.path.dirname(__file__), "workloads.json")
        self.workload.load_config(workload_config if os.path.exists(workload_config) else None)

        logger.info("IARIS Engine initialized")

    def _process_tick(self, system: SystemSnapshot, processes: dict[int, ProcessMetrics]) -> None:
        """Process a single monitoring tick — classify, score, decide."""
        self._system = system
        self._tick_count += 1

        active_pids = set(processes.keys())
        tick_decisions: list[AllocationDecision] = []

        # Get dummy process PIDs for focused analysis
        dummy_pids = set()
        for dummy in self.simulator.active_processes.values():
            if dummy.pid:
                dummy_pids.add(dummy.pid)

        # Process each monitored process
        for pid, metrics in processes.items():
            # Classify behavior
            profile = self.classifier.classify(metrics)

            # Apply learned profile if this is a new process
            if profile.observation_count == 1:
                self.knowledge.apply_learned_profile(profile)

            # Assign to workload
            wg = self.workload.assign_process(metrics)

            # Score and decide
            decision = self.scorer.decide(profile, system, wg)
            self._profiles[pid] = profile

            # Only track decisions for interesting processes
            # (dummy processes + high-resource processes)
            if (pid in dummy_pids or
                    metrics.cpu_percent > 5 or
                    metrics.memory_percent > 5):
                tick_decisions.append(decision)

        # Store top decisions
        # Sort by score extremes (most interesting decisions)
        tick_decisions.sort(key=lambda d: abs(d.score - 0.5), reverse=True)
        for decision in tick_decisions[:10]:  # Keep top 10 per tick
            self._decisions.append(decision)

        # Cleanup stale entries
        self.classifier.cleanup_stale(active_pids)
        self.workload.cleanup_stale(active_pids)
        stale_pids = set(self._profiles.keys()) - active_pids
        for pid in stale_pids:
            del self._profiles[pid]

        # Update workload aggregate metrics
        self.workload.update_workload_metrics(self._profiles)

        # Periodically persist to knowledge base (every 30 ticks)
        if self._tick_count % 30 == 0:
            self._persist_state()

        # Save system snapshot
        self.knowledge.save_system_snapshot(
            system.cpu_percent, system.memory_percent,
            system.state.value, system.behavior.value,
            system.process_count,
        )

    def _persist_state(self) -> None:
        """Persist current state to knowledge base."""
        for profile in self._profiles.values():
            if profile.observation_count > 5:
                self.knowledge.save_profile(profile)

        # Save recent decisions
        for decision in list(self._decisions)[-20:]:
            self.knowledge.save_decision(decision)

    async def start(self) -> None:
        """Start the IARIS engine."""
        self.initialize()
        self._running = True

        logger.info("IARIS Engine started")

        # Register our tick handler
        self.monitor.on_update(self._on_monitor_update)

        # Start monitoring loop
        await self.monitor.start()

    async def _on_monitor_update(self, system: SystemSnapshot, processes: dict[int, ProcessMetrics]) -> None:
        """Handle monitor updates."""
        self._process_tick(system, processes)

        # Notify callbacks
        for callback in self._callbacks:
            try:
                result = callback(self)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Engine callback error: {e}")

    def stop(self) -> None:
        """Stop the IARIS engine."""
        self._running = False
        self.monitor.stop()
        self._persist_state()
        self.knowledge.close()
        self.simulator.stop_all()
        logger.info("IARIS Engine stopped")

    def get_state(self) -> dict:
        """Get complete engine state as a dictionary (for API/UI consumption)."""
        return {
            "system": {
                "cpu_percent": round(self._system.cpu_percent, 1),
                "cpu_count": self._system.cpu_count,
                "memory_percent": round(self._system.memory_percent, 1),
                "memory_total_gb": self._system.memory_total_gb,
                "memory_available_gb": round(self._system.memory_available_gb, 2),
                "disk_io_read_rate": round(self._system.disk_io_read_rate, 0),
                "disk_io_write_rate": round(self._system.disk_io_write_rate, 0),
                "net_io_send_rate": round(self._system.net_io_send_rate, 0),
                "net_io_recv_rate": round(self._system.net_io_recv_rate, 0),
                "process_count": self._system.process_count,
                "state": self._system.state.value,
                "behavior": self._system.behavior.value,
                "timestamp": self._system.timestamp,
            },
            "processes": [
                {
                    "pid": p.pid,
                    "name": p.name,
                    "behavior_type": p.behavior_type.value,
                    "avg_cpu": round(p.avg_cpu, 1),
                    "avg_memory": round(p.avg_memory, 1),
                    "allocation_score": round(p.allocation_score, 3),
                    "criticality": round(p.criticality, 3),
                    "signature": p.signature,
                    "observation_count": p.observation_count,
                }
                for p in sorted(
                    self._profiles.values(),
                    key=lambda p: p.avg_cpu,
                    reverse=True,
                )[:50]  # Top 50 by CPU
            ],
            "workloads": self.workload.get_status(),
            "decisions": [d.to_dict() for d in list(self._decisions)[-30:]],
            "dummy_processes": self.simulator.get_status(),
            "tick_count": self._tick_count,
        }
