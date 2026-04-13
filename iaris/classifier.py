"""
IARIS Behavior Classifier

Classifies processes into behavior types based on their resource usage patterns.
Uses configurable thresholds and tracks behavior history for dynamic reclassification.
"""

from __future__ import annotations

import logging
from typing import Optional

from iaris.models import (
    BehaviorProfile,
    BehaviorType,
    IARISConfig,
    ProcessMetrics,
)

logger = logging.getLogger("iaris.classifier")


class BehaviorClassifier:
    """
    Classifies processes into behavior types based on resource metrics.

    Examines CPU usage, memory consumption, I/O patterns, and variance
    to determine the dominant behavior pattern.
    """

    def __init__(self, config: Optional[IARISConfig] = None):
        self.config = config or IARISConfig()
        self._profiles: dict[int, BehaviorProfile] = {}
        self._cpu_history: dict[int, list[float]] = {}  # For variance calculation
        self._history_window = 30  # Keep last 30 samples

    @property
    def profiles(self) -> dict[int, BehaviorProfile]:
        """Current behavior profiles."""
        return self._profiles.copy()

    def classify(self, metrics: ProcessMetrics) -> BehaviorProfile:
        """
        Classify a process based on its current metrics.

        Updates or creates a BehaviorProfile with EWMA-smoothed values
        and assigns a behavior type.
        """
        pid = metrics.pid
        profile = self._profiles.get(pid)

        if profile is None:
            profile = BehaviorProfile(pid=pid, name=metrics.name)
            self._profiles[pid] = profile
            self._cpu_history[pid] = []

        # Track CPU history for variance
        history = self._cpu_history.setdefault(pid, [])
        history.append(metrics.cpu_percent)
        if len(history) > self._history_window:
            history.pop(0)

        # Determine EWMA alpha based on observation count
        alpha = (
            self.config.ewma_warmup_alpha
            if profile.observation_count < self.config.warmup_observations
            else self.config.ewma_alpha
        )

        # Update EWMA-smoothed metrics
        profile.avg_cpu = alpha * metrics.cpu_percent + (1 - alpha) * profile.avg_cpu
        profile.avg_memory = alpha * metrics.memory_percent + (1 - alpha) * profile.avg_memory
        io_rate = metrics.io_read_rate + metrics.io_write_rate
        profile.avg_io_rate = alpha * io_rate + (1 - alpha) * profile.avg_io_rate

        # Calculate burstiness (variance of CPU usage)
        if len(history) >= 3:
            mean = sum(history) / len(history)
            variance = sum((x - mean) ** 2 for x in history) / len(history)
            profile.burstiness = alpha * variance + (1 - alpha) * profile.burstiness

        # Calculate blocking ratio
        is_blocked = metrics.status in ("sleeping", "disk-sleep", "stopped", "idle")
        blocked_val = 1.0 if is_blocked else 0.0
        profile.blocking_ratio = alpha * blocked_val + (1 - alpha) * profile.blocking_ratio

        # Determine behavior type
        profile.behavior_type = self._determine_type(profile)

        # Update metadata
        profile.observation_count += 1
        profile.last_seen = metrics.timestamp
        profile.name = metrics.name
        profile.generate_signature()

        return profile

    def _determine_type(self, profile: BehaviorProfile) -> BehaviorType:
        """Determine behavior type from smoothed profile metrics."""
        cfg = self.config

        # Check idle first (low CPU)
        if profile.avg_cpu < cfg.idle_cpu_threshold:
            return BehaviorType.IDLE

        # Check CPU hog (sustained high CPU, low variance)
        if (profile.avg_cpu >= cfg.cpu_hog_threshold and
                profile.burstiness < cfg.bursty_variance_threshold):
            return BehaviorType.CPU_HOG

        # Check bursty (high variance in CPU)
        if profile.burstiness >= cfg.bursty_variance_threshold:
            return BehaviorType.BURSTY

        # Check blocking (high blocking ratio)
        if profile.blocking_ratio >= cfg.blocking_ratio_threshold:
            return BehaviorType.BLOCKING

        # Check memory heavy
        if profile.avg_memory >= cfg.memory_heavy_threshold:
            return BehaviorType.MEMORY_HEAVY

        # Check latency sensitive (moderate CPU, low variance, responsive)
        if (profile.avg_cpu > cfg.idle_cpu_threshold and
                profile.avg_cpu < cfg.cpu_hog_threshold and
                profile.burstiness < cfg.bursty_variance_threshold):
            return BehaviorType.LATENCY_SENSITIVE

        return BehaviorType.UNKNOWN

    def remove_process(self, pid: int) -> None:
        """Remove a process from classification tracking."""
        self._profiles.pop(pid, None)
        self._cpu_history.pop(pid, None)

    def cleanup_stale(self, active_pids: set[int]) -> None:
        """Remove profiles for processes that no longer exist."""
        stale = set(self._profiles.keys()) - active_pids
        for pid in stale:
            self.remove_process(pid)
