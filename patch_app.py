import sys

def main():
    with open('frontend/src/App.jsx', 'r', encoding='utf-8') as f:
        text = f.read()

    header_idx = text.find('</header>') + 9
    app_closing_idx = text.rfind('</div>\n  );\n}')

    if header_idx < 10 or app_closing_idx == -1:
        print('Error finding boundaries')
        return

    top = text[:header_idx]
    content = text[header_idx:app_closing_idx]
    bottom = text[app_closing_idx:]

    def get_block(start_str, end_str=None):
        s = content.find(start_str)
        if s == -1:
            raise ValueError(f"Start not found: {start_str[:30]}")
        if end_str is None:
            return content[s:].rstrip()
        e = content.find(end_str, s)
        if e == -1:
            raise ValueError(f"End not found: {end_str[:30]}")
        return content[s:e].rstrip()

    marker_top_panels = '      {/* ═══════════════════════════════════════════════════════════════════\n          TOP PANELS GRID'
    
    top_grid_start = content.find('<div className="top-panels-grid">')
    sys_state = get_block('        {/* System State */}', '        {/* Decision Engine — ')
    dec_engine = get_block('        {/* Decision Engine — ', '        {/* Workload Intelligence — ')
    workload = get_block('        {/* Workload Intelligence — ', '      </div>\n\n      {/* ════════════════════')

    graph_start = get_block('      {/* ═══════════════════════════════════════════════════════════════════\n          GRAPH DASHBOARD', '      {/* ═══════════════════════════════════════════════════════════════════\n          BEFORE / AFTER SNAPSHOT')
    graph_comp = get_block('        <div className="glass-panel graph-container"', '        {/* What-If Simulation — ')
    what_if = get_block('        {/* What-If Simulation — ', '      </div>\n\n')

    snapshot = get_block('      {/* ═══════════════════════════════════════════════════════════════════\n          BEFORE / AFTER SNAPSHOT', '      {/* ═══════════════════════════════════════════════════════════════════\n          IMPACT METRICS')
    impact_metrics = get_block('      {/* ═══════════════════════════════════════════════════════════════════\n          IMPACT METRICS', '      {/* ═══════════════════════════════════════════════════════════════════\n          PROCESS INTELLIGENCE TABLE')
    process_intel = get_block('      {/* ═══════════════════════════════════════════════════════════════════\n          PROCESS INTELLIGENCE TABLE', '      {/* ═════════════════════════════════════════════════════════════════════\n          INSIGHT FEED')
    insight_feed = get_block('      {/* ═════════════════════════════════════════════════════════════════════\n          INSIGHT FEED', '      {/* ═════════════════════════════════════════════════════════════════════\n          THROTTLING  &  LIMITATION PANEL')
    throttling = get_block('      {/* ═════════════════════════════════════════════════════════════════════\n          THROTTLING  &  LIMITATION PANEL', '      {/* ═════════════════════════════════════════════════════════════════════\n          PREDICTION PANEL')
    prediction = get_block('      {/* ═════════════════════════════════════════════════════════════════════\n          PREDICTION PANEL', '      {/* ═════════════════════════════════════════════════════════════════════\n          KNOWLEDGE PANEL')
    knowledge = get_block('      {/* ═════════════════════════════════════════════════════════════════════\n          KNOWLEDGE PANEL')

    tabs_ui = """
      {/* TABS NAVIGATION */}
      <div className="tabs-container" style={{ display: 'flex', gap: '8px', padding: '16px 0 8px 0', borderBottom: '1px solid rgba(255,255,255,0.1)', marginBottom: '16px' }}>
        {['VISUALIZATION', 'RESULTS AND SIMULATION', 'KEY INSIGHTS', 'IMPACT ANALYSIS', 'KNOWLEDGE BASE'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '8px 16px',
              background: activeTab === tab ? 'var(--accent-primary)' : 'rgba(255,255,255,0.05)',
              color: activeTab === tab ? '#fff' : 'var(--text-secondary)',
              border: 'none',
              borderRadius: '4px',
              fontFamily: 'monospace',
              fontSize: '12px',
              fontWeight: 'bold',
              cursor: 'pointer',
              transition: 'all 0.2s ease'
            }}
          >
            {tab}
          </button>
        ))}
      </div>
"""

    tab_viz = f"""
      {{activeTab === 'VISUALIZATION' && (
        <div className="simulation-grid">
{graph_comp}
        </div>
      )}}
"""

    tab_results = f"""
      {{activeTab === 'RESULTS AND SIMULATION' && (
        <>
          <div className="top-panels-grid">
{sys_state}
{dec_engine}
          </div>
          <div className="simulation-grid" style={{ marginTop: '16px' }}>
{what_if}
          </div>
          <div style={{ marginTop: '16px' }}>
{impact_metrics}
          </div>
        </>
      )}}
"""

    tab_insights = f"""
      {{activeTab === 'KEY INSIGHTS' && (
        <>
{process_intel}
{insight_feed}
        </>
      )}}
"""

    tab_impact = f"""
      {{activeTab === 'IMPACT ANALYSIS' && (
        <>
          <div className="top-panels-grid">
{workload}
          </div>
{throttling}
{prediction}
        </>
      )}}
"""

    tab_knowledge = f"""
      {{activeTab === 'KNOWLEDGE BASE' && (
        <>
{knowledge}
        </>
      )}}
"""

    snapshot_block = f"""
{snapshot}
"""

    new_content = tabs_ui + snapshot_block + tab_viz + tab_results + tab_insights + tab_impact + tab_knowledge

    final = top + new_content + "\n" + bottom

    with open('frontend/src/App.jsx', 'w', encoding='utf-8') as fw:
        fw.write(final)

if __name__ == '__main__':
    main()
