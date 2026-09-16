# Périmètre complet de la version figée

19 modules ; les niveaux présents ne garantissent pas quatre implémentations différentes ou complètes. Le niveau « impossible » est une référence pédagogique upstream, pas une certification.

| Module | Objet | Niveaux présents | Prérequis / points à vérifier |
|---|---|---|---|
| `api` | API | low, medium, high, impossible | Dépendances Composer, réécriture Apache ; étudier les versions et routes API. |
| `authbypass` | Contournement des autorisations | low, medium, high, impossible | Entrée de menu réservée à admin ; comparer plusieurs comptes. |
| `bac` | Contrôle d’accès défaillant | low, medium, high, impossible | Présent dans le dépôt mais masqué dans le menu ; ouvrir directement /vulnerabilities/bac/. |
| `brute` | Force brute | low, medium, high, impossible | Mesurer tentatives, temporisation et verrouillage avec une petite liste locale. |
| `captcha` | CAPTCHA non sûr | low, medium, high, impossible | Clés reCAPTCHA et accès externe requis pour le parcours complet : indisponible hors ligne. |
| `cryptography` | Cryptographie | low, medium, high, impossible | Plusieurs sous-exercices ; inventorier aussi les pages ECB, oracle et jetons. |
| `csp` | Contournement de CSP | low, medium, high, impossible | Certains exemples dépendent de domaines externes ; navigateur requis. |
| `csrf` | CSRF | low, medium, high, impossible | Navigateur victime connecté et origine attaquante locale distincte. |
| `exec` | Injection de commandes | low, medium, high, impossible | Cible locale et fichier témoin dans le conteneur uniquement. |
| `fi` | Inclusion de fichiers | low, medium, high, impossible | Inclure traversée et inclusion locale ; inclusion distante avec serveur témoin local à préparer. |
| `javascript` | Attaques JavaScript | low, medium, high, impossible | Analyse du code client et vérification serveur ; navigateur requis. |
| `open_redirect` | Redirection ouverte | low, medium, high, impossible | Destination témoin locale et analyse de Location / navigation. |
| `sqli` | Injection SQL | low, medium, high, impossible | Requête, résultat et preuve de divulgation sur données DVWA. |
| `sqli_blind` | Injection SQL aveugle | low, medium, high, impossible | Comparer réponses booléennes et délais selon les sources du niveau. |
| `upload` | Téléversement non sûr | low, medium, high, impossible | Types, contenu, stockage et exécution : fichiers témoins inoffensifs. |
| `weak_id` | Identifiants de session faibles | low, medium, high, impossible | Échantillon de jetons ; prédictibilité et limites statistiques. |
| `xss_d` | XSS DOM | low, medium, high, impossible | Source et sink client, exécution dans un navigateur. |
| `xss_r` | XSS réfléchie | low, medium, high, impossible | Réponse HTTP et exécution dans un navigateur. |
| `xss_s` | XSS stockée | low, medium, high, impossible | Persistance et ouverture depuis une autre session victime. |

Tous les modules sont au périmètre. Aucun n’est encore déclaré corrigé ou validé en exploitation. Le contrôle HTTP ne prouve que le chargement des pages. SSRF ne figure pas comme module autonome dans cette version : ne pas annoncer une couverture DVWA dédiée de ce sujet.
