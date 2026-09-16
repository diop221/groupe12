from pathlib import Path
import json
root = Path('upstream/vulnerabilities')
names = {
'api': ('API', 'Dépendances Composer, réécriture Apache ; étudier les versions et routes API.'),
'authbypass': ('Contournement des autorisations', 'Entrée de menu réservée à admin ; comparer plusieurs comptes.'),
'bac': ('Contrôle d’accès défaillant', 'Présent dans le dépôt mais masqué dans le menu ; ouvrir directement /vulnerabilities/bac/.'),
'brute': ('Force brute', 'Mesurer tentatives, temporisation et verrouillage avec une petite liste locale.'),
'captcha': ('CAPTCHA non sûr', 'Clés reCAPTCHA et accès externe requis pour le parcours complet : indisponible hors ligne.'),
'cryptography': ('Cryptographie', 'Plusieurs sous-exercices ; inventorier aussi les pages ECB, oracle et jetons.'),
'csp': ('Contournement de CSP', 'Certains exemples dépendent de domaines externes ; navigateur requis.'),
'csrf': ('CSRF', 'Navigateur victime connecté et origine attaquante locale distincte.'),
'exec': ('Injection de commandes', 'Cible locale et fichier témoin dans le conteneur uniquement.'),
'fi': ('Inclusion de fichiers', 'Inclure traversée et inclusion locale ; inclusion distante avec serveur témoin local à préparer.'),
'javascript': ('Attaques JavaScript', 'Analyse du code client et vérification serveur ; navigateur requis.'),
'open_redirect': ('Redirection ouverte', 'Destination témoin locale et analyse de Location / navigation.'),
'sqli': ('Injection SQL', 'Requête, résultat et preuve de divulgation sur données DVWA.'),
'sqli_blind': ('Injection SQL aveugle', 'Comparer réponses booléennes et délais selon les sources du niveau.'),
'upload': ('Téléversement non sûr', 'Types, contenu, stockage et exécution : fichiers témoins inoffensifs.'),
'weak_id': ('Identifiants de session faibles', 'Échantillon de jetons ; prédictibilité et limites statistiques.'),
'xss_d': ('XSS DOM', 'Source et sink client, exécution dans un navigateur.'),
'xss_r': ('XSS réfléchie', 'Réponse HTTP et exécution dans un navigateur.'),
'xss_s': ('XSS stockée', 'Persistance et ouverture depuis une autre session victime.')}
rows=[]
for p in sorted(root.iterdir()):
    if not p.is_dir(): continue
    title, note=names[p.name]
    levels=[n for n in ('low','medium','high','impossible') if (p/'source'/f'{n}.php').exists()]
    rows.append(dict(module=p.name,title=title,levels=levels,note=note,status='À analyser / exploiter / corriger / rejouer'))
Path('docs/inventory.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
header='# Périmètre complet de la version figée\n\n19 modules ; les niveaux présents ne garantissent pas quatre implémentations différentes ou complètes. Le niveau « impossible » est une référence pédagogique upstream, pas une certification.\n\n| Module | Objet | Niveaux présents | Prérequis / points à vérifier |\n|---|---|---|---|\n'
Path('docs/inventory.md').write_text(header+'\n'.join(f"| `{r['module']}` | {r['title']} | {', '.join(r['levels'])} | {r['note']} |" for r in rows)+'\n\nTous les modules sont au périmètre. Aucun n’est encore déclaré corrigé ou validé en exploitation. Le contrôle HTTP ne prouve que le chargement des pages. SSRF ne figure pas comme module autonome dans cette version : ne pas annoncer une couverture DVWA dédiée de ce sujet.\n')
