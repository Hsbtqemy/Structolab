#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extrait le squelette exact de fichiers XML : le document est recopie tel quel,
caractere pour caractere, en retirant uniquement le texte.

Ce qui est conserve a l'identique :
  - la declaration XML, le DOCTYPE, les instructions de traitement
  - chaque balise telle qu'ecrite (ordre, guillemets et espacement des attributs,
    <a/> reste <a/>, <a></a> reste <a></a>)
  - l'indentation, les retours a la ligne (LF ou CRLF), le BOM et l'encodage

Ce qui est retire :
  - le texte des elements (<s>Bonjour</s> devient <s></s>)
  - les sections CDATA et les commentaires (option --garder-commentaires)
Les retours a la ligne et l'indentation qui entouraient un texte sont gardes,
pour que la mise en page du squelette reste celle du document.

Apres ecriture, le squelette est relu et compare a l'original : memes elements,
meme ordre, memes attributs. Tout ecart est signale comme une erreur.

Utilisation :
  python extraire_structure.py DOSSIER_ENTREE DOSSIER_SORTIE [options]

Options :
  --garder-commentaires   conserve les commentaires <!-- ... -->
  --vider-attributs       garde les attributs mais efface leurs valeurs
  --sans-attributs        supprime les attributs (sauf declarations xmlns)
  --vider-dans NOMS       efface les valeurs d'attributs des elements nommes
                          ET de tout ce qu'ils contiennent, le reste etant garde
                          (noms separes par des virgules, ex. profileDesc,measure)
  --chemins               produit en plus <nom>_chemins.txt (liste des chemins)

