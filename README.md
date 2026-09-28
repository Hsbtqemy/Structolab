# Structolab

Extrait le **squelette exact** de documents XML : le fichier est recopié caractère pour caractère, seul le texte est retiré.

Balises, attributs, indentation, déclaration XML, DOCTYPE, fins de ligne (LF/CRLF), BOM et encodage restent ceux de l'original. Chaque squelette est relu et comparé à l'original : tout écart de structure est signalé comme une erreur.

```xml
<!-- original -->
<p>
  <s>Par devant maître Honorat Grapazi, notaire…</s>
</p>

<!-- squelette -->
<p>
  <s></s>
</p>
```

## Utilisation

Trois façons de l'utiliser, toutes avec le même moteur (`extraire_structure.py`) :

| Outil | Usage | Installation |
|---|---|---|
| `extraire_structure.bat` | traitement par lot, double-clic | aucune : un Python portable est téléchargé au premier lancement (~11 Mo) dans `python_portable/` |
| `lancer_interface.bat` | interface dans le navigateur (Streamlit) | aucune : l'outil [uv](https://github.com/astral-sh/uv) installe Python et Streamlit dans `outils/` au premier lancement (~300 Mo) |
| `extraire_structure.ipynb` | Jupyter | nécessite Jupyter |

### Traitement par lot (`extraire_structure.bat`)

1. Double-cliquez sur `extraire_structure.bat` : les dossiers `depot/` et `sortie/` sont créés.
2. Déposez vos `.xml` dans `depot/` (sous-dossiers acceptés).
3. Relancez : les squelettes arrivent dans `sortie/`, avec la même arborescence. Les erreurs éventuelles sont détaillées dans `sortie/_erreurs.log`.

Les options se règlent dans la ligne `OPTIONS` du `.bat`.

### Interface (`lancer_interface.bat`)

Le navigateur s'ouvre sur `http://localhost:8501`. Onglet **Déposer des fichiers** (XML ou ZIP, téléchargement du résultat) ou **Traiter un dossier** (gros volumes). Fermez la fenêtre noire pour arrêter.

### En ligne de commande

```
python extraire_structure.py DOSSIER_ENTREE DOSSIER_SORTIE [options]
```

## Options

| Option | Effet |
|---|---|
| *(aucune)* | attributs conservés avec leurs valeurs |
| `--vider-dans A,B` | efface les valeurs d'attributs des éléments `A`, `B` et de tout ce qu'ils contiennent (ex. `--vider-dans profileDesc`) |
| `--vider-attributs` | efface toutes les valeurs d'attributs (`ident="fr"` → `ident=""`) |
| `--sans-attributs` | supprime les attributs (les déclarations `xmlns` sont toujours gardées) |
| `--garder-commentaires` | conserve les `<!-- commentaires -->` (retirés par défaut, comme les sections CDATA) |
| `--chemins` | ajoute `<nom>_chemins.txt` : liste des chemins avec leur nombre d'occurrences |
| `--garder-metadonnees` | recopie le `<teiHeader>` tel quel, texte compris (voir ci-dessous) |
| `--garder-dans A,B` | idem pour d'autres éléments |

Le `.bat` est livré avec `--vider-dans profileDesc`.

### Garder les métadonnées

Avec `--garder-metadonnees` (case « Garder les métadonnées » dans l'interface), chaque `<teiHeader>` est recopié à l'identique : texte, valeurs d'attributs, commentaires et CDATA compris. Aucune autre option ne s'applique à l'intérieur ; un `--vider-dans profileDesc` est donc sans effet sur le `profileDesc` de l'en-tête. Le reste du document est traité normalement.

## Précisions

- Un texte entouré de retours à la ligne garde ces retours à la ligne et son indentation, pour que la mise en page du squelette reste celle du document. Les retours à la ligne *à l'intérieur* d'un texte partent avec lui.
- Un fichier XML mal formé est signalé et n'interrompt pas le traitement des autres.
- Le moteur n'utilise que la bibliothèque standard de Python (3.9+) ; Streamlit n'est nécessaire que pour l'interface.
