import sys

file_path = "frontend/src/App.jsx"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# I want to wrap the return statement's main <div className="dashboard-container"> 
# with the app-layout structure.

# Let's find: `return (`
idx_return = content.find("return (\n    <div className=\"dashboard-container\">")
if idx_return == -1:
    print("Could not find return statement")
    sys.exit(1)

# we need to replace the `tabConfig` with new labels and icons
new_tabs = """  const tabConfig = [
    { id: 'VISUALIZATION', label: 'Dashboard', icon: <ActivitySquare size={16} /> },
    { id: 'IMPACT ANALYSIS', label: 'Analysis', icon: <BarChart size={16} /> },
    { id: 'KEY INSIGHTS', label: 'Insights', icon: <Lightbulb size={16} /> },
    { id: 'KNOWLEDGE BASE', label: 'Knowledge Base', icon: <Server size={16} /> },
    { id: 'TUNING PANEL', label: 'Control', icon: <SlidersHorizontal size={16} /> },
    { id: 'RESULTS AND SIMULATION', label: 'Simulation', icon: <FlaskConical size={16} /> },
  ];"""

content = content.replace("  const tabConfig = [\n    { id: 'VISUALIZATION', label: 'VISUALIZATION' },\n    { id: 'RESULTS AND SIMULATION', label: 'RESULTS AND SIMULATION' },\n    { id: 'TUNING PANEL', label: 'TUNING PANEL' },\n    { id: 'KEY INSIGHTS', label: 'KEY INSIGHTS' },\n    { id: 'IMPACT ANALYSIS', label: 'IMPACT ANALISIS' },\n    { id: 'KNOWLEDGE BASE', label: 'KNOWLEDGE BASE' },\n  ];", new_tabs)

# Add imports if missing: SlidersHorizontal, Lightbulb, BarChart, Settings, Bell, Search mapped from lucide-react
top_imports = "import { "
import_line_idx = content.find("import { \n  Activity")
if import_line_idx == -1:
    import_line_idx = content.find("import {\n  Activity")

if import_line_idx != -1:
    # ensure new icons exist
    if "Lightbulb" not in content:
        content = content.replace("Activity,", "Activity,\n  Lightbulb,\n  Settings,\n  Bell,\n  SlidersHorizontal,\n  BarChart,\n  Search,")

old_return = """  return (
    <div className="dashboard-container">"""

new_return = """  return (
    <div className="app-layout">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="sidebar-brand-title">IARIS</div>
          <div className="sidebar-brand-subtitle">SYSTEM ACTIVE</div>
        </div>
        <div className="sidebar-nav">
          {tabConfig.map(tab => (
            <button
              key={tab.id}
              className={`sidebar-nav-item ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>
        <div className="sidebar-footer">
          <button className="btn-optimize w-full" onClick={manualRefreshFromApi} disabled={isManualRefreshing} style={{width: '100%'}}>
            {isManualRefreshing ? 'Refreshing...' : <>Optimize System</>}
          </button>
        </div>
      </aside>

      <div className="main-content-wrapper">
        {/* Top Navbar */}
        <header className="top-navbar">
          <div className="top-navbar-left">
            <div className="top-navbar-brand">IARIS</div>
            <div className="top-navbar-links">
              {['Dashboard', 'Analysis', 'Insights', 'Control', 'Simulation'].map(link => (
                <span key={link} className={`top-navbar-link ${tabConfig.find(t => t.id === activeTab)?.label === link ? 'active' : ''}`}>
                  {link}
                </span>
              ))}
            </div>
          </div>
          <div className="top-navbar-right">
             <div className="search-input-wrapper">
               <Search size={14} />
               <input type="text" className="top-search-input" placeholder="Search learned patterns..." />
             </div>
             <Bell size={20} color="var(--text-secondary)" style={{cursor: 'pointer'}} />
             <Settings size={20} color="var(--text-secondary)" style={{cursor: 'pointer'}} />
             <div style={{width: 32, height: 32, borderRadius: 16, background: '#333'}}></div>
             <button className="btn-optimize" style={{marginLeft: 8}} onClick={manualRefreshFromApi}>Optimize Now</button>
          </div>
        </header>

        <div className="dashboard-container">"""

content = content.replace(old_return, new_return)

# Close the new div at the end
end_idx = content.rfind("</div>\n  );\n}")
if end_idx != -1:
    content = content[:end_idx] + "</div>\n      </div>\n" + content[end_idx:]

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Patched App.jsx")
