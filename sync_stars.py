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

def github_headers(media_type):
    headers = {'Accept': media_type, 'User-Agent': 'momo-toolbox', 'X-GitHub-Api-Version': '2022-11-28'}
    token = os.getenv('GH_TOKEN') or os.getenv('GITHUB_TOKEN')
    if token:
        headers['Authorization'] = 'Bearer '+token
    return headers

def fetch_stars(username):
    if not re.fullmatch(r'[A-Za-z0-9-]+', username):
        raise ValueError('Invalid GitHub username')
    headers = github_headers('application/vnd.github.star+json')
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
        for field in ('ai_summary', 'ai_tags', 'ai_use_when', 'ai_summary_attempts', 'ai_no_evidence'):
            if field in old:
                records[r['id']][field] = old[field]
    return sorted(records.values(), key=lambda r:r.get('starred_at') or r['first_seen'], reverse=True)

def note_for(record, notes):
    note = notes.get(str(record['id']), notes.get(record['full_name'], {}))
    if not isinstance(note, dict):
        raise ValueError('Each note must be an object')
    return note

def validate_summary(text):
    if not isinstance(text, str):
        raise ValueError('expected a Chinese summary')
    sentence = ' '.join(text.replace('\u200b', '').split()).removesuffix('。').strip()
    if (not 4 <= len(sentence) <= 100 or not re.search(r'[\u4e00-\u9fff]', sentence)
            or sentence.startswith('资料不足') or not sentence.isprintable()
            or re.search(r'https?://|[。！？<>\[\]]', sentence, re.I)):
        raise ValueError('expected one short Chinese sentence')
    return sentence + '。'

def validate_keywords(tags):
    if not isinstance(tags, list):
        raise ValueError('expected a list of keywords')
    result = {}
    for tag in tags:
        if not isinstance(tag, str):
            raise ValueError('invalid keyword')
        tag = tag.strip()
        if (not 1 <= len(tag) <= 32 or not tag.isprintable() or not re.search(r'\w', tag)
                or re.search(r'//|[<>\[\]|\x60]', tag)):
            raise ValueError('invalid keyword')
        result.setdefault(tag.casefold(), tag)
    if not 3 <= len(result) <= 5:
        raise ValueError('expected 3 to 5 distinct keywords')
    return list(result.values())

def enrich(records, notes):
    out=[]
    for r in records:
        n=note_for(r, notes)
        cats=n.get('categories') or r['suggested_categories']
        if not isinstance(cats,list) or not all(isinstance(c,str) for c in cats):
            raise ValueError('categories must be a list of strings')
        generated = r.get('ai_summary')
        summary = n.get('summary') or (validate_summary(generated) if generated else '')
        tags = n.get('tags') or (validate_keywords(r['ai_tags']) if r.get('ai_tags') else [])
        use_when = n.get('use_when') or (validate_summary(r['ai_use_when']) if r.get('ai_use_when') else '')
        out.append(dict(r, categories=cats, summary=summary, use_when=use_when, tags=tags,
                        note=n.get('note',''), reviewed=n.get('reviewed',False)))
    return out

def md(s):
    return html.escape(str(s or '')).replace('|','&#124;').replace('\n',' ').replace('[','&#91;').replace(']','&#93;')

def render(records, now, owner):
    rows=enrich(records, read_json(ROOT/'notes.json', {}))
    active=[r for r in rows if r['active']]
    inbox=[r for r in active if not r['reviewed']]
    def table(items):
        lines = ['| 项目 | 简介 / 使用场景 | 关键词 | 分类 |', '|---|---|---|---|']
        for r in items:
            details = md(r['summary'] or r['description'])
            if r['use_when']:
                details += '<br>使用场景：' + md(r['use_when'])
            lines.append(f"| [{md(r['full_name'])}]({r['url']}) | {details} | {md('、'.join(r['tags']))} | {md(' / '.join(r['categories']))} |")
        return '\n'.join(lines)
    write(ROOT/'INBOX.md', f'# 待整理清单\n\n最后成功同步：{now}。共 {len(inbox)} 项。分类为关键词建议，不是 AI 结论。\n\n'+table(inbox)+'\n')
    sections=['# 分类索引', f'最后成功同步：{now}。当前 Star：{len(active)}。', '[待整理](INBOX.md) · [使用说明](README.md) · [个人笔记](notes.json)']
    for cat in sorted({c for r in active for c in r['categories']}):
        sections += ['## '+md(cat), table([r for r in active if cat in r['categories']])]
    write(ROOT/'INDEX.md', '\n\n'.join(sections)+'\n')
    payload=json.dumps(rows,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    template = Path(__file__).with_name('search.template.html').read_text(encoding='utf-8')
    page = template.replace('__LAST_SYNC__', html.escape(now, quote=True))
    write(ROOT/'search.html', page.replace('__STAR_DATA__', payload))

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
