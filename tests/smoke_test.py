import urllib.request
import json
import sys

base = 'http://127.0.0.1:8080'

def get(path):
    with urllib.request.urlopen(base + path) as r:
        return r.status, r.read().decode('utf-8')

def post(path, payload):
    req = urllib.request.Request(
        base + path,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as r:
        return r.status, r.read().decode('utf-8')

print("=" * 68)
print("              CODEGUARD COMPREHENSIVE SMOKE TEST               ")
print("=" * 68)

# 1. Assets
for p in ['/', '/styles.css', '/app.js']:
    st, body = get(p)
    print(f"[STATIC] {p:<15} -> Status: {st} (Size: {len(body):,} bytes)")

# 2. Config
st, body = get('/api/config')
cfg = json.loads(body)
enabled_langs = [l["name"] for l in cfg["languages"] if l["enabled"]]
print(f"\n[CONFIG] Available languages: {enabled_langs}")
print(f"[CONFIG] Registered Presets: {len(cfg['presets'])}")

# 3. Presets & Pairwise Comparison
print("\n[PAIRWISE TESTS]")
for p_id in cfg['presets'].keys():
    _, p_body = get(f'/api/presets/{p_id}')
    p_data = json.loads(p_body)
    _, comp_body = post('/api/compare', {'code_a': p_data['code_a'], 'code_b': p_data['code_b'], 'language': 'c'})
    res = json.loads(comp_body)
    print(f"  • {p_id:<16}: Overall={res['overall_similarity']:>5.1f}% | Token={res['token_similarity']:>5.1f}% | AST={res['structural_similarity']:>5.1f}% | Risk=[{res['risk_level']}] | Short={res['is_short_code']}")

# 4. Batch Analysis
print("\n[BATCH MATRIX TEST]")
p_ident = json.loads(get('/api/presets/pair_identical')[1])
p_ren = json.loads(get('/api/presets/pair_renamed')[1])
p_unrel = json.loads(get('/api/presets/pair_unrelated')[1])
sample_batch = [
    {'filename': 'alice.c', 'author': 'Alice Chen', 'content': p_ident['code_a']},
    {'filename': 'bob.c', 'author': 'Bob Miller', 'content': p_ident['code_b']},
    {'filename': 'charlie.c', 'author': 'Charlie Davis', 'content': p_ren['code_b']},
    {'filename': 'evan.c', 'author': 'Evan Wright', 'content': p_unrel['code_b']}
]
st, b_body = post('/api/batch', {'submissions': sample_batch, 'threshold': 70.0})
b_res = json.loads(b_body)
print(f"  • Total Submissions: {b_res['total_submissions']}")
print(f"  • Total Pairwise Comparisons: {b_res['total_comparisons']}")
print(f"  • Flagged High-Risk Pairs (>70%): {len(b_res['flagged_pairs'])}")
for pair in b_res['flagged_pairs']:
    print(f"     - {pair['author_a']} & {pair['author_b']}: {pair['overall_similarity']:.1f}% [{pair['risk_level']}]")

# 5. Report Export
print("\n[REPORT EXPORT TEST]")
st, r_body = post('/api/report', {'code_a': p_ren['code_a'], 'code_b': p_ren['code_b'], 'language': 'c', 'author_a': 'Alice', 'author_b': 'Bob'})
print(f"  • Status: {st} (HTML Report Generated: {len(r_body):,} bytes)")
print("=" * 68)
print("              ALL SMOKE TESTS COMPLETED SUCCESSFULLY!          ")
print("=" * 68)
