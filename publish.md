Pour publier cette librairie sur les dépôts Python, le flux standard est : construire le package, le vérifier, puis l’envoyer sur TestPyPI et enfin sur PyPI. Dans votre cas, la base est déjà prête dans pyproject.toml : backend setuptools, métadonnées projet et découverte des packages sous vtherm_api.

La procédure concrète :

0. Mettre à jour __init__.py avec la version `__version__`
1. Créer un compte sur PyPI et TestPyPI.
2. Générer un token API sur chaque site.
3. Installer les outils de publication dans votre environnement :

  > `python -m pip install --upgrade build twine`

4. Construire les artefacts depuis la racine du repo :
Vous obtiendrez en général un sdist et une wheel dans dist/.
  > `python -m build`

5. Vérifier les artefacts :
  > `python -m twine check dist/*`

6. Publier d’abord sur TestPyPI :
  > `python -m twine upload --repository testpypi dist/*`

7. Tester l’installation :
  > `pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple vtherm_api`

8. Si tout est bon, publier sur PyPI :
    > `python -m twine upload dist/*`

Points spécifiques configurés sur ce dépôt :

- **Version dynamique** : La version source est définie dans [src/vtherm_api/__init__.py](src/vtherm_api/__init__.py) (`__version__ = "0.10.0"`). `pyproject.toml` la lit dynamiquement.
- **Support Python** : `requires-python` est configuré à `>=3.13`.
- **Métadonnées PyPI** : `project.urls` est renseigné (Repository, Documentation, Bug Tracker).
- **Dépendances de dev** : `build` et `twine` sont inclus dans `requirements-dev.txt` et `pyproject.toml`.