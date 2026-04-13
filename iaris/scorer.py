"""
IARIS Scoring & Decision Engine

Computes allocation scores for processes based on behavior, system state, and workload context.
Produces resource allocation decisions (boost/maintain/throttle/pause).
"""

from __future__ import annotations

import logging
from typing import Optional

from iaris.models import (
    AllocationAction,
    AllocationDecision,
    BehaviorProfile,
    BehaviorType,
    IARISConfig,
    SystemBehavior,
    SystemSnapshot,
    SystemState,
    WorkloadGroup,
)

logger = logging.getLogger("iaris.scorer")


class ScoringEngine:
    """
    Computes allocation scores and produces resource decisions.

    Score formula:
        allocationScore = (weight_behavior × behaviorScore)
                        + (weight_system_state × stateScore)
                        + (weight_workload × workloadScore)

    Higher score = higher priority = more resources.
    """

    def __init__(self, config: Optional[IARISConfig] = None):
        self.config = config or IARISConfig()

    def compute_score(
        self,
        profile: BehaviorProfile,
        system: SystemSnapshot,
        workload: Optional[WorkloadGroup] = None,
    ) -> float:
        """
        Compute allocation score for a process (0.0 to 1.0).

        Higher score = more resources.
        """
        behavior_score = self._behavior_score(profile, system)
        state_score = self._state_score(profile, system)
        workload_score = self._workload_score(profile, workload)

        total = (
            self.config.weight_behavior * behavior_score
            + self.config.weight_system_state * state_score
            + self.config.weight_workload * workload_score
        )

        # Clamp to [0, 1]
        return max(0.0, min(1.0, total))

    def _behavior_score(self, profile: BehaviorProfile, system: SystemSnapshot) -> float:
        """Score based on process behavior type and system context."""
        scores = {
            BehaviorType.LATENCY_SENSITIVE: 0.9,  # Protect responsive processes
            BehaviorType.BURSTY: 0.6,              # Needs occasional burst capacity
            BehaviorType.BLOCKING: 0.5,            # I/O bound, moderate priority
            BehaviorType.MEMORY_HEAVY: 0.4,        # Often background work
            BehaviorType.CPU_HOG: 0.3,             # Usually background/batch
            BehaviorType.IDLE: 0.2,                # Not using resources
            BehaviorType.UNKNOWN: 0.5,             # Default middle ground
        }

        base = scores.get(profile.behavior_type, 0.5)

        # Adjust based on system state
        if system.state == SystemState.PRESSURE:
            # Under pressure, penalize hogs more, protect sensitive more
            if profile.behavior_type == BehaviorType.CPU_HOG:
                base *= 0.5
            elif profile.behavior_type == BehaviorType.LATENCY_SENSITIVE:
                base = min(1.0, base * 1.2)

        elif system.state == SystemState.CRITICAL:
            # Critical: aggressively throttle everything except essential
            if profile.behavior_type in (BehaviorType.CPU_HOG, BehaviorType.MEMORY_HEAVY):
                base *= 0.2
            elif profile.behavior_type == BehaviorType.LATENCY_SENSITIVE:
                base = min(1.0, base * 1.1)

        return base

    def _state_score(self, profile: BehaviorProfile, system: SystemSnapshot) -> float:
        """Score adjustment based on system state."""
        if system.state == SystemState.STABLE:
            return 0.5  # No adjustment needed

        elif system.state == SystemState.PRESSURE:
            # Favor low-resource processes
            if profile.avg_cpu < 10:
                return 0.7
            elif profile.avg_cpu > 50:
                return 0.2
            return 0.4

        else:  # CRITICAL
            # Heavily penalize high-resource processes
            if profile.avg_cpu < 5 and profile.avg_memory < 5:
                return 0.8
            elif profile.avg_cpu > 30:
                return 0.1
            return 0.3

    def _workload_score(self, profile: BehaviorProfile, workload: Optional[WorkloadGroup]) -> float:
        """Score based on workload membership."""
        if workload is None:
            return 0.5  # No workload context
        return workload.priority

    def decide(
        self,
        profile: BehaviorProfile,
        system: SystemSnapshot,
        workload: Optional[WorkloadGroup] = None,
    ) -> AllocationDecision:
        """
        Produce an allocation decision for a process.

        Returns an AllocationDecision with action and natural language reasoning.
        """
        score = self.compute_score(profile, system, workload)
        profile.allocation_score = score

        # Map score to action
        if score >= 0.75:
            action = AllocationAction.BOOST
        elif score >= 0.4:
            action = AllocationAction.MAINTAIN
        elif score >= 0.2:
            action = AllocationAction.THROTTLE
        else:
            action = AllocationAction.PAUSE

        # Generate reasoning
        reason = self._generate_reason(profile, system, workload, score, action)

        # Update profile scores
        profile.criticality = score
        profile.latency_sensitivity = (
            0.9 if profile.behavior_type == BehaviorType.LATENCY_SENSITIVE
            else 0.3 if profile.behavior_type == BehaviorType.CPU_HOG
            else 0.5
        )

        return AllocationDecision(
            pid=profile.pid,
            process_name=profile.name,
            action=action,
            score=score,
            reason=reason,
            system_state=system.state,
            behavior_type=profile.behavior_type,
        )

    def _generate_reason(
        self,
        profile: BehaviorProfile,
        system: SystemSnapshot,
        workload: Optional[WorkloadGroup],
        score: float,
        action: AllocationAction,
    ) -> str:
        """Generate a natural language explanation for the decision."""
        parts = []

        # What we're doing
        action_desc = {
            AllocationAction.BOOST: "Boosting resources for",
            AllocationAction.MAINTAIN: "Maintaining current allocation for",
            AllocationAction.THROTTLE: "Throttling",
            AllocationAction.PAUSE: "Pausing",
        }
        parts.append(f"{action_desc[action]} '{profile.name}' (PID {profile.pid}).")

        # Why — behavior
        behavior_desc = {
            BehaviorType.CPU_HOG: "Process shows sustained high CPU usage ({:.1f}% avg)",
            BehaviorType.LATENCY_SENSITIVE: "Process is latency-sensitive with responsive behavior ({:.1f}% avg CPU)",
            BehaviorType.BURSTY: "Process shows bursty behavior with periodic spikes (variance: {:.1f})",
            BehaviorType.BLOCKING: "Process is I/O-bound, spending {:.0%} time in wait state",
            BehaviorType.MEMORY_HEAVY: "Process consumes significant memory ({:.1f}% avg)",
            BehaviorType.IDLE: "Process is mostly idle ({:.1f}% avg CPU)",
            BehaviorType.UNKNOWN: "Process behavior is still being learned ({:.1f}% avg CPU)",
        }

        if profile.behavior_type == BehaviorType.BLOCKING:
            parts.append(behavior_desc[profile.behavior_type].format(profile.blocking_ratio))
        elif profile.behavior_type == BehaviorType.BURSTY:
            parts.append(behavior_desc[profile.behavior_type].format(profile.burstiness))
        elif profile.behavior_type == BehaviorType.MEMORY_HEAVY:
            parts.append(behavior_desc[profile.behavior_type].format(profile.avg_memory))
        else:
            parts.append(behavior_desc.get(profile.behavior_type, "").format(profile.avg_cpu))

        # Why — system state
        state_desc = {
            SystemState.STABLE: "System is stable — balanced allocation active.",
            SystemState.PRESSURE: f"System under pressure (CPU: {system.cpu_percent:.1f}%, Memory: {system.memory_percent:.1f}%) — protecting critical processes.",
            SystemState.CRITICAL: f"System CRITICAL (CPU: {system.cpu_percent:.1f}%, Memory: {system.memory_percent:.1f}%) — aggressive throttling of non-essential workloads.",
        }
        parts.append(state_desc[system.state])

        # Why — workload context
        if workload:
            parts.append(f"Part of '{workload.name}' workload (priority: {workload.priority:.1f}).")

        parts.append(f"Score: {score:.3f}")

        return " ".join(parts)
