from __future__ import annotations
import argparse, datetime as dt, html, json, os, re, tempfile, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RULES = {
    '本地大模型': ['llama', 'ollama', 'strata', 'mlx', 'inference', 'local-llm', 'gguf'],
    '游戏开发': ['unity', 'unreal', 'godot', 'game-development', 'gamedev'],
    'AI与智能体': ['agent', 'llm', 'ai', 'deepseek', 'chatgpt', 'mcp', 'rag'],
    '界面与网页': ['frontend', 'css', 'react', 'vue', 'ui', 'design', 'web'],
    '开发工具': ['developer-tools', 'cli', 'devtools', 'git', 'automation'],
    '知识与效率': ['notes', 'bookmark', 'knowledge', 'productivity', 'markdown'],
}

def classify(repo):
    words = set(re.findall(r'[a-z0-9]+(?:-[a-z0-9]+)*', (repo['full_name']+' '+(repo.get('description') or '')+' '+' '.join(repo.get('topics', []))).lower()))
    return [k for k, terms in RULES.items() if words.intersection(terms)] or ['其他']

def read_json(path, default):
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else default

def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as f:
        f.write(text)
        tmp = Path(f.name)
    tmp.replace(path)

def fetch_stars(username):
    if not re.fullmatch(r'[A-Za-z0-9-]+', username):
        raise ValueError('Invalid GitHub username')
    headers = {'Accept': 'application/vnd.github.star+json', 'User-Agent': 'momo-toolbox', 'X-GitHub-Api-Version': '2022-11-28'}
    token = os.getenv('GH_TOKEN') or os.getenv('GITHUB_TOKEN')
    if token:
        headers['Authorization'] = 'Bearer '+token
    result = []
    for page in range(1, 1001):
        url = f'https://api.github.com/users/{username}/starred?per_page=100&page={page}&sort=created&direction=desc'
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
            batch = json.load(response)
        if not isinstance(batch, list) or any(not isinstance(x,dict) or 'repo' not in x or not isinstance(x['repo'].get('id'),int) for x in batch):
            raise ValueError('Unexpected API response; existing data left unchanged')
        result.extend(batch)
        if len(batch) < 100:
            return result
    raise RuntimeError('Pagination limit exceeded; existing data left unchanged')

def merge(previous, fetched, now):
    records = {r['id']: dict(r, active=False) for r in previous}
    for item in fetched:
        r = item['repo']
        if r.get('private'):
            continue  # v1 intentionally imports public starred repositories only
        old = records.get(r['id'], {})
        records[r['id']] = {k:r.get(k) for k in ['id','full_name','description','language','topics','pushed_at','archived']}
        records[r['id']].update(url='https://github.com/'+r['full_name'], starred_at=item.get('starred_at'), first_seen=old.get('first_seen',now), active=True, suggested_categories=classify(r))
    return sorted(records.values(), key=lambda r:r.get('starred_at') or r['first_seen'], reverse=True)

def enrich(records, notes):
    out=[]
    for r in records:
        n=notes.get(str(r['id']), notes.get(r['full_name'], {}))
        if not isinstance(n,dict):
            raise ValueError('Each note must be an object')
        cats=n.get('categories') or r['suggested_categories']
        if not isinstance(cats,list) or not all(isinstance(c,str) for c in cats):
            raise ValueError('categories must be a list of strings')
        out.append(dict(r, categories=cats, summary=n.get('summary',''), use_when=n.get('use_when',''), tags=n.get('tags',[]), note=n.get('note',''), reviewed=n.get('reviewed',False)))
    return out

def md(s):
    return html.escape(str(s or '')).replace('|','&#124;').replace('\n',' ').replace('[','&#91;').replace(']','&#93;')

