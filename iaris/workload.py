"""
IARIS Workload Coordinator

Groups related processes into logical workloads, manages inter-workload
conflicts, and coordinates resource allocation at the workload level.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from iaris.models import (
    BehaviorProfile,
    ProcessMetrics,
    WorkloadGroup,
    IARISConfig,
)

logger = logging.getLogger("iaris.workload")

# Default workload config
DEFAULT_WORKLOADS = [
    {
        "name": "web-service",
        "description": "Web server and API processes",
        "process_patterns": ["uvicorn", "gunicorn", "nginx", "apache", "flask", "fastapi"],
        "priority": 0.8,
    },
    {
        "name": "database",
        "description": "Database processes",
        "process_patterns": ["postgres", "mysql", "mongo", "redis", "sqlite"],
        "priority": 0.9,
    },
    {
        "name": "iaris-demo",
        "description": "IARIS dummy processes",
        "process_patterns": ["iaris-dummy"],
        "priority": 0.5,
    },
]


class WorkloadCoordinator:
    """
    Coordinates resource allocation across workload groups.

    Workload groups contain related processes (e.g., a web service = API + DB + cache).
    The coordinator ensures workload-level goals are met, not just individual process goals.
    """

    def __init__(self, config: Optional[IARISConfig] = None):
        self.config = config or IARISConfig()
        self._workloads: dict[str, WorkloadGroup] = {}
        self._pid_to_workload: dict[int, str] = {}

    @property
    def workloads(self) -> dict[str, WorkloadGroup]:
        """Current workload groups."""
        return self._workloads.copy()

    def load_config(self, config_path: Optional[str] = None) -> None:
        """Load workload definitions from JSON config or defaults."""
        workload_defs = DEFAULT_WORKLOADS

        if config_path and os.path.exists(config_path):
            try:
                with open(config_path) as f:
                    data = json.load(f)
                    workload_defs = data.get("workloads", DEFAULT_WORKLOADS)
            except Exception as e:
                logger.warning(f"Failed to load workload config: {e}")

        for wdef in workload_defs:
            wg = WorkloadGroup(
                name=wdef["name"],
                description=wdef.get("description", ""),
                process_patterns=wdef.get("process_patterns", []),
                priority=wdef.get("priority", 0.5),
            )
            self._workloads[wg.name] = wg

        logger.info(f"Loaded {len(self._workloads)} workload groups")

    def assign_process(self, metrics: ProcessMetrics) -> Optional[WorkloadGroup]:
        """Assign a process to a workload group based on its name."""
        # Check if already assigned
        existing = self._pid_to_workload.get(metrics.pid)
        if existing and existing in self._workloads:
            wg = self._workloads[existing]
            if metrics.pid not in wg.member_pids:
                wg.member_pids.append(metrics.pid)
            return wg

        # Try to match by name pattern
        for wg in self._workloads.values():
            if wg.matches_process(metrics.name):
                wg.member_pids.append(metrics.pid)
                self._pid_to_workload[metrics.pid] = wg.name
                return wg

        return None

    def get_workload(self, pid: int) -> Optional[WorkloadGroup]:
        """Get the workload group for a process."""
        wname = self._pid_to_workload.get(pid)
        if wname:
            return self._workloads.get(wname)
        return None

    def update_workload_metrics(self, profiles: dict[int, BehaviorProfile]) -> None:
        """Update aggregate metrics for each workload group."""
        # Reset totals
        for wg in self._workloads.values():
            wg.total_cpu = 0.0
            wg.total_memory = 0.0

            # Clean up dead members
            wg.member_pids = [pid for pid in wg.member_pids if pid in profiles]

            # Aggregate live member metrics
            for pid in wg.member_pids:
                profile = profiles.get(pid)
                if profile:
                    wg.total_cpu += profile.avg_cpu
                    wg.total_memory += profile.avg_memory

    def detect_conflicts(self) -> list[dict]:
        """Detect resource conflicts between workloads."""
        conflicts = []
        workloads = list(self._workloads.values())

        for i, wg1 in enumerate(workloads):
            for wg2 in workloads[i + 1:]:
                # Check CPU contention
                total_cpu = wg1.total_cpu + wg2.total_cpu
                if total_cpu > 80:  # Both consuming significant CPU
                    conflicts.append({
                        "type": "cpu_contention",
                        "workloads": [wg1.name, wg2.name],
                        "total_cpu": total_cpu,
                        "resolution": f"Prioritize '{wg1.name}' (priority {wg1.priority:.1f}) over '{wg2.name}' (priority {wg2.priority:.1f})"
                        if wg1.priority >= wg2.priority
                        else f"Prioritize '{wg2.name}' (priority {wg2.priority:.1f}) over '{wg1.name}' (priority {wg1.priority:.1f})",
                    })

        return conflicts

    def resolve_priority(self, pid1: int, pid2: int) -> int:
        """Given two PIDs in conflict, return the one with higher workload priority."""
        wg1 = self.get_workload(pid1)
        wg2 = self.get_workload(pid2)

        p1 = wg1.priority if wg1 else 0.5
        p2 = wg2.priority if wg2 else 0.5

        return pid1 if p1 >= p2 else pid2

    def cleanup_stale(self, active_pids: set[int]) -> None:
        """Remove stale PID mappings."""
        stale = set(self._pid_to_workload.keys()) - active_pids
        for pid in stale:
            wname = self._pid_to_workload.pop(pid, None)
            if wname and wname in self._workloads:
                wg = self._workloads[wname]
                if pid in wg.member_pids:
                    wg.member_pids.remove(pid)

    def get_status(self) -> list[dict]:
        """Get status of all workload groups."""
        return [
            {
                "name": wg.name,
                "description": wg.description,
                "priority": wg.priority,
                "member_count": len(wg.member_pids),
                "member_pids": wg.member_pids[:],
                "total_cpu": round(wg.total_cpu, 1),
                "total_memory": round(wg.total_memory, 1),
            }
            for wg in self._workloads.values()
        ]
