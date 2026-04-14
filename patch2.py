import sys

def main():
    with open('frontend/src/App.jsx.backup', 'r', encoding='utf-8') as f:
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
    
    sys_state = get_block('        {/* System State */}', '        {/* Decision Engine — ')
    dec_engine = get_block('        {/* Decision Engine — ', '        {/* Workload Intelligence — ')
    workload = get_block('        {/* Workload Intelligence — ', '      </div>\n\n      {/* ════════════')

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

    tab_viz = "\n      {activeTab === 'VISUALIZATION' && (\n        <div className=\"simulation-grid\">\n" + graph_comp + "\n        </div>\n      )}\n"
    tab_results = "\n      {activeTab === 'RESULTS AND SIMULATION' && (\n        <>\n          <div className=\"top-panels-grid\">\n" + sys_state + "\n" + dec_engine + "\n          </div>\n\n          <div className=\"simulation-grid\" style={{ marginTop: '16px' }}>\n" + what_if + "\n          </div>\n          <div style={{ marginTop: '16px' }}>\n" + impact_metrics + "\n          </div>\n        </>\n      )}\n"
    tab_insights = "\n      {activeTab === 'KEY INSIGHTS' && (\n        <>\n" + process_intel + "\n" + insight_feed + "\n        </>\n      )}\n"
    tab_impact = "\n      {activeTab === 'IMPACT ANALYSIS' && (\n        <>\n          <div className=\"top-panels-grid\">\n" + workload + "\n          </div>\n" + throttling + "\n" + prediction + "\n        </>\n      )}\n"
    tab_knowledge = "\n      {activeTab === 'KNOWLEDGE BASE' && (\n        <>\n" + knowledge + "\n        </>\n      )}\n"

    snapshot_block = "\n" + snapshot + "\n"

    new_content = tabs_ui + snapshot_block + tab_viz + tab_results + tab_insights + tab_impact + tab_knowledge

    final = top + new_content + "\n" + bottom

    with open('frontend/src/App.jsx', 'w', encoding='utf-8') as fw:
        fw.write(final)

if __name__ == '__main__':
    main()