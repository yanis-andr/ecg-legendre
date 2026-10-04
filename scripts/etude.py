"""Rejoue toute l'étude : uv run python scripts/etude.py

Écrit results/etude.json (tous les chiffres) puis results/rapport.md (via scripts/rapport.py).
Données : data/mitdb/ (PhysioNet, téléchargé si absent). Pour Q1-Q2, les fichiers patient_*.mat du
projet sont lus dans data/projet/ s'ils y sont ; sinon, les mêmes enregistrements sont relus sur PhysioNet
avec la même table d'étiquettes (donnees.lire_comme_projet), ce qui donne les mêmes battements.
"""
import hashlib
import json
import platform
import sys
import time
import urllib.request
from importlib.metadata import version
from pathlib import Path

import numpy as np
import scipy.io as sio
import wfdb

from ecg_legendre import battements, donnees, legendre, metriques, protocoles

RACINE = Path(__file__).resolve().parents[1]
DATA, RES = RACINE / "data", RACINE / "results"
PATIENTS_PROJET = [100, 101, 105, 111]
GRAINES_Q1 = list(range(20))
GRAINE = 0          # graine unique des étapes Q3-Q5 (sous-échantillonnage)
NMAX, NMAX_MAX = 12, 27
NMAX_Q4 = [2, 4, 6, 8, 10, 12, 15, 18, 22, 27]
CLASSIFIEURS = ["knn", "svm"]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# --- Q1 / Q2 : les quatre patients du projet -------------------------------------

def fichier_projet(p):
    return DATA / "projet" / f"patient_{p}.mat"


def patient_projet(p, dossier):
    """Fichier patient_XXX.mat du projet s'il est là, sinon le même contenu relu sur PhysioNet."""
    if fichier_projet(p).exists():
        return donnees.lire_mat_projet(fichier_projet(p))
    return donnees.lire_comme_projet(p, dossier)


def battements_projet(dossier, decalage=1):
    """La chaîne exacte du projet : pics base 1 + 1 (classification_ecg.m), étiquette 3 écartée."""
    F, Y, G = [], [], []
    for p in PATIENTS_PROJET:
        d = patient_projet(p, dossier)
        ok = d["etiquettes"] != 3
        W, g = battements.fenetres(d["signal"], d["pics"][ok], decalage=decalage)
        Wn, g2 = battements.normaliser(W)
        F.append(legendre.projeter(Wn, NMAX))
        Y.append(d["etiquettes"][ok][g][g2])
        G.append(np.full(len(Wn), p))
    return np.vstack(F), np.concatenate(Y), np.concatenate(G)


def classer_comme_projet(Xtr, ytr, Xte, yte):
    """KNN K=1, KNN « meilleur K » choisi sur le test (comme le script du projet), SVM RBF C=1."""
    pred = {"knn1": protocoles.classifieur("knn", k=1).fit(Xtr, ytr).predict(Xte),
            "svm": protocoles.classifieur("svm", C=1.0).fit(Xtr, ytr).predict(Xte)}
    acc_k = {k: (protocoles.classifieur("knn", k=k).fit(Xtr, ytr).predict(Xte) == yte).mean()
             for k in [1, 3, 5, 7, 11]}
    return pred, max(acc_k.values())


def resume(v):
    v = np.asarray(v, float)
    return {"moyenne": v.mean(), "min": v.min(), "max": v.max(), "n": len(v)}


