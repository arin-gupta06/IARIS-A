import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  SlidersHorizontal,
  Shield,
  Zap,
  Gauge,
  ChevronDown,
  ChevronUp,
  Save,
  RotateCcw,
  Undo2,
  PlayCircle,
  AlertTriangle,
  CheckCircle2,
  FlaskConical,
} from 'lucide-react';

const LOCAL_PROFILE_KEY = 'iaris_tuning_profiles_v1';

const PRESETS = {
  Balanced: {
    cold_start_threshold: 0.6,
    cache_ttl: 30,
    ewma_alpha: 0.3,
    process_churn_sensitivity: 50,
  },
  'Fast Learning': {
    cold_start_threshold: 0.52,
    cache_ttl: 20,
    ewma_alpha: 0.48,
    process_churn_sensitivity: 72,
  },
  'High Stability': {
    cold_start_threshold: 0.72,
    cache_ttl: 45,
    ewma_alpha: 0.16,
    process_churn_sensitivity: 34,
  },
  'Low Overhead': {
    cold_start_threshold: 0.66,
    cache_ttl: 70,
    ewma_alpha: 0.12,
    process_churn_sensitivity: 20,
  },
  'Aggressive Optimization': {
    cold_start_threshold: 0.44,
    cache_ttl: 12,
    ewma_alpha: 0.58,
    process_churn_sensitivity: 86,
  },
};

const DEFAULT_RANGES = {
  cold_start_threshold: { min: 0.35, max: 0.9, step: 0.01 },
  cache_ttl: { min: 5, max: 120, step: 1 },
  ewma_alpha: { min: 0.05, max: 0.7, step: 0.01 },
  process_churn_sensitivity: { min: 0, max: 100, step: 1 },
};

function formatSigned(value, suffix = '%', digits = 1, invert = false) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '--';
  const numeric = Number(value);
  const sign = numeric > 0 ? '+' : numeric < 0 ? '-' : '';
  const out = `${sign}${Math.abs(numeric).toFixed(digits)}${suffix}`;
  if (!invert) return out;
  if (numeric === 0) return out;
  return `${numeric > 0 ? 'worse' : 'better'} ${out}`;
}

function modeClass(mode) {
  if (mode === 'Aggressive Mode') return 'badge-red';
  if (mode === 'Adaptive Mode') return 'badge-yellow';
  return 'badge-green';
}

function verdictClass(color) {
  if (color === 'red') return 'risk-red';
  if (color === 'yellow') return 'risk-yellow';
  return 'risk-green';
}

