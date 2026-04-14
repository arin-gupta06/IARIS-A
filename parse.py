import re
with open('app_content.txt', encoding='utf-8') as f:
    content = f.read()

for m in re.findall(r'<div className=[\"\'\']panel-header.*?>(.*?)</div>', content, re.DOTALL | re.IGNORECASE):
    print(re.sub(r'<[^>]+>', '', m).strip().replace('\n', ' '))
