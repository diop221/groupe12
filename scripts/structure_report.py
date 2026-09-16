from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from xml.etree import ElementTree as E

root = Path(__file__).resolve().parents[1]
path = root / 'GROUPE-12/Rapport-DVWA-TRAME.docx'
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
E.register_namespace('w', W)
def tag(n): return '{'+W+'}'+n
def el(n, attrs=None, text=None):
    e=E.Element(tag(n), {tag(k):v for k,v in (attrs or {}).items()})
    if text is not None: e.text=text
    return e
def para(text='', style=None):
    p=el('p')
    if style:
        pr=E.SubElement(p,tag('pPr')); pr.append(el('pStyle',{'val':style}))
    r=E.SubElement(p,tag('r')); r.append(el('t',text=text))
    return p
def field(code, fallback):
    p=el('p')
    for kind, value in [('begin',None),('instruction',code),('separate',None),('text',fallback),('end',None)]:
        r=E.SubElement(p,tag('r'))
        if kind=='instruction':
            t=el('instrText',text=value); t.set('{http://www.w3.org/XML/1998/namespace}space','preserve'); r.append(t)
        elif kind=='text': r.append(el('t',text=value))
        else: r.append(el('fldChar',{'fldCharType':kind, **({'dirty':'true'} if kind=='begin' else {})}))
    return p
def page():
    p=el('p'); r=E.SubElement(p,tag('r')); r.append(el('br',{'type':'page'})); return p
def table(rows):
    t=el('tbl'); pr=E.SubElement(t,tag('tblPr')); borders=E.SubElement(pr,tag('tblBorders'))
    for side in ['top','left','bottom','right','insideH','insideV']: borders.append(el(side,{'val':'single','sz':'4','color':'AAAAAA'}))
    for row in rows:
        tr=E.SubElement(t,tag('tr'))
        for text in row:
            tc=E.SubElement(tr,tag('tc')); tc.append(para(text))
    return t
with ZipFile(path) as z: files={n:z.read(n) for n in z.namelist()}
doc=E.fromstring(files['word/document.xml']); body=doc.find(tag('body'))
if 'Liste des figures' in ''.join(body.itertext()):
    raise SystemExit('Structure déjà ajoutée ; aucune modification.')
# Front matter after cover paragraphs, before chapter 1.
idx=next(i for i,p in enumerate(body) if ''.join(p.itertext()).startswith('1. Description'))
front=[page(),para('Sommaire','FrontTitle'),field(' TOC \\o "1-3" \\h \\z \\u ','Mettre à jour le champ pour afficher les titres et les pages.'),page(),para('Liste des figures','FrontTitle'),field(' TOC \\t "FigureCaption,1" \\h \\z ','Aucune capture intégrée à ce stade. La liste sera alimentée par les légendes des captures réelles.'),para('Les emplacements de captures ne sont pas des figures : ajouter une légende de style FigureCaption à chaque image réelle, avec un numéro de figure et une description.'),para('Liste des tableaux','FrontTitle'),field(' TOC \\t "TableCaption,1" \\h \\z ','Mettre à jour le champ pour afficher les tableaux et les pages.'),page()]
for offset,item in enumerate(front): body.insert(idx+offset,item)
idx=next(i for i,p in enumerate(body) if ''.join(p.itertext()).startswith('5. État'))
new=[para('4.1. Règles de preuve pour chaque test','Heading2'),para('Chaque essai doit disposer de captures réelles et lisibles : usage normal, attaque et effet observé, rejeu après correction, puis fonctionnement légitime après correction. Si un scénario comporte plusieurs essais (conditions vraie/fausse, niveaux, comptes ou variantes), dupliquer la fiche et associer les captures à chaque essai. Une capture du code complète la preuve ; elle ne remplace pas celle du résultat.'),para('Pour chaque capture : noter identifiant du test, instance, niveau DVWA, compte, date, entrée et résultat observé. Ajouter une légende numérotée « Figure n — … » et un renvoi dans le texte. Conserver les originaux dans docs/captures/. Ne pas conclure à une réussite sans preuve. Un test non exécuté doit rester indiqué comme tel.'),para('Tableau 1 — Suivi des modules et des preuves à recueillir','TableCaption')]
modules=[]
for line in (root/'docs/inventory.md').read_text().splitlines():
    if line.startswith('| `'):
        cells=[s.strip() for s in line.split('|')[1:-1]]; modules.append((cells[0].strip('`'),cells[1]))
new.append(table([['Identifiant','Module','État des essais / captures']]+[[f'T{i:02d}',title,'À réaliser / à insérer'] for i,(slug,title) in enumerate(modules,1)]))
for i,(slug,title) in enumerate(modules,1):
    test=f'T{i:02d}'
    new.extend([para(f'4.{i+1}. {test} — {title}','Heading2'),para(f'Module : /vulnerabilities/{slug}/. Fiche à dupliquer pour chaque variante testée. Statut : à réaliser ; aucune capture de test intégrée.'),para('Objectif et mécanisme : [à compléter]. Préconditions, compte, niveau, instance, date et état initial : [à compléter].'),para(f'Tableau {i+1} — Fiche de résultats {test} : {title}','TableCaption'),table([['Essai','Entrée / étapes','Attendu','Observé / preuve'],['Usage normal avant correction','À renseigner','À définir','Non exécuté'],['Attaque avant correction','À renseigner','À définir','Non exécuté'],['Rejeu après correction','À renseigner','À définir','Non exécuté'],['Usage normal après correction','À renseigner','À définir','Non exécuté']]),para(f'[Capture {test}-01 à insérer : usage normal avant correction.]'),para(f'[Capture {test}-02 à insérer : entrée de l’attaque et résultat observable ; ajouter des images si nécessaire.]'),para('Cause dans le code, protection DVWA étudiée, correctif personnel et justification : [à compléter en distinguant les contributions].'),para(f'[Capture {test}-03 à insérer : rejeu de l’attaque après correction et résultat.]'),para(f'[Capture {test}-04 à insérer : usage légitime après correction et résultat.]'),para('Analyse des résultats, limites et verdict : [à compléter après exécution].')])
for offset,item in enumerate(new): body.insert(idx+offset,item)
styles=E.fromstring(files['word/styles.xml'])
for name,size in [('FrontTitle','32'),('Heading2','26'),('FigureCaption','22'),('TableCaption','22')]:
    s=el('style',{'type':'paragraph','styleId':name}); s.append(el('name',{'val':name})); pr=E.SubElement(s,tag('pPr'))
    if name=='Heading2': pr.append(el('outlineLvl',{'val':'1'}))
    pr.append(el('spacing',{'before':'180','after':'100'})); rp=E.SubElement(s,tag('rPr')); rp.append(el('b')); rp.append(el('sz',{'val':size})); styles.append(s)
files['word/document.xml']=E.tostring(doc,encoding='utf-8',xml_declaration=True)
files['word/styles.xml']=E.tostring(styles,encoding='utf-8',xml_declaration=True)
with ZipFile(path,'w',ZIP_DEFLATED) as z:
    for n,data in files.items(): z.writestr(n,data)
with ZipFile(path) as z:
    assert z.testzip() is None
    d=E.fromstring(z.read('word/document.xml'))
    assert len(d.findall('.//'+tag('tbl')))==20
    assert len(d.findall('.//'+tag('instrText')))==3
print(f'Word mis à jour : 3 index, 19 fiches, 20 tableaux et 76 emplacements de captures. {path}')