def render(records, now, owner):
    rows=enrich(records, read_json(ROOT/'notes.json', {}))
    active=[r for r in rows if r['active']]
    inbox=[r for r in active if not r['reviewed']]
    def table(items):
        return '\n'.join(['| 项目 | 简介 / 使用场景 | 分类 |','|---|---|---|']+[f"| [{md(r['full_name'])}]({r['url']}) | {md(r['summary'] or r['description'])} {md(r['use_when'])} | {md(' / '.join(r['categories']))} |" for r in items])
    write(ROOT/'INBOX.md', f'# 待整理清单\n\n最后成功同步：{now}。共 {len(inbox)} 项。分类为关键词建议，不是 AI 结论。\n\n'+table(inbox)+'\n')
    sections=['# 分类索引', f'最后成功同步：{now}。当前 Star：{len(active)}。', '[待整理](INBOX.md) · [使用说明](README.md) · [个人笔记](notes.json)']
    for cat in sorted({c for r in active for c in r['categories']}):
        sections += ['## '+md(cat), table([r for r in active if cat in r['categories']])]
    write(ROOT/'INDEX.md', '\n\n'.join(sections)+'\n')
    payload=json.dumps(rows,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Momo 收藏工具箱</title><style>body{font:16px system-ui;margin:36px auto;max-width:1000px;padding:0 20px;background:#f5f7fb;color:#192638}h1{margin-bottom:8px}input,select{font:inherit;padding:10px;margin:8px 8px 8px 0;border:1px solid #bdc7d4;border-radius:8px}input{width:min(90%,430px)}article{background:white;padding:20px;border-radius:12px;margin:14px 0;border:1px solid #e0e5ed}a{color:#215db0}small{color:#526279}p{white-space:pre-wrap}button{font:inherit;padding:10px;cursor:pointer}</style><h1>📚 Momo 收藏工具箱</h1><p>按你要解决的问题找工具。纯本地搜索，不上传数据。</p><input id="q" aria-label="搜索" placeholder="搜索名称、简介、标签、用途…"><select id="cat" aria-label="分类"><option value="">全部分类</option></select><select id="status" aria-label="状态"><option value="active">当前收藏</option><option value="inbox">待整理</option><option value="all">全部（含已取消或不可见）</option></select><button id="reset">重置</button><p id="count"></p><main id="results"></main><script id="data" type="application/json">PAYLOAD</script><script>
const rows=JSON.parse(document.getElementById('data').textContent), q=document.getElementById('q'), cat=document.getElementById('cat'), status=document.getElementById('status'), results=document.getElementById('results');
[...new Set(rows.flatMap(r=>r.categories))].sort().forEach(c=>{const o=document.createElement('option');o.value=c;o.textContent=c;cat.append(o)});
function draw(){const words=q.value.toLowerCase().trim().split(/\\s+/).filter(Boolean);const found=rows.filter(r=>(status.value==='all'||r.active)&&(status.value!=='inbox'||!r.reviewed)&&(!cat.value||r.categories.includes(cat.value))&&words.every(w=>JSON.stringify(r).toLowerCase().includes(w)));results.replaceChildren();document.getElementById('count').textContent=found.length+' 个结果 · 最后同步 SYNC_TIME';found.forEach(r=>{const a=document.createElement('article'),link=document.createElement('a'),p=document.createElement('p'),small=document.createElement('small');link.href=r.url;link.target='_blank';link.rel='noopener noreferrer';link.textContent=r.full_name;p.textContent=[r.summary||r.description||'暂无简介',r.use_when&&'使用场景：'+r.use_when,r.note&&'笔记：'+r.note].filter(Boolean).join('\\n');small.textContent=r.categories.join(' / ')+' · '+(r.reviewed?'已整理':'待整理')+(!r.active?' · 已取消 Star 或当前不可见':'')+(r.archived?' · 上游已归档':'');a.append(link,p,small);results.append(a)});if(!found.length)results.textContent='没有匹配结果，试试更短的关键词。'}
q.addEventListener('input',draw);cat.addEventListener('change',draw);status.addEventListener('change',draw);document.getElementById('reset').onclick=()=>{q.value='';cat.value='';status.value='active';draw()};draw();</script></html>'''
    write(ROOT/'search.html',page.replace('PAYLOAD',payload).replace('SYNC_TIME',now))

def main():
    p=argparse.ArgumentParser();p.add_argument('--render-only',action='store_true');args=p.parse_args()
    config=read_json(ROOT/'config.json', {'username':'BreezyMomo'})
    path=ROOT/'stars.json';old=read_json(path, {'records':[], 'last_sync':None})
    if args.render_only:
        render(old['records'],old['last_sync'] or '尚未同步',config['username']);return
    fetched=fetch_stars(config['username'])
    if not fetched and any(r['active'] for r in old['records']):
        raise RuntimeError('API unexpectedly returned zero stars; refusing to overwrite. Check account visibility/access.')
    now=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    records=merge(old['records'],fetched,now)
    render(records,now,config['username'])
    write(path,json.dumps({'username':config['username'],'last_sync':now,'records':records},ensure_ascii=False,indent=2)+'\n')
    print(f'Synced {sum(r["active"] for r in records)} public stars; notes untouched.')

if __name__=='__main__':main()
