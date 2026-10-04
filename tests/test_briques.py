import numpy as np
import pytest
from scipy.special import eval_legendre

from ecg_legendre import battements, donnees, legendre, metriques, protocoles


# --- Projection sur Legendre -------------------------------------------------

def test_recurrence_egale_scipy():
    x = np.linspace(-1, 1, 181)
    P = legendre.base(x, 27)
    for n in range(28):
        np.testing.assert_allclose(P[n], eval_legendre(n, x), atol=1e-10)


def test_projection_redonne_les_coefficients_d_un_polynome_connu():
    x = np.linspace(-1, 1, 181)
    P = legendre.base(x, 12)
    bas = np.zeros(13)
    bas[[0, 2, 4]] = [0.3, -0.8, 0.5]
    c = legendre.projeter((bas @ P)[None, :], 12)[0]
    np.testing.assert_allclose(c, bas, atol=1e-3)
    # avec P_7 et P_12 : la méthode des trapèzes sur 181 points n'est plus tout à fait
    # orthogonale (bords de [-1, 1]), écart de l'ordre de 1e-2 : c'est la méthode, pas un bug
    haut = bas.copy()
    haut[[7, 12]] = [0.5, 0.2]
    c = legendre.projeter((haut @ P)[None, :], 12)[0]
    np.testing.assert_allclose(c, haut, atol=2e-2)


def test_reconstruction_complete_quasi_exacte_pour_un_polynome():
    x = np.linspace(-1, 1, 181)
    f = 0.4 * eval_legendre(3, x) - 0.1 * eval_legendre(5, x)
    c = legendre.projeter(f[None, :], 12)
    err = legendre.erreur_reconstruction(f[None, :], c)
    assert err[0] < 1e-2


# --- Fenêtres ----------------------------------------------------------------

def test_fenetres_en_bord_de_signal_sont_ecartees():
    sig = np.sin(np.arange(1000) / 7.0)
    pics = np.array([10, 89, 90, 500, 909, 910, 995])
    W, garde = battements.fenetres(sig, pics, demi=90)
    # 90 est la première position valable (0..180), 909 la dernière (819..999)
    np.testing.assert_array_equal(garde, [False, False, True, True, True, False, False])
    assert W.shape == (3, 181)
    np.testing.assert_array_equal(W[0], sig[0:181])


def test_decalage_d_un_echantillon():
    sig = np.arange(1000.0)
    W, _ = battements.fenetres(sig, np.array([500]), demi=90, decalage=1)
    assert W[0, 90] == 501


def test_normalisation_entre_moins_un_et_un_et_fenetre_plate_ecartee():
    W = np.array([np.linspace(2, 5, 181), np.full(181, 3.0)])
    Wn, garde = battements.normaliser(W)
    np.testing.assert_array_equal(garde, [True, False])
    assert Wn.min() == -1 and Wn.max() == 1


# --- Listes d'enregistrements et étiquettes ---------------------------------

def test_ds1_ds2_disjoints_et_complets():
    ds1, ds2, ex = set(donnees.DS1), set(donnees.DS2), set(donnees.EXCLUS)
    assert len(ds1) == 22 and len(ds2) == 22 and len(ex) == 4
    assert not (ds1 & ds2) and not (ds1 & ex) and not (ds2 & ex)
    assert len(ds1 | ds2 | ex) == 48


def test_etiquettes():
    e = donnees.etiquette_projet
    assert [e(s) for s in "NejnVLRAaJSEF"] == [0] * 4 + [1] * 9
    assert e("Q") is None and e("/") is None and e("+") is None
    v = donnees.etiquette_n_contre_v
    assert [v(s) for s in "NLRejVE"] == [0] * 5 + [1] * 2
    assert v("A") is None and v("F") is None


# --- Protocoles --------------------------------------------------------------

def test_aucun_patient_de_test_dans_un_pli_d_entrainement():
    groupes = np.repeat(np.arange(22), 50)
    for tr, te in protocoles.plis_par_patient(groupes, n_plis=5):
        assert not set(groupes[tr]) & set(groupes[te])
        assert len(tr) + len(te) == len(groupes)


def test_sous_echantillonnage_equilibre():
    y = np.array([0] * 90 + [1] * 10)
    idx = protocoles.sous_echantillonner(y, np.random.default_rng(0))
    assert (y[idx] == 0).sum() == 10 and (y[idx] == 1).sum() == 10


# --- Métriques ---------------------------------------------------------------

def test_metriques():
    y = np.array([1, 1, 1, 1, 0, 0, 0, 0, 0, 0])
    p = np.array([1, 1, 1, 0, 0, 0, 0, 0, 1, 1])
    m = metriques.binaires(y, p)
    assert m["vp"] == 3 and m["fn"] == 1 and m["vn"] == 4 and m["fp"] == 2
    assert m["sensibilite"] == pytest.approx(0.75)
    assert m["specificite"] == pytest.approx(4 / 6)
    assert m["exactitude_equilibree"] == pytest.approx((0.75 + 4 / 6) / 2)
    assert m["f1"] == pytest.approx(2 * 0.6 * 0.75 / (0.6 + 0.75))
    assert m["exactitude"] == pytest.approx(0.7)
    assert m["classe_majoritaire"] == pytest.approx(0.6)