def q1_q2(dossier):
    X, y, g = battements_projet(dossier)
    out = {"n_battements": len(y), "n_normaux": int((y == 0).sum()), "n_anomalies": int((y == 1).sum()),
           "par_patient": {int(p): {"normaux": int(((g == p) & (y == 0)).sum()),
                                    "anomalies": int(((g == p) & (y == 1)).sum())} for p in PATIENTS_PROJET}}
    # Contrôle MATLAB (si matlab_check/matlab_resultats.mat existe : voir matlab/controle_matlab.m)
    fm = RACINE / "matlab_check" / "matlab_resultats.mat"
    m = sio.loadmat(fm, simplify_cells=True) if fm.exists() else None
    if m is not None:
        out["matlab"] = {
            "ecart_max_coefficients": float(np.abs(X - m["feat"]).max()),
            "etiquettes_identiques": bool((y == m["lab"]).all()),
            "graines": [int(s) for s in m["seeds"]],
            "knn1": [float(a) / 100 for a in m["acc_knn1"]],
            "knn_meilleur_k": [float(a) / 100 for a in m["acc_knnbest"]],
            "svm": [float(a) / 100 for a in m["acc_svm"]],
        }
    rangs = {"knn1": [], "knn_meilleur_k": [], "svm": [], "patient_111": [], "classe_majoritaire": []}
    autres = {"knn1": [0, 0], "svm": [0, 0]}   # [justes, total] sur les anomalies de 100/101/105 en test
    detail_graines = []
    for s in GRAINES_Q1:
        tr, te = protocoles.decoupage_aleatoire(y, s)
        pred, best = classer_comme_projet(X[tr], y[tr], X[te], y[te])
        pred["patient_111"] = (g[te] == 111).astype(int)   # « classifieur » : anomalie ssi patient 111
        for k in ["knn1", "svm", "patient_111"]:
            rangs[k].append(float((pred[k] == y[te]).mean()))
        rangs["knn_meilleur_k"].append(float(best))
        rangs["classe_majoritaire"].append(metriques.binaires(y[te], pred["svm"])["classe_majoritaire"])
        a = (y[te] == 1) & (g[te] != 111)
        for k in autres:
            autres[k][0] += int((pred[k][a] == 1).sum())
            autres[k][1] += int(a.sum())
        detail_graines.append({"graine": s, "anomalies_test_hors_111": int(a.sum()),
                               "anomalies_test": int((y[te] == 1).sum())})
    out["python"] = {"graines": GRAINES_Q1, **{k: v for k, v in rangs.items() if k != "patient_111"}}
    out["resume"] = {k: resume(v) for k, v in rangs.items()}
    if m is not None:
        out["resume_matlab"] = {k: resume(out["matlab"][k]) for k in ["knn1", "knn_meilleur_k", "svm"]}
        # mêmes découpages que MATLAB, classifieurs Python : isole l'écart dû aux classifieurs
        memes = {"knn1": [], "svm": []}
        for sp in m["splits"]:
            tr, te = np.atleast_1d(sp["train"]) - 1, np.atleast_1d(sp["test"]) - 1
            pred, _ = classer_comme_projet(X[tr], y[tr], X[te], y[te])
            for k in memes:
                memes[k].append(float((pred[k] == y[te]).mean()))
        out["python_sur_decoupages_matlab"] = {k: {"valeurs": v, **resume(v)} for k, v in memes.items()}
    # Q2
    part_111 = out["par_patient"][111]["anomalies"] / out["n_anomalies"]
    ens_equilibre = 1 - (1 - part_111) / 2   # exactitude attendue du « classifieur patient 111 »
    out["q2"] = {
        "part_anomalies_111": part_111,
        "exactitude_attendue_classifieur_111": ens_equilibre,
        "exactitude_classifieur_111": resume(rangs["patient_111"]),
        "anomalies_hors_111_en_test": {k: {"justes": a, "total": t, "exactitude": a / t}
                                       for k, (a, t) in autres.items()},
        "detail_graines": detail_graines,
        "un_patient_retire": un_patient_retire(X, y, g),
    }
    return out


def un_patient_retire(X, y, g):
    """Entraînement sur trois patients (équilibré comme le projet), test sur le quatrième."""
    res = {}
    for p in PATIENTS_PROJET:
        tr, te = g != p, g == p
        idx = protocoles.sous_echantillonner(y[tr], np.random.default_rng(GRAINE))
        Xtr, ytr = X[tr][idx], y[tr][idx]
        res[p] = {k: metriques.binaires(y[te], protocoles.classifieur(k).fit(Xtr, ytr).predict(X[te]))
                  for k in CLASSIFIEURS}
    return res


# --- Q3-Q5 : MIT-BIH complète ---------------------------------------------------

def telecharger():
    dossier = DATA / "mitdb"
    manquants = [r for r in donnees.DS1 + donnees.DS2 + donnees.EXCLUS
                 if not (dossier / f"{r}.dat").exists() or not (dossier / f"{r}.atr").exists()]
    if manquants:
        log("téléchargement PhysioNet :", manquants)
        wfdb.dl_database("mitdb", str(dossier), records=[str(r) for r in manquants])
    return dossier


