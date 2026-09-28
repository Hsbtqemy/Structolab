# -*- coding: utf-8 -*-
"""
Interface Streamlit pour l'extraction du squelette XML.
Lancement : streamlit run app_streamlit.py   (ou lancer_interface.bat)
Le moteur est celui de extraire_structure.py, place dans le meme dossier.
"""

import io
import time
import zipfile
from pathlib import Path, PurePosixPath

import streamlit as st

import extraire_structure as moteur

DOSSIER_APP = Path(__file__).resolve().parent

st.set_page_config(page_title="Structolab - Squelette XML", page_icon="🦴", layout="wide")


# --------------------------------------------------------------------------
# Traitement
# --------------------------------------------------------------------------
@st.cache_data(show_spinner=False, max_entries=500)
def traiter(octets, mode, commentaires, vider_dans, garder_dans, chemins, nom):
    """Renvoie (statut, detail, squelette, chemins_txt)."""
    try:
        resultat = moteur.squelette_octets(octets, mode, commentaires, vider_dans, garder_dans)
        txt = moteur.texte_chemins(moteur.ET.fromstring(octets), nom) if chemins else None
        return "OK", "", resultat, txt
    except moteur.ET.ParseError as e:
        return "Erreur", f"XML invalide : {e}", None, None
    except Exception as e:
        return "Erreur", f"{type(e).__name__} : {e}", None, None


def lire_depots(fichiers):
    """Fichiers deposes -> liste (chemin relatif, octets). Les ZIP sont ouverts."""
    documents = []
    for f in fichiers:
        if f.name.lower().endswith(".zip"):
            with zipfile.ZipFile(f) as z:
                for info in z.infolist():
                    chemin = PurePosixPath(info.filename)
                    if (not info.is_dir() and chemin.suffix.lower() == ".xml"
                            and "__MACOSX" not in chemin.parts):
                        documents.append((str(chemin), z.read(info)))
        else:
            documents.append((f.name, f.getvalue()))
    return documents


def lignes_debut(octets, n):
    texte = octets.decode(moteur.detecter_encodage(octets), errors="replace")
    lignes = texte.splitlines()
    extrait = "\n".join(lignes[:n])
    return extrait, len(lignes)


def taille(n):
    return f"{n / 1024:.1f} Ko" if n < 1024 ** 2 else f"{n / 1024 ** 2:.1f} Mo"


# --------------------------------------------------------------------------
# Options
# --------------------------------------------------------------------------
with st.sidebar:
    st.header("Options")

    metadonnees = st.checkbox(
        "Garder les métadonnées",
        value=False,
        help="Recopie le <teiHeader> tel quel, texte compris. "
             "Les autres options ne s'appliquent pas à l'intérieur.")
    garder_dans = frozenset({"teiHeader"}) if metadonnees else frozenset()

    choix_attr = st.radio(
        "Attributs",
        ["Garder les valeurs", "Effacer les valeurs", "Supprimer les attributs"],
        help="Effacer : ident=\"fr\" devient ident=\"\". "
             "Les déclarations xmlns sont toujours conservées.")
    mode = {"Garder les valeurs": "garder", "Effacer les valeurs": "vider",
            "Supprimer les attributs": "supprimer"}[choix_attr]

    zones = st.text_input(
        "Effacer les valeurs d'attributs dans",
        value="profileDesc",
        disabled=(mode != "garder"),
        help="Noms d'éléments séparés par des virgules. Les valeurs d'attributs de "
             "ces éléments et de tout ce qu'ils contiennent sont effacées.")
    vider_dans = frozenset(z.strip() for z in zones.split(",") if z.strip()) \
        if mode == "garder" else frozenset()

    commentaires = st.checkbox("Garder les commentaires", value=False)
    chemins = st.checkbox("Ajouter la liste des chemins (.txt)", value=False)

    st.divider()
    st.caption("Le texte est retiré (sauf dans les métadonnées si elles sont gardées) ; balises, indentation, déclaration, DOCTYPE, "
               "fins de ligne et encodage restent ceux de l'original. Chaque squelette "
               "est relu et comparé à l'original avant d'être proposé.")


# --------------------------------------------------------------------------
# Page
# --------------------------------------------------------------------------
st.title("Structolab - Squelette XML")
st.write("Retire le texte d'un document XML et garde sa structure exacte.")

onglet_depot, onglet_dossier = st.tabs(["Déposer des fichiers", "Traiter un dossier"])

