"""Découpage des battements autour du pic R et normalisation dans [-1, 1]."""
import numpy as np


def fenetres(signal, pics, demi=90, decalage=0):
    """Fenêtres signal[c-demi : c+demi+1] avec c = pic + decalage (indices base 0).

    Les fenêtres qui dépassent le signal sont écartées ; `garde` dit lesquelles restent.
    """
    centres = np.asarray(pics) + decalage
    garde = (centres - demi >= 0) & (centres + demi <= len(signal) - 1)
    idx = centres[garde, None] + np.arange(-demi, demi + 1)[None, :]
    return signal[idx], garde


def normaliser(W):
    """Ramène chaque fenêtre dans [-1, 1] ; écarte les fenêtres plates (comme classification_ecg.m)."""
    mini, maxi = W.min(axis=1, keepdims=True), W.max(axis=1, keepdims=True)
    garde = (maxi - mini)[:, 0] >= 1e-10
    mini, maxi = mini[garde], maxi[garde]
    return 2 * (W[garde] - mini) / (maxi - mini) - 1, garde