def verifier_sommes(dossier):
    """Compare les fichiers aux SHA-256 publiés par PhysioNet (SHA256SUMS.txt)."""
    url = "https://physionet.org/files/mitdb/1.0.0/SHA256SUMS.txt"
    try:
        lignes = urllib.request.urlopen(url, timeout=30).read().decode().split("\n")
    except OSError as e:
        return {"verifie": False, "erreur": str(e)}
    attendus = dict(reversed(l.split()) for l in lignes if l.strip())
    fichiers = [f"{r}.{e}" for r in donnees.DS1 + donnees.DS2 for e in ("dat", "atr", "hea")]
    faux = [f for f in fichiers if hashlib.sha256((dossier / f).read_bytes()).hexdigest() != attendus.get(f)]
    return {"verifie": True, "n_fichiers": len(fichiers), "differents": faux}


def controle_lecture(dossier):
    """Fichiers du projet contre PhysioNet (wfdb) : signal, pics, symboles et étiquettes, un par un.
    Vide si les fichiers du projet ne sont pas dans data/projet/."""
    res = {}
    for p in PATIENTS_PROJET:
        if not fichier_projet(p).exists():
            continue
        projet = donnees.lire_mat_projet(fichier_projet(p))
        pn = donnees.lire_physionet(p, dossier)
        relu = donnees.lire_comme_projet(p, dossier)
        battement = np.isin(pn["symboles"], sorted(donnees.PROJET_BATTEMENTS))
        res[p] = {
            "canal_mlii": pn["canal"],
            "ecart_max_signal_mV": float(np.abs(projet["signal"] - pn["signal"]).max()),
            "n_pics_projet": len(projet["pics"]), "n_pics_physionet": int(battement.sum()),
            "pics_identiques": bool(np.array_equal(projet["pics"], pn["pics"][battement])),
            "symboles_identiques": bool(np.array_equal(projet["symboles"], pn["symboles"][battement])),
            "etiquettes_identiques": bool(np.array_equal(projet["etiquettes"], relu["etiquettes"])),
        }
    return res


def base_mitbih(dossier):
    """Battements de DS1 et DS2 (pics PhysioNet base 0, sans décalage), coefficients jusqu'à 27."""
    lignes = {"coefs": [], "brut": [], "symb": [], "rec": []}
    canaux, symboles = {}, {}
    for r in donnees.DS1 + donnees.DS2:
        d = donnees.lire_physionet(r, dossier)
        canaux[r] = d["noms_canaux"]
        u, c = np.unique(d["symboles"], return_counts=True)
        symboles[r] = dict(zip(u.tolist(), c.tolist()))
        garde = np.array([donnees.etiquette_projet(s) is not None or donnees.etiquette_n_contre_v(s) is not None
                          for s in d["symboles"]])
        W, g = battements.fenetres(d["signal"], d["pics"][garde])
        Wn, g2 = battements.normaliser(W)
        lignes["coefs"].append(legendre.projeter(Wn, NMAX_MAX))
        lignes["brut"].append(Wn)
        lignes["symb"].append(d["symboles"][garde][g][g2])
        lignes["rec"].append(np.full(len(Wn), r))
    b = {k: np.concatenate(v) for k, v in lignes.items()}
    return b, canaux, symboles


def jeu(b, definition, ds, carac):
    lab = np.array([donnees.ETIQUETTES[definition](s) for s in b["symb"]], dtype=object)
    m = np.isin(b["rec"], ds) & (lab != None)  # noqa: E711
    return carac[m], lab[m].astype(int), b["rec"][m]


def evaluer_ds2(b, definition, carac, nom):
    X1, y1, g1 = jeu(b, definition, donnees.DS1, carac)
    X2, y2, g2 = jeu(b, definition, donnees.DS2, carac)
    plis = protocoles.plis_par_patient(g1)
    meilleur, essais = protocoles.selectionner(X1, y1, g1, nom, plis, GRAINE)
    modele = protocoles.ajuster(X1, y1, nom, meilleur["params"], GRAINE)
    pred = modele.predict(X2)
    par_patient = {}
    for r in donnees.DS2:
        m = g2 == r
        mt = metriques.binaires(y2[m], pred[m])
        par_patient[r] = {"n_normaux": int((y2[m] == 0).sum()), "n_anomalies": int((y2[m] == 1).sum()),
                          "sensibilite": mt["sensibilite"], "specificite": mt["specificite"]}
    sens = [v["sensibilite"] for v in par_patient.values() if v["n_anomalies"] > 0]
    return {"n_ds1": len(y1), "anomalies_ds1": int(y1.sum()), "n_ds2": len(y2), "anomalies_ds2": int(y2.sum()),
            "choix_cv": meilleur, "grille_cv": essais, "ds2": metriques.binaires(y2, pred),
            "ds2_par_patient": par_patient,
            "sensibilite_par_patient": {"min": min(sens), "max": max(sens), "mediane": float(np.median(sens)),
                                        "n_patients_avec_anomalies": len(sens)}}