# ---- Onglet 1 : depot de fichiers ------------------------------------------
with onglet_depot:
    fichiers = st.file_uploader(
        "Fichiers XML, ou un ZIP qui en contient",
        type=["xml", "zip"], accept_multiple_files=True)

    if not fichiers:
        st.info("Déposez un ou plusieurs fichiers .xml, ou un .zip : "
                "l'arborescence du ZIP sera conservée dans le résultat.")
    else:
        documents = lire_depots(fichiers)
        if not documents:
            st.warning("Aucun fichier .xml trouvé dans ce dépôt.")
        else:
            resultats = []
            with st.spinner("Extraction en cours…"):
                for nom, octets in documents:
                    statut, detail, sq, txt = traiter(
                        octets, mode, commentaires, vider_dans, garder_dans, chemins, nom)
                    resultats.append(dict(nom=nom, original=octets, statut=statut,
                                          detail=detail, squelette=sq, chemins=txt))

            nb_ok = sum(r["statut"] == "OK" for r in resultats)
            nb_err = len(resultats) - nb_ok
            if nb_err:
                st.error(f"{nb_ok} fichier(s) traité(s), {nb_err} en erreur.")
            else:
                st.success(f"{nb_ok} fichier(s) traité(s).")

            st.dataframe(
                [{"Fichier": r["nom"],
                  "Statut": "✅ OK" if r["statut"] == "OK" else "❌ Erreur",
                  "Original": taille(len(r["original"])),
                  "Squelette": taille(len(r["squelette"])) if r["squelette"] else "",
                  "Détail": r["detail"]} for r in resultats],
                width="stretch", hide_index=True)

            ok = [r for r in resultats if r["statut"] == "OK"]
            if ok:
                # Telechargement : le fichier seul, ou un ZIP
                if len(ok) == 1 and not chemins:
                    nom_sortie = PurePosixPath(ok[0]["nom"]).name
                    st.download_button(f"Télécharger {nom_sortie}", ok[0]["squelette"],
                                       file_name=nom_sortie, mime="application/xml",
                                       type="primary")
                else:
                    tampon = io.BytesIO()
                    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as z:
                        for r in ok:
                            z.writestr(r["nom"], r["squelette"])
                            if r["chemins"]:
                                base = PurePosixPath(r["nom"])
                                z.writestr(str(base.with_name(base.stem + "_chemins.txt")),
                                           r["chemins"])
                        erreurs = [r for r in resultats if r["statut"] != "OK"]
                        if erreurs:
                            z.writestr("_erreurs.log", "\n".join(
                                f"{r['nom']}\n  {r['detail']}" for r in erreurs))
                    st.download_button(f"Télécharger les {len(ok)} squelettes (ZIP)",
                                       tampon.getvalue(), file_name="squelettes.zip",
                                       mime="application/zip", type="primary")

                # Apercu cote a cote
                st.subheader("Aperçu")
                c1, c2 = st.columns([3, 1])
                choisi = c1.selectbox("Fichier", [r["nom"] for r in ok])
                nb_lignes = c2.number_input("Lignes affichées", 10, 2000, 60, step=10)
                r = next(r for r in ok if r["nom"] == choisi)
                extrait_o, total_o = lignes_debut(r["original"], nb_lignes)
                extrait_s, total_s = lignes_debut(r["squelette"], nb_lignes)
                g, d = st.columns(2)
                with g:
                    st.markdown(f"**Original** · {total_o} lignes")
                    st.code(extrait_o, language="xml")
                with d:
                    st.markdown(f"**Squelette** · {total_s} lignes")
                    st.code(extrait_s, language="xml")

# ---- Onglet 2 : dossier local ---------------------------------------------
with onglet_dossier:
    st.write("Pour les gros volumes : traite directement un dossier de votre ordinateur, "
             "sous-dossiers compris, et écrit les squelettes dans le dossier de sortie.")
    c1, c2 = st.columns(2)
    entree = c1.text_input("Dossier d'entrée", str(DOSSIER_APP / "depot"))
    sortie = c2.text_input("Dossier de sortie", str(DOSSIER_APP / "sortie"))

    if st.button("Traiter le dossier", type="primary"):
        entree_p, sortie_p = Path(entree).expanduser(), Path(sortie).expanduser()
        if not entree_p.is_dir():
            st.error(f"Le dossier d'entrée n'existe pas : {entree_p}")
        elif entree_p.resolve() == sortie_p.resolve():
            st.error("Le dossier de sortie doit être différent du dossier d'entrée, "
                     "sinon les originaux seraient écrasés.")
        else:
            liste = sorted(p for p in entree_p.rglob("*")
                           if p.is_file() and p.suffix.lower() == ".xml")
            if not liste:
                st.warning(f"Aucun fichier .xml dans {entree_p}")
            else:
                barre = st.progress(0.0, text="Démarrage…")
                bilan, debut = [], time.time()
                for i, f in enumerate(liste, 1):
                    relatif = f.relative_to(entree_p)
                    barre.progress(i / len(liste), text=f"{i}/{len(liste)} · {relatif}")
                    try:
                        moteur.traiter_fichier(f, sortie_p / relatif, mode, commentaires,
                                               chemins, vider_dans, garder_dans)
                        bilan.append({"Fichier": str(relatif), "Statut": "✅ OK", "Détail": ""})
                    except moteur.ET.ParseError as e:
                        bilan.append({"Fichier": str(relatif), "Statut": "❌ Erreur",
                                      "Détail": f"XML invalide : {e}"})
                    except Exception as e:
                        bilan.append({"Fichier": str(relatif), "Statut": "❌ Erreur",
                                      "Détail": f"{type(e).__name__} : {e}"})
                barre.empty()
                nb_err = sum(b["Statut"] != "✅ OK" for b in bilan)
                message = (f"{len(bilan) - nb_err} fichier(s) traité(s) en "
                           f"{time.time() - debut:.1f} s, écrits dans {sortie_p}")
                (st.error if nb_err else st.success)(
                    message + (f" — {nb_err} en erreur." if nb_err else "."))
                st.dataframe(bilan, width="stretch", hide_index=True)
