"""Verify every connection in a skills repo.

Checks:
  1. `Skill tool with "X"` targets exist AND are model-invoked (a user-invoked
     skill can never be reached by another skill).
  2. Cross-skill dependencies stay satisfiable given starter/extras split.
  3. /slash mentions in skills and docs resolve to a real skill or a known
     Claude Code builtin.
  4. Relative markdown/file links resolve.
  5. agents/openai.yaml agrees with SKILL.md on invocation.
  6. Markdown anchors referenced across docs exist.
"""
import os, re, sys, glob, yaml

ROOT = sys.argv[1] if len(sys.argv) > 1 else '.'
os.chdir(ROOT)

# Words that look like slash commands but are not: doc conventions and
# example URL routes appearing inside prose.
DOC_WORDS = {'slash', 'settings', 'login', 'users', 'posts', 'orders', 'search'}

BUILTINS = {
    'clear', 'compact', 'help', 'plugin', 'config', 'doctor', 'hooks', 'init',
    'review', 'code-review', 'debug', 'run', 'verify', 'security-review',
    'simplify', 'login', 'model', 'memory', 'agents', 'mcp', 'resume',
    'export', 'vim', 'terminal-setup', 'bug', 'cost', 'status', 'permissions',
    'add-dir', 'ide', 'skill-doctor',
}

FENCE = re.compile(r'```.*?```', re.S)
def strip_code(t):
    return FENCE.sub('', t)

def load_skills():
    out = {}
    for pattern, group in (('skills/*/SKILL.md', 'starter'), ('extras/*/*/SKILL.md', 'extras')):
        for p in glob.glob(pattern):
            d = os.path.dirname(p)
            name = os.path.basename(d)
            fm = re.match(r'^---\n(.*?)\n---\n', open(p, encoding='utf-8').read(), re.S)
            data = yaml.safe_load(fm.group(1)) if fm else {}
            out[name] = {
                'dir': d, 'path': p, 'group': group,
                'user_invoked': bool(data.get('disable-model-invocation')),
                'name_field': data.get('name'),
            }
    return out

S = load_skills()
problems = []
def bad(kind, where, msg):
    problems.append((kind, where, msg))

# ---- 1 & 2: Skill tool invocations -------------------------------------
deps = {}
for name, meta in S.items():
    for f in glob.glob(meta['dir'] + '/**/*.md', recursive=True):
        text = open(f, encoding='utf-8').read()
        clauses = re.findall(r'Skill tool[^.\n]*', text)
        targets = [q for c in clauses for q in re.findall(r'"([a-z][a-z0-9-]*)"', c)]
        for tgt in targets:
            deps.setdefault(name, set()).add(tgt)
            if tgt not in S:
                bad('MISSING SKILL', f, 'calls "%s" which does not exist' % tgt)
            elif S[tgt]['user_invoked']:
                bad('UNCALLABLE', f, 'calls "%s" but it is user-invoked, so no skill can reach it' % tgt)

# ---- 3: /slash mentions ------------------------------------------------
def slash_check(path, text):
    for m in re.findall(r'(?<![\w/.<])/([a-z][a-z0-9-]{2,})(?![\w/.-])', strip_code(text)):
        if m in DOC_WORDS:
            continue
        if m in S or m in BUILTINS:
            continue
        bad('DANGLING SLASH', path, '/%s' % m)

for name, meta in S.items():
    for f in glob.glob(meta['dir'] + '/**/*.md', recursive=True):
        slash_check(f, open(f, encoding='utf-8').read())
for f in glob.glob('*.md') + glob.glob('ideas/*.md'):
    slash_check(f, open(f, encoding='utf-8').read())

# ---- 4: relative links -------------------------------------------------
LINK = re.compile(r'\[[^\]]*\]\(([^)]+)\)')
for f in (glob.glob('*.md') + glob.glob('ideas/*.md')
          + [p for m in S.values() for p in glob.glob(m['dir'] + '/**/*.md', recursive=True)]):
    base = os.path.dirname(f)
    for href in LINK.findall(strip_code(open(f, encoding='utf-8').read())):
        if href.startswith(('http://', 'https://', 'mailto:', '#')):
            continue
        target, _, anchor = href.partition('#')
        if not target:
            continue
        cand = os.path.normpath(os.path.join(base, target))
        if not os.path.exists(cand) and not os.path.exists(target):
            bad('BROKEN LINK', f, href)
        elif anchor:
            real = cand if os.path.exists(cand) else target
            if real.endswith('.md'):
                heads = re.findall(r'^#+\s+(.*)$', open(real, encoding='utf-8').read(), re.M)
                slugs = {re.sub(r'[^a-z0-9 -]', '', h.lower()).replace(' ', '-') for h in heads}
                if anchor.lower() not in slugs:
                    bad('BROKEN ANCHOR', f, href)

# ---- 5: openai.yaml agreement ------------------------------------------
for name, meta in S.items():
    if meta['name_field'] != name:
        bad('NAME MISMATCH', meta['path'], 'frontmatter name=%r, dir=%r' % (meta['name_field'], name))
    y = os.path.join(meta['dir'], 'agents', 'openai.yaml')
    if not os.path.exists(y):
        bad('NO OPENAI YAML', meta['dir'], 'missing agents/openai.yaml')
        continue
    data = yaml.safe_load(open(y, encoding='utf-8')) or {}
    implicit = data.get('policy', {}).get('allow_implicit_invocation')
    codex_user = (implicit is False)
    if codex_user != meta['user_invoked']:
        bad('INVOCATION MISMATCH', y,
            'SKILL.md user_invoked=%s but openai.yaml implies user_invoked=%s'
            % (meta['user_invoked'], codex_user))

# ---- 2b: starter-set closure & extras dependency reachability ----------
print('=== dependency graph ===')
for a in sorted(deps):
    print('  %-28s -> %s' % (a, ', '.join(sorted(deps[a]))))

print()
print('=== starter set closure ===')
starter = {n for n, m in S.items() if m['group'] == 'starter'}
for a in sorted(starter):
    missing = {t for t in deps.get(a, ()) if t not in starter}
    if missing:
        bad('STARTER NOT CLOSED', a, 'needs %s which is not in the starter set' % sorted(missing))
print('  starter:', sorted(starter))

print()
print('=== extras that depend on other extras ===')
for a in sorted(deps):
    if S.get(a, {}).get('group') != 'extras':
        continue
    ext = sorted(t for t in deps[a] if S.get(t, {}).get('group') == 'extras')
    if ext:
        print('  %-28s needs %s (not installed by default)' % (a, ', '.join(ext)))

print()
print('=== problems ===')
if not problems:
    print('  none')
for kind, where, msg in sorted(problems):
    print('  [%s] %s: %s' % (kind, where, msg))
print()
print('total problems:', len(problems))
