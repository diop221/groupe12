"""Initialisation explicite (--init) et contrôle HTTP ; aucune preuve d'exploitation."""
import argparse
import http.cookiejar
import json
from pathlib import Path
import re
from urllib.request import build_opener, HTTPCookieProcessor, ProxyHandler
from urllib.parse import urlencode

parser = argparse.ArgumentParser()
parser.add_argument('--init', action='store_true', help='Réinitialise uniquement les deux bases dédiées DVWA')
args = parser.parse_args()
modules = sorted(p.name for p in Path('upstream/vulnerabilities').iterdir() if p.is_dir())
results = []
for port in (4280, 4281):
    base = f'http://127.0.0.1:{port}'
    client = build_opener(ProxyHandler({}), HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def get(path, data=None):
        with client.open(base + path, urlencode(data).encode() if data is not None else None, timeout=20) as r:
            return r.status, r.geturl(), r.read().decode(errors='replace')
    def token(html):
        return re.search(r"name=['\"]user_token['\"]\s+value=['\"]([^'\"]+)", html).group(1)
    if args.init:
        _, _, page = get('/setup.php')
        get('/setup.php', {'create_db': 'Create / Reset Database', 'user_token': token(page)})
    _, _, page = get('/login.php')
    _, url, page = get('/login.php', {'username': 'admin', 'password': 'password', 'Login': 'Login', 'user_token': token(page)})
    assert 'login.php' not in url, f'Connexion échouée : {base}'
    for module in modules:
        path = f'/vulnerabilities/{module}/' + ('?page=include.php' if module == 'fi' else '')
        try:
            code, url, html = get(path)
            ok = code == 200 and 'login.php' not in url and 'Fatal error' not in html
            results.append({'port': port, 'module': module, 'http': code, 'page_ok': ok})
        except Exception as error:
            results.append({'port': port, 'module': module, 'page_ok': False, 'error': str(error)})
Path('evidence').mkdir(exist_ok=True)
Path('evidence/http-check.json').write_text(json.dumps(results, indent=2))
for r in results:
    print(r)
raise SystemExit(0 if all(r['page_ok'] for r in results) else 1)