Uniquement la bibliotheque standard de Python (3.9+).
"""

import argparse
import codecs
import re
import sys
import traceback
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

# --------------------------------------------------------------------------
# Decoupage lexical du document
# --------------------------------------------------------------------------
_ATTR_VAL = r'(?:"[^"]*"|\'[^\']*\')'
JETON = re.compile(
    r"(?P<commentaire><!--.*?-->)"
    r"|(?P<cdata><!\[CDATA\[.*?\]\]>)"
    r"|(?P<pi><\?.*?\?>)"
    r"|(?P<doctype><!DOCTYPE(?:[^\[>\"']|" + _ATTR_VAL + r")*(?:\[.*?\]\s*)?>)"
    r"|(?P<balise></?[^\s<>!?/][^<>\"']*(?:" + _ATTR_VAL + r"[^<>\"']*)*>)"
    r"|(?P<texte>[^<]+)",
    re.DOTALL,
)
ATTRIBUT = re.compile(r"(\s+)([^\s=/>]+)(\s*=\s*)(" + _ATTR_VAL + r")")


def blanc_de_structure(texte):
    """Pour un texte contenant des caracteres, ne garde que les blancs de mise
    en page (retour a la ligne + indentation) situes avant et apres."""
    avant = texte[: len(texte) - len(texte.lstrip())]
    apres = texte[len(texte.rstrip()):]
    garder = ""
    if "\n" in avant or "\r" in avant:
        garder += avant
    if "\n" in apres or "\r" in apres:
        garder += apres
    return garder


NOM_BALISE = re.compile(r"</?([^\s/>]+)")


def nom_local(nom):
    """'tei:profileDesc' ou '{uri}profileDesc' -> 'profileDesc'"""
    return nom.rsplit("}", 1)[-1].rsplit(":", 1)[-1]


def traiter_attributs(balise, mode):
    if mode == "garder" or balise.startswith("</"):
        return balise

    def remplacer(m):
        espace, nom, egal, valeur = m.groups()
        if nom == "xmlns" or nom.startswith("xmlns:"):
            return m.group(0)  # indispensable pour que le XML reste valide
        if mode == "vider":
            return f"{espace}{nom}{egal}{valeur[0]}{valeur[0]}"
        return ""  # supprimer

    return ATTRIBUT.sub(remplacer, balise)


def squelette(document, mode_attributs, garder_commentaires, vider_dans=frozenset()):
    morceaux, pos = [], 0
    pile = []  # True si l'element ouvert est dans une zone a vider
    en_attente = None  # blanc precedant un commentaire/CDATA retire
    for m in JETON.finditer(document):
        if m.start() != pos:
            raise ValueError(f"caractere inattendu a la position {pos}")
        pos = m.end()
        genre, valeur = m.lastgroup, m.group()

        if genre == "cdata" or (genre == "commentaire" and not garder_commentaires):
            # On met de cote le blanc qui precedait (retour a la ligne + indentation).
            # Si l'element retire occupait seul sa ligne, ce blanc est abandonne
            # pour ne pas laisser de ligne vide ; sinon il est remis tel quel.
            if en_attente is None:
                en_attente = morceaux.pop() if morceaux and not morceaux[-1].strip() else ""
            continue
        if en_attente is not None:
            seul_sur_sa_ligne = (genre == "texte" and not valeur.strip()
                                 and ("\n" in valeur or "\r" in valeur)
                                 and ("\n" in en_attente or "\r" in en_attente))
            if not seul_sur_sa_ligne:
                morceaux.append(en_attente)
            en_attente = None

        if genre == "texte":
            morceaux.append(valeur if not valeur.strip() else blanc_de_structure(valeur))
        elif genre == "balise":
            if valeur.startswith("</"):
                pile.pop()
                morceaux.append(valeur)
                continue
            nom = nom_local(NOM_BALISE.match(valeur).group(1))
            dans_zone = (pile and pile[-1]) or nom in vider_dans
            mode = "vider" if (dans_zone and mode_attributs == "garder") else mode_attributs
            morceaux.append(traiter_attributs(valeur, mode))
            if not valeur.endswith("/>"):
                pile.append(bool(dans_zone))
        else:  # declaration, instruction de traitement, DOCTYPE
            morceaux.append(valeur)
    if en_attente is not None:
        morceaux.append(en_attente)
    if pos != len(document):
        raise ValueError(f"fin de document non reconnue a la position {pos}")
    return "".join(morceaux)


# --------------------------------------------------------------------------
# Encodage : on relit et on reecrit dans l'encodage d'origine
# --------------------------------------------------------------------------
def detecter_encodage(octets):
    for bom, enc in ((codecs.BOM_UTF8, "utf-8-sig"),
                     (codecs.BOM_UTF32_LE, "utf-32"), (codecs.BOM_UTF32_BE, "utf-32"),
                     (codecs.BOM_UTF16_LE, "utf-16"), (codecs.BOM_UTF16_BE, "utf-16")):
        if octets.startswith(bom):
            return enc
    m = re.match(rb"\s*<\?xml[^?]*encoding\s*=\s*[\"']([A-Za-z0-9._-]+)", octets)
    if m:
        enc = m.group(1).decode("ascii")
        try:
            codecs.lookup(enc)
            return enc
        except LookupError:
            raise ValueError(f"encodage inconnu declare : {enc}")
    return "utf-8"


# --------------------------------------------------------------------------
# Controle : le squelette doit avoir exactement la structure de l'original
# --------------------------------------------------------------------------
def empreinte(racine, mode_attributs, vider_dans=frozenset()):
    """Liste (balise, attributs attendus) de tous les elements, dans l'ordre."""
    resultat = []

    def parcourir(e, dans_zone):
        dans_zone = dans_zone or nom_local(e.tag) in vider_dans
        mode = "vider" if (dans_zone and mode_attributs == "garder") else mode_attributs
        if mode == "garder":
            attrs = dict(e.attrib)
        elif mode == "vider":
            attrs = {k: "" for k in e.attrib}
        else:
            attrs = None
        resultat.append((e.tag, attrs))
        for enfant in e:
            parcourir(enfant, dans_zone)

    parcourir(racine, False)
    return resultat


def verifier(original, resultat, mode_attributs, vider_dans=frozenset()):
    a = ET.fromstring(original)
    b = ET.fromstring(resultat)
    if empreinte(a, mode_attributs, vider_dans) != empreinte(b, mode_attributs, vider_dans):
        raise ValueError("le squelette ne correspond pas a la structure d'origine")
    reste = [e.tag for e in b.iter() if e.text and e.text.strip()
             or e.tail and e.tail.strip()]
    if reste:
        raise ValueError(f"du texte subsiste dans : {reste[:5]}")


