import re

with open('app_content.txt', encoding='utf-8') as f:
    text = f.read()

def get_block(start_comment):
    # Find the comment
    idx = text.find(start_comment)
    if idx == -1: return None
    
    # We assume the next thing is a block like <div...
    start_tag_idx = text.find('<div', idx)
    
    # Simple brace matcher to find the end of the div
    open_braces = 0
    in_tag = False
    for i in range(start_tag_idx, len(text)):
        if text[i:i+4] == '<div':
            open_braces += 1
        elif text[i:i+6] == '</div>':
            open_braces -= 1
            if open_braces == 0:
                return text[idx:i+6]
    return None

import pprint
# Panels:
p_sys = get_block('{/* System Core State */}')
p_dec = get_block('{/* Decision Engine')
p_work = get_block('{/* Workload Intelligence')
p_hist = get_block('{/* History & Convergence Trend */}')
p_sim = get_block('{/* What-If Simulation')
p_eff = get_block('{/* Operating Efficiency')
p_insight = get_block('{/* Insight Feed')
p_proc = get_block('{/* Active Process Pool')

# Throttling is inside an IIFE
idx = text.find('{(() => {\n        const allDecs = gameState.decisions || [];\n        const throttled')
if idx == -1:
    idx = text.find('{(() => {')
end_iife = text.find('})()}', idx) + 5
p_throttle = text[idx:end_iife] if idx != -1 else None

p_sys_pred = get_block('{/* System Predictions')
if not p_sys_pred: p_sys_pred = "<!-- SYS PRED MISSING -->"
p_rec = get_block('{/* Recommendations')
if not p_rec: p_rec = "<!-- REC MISSING -->"
p_know = "<KnowledgePanel />"

print(p_sys is not None, p_dec is not None, p_work is not None, p_hist is not None, p_sim is not None, p_eff is not None, p_insight is not None, p_proc is not None, p_throttle is not None)