def q4(b, definition):
    """Exactitude équilibrée hors-pli sur DS1 selon Nmax (hyperparamètres re-choisis à chaque Nmax)."""
    courbe = {}
    for n in NMAX_Q4:
        X1, y1, g1 = jeu(b, definition, donnees.DS1, b["coefs"][:, :n + 1])
        plis = protocoles.plis_par_patient(g1)
        courbe[n] = {}
        for nom in CLASSIFIEURS:
            meilleur, _ = protocoles.selectionner(X1, y1, g1, nom, plis, GRAINE)
            courbe[n][nom] = {k: meilleur[k] for k in ["params", "exactitude_equilibree", "sensibilite",
                                                       "specificite", "exactitude_equilibree_par_pli"]}
        log("Q4", definition, n, {k: round(v["exactitude_equilibree"], 4) for k, v in courbe[n].items()})
    return courbe


def erreurs_reconstruction(b):
    m = np.isin(b["rec"], donnees.DS1)
    idx = np.random.default_rng(GRAINE).choice(np.flatnonzero(m), 5000, replace=False)
    W, C = b["brut"][idx], b["coefs"][idx]
    ref27 = legendre.reconstruire(C, W.shape[1])
    out = {}
    for n in NMAX_Q4:
        rec = legendre.reconstruire(C[:, :n + 1], W.shape[1])
        out[n] = {"vs_battement": float(np.mean(np.linalg.norm(W - rec, axis=1) / np.linalg.norm(W, axis=1))),
                  "vs_reconstruction_27_comme_projet": float(np.mean(np.linalg.norm(ref27 - rec, axis=1)
                                                                  / np.linalg.norm(ref27, axis=1)))}
    return out


def main():
    RES.mkdir(exist_ok=True)
    t0 = time.time()
    etude = {"versions": {"python": sys.version.split()[0], "plateforme": platform.platform(),
                          **{p: version(p) for p in ["numpy", "scipy", "scikit-learn", "wfdb"]}},
             "graines": {"q1_q2": GRAINES_Q1, "q3_q5": GRAINE}}
    dossier = telecharger()
    etude["sommes_sha256"] = verifier_sommes(dossier)
    log("Q1/Q2")
    etude["source_q1_q2"] = ("fichiers du projet (data/projet)" if all(fichier_projet(p).exists() for p in PATIENTS_PROJET)
                             else "PhysioNet, relu avec la table du projet")
    etude["q1_q2"] = q1_q2(dossier)
    etude["controle_lecture"] = controle_lecture(dossier)
    log("lecture MIT-BIH")
    b, canaux, symboles = base_mitbih(dossier)
    etude["canaux"] = {r: c for r, c in canaux.items()}
    etude["symboles_par_enregistrement"] = symboles
    etude["q3"], etude["q5"] = {}, {}
    for definition in donnees.ETIQUETTES:
        etude["q3"][definition], etude["q5"][definition] = {}, {}
        for nom in CLASSIFIEURS:
            log("Q3", definition, nom)
            etude["q3"][definition][nom] = evaluer_ds2(b, definition, b["coefs"][:, :NMAX + 1], nom)
            log("Q5", definition, nom)
            etude["q5"][definition][nom] = evaluer_ds2(b, definition, b["brut"], nom)
    etude["q4"] = {"reconstruction": erreurs_reconstruction(b),
                   **{d: q4(b, d) for d in donnees.ETIQUETTES}}
    etude["duree_s"] = time.time() - t0
    texte = json.dumps(_sans_nan(json.loads(json.dumps(etude, default=_json))), indent=1, ensure_ascii=False)
    (RES / "etude.json").write_text(texte)
    log("écrit", RES / "etude.json")
    import rapport
    rapport.ecrire(RES / "etude.json", RES / "rapport.md")


def _sans_nan(o):
    """NaN (ex. spécificité d'un patient sans battement normal) -> null en JSON."""
    if isinstance(o, float) and o != o:
        return None
    if isinstance(o, dict):
        return {k: _sans_nan(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_sans_nan(v) for v in o]
    return o


def _json(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


if __name__ == "__main__":
    main()
