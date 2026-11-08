"""Recherche d'offres de stage en énergie via l'API Offres d'emploi (France Travail).

Utilisation :
    1. Copiez .env.example en .env et mettez-y votre client_id et client_secret.
    2. pip install requests python-dotenv
    3. python recherche_offres.py

Résultat : un fichier offres.csv avec les offres trouvées (sans doublons).
"""
import csv
import json
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("FT_CLIENT_ID")
CLIENT_SECRET = os.getenv("FT_CLIENT_SECRET")

TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=/partenaire"
SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
SCOPE = "api_offresdemploiv2 o2dsoffre"


def get_token():
    if not CLIENT_ID or not CLIENT_SECRET:
        raise SystemExit("FT_CLIENT_ID ou FT_CLIENT_SECRET manquant dans le fichier .env")
    r = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scope": SCOPE,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    if r.status_code != 200:
        raise SystemExit(f"Échec de l'authentification ({r.status_code}) : {r.text[:300]}")
    return r.json()["access_token"]


def search(token, mots_cles):
    """Retourne les offres pour un mot-clé (jusqu'à 150 résultats)."""
    r = requests.get(
        SEARCH_URL,
        params={"motsCles": mots_cles, "range": "0-149", "sort": 1},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if r.status_code == 204:  # aucun résultat
        return []
    if r.status_code not in (200, 206):
        print(f"  Erreur {r.status_code} pour '{mots_cles}' : {r.text[:200]}")
        return []
    return r.json().get("resultats", [])


def main():
    with open("profil.json", encoding="utf-8") as f:
        profil = json.load(f)
    mots = profil["stage"]["mots_cles_recherche"]

    token = get_token()
    offres = {}
    for m in mots:
        print(f"Recherche : {m}")
        for o in search(token, m):
            offres[o["id"]] = o
        time.sleep(1)  # reste poli avec l'API

    lignes = []
    for o in offres.values():
        lignes.append(
            {
                "id": o.get("id"),
                "intitule": o.get("intitule"),
                "entreprise": (o.get("entreprise") or {}).get("nom", ""),
                "lieu": (o.get("lieuTravail") or {}).get("libelle", ""),
                "type_contrat": o.get("typeContratLibelle", ""),
                "date": o.get("dateCreation", "")[:10],
                "lien": (o.get("origineOffre") or {}).get("urlOrigine", ""),
                "description": (o.get("description") or "").replace("\n", " ")[:1500],
            }
        )

    with open("offres.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0].keys()) if lignes else ["id"])
        w.writeheader()
        w.writerows(lignes)
    print(f"\n{len(lignes)} offres uniques enregistrées dans offres.csv")


if __name__ == "__main__":
    main()