function getStoredProfiles() {
  try {
    const raw = localStorage.getItem(LOCAL_PROFILE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function setStoredProfiles(profiles) {
  localStorage.setItem(LOCAL_PROFILE_KEY, JSON.stringify(profiles));
}

function SliderControl({
  label,
  value,
  min,
  max,
  step,
  onChange,
  description,
  hint,
  valueSuffix = '',
  formatter,
}) {
  return (
    <div className="tuning-control-row">
      <div className="tuning-control-head">
        <div>
          <div className="tuning-control-label">{label}</div>
          <div className="tuning-control-description">{description}</div>
        </div>
        <div className="tuning-control-value">{formatter ? formatter(value) : `${value}${valueSuffix}`}</div>
      </div>
      <input
        className="tuning-slider"
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
      <div className="tuning-control-hint">{hint}</div>
    </div>
  );
}

function TuningPanel({ apiBase, onPreviewUpdate, onApplied, onJumpToSimulator }) {
  const [loading, setLoading] = useState(true);
  const [ranges, setRanges] = useState(DEFAULT_RANGES);
  const [mode, setMode] = useState('Safe Mode');
  const [draft, setDraft] = useState(PRESETS.Balanced);
  const [preview, setPreview] = useState(null);
  const [warnings, setWarnings] = useState([]);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [selectedPreset, setSelectedPreset] = useState('Balanced');
  const [lastAppliedSnapshot, setLastAppliedSnapshot] = useState(null);
  const [profileName, setProfileName] = useState('');
  const [profiles, setProfiles] = useState(getStoredProfiles());
  const [advancedThresholds, setAdvancedThresholds] = useState({
    pressure_cpu: 70,
    pressure_memory: 75,
  });

  const initializedRef = useRef(false);
  const debounceRef = useRef(null);

  const loadInitial = async () => {
    setLoading(true);
    try {
      const [tuningResp, configResp] = await Promise.all([
        fetch(`${apiBase}/tuning`),
        fetch(`${apiBase}/config`),
      ]);
      if (!tuningResp.ok) throw new Error(`Failed to load tuning state (${tuningResp.status})`);
      const data = await tuningResp.json();
      setRanges(data.ranges || DEFAULT_RANGES);
      setDraft(data.current || PRESETS.Balanced);
      setMode(data.mode || 'Safe Mode');
      setPreview(data.prediction || null);
      setWarnings([]);
      initializedRef.current = true;

      if (data.prediction && onPreviewUpdate) {
        onPreviewUpdate({
          mode: data.mode,
          settings: data.current,
          prediction: data.prediction,
          warnings: [],
          source: 'baseline',
        });
      }

      if (configResp.ok) {
        const cfg = await configResp.json();
        setAdvancedThresholds({
          pressure_cpu: Number(cfg.pressure_cpu_threshold ?? 70),
          pressure_memory: Number(cfg.pressure_memory_threshold ?? 75),
        });
      }
    } catch (error) {
      setWarnings([error.message || 'Unable to load tuning configuration.']);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInitial();
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  const payload = useMemo(() => ({
    cold_start_threshold: Number(draft.cold_start_threshold),
    cache_ttl: Number(draft.cache_ttl),
    ewma_alpha: Number(draft.ewma_alpha),
    process_churn_sensitivity: Number(draft.process_churn_sensitivity),
  }), [draft]);

  const previewNow = async (source = 'manual') => {
    setIsPreviewing(true);
    try {
      const response = await fetch(`${apiBase}/tuning/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error(`Preview failed (${response.status})`);
      const data = await response.json();
      setPreview(data.prediction || null);
      setMode(data.mode || 'Safe Mode');
      setWarnings(data.warnings || []);
      if (onPreviewUpdate) {
        onPreviewUpdate({
          mode: data.mode,
          settings: data.settings,
          prediction: data.prediction,
          warnings: data.warnings || [],
          source,
        });
      }
    } catch (error) {
      setWarnings([error.message || 'Preview failed.']);
    } finally {
      setIsPreviewing(false);
    }
  };

  useEffect(() => {
    if (!initializedRef.current) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      previewNow('auto');
    }, 260);
  }, [payload]);

  const applyPreset = (name) => {
    const preset = PRESETS[name];
    if (!preset) return;
    setSelectedPreset(name);
    setDraft(preset);
  };

  const handleApply = async () => {
    const approved = window.confirm('Apply tuning changes to IARIS now? This updates live behavior.');
    if (!approved) return;

    setIsApplying(true);
    try {
      const [applyResp, thresholdResp] = await Promise.all([
        fetch(`${apiBase}/tuning/apply`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ confirm: true, tuning: payload }),
        }),
        fetch(`${apiBase}/config/thresholds`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            pressure_cpu: Number(advancedThresholds.pressure_cpu),
            pressure_memory: Number(advancedThresholds.pressure_memory),
          }),
        }),
      ]);

      if (!applyResp.ok) throw new Error(`Apply failed (${applyResp.status})`);
      if (!thresholdResp.ok) throw new Error(`Advanced threshold apply failed (${thresholdResp.status})`);

      const data = await applyResp.json();
      setDraft(data.applied || payload);
      setMode(data.mode || 'Safe Mode');
      setPreview(data.prediction || null);
      setWarnings(data.warnings || []);
      setLastAppliedSnapshot(data.previous || null);

      if (onApplied) {
        onApplied({
          mode: data.mode,
          settings: data.applied,
          prediction: data.prediction,
          previous: data.previous,
          warnings: data.warnings || [],
        });
      }

      if (onPreviewUpdate) {
        onPreviewUpdate({
          mode: data.mode,
          settings: data.applied,
          prediction: data.prediction,
          warnings: data.warnings || [],
          source: 'applied',
        });
      }
    } catch (error) {
      setWarnings([error.message || 'Failed to apply tuning.']);
    } finally {
      setIsApplying(false);
    }
  };

  const handleReset = async () => {
    const approved = window.confirm('Reset tuning values to startup defaults?');
    if (!approved) return;

    setIsApplying(true);
    try {
      const response = await fetch(`${apiBase}/tuning/reset?confirm=true`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error(`Reset failed (${response.status})`);
      const data = await response.json();
      setDraft(data.applied || PRESETS.Balanced);
      setMode(data.mode || 'Safe Mode');
      setPreview(data.prediction || null);
      setWarnings(data.warnings || []);
      setSelectedPreset('Balanced');
      if (onPreviewUpdate) {
        onPreviewUpdate({
          mode: data.mode,
          settings: data.applied,
          prediction: data.prediction,
          warnings: data.warnings || [],
          source: 'reset',
        });
      }
    } catch (error) {
      setWarnings([error.message || 'Reset failed.']);
    } finally {
      setIsApplying(false);
    }
  };

  const handleUndo = async () => {
    if (!lastAppliedSnapshot) {
      setWarnings(['No prior tuning snapshot available to undo.']);
      return;
    }

    setIsApplying(true);
    try {
      const response = await fetch(`${apiBase}/tuning/apply`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirm: true, tuning: lastAppliedSnapshot }),
      });
      if (!response.ok) throw new Error(`Undo failed (${response.status})`);
      const data = await response.json();
      setDraft(data.applied || lastAppliedSnapshot);
      setPreview(data.prediction || null);
      setMode(data.mode || 'Safe Mode');
      setWarnings(data.warnings || []);
      if (onPreviewUpdate) {
        onPreviewUpdate({
          mode: data.mode,
          settings: data.applied,
          prediction: data.prediction,
          warnings: data.warnings || [],
          source: 'undo',
        });
      }
    } catch (error) {
      setWarnings([error.message || 'Undo failed.']);
    } finally {
      setIsApplying(false);
    }
  };

  const handleSaveProfile = () => {
    const normalizedName = profileName.trim();
    if (!normalizedName) {
      setWarnings(['Enter a profile name before saving.']);
      return;
    }
    const nextProfiles = { ...profiles, [normalizedName]: payload };
    setProfiles(nextProfiles);
    setStoredProfiles(nextProfiles);
    setProfileName('');
    setWarnings([]);
  };

  const loadProfile = (name) => {
    const saved = profiles[name];
    if (!saved) return;
    setDraft(saved);
    setSelectedPreset('Custom');
  };

  const removeProfile = (name) => {
    const next = { ...profiles };
    delete next[name];
    setProfiles(next);
    setStoredProfiles(next);
  };

  if (loading) {
    return (
      <div className="glass-panel tuning-loading-panel">
        <div className="panel-header">
          <span><SlidersHorizontal size={18} /> Tuning Panel</span>
        </div>
        <div className="text-secondary">Loading current tuning values...</div>
      </div>
    );
  }

  return (
    <div className="tuning-layout">
      <div className="glass-panel tuning-main-card">
        <div className="tuning-header-row">
          <div>
            <div className="tuning-title">Tuning Panel</div>
            <div className="tuning-subtitle">Adjust IARIS behavior for better efficiency and stability</div>
          </div>
          <span className={`badge ${modeClass(mode)}`}>{mode}</span>
        </div>

        <div className="tuning-controls-stack">
          <SliderControl
            label="Cold Start Threshold"
            value={payload.cold_start_threshold}
            min={ranges.cold_start_threshold.min}
            max={ranges.cold_start_threshold.max}
            step={ranges.cold_start_threshold.step}
            onChange={(value) => setDraft((prev) => ({ ...prev, cold_start_threshold: Number(value.toFixed(2)) }))}
            description="Confidence required before bootstrapping from similar process history."
            hint="Higher improves cold-start accuracy but may delay early matching for unfamiliar processes."
            formatter={(value) => value.toFixed(2)}
          />

          <SliderControl
            label="Cache TTL"
            value={payload.cache_ttl}
            min={ranges.cache_ttl.min}
            max={ranges.cache_ttl.max}
            step={ranges.cache_ttl.step}
            onChange={(value) => setDraft((prev) => ({ ...prev, cache_ttl: value }))}
            description="Control how often the system rechecks cached decisions."
            hint="Higher reduces CPU overhead, lower reacts faster to rapid behavior shifts."
            valueSuffix="s"
          />

          <SliderControl
            label="EWMA Learning Rate (Alpha)"
            value={payload.ewma_alpha}
            min={ranges.ewma_alpha.min}
            max={ranges.ewma_alpha.max}
            step={ranges.ewma_alpha.step}
            onChange={(value) => setDraft((prev) => ({ ...prev, ewma_alpha: Number(value.toFixed(2)) }))}
            description="Adjust how quickly IARIS learns from new process telemetry."
            hint="Higher adapts faster; lower is calmer and more stable during noisy periods."
            formatter={(value) => value.toFixed(2)}
          />

          <SliderControl
            label="Process Churn Sensitivity"
            value={payload.process_churn_sensitivity}
            min={ranges.process_churn_sensitivity.min}
            max={ranges.process_churn_sensitivity.max}
            step={ranges.process_churn_sensitivity.step}
            onChange={(value) => setDraft((prev) => ({ ...prev, process_churn_sensitivity: value }))}
            description="Sensitivity to process metric shifts between cached scoring windows."
            hint="Higher catches churn sooner but increases recomputation overhead."
          />
        </div>
      </div>

      <div className="tuning-side-stack">
        <div className="glass-panel tuning-presets-card">
          <div className="panel-header">
            <span><Gauge size={16} /> Quick Presets</span>
          </div>
          <div className="tuning-preset-grid">
            {Object.keys(PRESETS).map((name) => (
              <button
                key={name}
                type="button"
                className={`tuning-preset-chip ${selectedPreset === name ? 'active' : ''}`}
                onClick={() => applyPreset(name)}
              >
                {name}
              </button>
            ))}
          </div>
          <div className="tuning-preset-note">
            Choose a balanced or aggressive mode, then fine tune with sliders.
          </div>
        </div>

        <div className="glass-panel tuning-summary-card">
          <div className="panel-header">
            <span><FlaskConical size={16} /> Live Impact Summary</span>
            <span className={`tuning-risk-pill ${verdictClass(preview?.risk?.color)}`}>
              {preview?.risk?.verdict || 'Pending'}
            </span>
          </div>
          <div className="tuning-summary-grid">
            <div className="tuning-summary-metric info">
              <span>Hit Rate</span>
              <strong>{preview?.hit_rate?.toFixed(1) ?? '--'}%</strong>
              <em>{formatSigned(preview?.delta?.hit_rate, '%')}</em>
            </div>
            <div className="tuning-summary-metric caution">
              <span>CPU Overhead</span>
              <strong>{preview?.cpu_overhead?.toFixed(1) ?? '--'}%</strong>
              <em>{formatSigned(preview?.delta?.cpu_overhead, '%', 1, true)}</em>
            </div>
            <div className="tuning-summary-metric info">
              <span>Convergence Time</span>
              <strong>{preview?.convergence_time ?? '--'}s</strong>
              <em>{formatSigned(preview?.delta?.convergence_time, 's', 0, true)}</em>
            </div>
            <div className="tuning-summary-metric healthy">
              <span>Cold Start Accuracy</span>
              <strong>{preview?.cold_start_accuracy?.toFixed(1) ?? '--'}%</strong>
              <em>{formatSigned(preview?.delta?.cold_start_accuracy, '%')}</em>
            </div>
          </div>
          <div className="tuning-summary-helper">
            Preview impact before applying. These projections are synchronized with what-if simulation insights.
          </div>
        </div>

        <div className="glass-panel tuning-advanced-card">
          <button type="button" className="tuning-advanced-toggle" onClick={() => setAdvancedOpen((prev) => !prev)}>
            <span>
              <Shield size={16} /> Advanced
            </span>
            {advancedOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
          {advancedOpen && (
            <div className="tuning-advanced-content">
              <SliderControl
                label="CPU Pressure Threshold"
                value={advancedThresholds.pressure_cpu}
                min={50}
                max={95}
                step={1}
                onChange={(value) => setAdvancedThresholds((prev) => ({ ...prev, pressure_cpu: value }))}
                description="When CPU reaches this level, IARIS enters pressure handling mode."
                hint="Lower values are safer but may trigger mitigation too early."
                valueSuffix="%"
              />
              <SliderControl
                label="Memory Pressure Threshold"
                value={advancedThresholds.pressure_memory}
                min={50}
                max={95}
                step={1}
                onChange={(value) => setAdvancedThresholds((prev) => ({ ...prev, pressure_memory: value }))}
                description="Memory threshold that triggers protective allocation behavior."
                hint="Use higher values only when workloads are naturally memory-heavy."
                valueSuffix="%"
              />
            </div>
          )}
        </div>

        <div className="glass-panel tuning-actions-card">
          <div className="panel-header">
            <span><Zap size={16} /> Actions</span>
          </div>
          <div className="tuning-actions-grid">
            <button className="btn btn-primary" onClick={() => previewNow('manual')} disabled={isPreviewing || isApplying}>
              <PlayCircle size={16} /> {isPreviewing ? 'Previewing...' : 'Preview Impact'}
            </button>
            <button className="btn" onClick={handleApply} disabled={isApplying || isPreviewing}>
              <CheckCircle2 size={16} /> {isApplying ? 'Applying...' : 'Apply Changes'}
            </button>
            <button className="btn" onClick={handleReset} disabled={isApplying || isPreviewing}>
              <RotateCcw size={16} /> Reset to Default
            </button>
            <button className="btn" onClick={handleSaveProfile} disabled={isApplying || isPreviewing}>
              <Save size={16} /> Save Profile
            </button>
            <button className="btn" onClick={handleUndo} disabled={isApplying || isPreviewing}>
              <Undo2 size={16} /> Undo Last Change
            </button>
            <button className="btn" onClick={onJumpToSimulator}>
              <FlaskConical size={16} /> Open in Simulator
            </button>
          </div>

          <div className="tuning-profile-save-row">
            <input
              className="tuning-profile-input"
              type="text"
              value={profileName}
              maxLength={40}
              placeholder="Profile name (for local save)"
              onChange={(event) => setProfileName(event.target.value)}
            />
          </div>

          {Object.keys(profiles).length > 0 && (
            <div className="tuning-profile-list">
              {Object.keys(profiles).sort().map((name) => (
                <div key={name} className="tuning-profile-item">
                  <button className="tuning-profile-load" onClick={() => loadProfile(name)}>{name}</button>
                  <button className="tuning-profile-delete" onClick={() => removeProfile(name)}>remove</button>
                </div>
              ))}
            </div>
          )}

          {warnings.length > 0 && (
            <div className="tuning-warning-box">
              <div className="tuning-warning-title"><AlertTriangle size={14} /> Review Before Apply</div>
              {warnings.map((warning, idx) => (
                <div key={`${warning}-${idx}`} className="tuning-warning-item">{warning}</div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default TuningPanel;
