# Publication sur PyPI

La publication est automatisée par le workflow GitHub Actions
[release.yml](.github/workflows/release.yml) : un push de tag `v…` construit les
distributions, vérifie que le tag correspond à leur version, publie sur PyPI via *Trusted Publishing*,
puis crée la release GitHub avec ses notes. La procédure manuelle historique
reste décrite en fin de document comme solution de secours.

## Configuration préalable (une seule fois)

### 1. Trusted publisher PyPI

Sur PyPI, dans les paramètres du projet `vtherm_api`, ajouter un
*pending publisher* (ou configurer le projet existant) avec :

- **Owner / Repository** : le dépôt GitHub où s'exécute le workflow
  (ex. `jmcollin78/vtherm_api`).
- **Workflow name** : `release.yml`
- **Environment name** : `pypi`

Aucun token API n'est alors nécessaire : le job `pypi` obtient un token OIDC
temporaire (`id-token: write` limité à ce job).

### 2. Environnement GitHub `pypi`

Créer l'environnement `pypi` dans les paramètres du dépôt GitHub
(*Settings > Environments*) et y activer de préférence une **approbation
manuelle requise** (*Required reviewers*) : chaque publication PyPI attendra
une validation humaine. Le nom doit être exactement `pypi`, référencé par le
job de publication.

### 3. Protection des tags de release

Seuls les tags commençant par `v` déclenchent une release. Créer un *tag
ruleset* (*Settings > Rules > Rulesets > New tag ruleset*) ciblant le motif
`v*`, avec les règles *Restrict creations*, *Restrict updates* et *Restrict
deletions*, et n'autoriser en *Bypass list* que les mainteneurs habilités à
publier. Les autres tags restent libres et ne publient rien.

## Procédure de release

1. **Préparer la version** : mettre à jour `__version__` dans
   [src/vtherm_api/__init__.py](src/vtherm_api/__init__.py) (`pyproject.toml`
   la lit dynamiquement), committer et pousser sur `main`. La version ne doit
   jamais réutiliser une version déjà publiée sur PyPI (versions immuables).
2. **Taguer** avec `v` suivi exactement de la valeur de `__version__` (un tag
   sans `v` ne déclenche pas le workflow) :

   > `git tag v1.2.3 && git push origin v1.2.3`

   Le tag doit reprendre la forme normalisée PEP 440 de la version, celle des
   noms de fichiers construits : `v1.2.3rc1` et non `v1.2.3-rc.1`. Les
   préversions (`a`, `b`, `rc`, `.dev`) sont marquées *pre-release* sur GitHub.
3. **Contrôler le workflow** dans l'onglet Actions :
   - job `validate` : absence de release GitHub existante pour ce tag,
     construction, `twine check` et accord du tag avec la version construite ;
   - job `pypi` : publication (après approbation si configurée) ;
   - job `github-release` : création de la release GitHub, avec des notes
     générées par GitHub (`--generate-notes` : pull requests fusionnées depuis
     la release précédente et lien *Full Changelog*).
4. **Vérifier le résultat** : la version sur PyPI, la release GitHub et son
   drapeau *pre-release* le cas échéant.

## Dépannage

- **Tag invalide ou désaccord avec `__version__`** : le job `validate`
  échoue avant toute publication. Corriger la source ou supprimer le tag
  (`git push origin :refs/tags/v…`), puis retaguer.
- **Échec du job `github-release` après une publication PyPI réussie** : ne
  pas repousser le tag (PyPI rejetterait la version déjà publiée). Relancer
  uniquement le job échoué via *Re-run failed jobs* dans l'onglet Actions.
- **Upload PyPI partiel** (certains fichiers envoyés avant un échec) : une
  version PyPI est immuable, ne pas republier aveuglément. Vérifier sur PyPI
  les fichiers présents et leurs empreintes (`pip download vtherm_api==X.Y.Z
  --no-deps` puis comparer les SHA256 avec ceux de `dist/`) avant toute
  intervention manuelle sur le portail PyPI.
- **Le tag a déjà une release GitHub** : le job `validate` échoue avant toute
  publication ; supprimer la release existante ou utiliser un nouveau tag.
- **Notes de release incomplètes** : seules les pull requests fusionnées y
  figurent, pas les commits poussés directement sur `main`. Les notes restent
  modifiables à la main sur la page de la release.

## Procédure manuelle de secours

Si le workflow est indisponible, la publication manuelle reste possible :

0. Mettre à jour `__version__` dans `src/vtherm_api/__init__.py`.
1. Installer les outils : `python -m pip install --upgrade build twine`
2. Construire : `python -m build` (sdist et wheel dans `dist/`)
3. Vérifier : `python -m twine check dist/*`
4. Publier d'abord sur TestPyPI : `python -m twine upload --repository testpypi dist/*`
5. Tester l'installation :
   `pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple vtherm_api`
6. Publier sur PyPI : `python -m twine upload dist/*` (token API requis)

Points spécifiques configurés sur ce dépôt :

- **Version dynamique** : `pyproject.toml` lit `vtherm_api.__version__`.
- **Support Python** : `requires-python` est configuré à `>=3.13`.
- **Métadonnées PyPI** : `project.urls` est renseigné (Repository,
  Documentation, Bug Tracker).
- **Dépendances de dev** : `build` et `twine` sont inclus dans
  `requirements-dev.txt` et `pyproject.toml`.
