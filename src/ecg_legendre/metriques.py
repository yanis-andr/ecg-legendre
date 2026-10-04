"""Métriques binaires, classe « anomalie » (1) positive."""
import numpy as np


def _div(a, b):
    return float(a / b) if b else float("nan")


def binaires(y, p):
    y, p = np.asarray(y), np.asarray(p)
    vp = int(((y == 1) & (p == 1)).sum())
    vn = int(((y == 0) & (p == 0)).sum())
    fp = int(((y == 0) & (p == 1)).sum())
    fn = int(((y == 1) & (p == 0)).sum())
    sens, spec = _div(vp, vp + fn), _div(vn, vn + fp)
    prec = _div(vp, vp + fp)
    return {
        "vp": vp, "fn": fn, "fp": fp, "vn": vn,
        "sensibilite": sens,
        "specificite": spec,
        "precision": prec,
        "exactitude_equilibree": (sens + spec) / 2,
        "f1": _div(2 * vp, 2 * vp + fp + fn),
        "exactitude": _div(vp + vn, len(y)),
        "classe_majoritaire": _div(max((y == 1).sum(), (y == 0).sum()), len(y)),
    }
