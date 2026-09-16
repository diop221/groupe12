# Étude DVWA — Master SSI

Source officielle : https://github.com/digininja/DVWA
Version du code : `b496a5d3de6b967410155e1b7d3e51e9d035eb22` (voir VERSION).

## Accès

- Référence : http://127.0.0.1:4280
- Copie de travail à corriger : http://127.0.0.1:4281
- Connexion initiale : **admin / password**.

La seconde instance est encore vulnérable : aucun correctif personnel n’a été appliqué. Les deux instances commencent au niveau low. Changer de niveau dans « DVWA Security » permet d'étudier les protections fournies par DVWA, sans les attribuer à notre travail.

Utiliser deux profils de navigateur distincts pour comparer les instances : leurs sessions PHP sont séparées mais DVWA utilise aussi un cookie `security`, partagé entre ports sur une même adresse.

## Démarrer / arrêter

```bash
cd /home/modou/dvwa-study
mkdir -p corrections/vulnerabilities/api/vendor
docker compose up -d
docker compose ps
# Arrêt sans suppression des bases
docker compose down
```

Les données MariaDB et les fichiers téléversés sont conservés dans des volumes distincts. Ne pas ajouter `-v` à down pour les préserver. Les applications et bases utilisent deux réseaux internes séparés ; seul le proxy publie les deux ports sur la boucle locale. Aucun dossier personnel n'est monté dans DVWA.

## Initialisation et contrôles

Les bases ont une initialisation explicite via le formulaire officiel de DVWA. Pour la première installation seulement, ou pour une réinitialisation volontaire :

```bash
python3 scripts/check.py --init
```

Cette commande réinitialise les deux bases dédiées ; les comptes reviennent aux valeurs de démonstration. Pour vérifier sans réinitialiser :

```bash
python3 scripts/check.py
```

Le script contrôle la connexion et les 19 pages de modules sur les deux instances. Résultats : `evidence/http-check.json`. Il ne réalise pas les attaques et ne prouve pas le fonctionnement JavaScript ou CAPTCHA.

## Code et correctifs

- `upstream/` : dépôt officiel à conserver comme référence.
- `corrections/` : worktree Git sur `study/corrections`, même point de départ.
- Les fichiers de `corrections/vulnerabilities/` sont servis directement en lecture seule dans la seconde instance. Les dépendances Composer API disposent d’un volume distinct.
- Les autres fichiers de la copie de travail ne sont pas montés : une modification hors de vulnerabilities nécessite d'adapter explicitement le déploiement.
- `git -C corrections diff` montre nos changements ; conserver un commit distinct par correction.

## Tous les modules

Voir [inventaire complet](docs/inventory.md) et `docs/inventory.json`. Le module BAC est volontairement caché par le menu upstream ; accès direct : http://127.0.0.1:4280/vulnerabilities/bac/ et http://127.0.0.1:4281/vulnerabilities/bac/.

Le CAPTCHA est inclus dans l'étude, mais son parcours complet nécessite des clés reCAPTCHA et des accès externes. Aucune clé n'est inventée et aucune ouverture réseau n'est ajoutée pour le simuler. Certains exemples CSP nécessitent aussi des ressources externes. Les serveurs témoins locaux nécessaires aux exercices distants seront ajoutés lors de leur préparation. Ces limites font partie du suivi ; elles ne constituent pas des tests réussis.

## Méthode pour chaque module

1. Décrire le fonctionnement légitime et les frontières de confiance.
2. Lire les sources de chaque niveau et inventorier les sous-scénarios.
3. Capturer les requêtes et les effets réels sur la référence.
4. Expliquer les protections upstream et leurs limites.
5. Implémenter notre correctif dans la copie de travail.
6. Rejouer l'attaque et les usages légitimes via le proxy et, si nécessaire, un navigateur victime distinct.
7. Conserver code, preuves, résultats et limites.

Le précédent laboratoire Flask est conservé séparément et n'a pas été modifié.
