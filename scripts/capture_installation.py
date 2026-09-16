from pathlib import Path
import json
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
out=root/'docs/captures/installation'; out.mkdir(parents=True,exist_ok=True)
results=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/home/modou/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome',headless=True,args=['--no-sandbox'])
    for port in (4280,4281):
        context=browser.new_context(viewport={'width':1280,'height':960},device_scale_factor=1)
        page=context.new_page()
        def shot(name):
            page.screenshot(path=str(out/f'{port}-{name}.png'),full_page=True)
            results.append({'port':port,'page':name,'url':page.url,'title':page.title()})
        page.goto(f'http://127.0.0.1:{port}/login.php'); shot('connexion')
        page.locator('input[name=username]').fill('admin')
        page.locator('input[name=password]').fill('password')
        page.locator('input[name=Login]').click(); page.wait_for_load_state('networkidle')
        assert 'login.php' not in page.url, 'Connexion échouée'
        shot('accueil')
        page.goto(f'http://127.0.0.1:{port}/setup.php'); shot('configuration')
        page.goto(f'http://127.0.0.1:{port}/security.php'); shot('securite')
        page.goto(f'http://127.0.0.1:{port}/vulnerabilities/sqli/'); shot('module-sqli')
        context.close()
    browser.close()
(out/'manifest.json').write_text(json.dumps(results,indent=2))
print('10 captures réelles enregistrées dans',out)
