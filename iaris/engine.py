"""
IARIS Engine — Central Orchestrator

Ties together all IARIS layers: Monitor → Classifier → Scorer → Knowledge → Workload → Reasoning.
This is the main entry point for the IARIS system.

Now includes three core hurdle solutions:
1. Cold Start Resolution (similarity matching)
2. Optimization Pipeline (caching, state continuity, differential updates)
3. Learning Acceleration (EWMA continuity)
"""

from __future__ import annotations

import asyncio
import logging
import os
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
from iaris.similarity import ColdStartResolver  # ← Cold start solution
from iaris.cache import OptimizationPipeline      # ← Overhead solution
from iaris.continuity import LearningAccelerator  # ← Learning delay solution
from iaris.insights import InsightEngine           # ← Insight + efficiency layer
from iaris.credentials import CredentialManager
from iaris.intelligence import IntelligenceLayer
from iaris.observability import ObservabilityTracker, build_snapshot

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
        
        # ─── Three-Hurdle Solutions ───────────────────────────────────────────
        # 🥶 Cold Start Solution — similarity matching for new processes
        self.cold_start = ColdStartResolver()
        
        # ⚡ Overhead Solution — caching + state continuity + differential updates
        self.optimizer = OptimizationPipeline(max_cache_size=10000, default_ttl=30)
        
        # 🐌 Learning Delay Solution — EWMA continuity
        self.accelerator = LearningAccelerator()

        # ─── Insight + Efficiency Engine ─────────────────────────────────────
        self._insight_engine = InsightEngine()
        self._credentials = CredentialManager()
        self._observability = ObservabilityTracker(max_events=240)
        self._intelligence = IntelligenceLayer(cache_ttl_seconds=45)
        
        # State
        self._running = False
        self._decisions: deque[AllocationDecision] = deque(maxlen=200)
        self._profiles: dict[int, BehaviorProfile] = {}
        self._system: SystemSnapshot = SystemSnapshot()
        self._tick_count = 0
        self._callbacks: list[Callable] = []

        # Track only IARIS-related processes for detailed analysis
        self._iaris_pids: set[int] = set()
        
        # Diagnostics for hurdle solutions
        self._cold_start_count = 0
        self._cache_hits = 0
        self._cache_misses = 0

        # Runtime payload caches for UI and APIs
        self._latest_insights: list[dict] = []
        self._latest_efficiency: dict = {
            "overall": 0,
            "cpu": 0,
            "memory": 0,
            "latency": 0,
            "process_balance": 50,
        }
        self._latest_observability: dict = {
            "snapshot": build_snapshot(self._system, {}),
            "diff": {},
            "changes": [],
            "recent_changes": [],
            "significant": False,
            "significance_reason": "No change detected",
        }
        self._latest_intelligence: dict = {
            "significant": False,
            "reason": "No change detected",
            "used_cache": False,
            "source": "local",
            "insight": "System stable. No significant changes detected.",
            "last_updated": self._system.timestamp,
            "cache_age_seconds": 0,
            "cache_ttl_seconds": 45,
            "forced_refresh": False,
            "gemini": {
                "enabled": False,
                "attempted": False,
                "status": "not_configured",
                "message": "Gemini integration not configured.",
                "api_version": "",
                "model": "",
            },
        }

        # Runtime tuning defaults used by preview/apply/reset workflows.
        self._default_tuning = self._capture_tuning_settings()

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

        # Load backend-managed credentials once at startup.
        self._credentials.load()

        # Initialize knowledge base
        self.knowledge.initialize()

        # Load cold-start recipes
        self.recipe_loader.load()

        # Load workload definitions
        workload_config = os.path.join(os.path.dirname(__file__), "workloads.json")
        self.workload.load_config(workload_config if os.path.exists(workload_config) else None)

        logger.info("IARIS Engine initialized")

    def _process_tick(self, system: SystemSnapshot, processes: dict[int, ProcessMetrics]) -> None:
        """
        Process a single monitoring tick — classify, score, decide.
        
        Integrates three-hurdle solutions:
        1. Cold start resolution via similarity matching
        2. Overhead reduction via caching pipeline
        3. Learning delay reduction via EWMA continuity
        """
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
            # ─── 1️⃣ CLASSIFY BEHAVIOR ────────────────────────────────────────
            profile = self.classifier.classify(metrics)
            
            # ─── 2️⃣ COLD START RESOLUTION ────────────────────────────────────
            # Resolve cold start for new processes using similarity matching
            if profile.observation_count == 1:
                # Apply learned profile from knowledge base
                self.knowledge.apply_learned_profile(profile)
                
                # 🥶 COLD START FIX: Similarity matching
                known_profiles = self.knowledge.get_all_profiles()
                if known_profiles:
                    profile = self.cold_start.resolve(metrics, profile, known_profiles)
                    self._cold_start_count += 1
            
            # ─── 3️⃣ CHECK OPTIMIZATION PIPELINE ──────────────────────────────
            # 3a. Check cache for recent computation
            cached_entry = self.optimizer.cache.lookup(pid)
            
            if cached_entry is not None:
                # ⚡ CACHE HIT: Use cached score
                profile.allocation_score = cached_entry.decision.score
                profile.criticality = cached_entry.profile.criticality
                profile.latency_sensitivity = cached_entry.profile.latency_sensitivity
                self._cache_hits += 1
                decision = cached_entry.decision
            else:
                # ⚡ CACHE MISS: Check if full recomputation needed
                self._cache_misses += 1
                
                # 3b. Differential update detection
                delta_info = self.optimizer.cache.get_delta(pid, profile)
                should_recompute = self.optimizer.cache.should_recompute(delta_info)
                
                if not should_recompute and pid in self._profiles:
                    # Use previous state continuity for incremental scoring
                    prev_profile = self._profiles[pid]
                    profile.allocation_score = prev_profile.allocation_score
                    profile.criticality = prev_profile.criticality
                    profile.latency_sensitivity = prev_profile.latency_sensitivity
                else:
                    # Full recomputation needed
                    pass  # Score will be computed below
                
                # ─── 4️⃣ EWMA CONTINUITY FOR LEARNING ─────────────────────────
                # Apply EWMA with continuity constraints to ensure smooth learning
                new_metrics = {
                    'cpu': metrics.cpu_percent,
                    'memory': metrics.memory_percent,
                    'io': metrics.io_read_rate + metrics.io_write_rate,
                }
                profile = self.accelerator.apply_continuity_update(profile, new_metrics)
                
                # Update convergence phase
                learning_info = self.accelerator.get_learning_status(pid)
                profile.learning_phase = learning_info['phase']
                profile.convergence_progress = learning_info['progress']
                
                # 3c. Assign to workload
                wg = self.workload.assign_process(metrics)
                
                # 3d. Score and decide
                decision = self.scorer.decide(profile, system, wg)
                profile.allocation_score = decision.score
                
                # Store in cache for next time
                self.optimizer.cache.store(
                    pid, metrics.name, profile, decision,
                    compute_type="full" if should_recompute else "delta"
                )
            
            self._profiles[pid] = profile
            
            # Track interesting decisions
            if (pid in dummy_pids or
                    metrics.cpu_percent > 5 or
                    metrics.memory_percent > 5):
                tick_decisions.append(decision)

        # Store top decisions
        # Sort by score extremes (most interesting decisions)
        tick_decisions.sort(key=lambda d: abs(d.score - 0.5), reverse=True)
        for decision in tick_decisions[:10]:  # Keep top 10 per tick
            self._decisions.append(decision)

        # ─── CLEANUP ──────────────────────────────────────────────────────────
        # Cleanup stale entries
        self.classifier.cleanup_stale(active_pids)
        self.workload.cleanup_stale(active_pids)
        self.optimizer.cleanup(active_pids)      # ← Cache cleanup
        self.accelerator.continuity.cleanup(active_pids)  # ← Learning history cleanup
        
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

        # Compute derived insight/observability payloads once per tick.
        self._latest_insights = self._insight_engine.generate(self)
        self._latest_efficiency = self._insight_engine.compute_efficiency(self)

        observability_update = self._observability.update(build_snapshot(system, processes))
        self._latest_observability = observability_update.to_dict()
        self._latest_intelligence = self._intelligence.evaluate(
            observability=self._latest_observability,
            engine_insights=self._latest_insights,
            credentials=self._credentials.get_store(),
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
    
    def get_hurdle_diagnostics(self) -> dict:
        """
        Get diagnostics for the three-hurdle solution framework.
        
        Returns comprehensive metrics on:
        1. Cold Start Resolution (similarity matching)
        2. Overhead Reduction (caching pipeline)
        3. Learning Acceleration (EWMA continuity)
        """
        cache_stats = self.optimizer.get_stats()
        total_accesses = cache_stats['hits'] + cache_stats['misses']
        cache_hit_rate = cache_stats['hits'] / total_accesses if total_accesses > 0 else 0.0
        
        # Count processes in each learning phase
        phase_counts = {'bootstrap': 0, 'adaptation': 0, 'stable': 0}
        bootstrapped_count = 0
        
        for profile in self._profiles.values():
            phase_counts[profile.learning_phase] += 1
            if profile.bootstrapped:
                bootstrapped_count += 1
        
        return {
            "hurdles": {
                # 🥶 COLD START RESOLUTION
                "cold_start": {
                    "enabled": True,
                    "algorithm": "similarity_matching",
                    "processes_bootstrapped": bootstrapped_count,
                    "bootstrap_percentage": round(
                        100 * bootstrapped_count / len(self._profiles) if self._profiles else 0,
                        1
                    ),
                    "expected_initial_accuracy": "~80-85%",
                    "description": "New processes matched with similar workloads to bypass cold start"
                },
                
                # ⚡ OVERHEAD REDUCTION
                "overhead_reduction": {
                    "enabled": True,
                    "algorithm": "v4.0_optimization_pipeline",
                    "cache_hit_rate": round(cache_hit_rate, 3),
                    "cache_hits": cache_stats['hits'],
                    "cache_misses": cache_stats['misses'],
                    "full_recomputes": cache_stats['full_recomputes'],
                    "delta_updates": cache_stats['delta_updates'],
                    "cache_evictions": cache_stats['cache_evictions'],
                    "cache_size": len(self.optimizer.cache._cache),
                    "expected_cpu_overhead": "~0.05%",
                    "expected_savings": "95% of redundant computation eliminated",
                    "description": "Caching + state continuity + differential updates"
                },
                
                # 🐌 LEARNING ACCELERATION
                "learning_acceleration": {
                    "enabled": True,
                    "algorithm": "ewma_continuity",
                    "learning_phases": {
                        "bootstrap": phase_counts['bootstrap'],
                        "adaptation": phase_counts['adaptation'],
                        "stable": phase_counts['stable'],
                    },
                    "expected_convergence_time": "30-90 seconds",
                    "alpha_warmup": self.config.ewma_warmup_alpha,
                    "alpha_steady": self.config.ewma_alpha,
                    "description": "EWMA never resets, enabling fast learning convergence"
                },
            },
            "metrics": {
                "total_processes": len(self._profiles),
                "tick_count": self._tick_count,
                "total_decisions": len(self._decisions),
            }
        }

    def get_credential_status(self) -> dict:
        """Safe credential status for diagnostics and UI."""
        return self._credentials.status()

    def refresh_intelligence(self, force_external: bool = True) -> dict:
        """Force-refresh intelligence payload, optionally forcing external API attempt."""
        self._latest_intelligence = self._intelligence.evaluate(
            observability=self._latest_observability,
            engine_insights=self._latest_insights,
            credentials=self._credentials.get_store(),
            force_refresh=True,
            force_external=force_external,
        )
        return self._latest_intelligence

    def _capture_tuning_settings(self) -> dict:
        """Capture current tunable values from all optimization subsystems."""
        churn_delta = self.optimizer.cache._delta
        avg_cpu_mem_threshold = (churn_delta.cpu_delta_threshold + churn_delta.memory_delta_threshold) / 2.0
        # Inverse mapping: lower thresholds => higher sensitivity.
        churn_sensitivity = int(round(max(0.0, min(100.0, (5.0 - avg_cpu_mem_threshold) / 4.0 * 100.0))))

        return {
            "cold_start_threshold": float(self.cold_start.matcher.bootstrap_threshold),
            "cache_ttl": int(self.optimizer.cache.default_ttl),
            "ewma_alpha": float(self.config.ewma_alpha),
            "process_churn_sensitivity": churn_sensitivity,
        }

    def _normalize_tuning_payload(self, payload: dict) -> tuple[dict, list[str], bool]:
        """Normalize and clamp tuning payload to safe ranges."""
        ranges = self.get_tuning_ranges()
        normalized = {}
        warnings: list[str] = []
        clamped = False

        def _clamp_number(name: str, value: float, min_v: float, max_v: float, digits: int = 3):
            nonlocal clamped
            safe_value = float(value)
            if safe_value < min_v:
                safe_value = min_v
                warnings.append(f"{name} increased to safe minimum ({min_v}).")
                clamped = True
            if safe_value > max_v:
                safe_value = max_v
                warnings.append(f"{name} reduced to safe maximum ({max_v}).")
                clamped = True
            return round(safe_value, digits)

        normalized["cold_start_threshold"] = _clamp_number(
            "Cold Start Threshold",
            payload.get("cold_start_threshold", self.cold_start.matcher.bootstrap_threshold),
            ranges["cold_start_threshold"]["min"],
            ranges["cold_start_threshold"]["max"],
            2,
        )

        normalized["cache_ttl"] = int(_clamp_number(
            "Cache TTL",
            payload.get("cache_ttl", self.optimizer.cache.default_ttl),
            ranges["cache_ttl"]["min"],
            ranges["cache_ttl"]["max"],
            0,
        ))

        normalized["ewma_alpha"] = _clamp_number(
            "EWMA Alpha",
            payload.get("ewma_alpha", self.config.ewma_alpha),
            ranges["ewma_alpha"]["min"],
            ranges["ewma_alpha"]["max"],
            2,
        )

        normalized["process_churn_sensitivity"] = int(_clamp_number(
            "Process Churn Sensitivity",
            payload.get("process_churn_sensitivity", self._capture_tuning_settings()["process_churn_sensitivity"]),
            ranges["process_churn_sensitivity"]["min"],
            ranges["process_churn_sensitivity"]["max"],
            0,
        ))

        return normalized, warnings, clamped

    def get_tuning_ranges(self) -> dict:
        """Supported safe ranges for tuning controls."""
        return {
            "cold_start_threshold": {"min": 0.35, "max": 0.9, "step": 0.01},
            "cache_ttl": {"min": 5, "max": 120, "step": 1},
            "ewma_alpha": {"min": 0.05, "max": 0.7, "step": 0.01},
            "process_churn_sensitivity": {"min": 0, "max": 100, "step": 1},
        }

    def _compute_mode(self, settings: dict) -> str:
        """Map settings to a user-facing mode badge."""
        risk_score = 0
        if settings["ewma_alpha"] >= 0.42:
            risk_score += 2
        if settings["cache_ttl"] <= 12:
            risk_score += 2
        if settings["cold_start_threshold"] <= 0.48:
            risk_score += 2
        if settings["process_churn_sensitivity"] >= 76:
            risk_score += 1

        if risk_score >= 5:
            return "Aggressive Mode"
        if risk_score >= 2:
            return "Adaptive Mode"
        return "Safe Mode"

    def _predict_tuning_impact(self, settings: dict) -> dict:
        """Predict impact of a tuning profile using current engine telemetry as baseline."""
        current = self._capture_tuning_settings()
        current_hit_rate = self.optimizer.cache.hit_rate if self.optimizer.cache.hit_rate > 0 else 0.78

        ttl_diff = settings["cache_ttl"] - current["cache_ttl"]
        alpha_diff = settings["ewma_alpha"] - current["ewma_alpha"]
        cold_diff = settings["cold_start_threshold"] - current["cold_start_threshold"]
        churn_diff = settings["process_churn_sensitivity"] - current["process_churn_sensitivity"]

        hit_rate = (current_hit_rate * 100.0) + (ttl_diff * 0.45) - (churn_diff * 0.08)
        hit_rate = max(35.0, min(99.0, hit_rate))

        cpu_overhead = 11.0 - (hit_rate * 0.08) + (settings["ewma_alpha"] * 9.5) + (settings["process_churn_sensitivity"] * 0.02)
        cpu_overhead = max(0.8, min(24.0, cpu_overhead))

        convergence_time = 42.0 + ((0.34 - settings["ewma_alpha"]) * 120.0) + ((settings["cold_start_threshold"] - 0.6) * 55.0)
        convergence_time = max(18.0, min(220.0, convergence_time))

        cold_start_accuracy = 81.0 + (cold_diff * 26.0) - (max(0.0, settings["ewma_alpha"] - 0.45) * 12.0)
        cold_start_accuracy = max(55.0, min(96.0, cold_start_accuracy))

        risk_points = 0
        if settings["ewma_alpha"] >= 0.45:
            risk_points += 2
        if settings["cache_ttl"] <= 10:
            risk_points += 2
        if settings["cold_start_threshold"] <= 0.45:
            risk_points += 2
        if settings["process_churn_sensitivity"] >= 80:
            risk_points += 1
        if cpu_overhead >= 12.0:
            risk_points += 1

        if risk_points >= 5:
            verdict = "High Risk"
            risk_color = "red"
        elif risk_points >= 3:
            verdict = "Moderate Risk"
            risk_color = "yellow"
        else:
            verdict = "Healthy"
            risk_color = "green"

        return {
            "hit_rate": round(hit_rate, 1),
            "cpu_overhead": round(cpu_overhead, 1),
            "convergence_time": round(convergence_time, 0),
            "cold_start_accuracy": round(cold_start_accuracy, 1),
            "risk": {
                "score": risk_points,
                "verdict": verdict,
                "color": risk_color,
            },
            "delta": {
                "hit_rate": round(hit_rate - (current_hit_rate * 100.0), 1),
                "cpu_overhead": round(cpu_overhead - (11.0 - ((current_hit_rate * 100.0) * 0.08) + (current["ewma_alpha"] * 9.5) + (current["process_churn_sensitivity"] * 0.02)), 1),
                "convergence_time": round(convergence_time - (42.0 + ((0.34 - current["ewma_alpha"]) * 120.0) + ((current["cold_start_threshold"] - 0.6) * 55.0)), 0),
                "cold_start_accuracy": round(cold_start_accuracy - (81.0 + ((current["cold_start_threshold"] - 0.6) * 26.0) - (max(0.0, current["ewma_alpha"] - 0.45) * 12.0)), 1),
            },
        }

    def get_tuning_state(self) -> dict:
        """Get current tuning values, ranges, and predicted impact."""
        settings = self._capture_tuning_settings()
        prediction = self._predict_tuning_impact(settings)
        return {
            "current": settings,
            "ranges": self.get_tuning_ranges(),
            "mode": self._compute_mode(settings),
            "prediction": prediction,
        }

    def preview_tuning(self, payload: dict) -> dict:
        """Preview tuning impact without mutating live engine state."""
        settings, warnings, clamped = self._normalize_tuning_payload(payload)
        prediction = self._predict_tuning_impact(settings)
        return {
            "settings": settings,
            "mode": self._compute_mode(settings),
            "prediction": prediction,
            "warnings": warnings,
            "clamped": clamped,
        }

    def apply_tuning(self, payload: dict) -> dict:
        """Apply validated tuning settings to runtime components."""
        previous = self._capture_tuning_settings()
        settings, warnings, clamped = self._normalize_tuning_payload(payload)

        # Cold start resolver tuning.
        self.cold_start.matcher.bootstrap_threshold = settings["cold_start_threshold"]

        # Cache tuning.
        self.optimizer.cache.default_ttl = settings["cache_ttl"]

        # EWMA tuning across config and continuity layers.
        self.config.ewma_alpha = settings["ewma_alpha"]
        self.accelerator.continuity.metrics.ewma_alpha_steady = settings["ewma_alpha"]
        self.accelerator.continuity.metrics.ewma_alpha_warmup = min(0.9, max(settings["ewma_alpha"] + 0.1, settings["ewma_alpha"] * 1.8))

        # Churn sensitivity tuning maps to delta thresholds.
        sensitivity = settings["process_churn_sensitivity"]
        cpu_mem_threshold = max(0.8, 5.0 - (sensitivity * 0.04))
        io_threshold = max(4.0, 20.0 - (sensitivity * 0.16))
        self.optimizer.cache._delta.cpu_delta_threshold = cpu_mem_threshold
        self.optimizer.cache._delta.memory_delta_threshold = cpu_mem_threshold
        self.optimizer.cache._delta.io_delta_threshold = io_threshold

        prediction = self._predict_tuning_impact(settings)

        return {
            "previous": previous,
            "applied": settings,
            "mode": self._compute_mode(settings),
            "prediction": prediction,
            "warnings": warnings,
            "clamped": clamped,
        }

    def reset_tuning(self) -> dict:
        """Reset runtime tuning to startup defaults."""
        return self.apply_tuning(self._default_tuning)

    def get_state(self) -> dict:
        """Get complete engine state as a dictionary (for API/UI consumption)."""
        return {
            "system": {
                "cpu_percent": round(self._system.cpu_percent, 1),
                "cpu_count": self._system.cpu_count,
                "memory_percent": round(self._system.memory_percent, 1),
                "disk_percent": round(self._system.disk_percent, 1),
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
                    # 🥶 Cold Start Info
                    "bootstrapped": p.bootstrapped,
                    "bootstrap_confidence": round(p.bootstrap_confidence, 2) if p.bootstrapped else None,
                    # 🐌 Learning Info
                    "learning_phase": p.learning_phase,
                    "convergence_progress": round(p.convergence_progress, 2),
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
            # ── Insight layer (new) ──────────────────────────────────────────
            "insights": self._latest_insights,
            "efficiency": self._latest_efficiency,
            # ── Observability + Intelligence layers ─────────────────────────
            "observability": self._latest_observability,
            "intelligence": self._latest_intelligence,
            "tuning": self.get_tuning_state(),
        }
