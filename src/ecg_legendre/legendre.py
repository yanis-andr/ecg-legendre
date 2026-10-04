"""Base de Legendre et projection par la méthode des trapèzes (comme Legendre.m)."""
import numpy as np


def base(x, nmax):
    """Polynômes P_0..P_nmax évalués en x, par la récurrence de Bonnet. Forme (nmax+1, len(x))."""
    P = np.empty((nmax + 1, len(x)))
    P[0] = 1.0
    if nmax >= 1:
        P[1] = x
    for n in range(1, nmax):
        P[n + 1] = ((2 * n + 1) * x * P[n] - n * P[n - 1]) / (n + 1)
    return P


def projeter(fenetres, nmax):
    """Coefficients c_n = trapz(f P_n) / trapz(P_n^2) de chaque ligne de `fenetres`."""
    x = np.linspace(-1, 1, fenetres.shape[1])
    P = base(x, nmax)
    num = np.trapezoid(fenetres[:, None, :] * P[None, :, :], x, axis=2)
    return num / np.trapezoid(P * P, x, axis=1)


def reconstruire(coefs, longueur):
    x = np.linspace(-1, 1, longueur)
    return coefs @ base(x, coefs.shape[1] - 1)


def erreur_reconstruction(fenetres, coefs):
    """Erreur relative ||f - f_N|| / ||f||, une valeur par battement."""
    f_hat = reconstruire(coefs, fenetres.shape[1])
    return np.linalg.norm(fenetres - f_hat, axis=1) / np.linalg.norm(fenetres, axis=1)