# --------------------------------------------------------------------------
# Liste des chemins (optionnelle)
# --------------------------------------------------------------------------
def texte_chemins(racine, nom_source):
    compteur = Counter()

    def parcourir(e, parent):
        chemin = f"{parent}/{e.tag}"
        compteur[chemin] += 1
        for nom in e.attrib:
            compteur[f"{chemin}/@{nom}"] += 1
        for enfant in e:
            parcourir(enfant, chemin)

    parcourir(racine, "")
    lignes = [f"{nb:>8}  {chemin}" for chemin, nb in compteur.items()]
    return (f"# Chemins de : {nom_source}\n# occurrences  chemin\n"
            + "\n".join(lignes) + "\n")


# --------------------------------------------------------------------------
def squelette_octets(octets, mode_attributs="garder", garder_commentaires=False,
                     vider_dans=frozenset()):
    """Octets d'un XML -> octets de son squelette (meme encodage), verifie."""
    ET.fromstring(octets)  # refuse d'emblee les XML mal formes
    encodage = detecter_encodage(octets)
    document = octets.decode(encodage)  # fins de ligne conservees telles quelles

    resultat = squelette(document, mode_attributs, garder_commentaires, vider_dans)
    sortie_octets = resultat.encode(encodage)
    if encodage == "utf-8-sig" and not sortie_octets.startswith(codecs.BOM_UTF8):
        sortie_octets = codecs.BOM_UTF8 + sortie_octets

    verifier(octets, sortie_octets, mode_attributs, vider_dans)
    return sortie_octets


def traiter_fichier(source, destination, mode_attributs, garder_commentaires, chemins,
                    vider_dans=frozenset()):
    octets = source.read_bytes()
    sortie_octets = squelette_octets(octets, mode_attributs, garder_commentaires, vider_dans)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(sortie_octets)
    if chemins:
        (destination.parent / f"{destination.stem}_chemins.txt").write_text(
            texte_chemins(ET.fromstring(octets), source.name), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Squelette exact de fichiers XML, sans le texte.")
    parser.add_argument("entree", help="Dossier contenant les fichiers XML")
    parser.add_argument("sortie", help="Dossier ou ecrire les squelettes")
    parser.add_argument("--garder-commentaires", action="store_true")
    parser.add_argument("--chemins", action="store_true")
    groupe = parser.add_mutually_exclusive_group()
    groupe.add_argument("--vider-attributs", action="store_true")
    groupe.add_argument("--sans-attributs", action="store_true")
    parser.add_argument("--vider-dans", default="",
                        help="elements (separes par des virgules) dont les valeurs "
                             "d'attributs sont effacees, descendants compris")
    args = parser.parse_args()

    mode = "supprimer" if args.sans_attributs else "vider" if args.vider_attributs else "garder"
    vider_dans = frozenset(n.strip() for n in args.vider_dans.split(",") if n.strip())
    entree, sortie = Path(args.entree).resolve(), Path(args.sortie).resolve()

    if not entree.is_dir():
        print(f"ERREUR : le dossier d'entree n'existe pas : {entree}")
        return 1
    sortie.mkdir(parents=True, exist_ok=True)

    fichiers = sorted(p for p in entree.rglob("*") if p.is_file() and p.suffix.lower() == ".xml")
    if not fichiers:
        print(f"Aucun fichier .xml trouve dans {entree}")
        return 0

    ok, erreurs = 0, []
    for f in fichiers:
        relatif = f.relative_to(entree)
        try:
            traiter_fichier(f, sortie / relatif, mode, args.garder_commentaires, args.chemins,
                            vider_dans)
            ok += 1
            print(f"[OK]     {relatif}")
        except ET.ParseError as e:
            erreurs.append((relatif, f"XML invalide : {e}"))
            print(f"[ERREUR] {relatif} -> XML invalide : {e}")
        except Exception as e:  # un fichier en echec ne bloque jamais le lot
            erreurs.append((relatif, f"{type(e).__name__} : {e}\n{traceback.format_exc()}"))
            print(f"[ERREUR] {relatif} -> {type(e).__name__} : {e}")

    if erreurs:
        journal = sortie / "_erreurs.log"
        journal.write_text("\n\n".join(f"{r}\n  {m}" for r, m in erreurs), encoding="utf-8")
        print(f"\nDetail des erreurs : {journal}")

    print(f"\nTermine : {ok} fichier(s) traite(s), {len(erreurs)} erreur(s).")
    return 0 if not erreurs else 2


if __name__ == "__main__":
    sys.exit(main())
