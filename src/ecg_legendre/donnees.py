"""Enregistrements MIT-BIH, définitions d'étiquettes, lecture des données.

Découpage inter-patients de de Chazal, O'Dwyer & Reilly, IEEE TBME 51(7):1196-1206, 2004,
listes vérifiées contre He et al., PLoS One 2018 (PMC6235298), qui les reproduit.
"""
from pathlib import Path

import numpy as np
import scipy.io as sio
import wfdb

DS1 = [101, 106, 108, 109, 112, 114, 115, 116, 118, 119, 122,
       124, 201, 203, 205, 207, 208, 209, 215, 220, 223, 230]
DS2 = [100, 103, 105, 111, 113, 117, 121, 123, 200, 202, 210,
       212, 213, 214, 219, 221, 222, 228, 231, 232, 233, 234]
EXCLUS = [102, 104, 107, 217]  # stimulateur cardiaque

# (a) table du projet, fonction sym2label de Read_mitbih.m
PROJET_NORMAL, PROJET_ANOMALIE = set("Nejn"), set("VLRAaJSEF")
# annotations gardées comme battements dans les fichiers patient_XXX.mat du projet
PROJET_BATTEMENTS = set("NLRaVFJASEj/Qef") | {"x"}
# (b) classes AAMI N et V
AAMI_N, AAMI_V = set("NLRej"), set("VE")


def etiquette_projet(sym):
    return 0 if sym in PROJET_NORMAL else 1 if sym in PROJET_ANOMALIE else None


def etiquette_n_contre_v(sym):
    return 0 if sym in AAMI_N else 1 if sym in AAMI_V else None


ETIQUETTES = {"projet": etiquette_projet, "n_contre_v": etiquette_n_contre_v}


def lire_mat_projet(chemin):
    """patient_XXX.mat de Read_mitbih.m. Pics renvoyés en base 0 (ils sont stockés en base 1)."""
    d = sio.loadmat(chemin)
    return {
        "signal": d["signal"].ravel().astype(float),
        "pics": d["r_peaks"].ravel().astype(int) - 1,
        "symboles": np.array(list(d["labels_str"])),
        "etiquettes": d["labels_num"].ravel().astype(int),  # 0, 1, 3 = exclu
    }


def lire_physionet(numero, dossier):
    """Canal MLII en mV, pics R (base 0) et symboles des annotations de battement."""
    chemin = str(Path(dossier) / str(numero))
    rec = wfdb.rdrecord(chemin)
    canal = rec.sig_name.index("MLII")
    ann = wfdb.rdann(chemin, "atr")
    return {
        "signal": rec.p_signal[:, canal],
        "canal": canal,
        "noms_canaux": rec.sig_name,
        "pics": np.asarray(ann.sample),
        "symboles": np.asarray(ann.symbol),
    }


def lire_comme_projet(numero, dossier):
    """Les champs de lire_mat_projet, relus sur PhysioNet : battements annotés de PROJET_BATTEMENTS,
    étiquettes de la table du projet (3 = écarté). Sur 100, 101, 105 et 111, identique aux fichiers
    patient_XXX.mat du projet (signal, pics, symboles et étiquettes)."""
    d = lire_physionet(numero, dossier)
    garde = np.isin(d["symboles"], sorted(PROJET_BATTEMENTS))
    symboles = d["symboles"][garde]
    etiquettes = [etiquette_projet(s) for s in symboles]
    return {
        "signal": d["signal"],
        "pics": d["pics"][garde],
        "symboles": symboles,
        "etiquettes": np.array([3 if e is None else e for e in etiquettes], dtype=int),
    }
