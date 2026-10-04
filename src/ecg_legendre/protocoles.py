"""Classifieurs, découpage aléatoire (celui du projet) et validation croisée par patient."""
import itertools

import numpy as np
from joblib import Parallel, delayed
from sklearn.model_selection import GroupKFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from . import metriques

def classifieur(nom, **p):
    """'Standardize', true de MATLAB = centrage-réduction appris sur l'entraînement."""
    if nom == "knn":
        modele = KNeighborsClassifier(n_neighbors=p.get("k", 1))
    else:
        # gamma relatif : noyau exp(-g/d ||x - x'||^2), d = nombre de caractéristiques
        gamma = p["g"] / p["d"] if "g" in p else "scale"
        modele = SVC(kernel="rbf", C=p.get("C", 1.0), gamma=gamma, class_weight=p.get("class_weight"))
    return make_pipeline(StandardScaler(), modele)


def sous_echantillonner(y, rng):
    """Indices équilibrés : chaque classe tirée sans remise à la taille de la plus petite."""
    n = min((y == 0).sum(), (y == 1).sum())
    return np.concatenate([rng.choice(np.flatnonzero(y == c), n, replace=False) for c in (0, 1)])


def plis_par_patient(groupes, n_plis=5):
    return list(GroupKFold(n_splits=n_plis).split(np.zeros(len(groupes)), groups=groupes))


# --- Q1/Q2 : protocole du projet --------------------------------------------

def decoupage_aleatoire(y, graine):
    """Équilibrage par sous-échantillonnage puis 80/20 aléatoire, comme classification_ecg.m."""
    rng = np.random.default_rng(graine)
    sel = sous_echantillonner(y, rng)
    perm = rng.permutation(len(sel))
    n_tr = round(0.8 * len(sel))
    return sel[perm[:n_tr]], sel[perm[n_tr:]]


# --- Q3-Q5 : validation croisée par patient ------------------------------------

def ajuster(X, y, nom, params, graine):
    """Ajuste un classifieur sur (X, y) avec l'équilibrage demandé dans params."""
    p = dict(params)
    equilibrage = p.pop("equilibrage")
    if equilibrage == "poids":
        p["class_weight"] = "balanced"
    p["d"] = X.shape[1]
    idx = np.arange(len(y))
    if equilibrage == "sous_echantillonnage":
        idx = sous_echantillonner(y, np.random.default_rng(graine))
    return classifieur(nom, **p).fit(X[idx], y[idx])


def predictions_hors_pli(X, y, groupes, nom, params, plis, graine):
    pred = np.empty_like(y)
    for i, (tr, te) in enumerate(plis):
        assert not set(groupes[tr]) & set(groupes[te])
        pred[te] = ajuster(X[tr], y[tr], nom, params, graine + i).predict(X[te])
    return pred


def grille(nom):
    if nom == "knn":
        return [{"k": k, "equilibrage": e}
                for k, e in itertools.product([1, 3, 5, 9, 15, 25], ["aucun", "sous_echantillonnage"])]
    return [{"C": C, "g": g, "equilibrage": e}
            for C, g, e in itertools.product([0.3, 3, 30], [0.3, 1, 3],
                                             ["poids", "sous_echantillonnage"])]


def selectionner(X, y, groupes, nom, plis, graine):
    """Choisit les hyperparamètres par exactitude équilibrée hors-pli (patients disjoints)."""
    def essai(params):
        pred = predictions_hors_pli(X, y, groupes, nom, params, plis, graine)
        plis_ee = [metriques.binaires(y[te], pred[te])["exactitude_equilibree"] for _, te in plis]
        return {"params": params, **metriques.binaires(y, pred), "exactitude_equilibree_par_pli": plis_ee}

    essais = Parallel(n_jobs=-1)(delayed(essai)(p) for p in grille(nom))
    meilleur = max(essais, key=lambda e: e["exactitude_equilibree"])
    return meilleur, essais
