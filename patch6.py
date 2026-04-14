import sys
import re

def main():
    with open('D:/IARIS/app_content.txt', 'r', encoding='utf-8') as f:
        text = f.read().replace('\r\n', '\n')

    # Attempt utf-8, fallback if it looks weird? 
    # Or just use regex to ignore the dash.
    
    header_idx = text.find('</header>') + 9
    app_closing_idx = text.rfind('</div>\n  );\n}')

    if header_idx < 10 or app_closing_idx == -1:
        print('Error finding boundaries')
        return

    top = text[:header_idx]
    content = text[header_idx:app_closing_idx]
    bottom = text[app_closing_idx:]

    def get_block(start_rgx, end_rgx=None):
        m_s = re.search(start_rgx, content)
        if not m_s:
            raise ValueError(f"Start not found: {start_rgx}")
        s = m_s.start()
        
        if end_rgx is None:
            return content[s:].rstrip()
            
        m_e = re.search(end_rgx, content[s:])
        if not m_e:
            raise ValueError(f"End not found: {end_rgx}")
        e = s + m_e.start()
        return content[s:e].rstrip()
    
    sys_state = get_block(r'        {\/\* System State \*/}', r'        {\/\* Decision Engine')
    dec_engine = get_block(r'        {\/\* Decision Engine', r'        {\/\* Workload Intelligence')
    workload = get_block(r'        {\/\* Workload Intelligence', r'      </div>\n\n      {\/\* ════════')

    graph_comp = get_block(r'        <div className="glass-panel graph-container"', r'        {\/\* What-If Simulation')
    what_if = get_block(r'        {\/\* What-If Simulation', r'      </div>\n\n      {\/\* ════════')

    snapshot = get_block(r'      {\/\* ═══════════════════════════════════════════════════════════════════\n          BEFORE / AFTER SNAPSHOT', r'      {\/\* ═══════════════════════════════════════════════════════════════════\n          IMPACT METRICS')
    impact_metrics = get_block(r'      {\/\* ═══════════════════════════════════════════════════════════════════\n          IMPACT METRICS', r'      {\/\* ═══════════════════════════════════════════════════════════════════\n          PROCESS INTELLIGENCE')
    process_intel = get_block(r'      {\/\* ═══════════════════════════════════════════════════════════════════\n          PROCESS INTELLIGENCE', r'      {\/\* ═════════════════════════════════════════════════════════════════════\n          INSIGHT FEED')
    insight_feed = get_block(r'      {\/\* ═════════════════════════════════════════════════════════════════════\n          INSIGHT FEED', r'      {\/\* ═════════════════════════════════════════════════════════════════════\n          THROTTLING  &  LIMITATION')
    throttling = get_block(r'      {\/\* ═════════════════════════════════════════════════════════════════════\n          THROTTLING  &  LIMITATION', r'      {\/\* ═════════════════════════════════════════════════════════════════════\n          PREDICTION PANEL')
    prediction = get_block(r'      {\/\* ═════════════════════════════════════════════════════════════════════\n          PREDICTION PANEL', r'      {\/\* ═════════════════════════════════════════════════════════════════════\n          KNOWLEDGE PANEL')
    knowledge = get_block(r'      {\/\* ═════════════════════════════════════════════════════════════════════\n          KNOWLEDGE PANEL')

    tabs_ui = """
      {/* TABS NAVIGATION */}
      <div className="tabs-container" style={{ display: 'flex', gap: '8px', padding: '16px 0 8px 0', borderBottom: '1px solid rgba(255,255,255,0.1)', marginBottom: '16px', overflowX: 'auto' }}>
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
              transition: 'all 0.2s ease',
              whiteSpace: 'nowrap'
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

    with open('D:/IARIS/frontend/src/App.jsx', 'w', encoding='utf-8') as fw:
        fw.write(final)

if __name__ == '__main__':
    main()
