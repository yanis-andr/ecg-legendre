"""Écrit results/rapport.md à partir de results/etude.json : uv run python scripts/rapport.py"""
import json
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
DEFS = {"projet": "(a) définition du projet : normal contre anomalie",
        "n_contre_v": "(b) normal (AAMI N) contre extrasystole ventriculaire (AAMI V)"}
COURT = {"projet": "(a)", "n_contre_v": "(b)"}
CLF = {"knn": "KNN", "svm": "SVM RBF"}
MIN_POSITIFS = 20  # pour une sensibilité par patient qui veuille dire quelque chose
SEUIL = 0.01   # écart d'exactitude équilibrée jugé négligeable (1 point), fixé avant les calculs


def pc(x, d=1):
    return "n.d." if x is None else f"{100 * x:.{d}f}".replace(".", ",") + " %"


def pts(x, d=1):
    return f"{100 * x:+.{d}f}".replace(".", ",").replace("-", "−") + " pt"


def plage(r, d=1):
    return f"{pc(r['moyenne'], d)} [{pc(r['min'], d)} ; {pc(r['max'], d)}]"


def params(p):
    p = dict(p)
    eq = {"aucun": "aucun", "sous_echantillonnage": "sous-échantillonnage", "poids": "poids de classe"}[
        p.pop("equilibrage")]
    if "k" in p:
        return f"K = {p['k']}, équilibrage : {eq}"
    return f"C = {p['C']}, gamma = {p['g']}/d, équilibrage : {eq}"


def tableau(entetes, lignes):
    t = ["| " + " | ".join(entetes) + " |", "|" + "---|" * len(entetes)]
    return "\n".join(t + ["| " + " | ".join(str(c) for c in l) + " |" for l in lignes])


def q1(e):
    q = e["q1_q2"]
    r, m = q["resume"], q.get("resume_matlab")
    lignes = [["Script du projet (graine 42, figure `fig1_confusion.png`)", "98,6 %", "98,6 % (K = 1)", "98,5 %"]]
    if m:
        mm = q["matlab"]
        lignes.append(["MATLAB R2024b, code du projet relancé, graine 42", pc(mm["knn1"][0], 2),
                       pc(mm["knn_meilleur_k"][0], 2), pc(mm["svm"][0], 2)])
        lignes.append([f"MATLAB, {m['knn1']['n']} graines (42, 1..20)", plage(m["knn1"]),
                       plage(m["knn_meilleur_k"]), plage(m["svm"])])
        ps = q["python_sur_decoupages_matlab"]
        lignes.append(["Python, sur les mêmes découpages que MATLAB", plage(ps["knn1"]), "", plage(ps["svm"])])
    lignes.append([f"Python, {r['knn1']['n']} graines (0..19)", plage(r["knn1"]), plage(r["knn_meilleur_k"]),
                   plage(r["svm"])])
    t = tableau(["Source", "KNN K = 1", "KNN « meilleur K » (choisi sur le test)", "SVM RBF"], lignes)
    ecart = abs(r["knn1"]["moyenne"] - 0.986), abs(r["svm"]["moyenne"] - 0.985)
    s = (f"**Réponse.** Oui : la chaîne Python redonne les chiffres du projet à moins d'un point "
         f"(KNN K = 1 : {plage(r['knn1'])} sur {r['knn1']['n']} graines contre 98,6 %, SVM : "
         f"{plage(r['svm'])} contre 98,5 %), et le 98,6 % du projet est l'un des tirages les plus bas de l'étendue.\n\n")
    if not (ecart[0] <= 0.01 and ecart[1] <= 0.01):
        s = "**Réponse.** Écart de plus d'un point avec les chiffres du projet : voir le tableau.\n\n"
    s += (f"Exactitude sur l'échantillon de test (881 battements, classes équilibrées), moyenne [min ; max]. "
          f"Classifieur trivial (toujours la classe majoritaire du test) : {plage(r['classe_majoritaire'])}, "
          f"règle « anomalie si patient 111 » : {plage(r['patient_111'])} (Q2).\n\n{t}\n\n")
    if m:
        mm = q["matlab"]
        s += (f"Contrôle MATLAB : `classification_ecg.m` relancé tel quel sur une copie redonne exactement "
              f"98,6 % et 98,5 %. Les coefficients c_0..c_12 des {q['n_battements']} battements calculés en Python "
              f"et en MATLAB diffèrent au plus de {mm['ecart_max_coefficients']:.1e} (arrondi numérique), les "
              f"étiquettes sont identiques. Sur les mêmes découpages que MATLAB, le KNN Python donne exactement "
              f"les mêmes exactitudes. Le SVM diffère de quelques battements parce que `KernelScale 'auto'` de "
              f"MATLAB (heuristique sur un sous-échantillon aléatoire) n'a pas d'équivalent exact : Python utilise "
              f"`gamma='scale'` (1 / nombre de caractéristiques après centrage-réduction). "
              f"L'écart restant entre lignes vient donc des tirages aléatoires, pas de la chaîne.\n\n")
    s += ("Deux détails du script du projet, reproduits ici pour la Q1 et corrigés ensuite : (1) `classification_ecg.m` "
          "ajoute 1 aux pics R « base 0 Python → base 1 MATLAB » alors que `Read_mitbih.m` les a déjà stockés en "
          "base 1 : chaque fenêtre est centrée un échantillon (2,8 ms) après le pic R (`choix_nmax.m`, lui, ne "
          "décale pas), (2) le K du KNN est choisi parmi 1, 3, 5, 7, 11 sur l'exactitude du **test**, ce qui est "
          "un réglage sur le test (effet faible ici, voir la colonne « meilleur K »).\n")
    return s


def q2(e):
    q = e["q1_q2"]
    z = q["q2"]
    pp = q["par_patient"]
    lignes = [[p, v["normaux"], v["anomalies"], pc(v["anomalies"] / q["n_anomalies"])] for p, v in pp.items()]
    t1 = tableau(["Patient", "Normaux", "Anomalies", "Part des anomalies"], lignes)
    a = z["anomalies_hors_111_en_test"]
    s = (f"**Réponse.** {pc(z['part_anomalies_111'])} des anomalies viennent du patient 111. Une règle qui "
         f"répond « anomalie » si et seulement si le battement vient du patient 111 obtient "
         f"{plage(z['exactitude_classifieur_111'])} sur les mêmes découpages (attendu : "
         f"{pc(z['exactitude_attendue_classifieur_111'])}), presque autant que les 98,6 % du projet. Sur les anomalies des "
         f"patients 100, 101 et 105 seules, le KNN n'a raison que dans {pc(a['knn1']['exactitude'])} des cas et le "
         f"SVM dans {pc(a['svm']['exactitude'])}.\n\n{t1}\n\n")
    s += (f"Battements retenus après fenêtrage ({q['n_battements']} au total). "
          f"Anomalies de 100/101/105 tombées dans le test, cumulées sur les {len(z['detail_graines'])} graines : "
          f"{a['knn1']['total']}, dont justes : KNN {a['knn1']['justes']}, SVM {a['svm']['justes']}.\n\n")
    lignes = []
    for p, r in z["un_patient_retire"].items():
        for k, m in r.items():
            lignes.append([p, CLF[k], f"{m['vp']}/{m['vp'] + m['fn']}", pc(m["sensibilite"]),
                           pc(m["specificite"]), pc(m["exactitude"]), pc(m["classe_majoritaire"])])
    s += ("Complément : chaque patient retiré à son tour (entraînement équilibré sur les trois autres, mêmes "
          "classifieurs, test sur le patient retiré). Le patient 111 n'a aucun battement normal : sa spécificité "
          "n'existe pas.\n\n")
    s += tableau(["Patient testé", "Classifieur", "Anomalies trouvées", "Sensibilité", "Spécificité",
                  "Exactitude", "Classe majoritaire"], lignes) + "\n\n"
    r111 = z["un_patient_retire"]["111"]
    s += (f"Même retiré de l'entraînement, le patient 111 est classé « anomalie » à "
          f"{pc(r111['knn']['sensibilite'])} (KNN) et {pc(r111['svm']['sensibilite'])} (SVM) : ses blocs de "
          "branche gauche ne ressemblent à aucun normal des trois autres. Ce sont les anomalies discrètes "
          "(extrasystoles auriculaires A de 100 et 101) qui ne sont presque jamais trouvées : le score de 98 % "
          "ne dit presque rien des anomalies de 100, 101 et 105, qui ne font que 3,5 % de la classe « anomalie ».\n")
    return s


def ligne_ds2(nom, r):
    d = r["ds2"]
    return [CLF[nom], params(r["choix_cv"]["params"]), pc(r["choix_cv"]["exactitude_equilibree"]),
            f"{d['vp']} / {d['fn']} / {d['fp']} / {d['vn']}", pc(d["sensibilite"]), pc(d["specificite"]),
            pc(d["exactitude_equilibree"]), pc(d["f1"]), pc(d["exactitude"]), pc(d["classe_majoritaire"]),
            f"{pc(r['sensibilite_par_patient']['min'], 0)} à {pc(r['sensibilite_par_patient']['max'], 0)}",
            sens_parlante(r)]


def sens_parlante(r):
    v = [x["sensibilite"] for x in r["ds2_par_patient"].values() if x["n_anomalies"] >= MIN_POSITIFS]
    return f"{pc(min(v), 0)} à {pc(max(v), 0)} ({len(v)} patients)"


ENTETES_DS2 = ["Classifieur", "Réglage choisi (CV par patient sur DS1)", "Exact. équil. CV DS1",
               "VP / FN / FP / VN (DS2)", "Sensibilité", "Spécificité", "Exact. équilibrée", "F1",
               "Exactitude brute", "Classe majoritaire", "Sensibilité par patient (min à max)",
               f"Idem, patients à {MIN_POSITIFS} positifs ou plus"]


def q3(e):
    s = ""
    for d, nomd in DEFS.items():
        r = e["q3"][d]
        k = r["knn"]
        s += (f"### {nomd}\n\nDS1 : {k['n_ds1']} battements dont {k['anomalies_ds1']} positifs, "
              f"DS2 : {k['n_ds2']} battements dont {k['anomalies_ds2']} positifs.\n\n")
        s += tableau(ENTETES_DS2, [ligne_ds2(n, r[n]) for n in CLF]) + "\n\n"
        lignes = []
        for p in r["knn"]["ds2_par_patient"]:
            a, b = r["knn"]["ds2_par_patient"][p], r["svm"]["ds2_par_patient"][p]
            lignes.append([p, a["n_normaux"], a["n_anomalies"], pc(a["sensibilite"]), pc(a["specificite"]),
                           pc(b["sensibilite"]), pc(b["specificite"])])
        s += ("Par patient de DS2 (sensibilité « n.d. » : aucun battement positif chez ce patient. À lire avec le "
              "nombre de positifs, une sensibilité sur 1 battement ne vaut rien) :\n\n")
        s += tableau(["Patient", "Normaux", "Positifs", "Sens. KNN", "Spéc. KNN", "Sens. SVM", "Spéc. SVM"],
                     lignes) + "\n\n"
    return s


def q4(e):
    q = e["q4"]
    rec = q["reconstruction"]
    s = ""
    verdicts = {}
    for d, nomd in DEFS.items():
        c = q[d]
        lignes = []
        for n, v in c.items():
            lignes.append([n] + [f"{pc(v[k]['exactitude_equilibree'])} (plis : "
                                 f"{pc(min(x for x in v[k]['exactitude_equilibree_par_pli'] if x is not None), 0)}"
                                 f" à {pc(max(x for x in v[k]['exactitude_equilibree_par_pli'] if x is not None), 0)})"
                                 for k in CLF] + [pc(rec[n]["vs_battement"]), pc(rec[n]["vs_reconstruction_27_comme_projet"])])
        s += f"#### {nomd}\n\n" + tableau(
            ["Nmax", "KNN : exact. équil. CV DS1", "SVM : exact. équil. CV DS1", "Erreur de reconstruction",
             "Erreur rel. à Nmax = 27 (mesure du projet)"], lignes) + "\n\n"
        for k in CLF:
            meilleur = max(c.items(), key=lambda kv: kv[1][k]["exactitude_equilibree"])
            verdicts[(d, k)] = (meilleur[0], meilleur[1][k]["exactitude_equilibree"],
                                c["12"][k]["exactitude_equilibree"])
    lignes, ecarts = [], {}
    for (d, k), (n, b, v12) in verdicts.items():
        plis_b = q[d][n][k]["exactitude_equilibree_par_pli"]
        plis_12 = q[d]["12"][k]["exactitude_equilibree_par_pli"]
        gagne = sum(1 for x, y in zip(plis_b, plis_12) if x is not None and y is not None and x > y)
        ecarts[(d, k)] = b - v12
        lignes.append([COURT[d], CLF[k], n, pc(b), pc(v12), pts(v12 - b), f"{gagne}/5",
                       "oui" if b - v12 <= SEUIL else "non"])
    sens = {d: "plus" if int(verdicts[(d, "svm")][0]) > 12 else "moins" for d in DEFS}
    s = (f"**Réponse.** Non, N = 12 n'est l'optimum pour aucune des deux questions : pour la définition (a) "
         f"l'exactitude équilibrée monte avec {sens['projet']} de coefficients (meilleur Nmax "
         f"{verdicts[('projet', 'knn')][0]} pour le KNN, {verdicts[('projet', 'svm')][0]} pour le SVM, "
         f"{pts(ecarts[('projet', 'knn')])} et {pts(ecarts[('projet', 'svm')])} par rapport à 12), pour la "
         f"définition (b) elle est meilleure avec {sens['n_contre_v']} de coefficients (Nmax "
         f"{verdicts[('n_contre_v', 'knn')][0]} et {verdicts[('n_contre_v', 'svm')][0]}, "
         f"{pts(ecarts[('n_contre_v', 'knn')])} et {pts(ecarts[('n_contre_v', 'svm')])}). Ces écarts vont dans le même "
         f"sens dans 4 ou 5 plis sur 5, mais restent petits devant la dispersion entre patients (un même réglage "
         f"varie de 30 à 45 points d'un pli à l'autre). Pour (a), le meilleur Nmax est au bord de la plage testée. "
         f"À Nmax = 12 la reconstruction laisse "
         f"{pc(rec['12']['vs_battement'])} d'erreur relative sur le battement normalisé.\n\n"
         + tableau(["Définition", "Classifieur", "Meilleur Nmax", "Exact. équil. au meilleur", "À Nmax = 12",
                    "Écart (12 − meilleur)", "Plis où le meilleur bat 12", f"12 à moins de {SEUIL * 100:.0f} point"],
                   lignes) + "\n\n"
         + "Hyperparamètres re-choisis par validation croisée par patient pour chaque Nmax. « Plis » : étendue de "
           "l'exactitude équilibrée entre les 5 plis. Erreur de reconstruction : moyenne de "
           "‖f − f_N‖ / ‖f‖ sur 5 000 battements de DS1 tirés au hasard, f étant le battement normalisé lui-même. "
           "La dernière colonne reprend la mesure de `choix_nmax.m` (écart à la reconstruction d'ordre 27, qui est "
           "nulle par construction à 27 et sous-estime l'erreur). Le complexe QRS occupe une trentaine "
           "d'échantillons sur 181 : une base polynomiale globale de degré 12 ne peut pas le suivre finement, "
           "d'où des erreurs de reconstruction élevées à tous les ordres testés.\n\n" + s)
    return s


def q5(e):
    lignes, verdict = [], []
    for d, nomd in DEFS.items():
        for k in CLF:
            a, b = e["q3"][d][k], e["q5"][d][k]
            for nom, r in [("13 coefficients", a), ("181 échantillons", b)]:
                x = r["ds2"]
                lignes.append([COURT[d], CLF[k], nom, pc(r["choix_cv"]["exactitude_equilibree"]),
                               pc(x["exactitude_equilibree"]), pc(x["sensibilite"]), pc(x["specificite"]), pc(x["f1"])])
            verdict.append(b["choix_cv"]["exactitude_equilibree"] - a["choix_cv"]["exactitude_equilibree"])
    cas = [f"{COURT[d]} {CLF[k]} {pts(v)}" for (d, k), v in zip(
        [(d, k) for d in DEFS for k in CLF], verdict)]
    mieux = sum(v <= 0 for v in verdict)
    s = (f"**Réponse.** Oui, à peu près : en validation croisée par patient sur DS1, les 13 coefficients font "
         f"aussi bien ou mieux que les 181 échantillons bruts dans {mieux} cas sur 4, et l'écart (bruts − "
         f"coefficients) reste entre {pts(min(verdict))} et {pts(max(verdict))} ({', '.join(cas)}), petit devant la "
         f"dispersion entre patients. Sur DS2, regardé pour information seulement, le SVM sur échantillons bruts de "
         f"la définition (a) fait nettement mieux "
         f"({pc(e['q5']['projet']['svm']['ds2']['exactitude_equilibree'])} contre "
         f"{pc(e['q3']['projet']['svm']['ds2']['exactitude_equilibree'])}) : la comparaison sur DS1 ne le "
         f"prévoyait pas, ce qui rappelle que ces écarts de quelques points dépendent des patients tirés.\n\n")
    return s + tableau(["Définition", "Classifieur", "Caractéristiques", "Exact. équil. CV DS1",
                        "Exact. équil. DS2", "Sensibilité DS2", "Spécificité DS2", "F1 DS2"], lignes) + "\n"


def ecrire(chemin_json, chemin_md, texte_libre=None):
    e = json.loads(Path(chemin_json).read_text())
    parties = (Path(__file__).parent / "rapport_texte.md").read_text()
    blocs = {"RESUME": resume(e), "Q3_REPONSE": q3_reponse(e), "ECARTS": ecarts(e), "DOUTES": doutes(e),
             "Q1": q1(e), "Q2": q2(e), "Q3": q3(e), "Q4": q4(e), "Q5": q5(e),
             "CONTROLE": controle(e), "VERSIONS": versions(e)}
    for k, v in blocs.items():
        parties = parties.replace("{{" + k + "}}", v)
    Path(chemin_md).write_text(parties)


def q3_reponse(e):
    a, b = e["q3"]["projet"], e["q3"]["n_contre_v"]
    return (f"**Réponse.** Sur des patients jamais vus, la définition (a) du projet tombe à "
            f"{pc(a['knn']['ds2']['exactitude_equilibree'])} (KNN) et {pc(a['svm']['ds2']['exactitude_equilibree'])} "
            f"(SVM) d'exactitude équilibrée, avec une sensibilité de {pc(a['knn']['ds2']['sensibilite'])} et "
            f"{pc(a['svm']['ds2']['sensibilite'])}. La question (b), normal contre extrasystole "
            f"ventriculaire, tient mieux : {pc(b['knn']['ds2']['exactitude_equilibree'])} et "
            f"{pc(b['svm']['ds2']['exactitude_equilibree'])} d'exactitude équilibrée (sensibilité "
            f"{pc(b['knn']['ds2']['sensibilite'])} et {pc(b['svm']['ds2']['sensibilite'])}, spécificité "
            f"{pc(b['knn']['ds2']['specificite'])} et {pc(b['svm']['ds2']['specificite'])}), mais son exactitude "
            f"brute ({pc(b['knn']['ds2']['exactitude'])} et {pc(b['svm']['ds2']['exactitude'])}) reste sous les "
            f"{pc(b['knn']['ds2']['classe_majoritaire'])} d'un classifieur qui répondrait toujours « normal », "
            f"le F1 ne dépasse pas {pc(max(b['knn']['ds2']['f1'], b['svm']['ds2']['f1']))}, et la sensibilité par "
            f"patient va de {sens_parlante(b['knn'])} pour le KNN et de {sens_parlante(b['svm'])} pour le SVM, "
            f"en ne comptant que les patients à {MIN_POSITIFS} extrasystoles ou plus.\n")


def resume(e):
    q = e["q1_q2"]
    a, b = e["q3"]["projet"], e["q3"]["n_contre_v"]
    return ("**En bref.**\n\n"
            f"- Les 98,6 % / 98,5 % du projet se reproduisent (MATLAB relancé : identique, Python : "
            f"{pc(q['resume']['knn1']['moyenne'])} / {pc(q['resume']['svm']['moyenne'])} en moyenne sur 20 graines).\n"
            f"- Ce chiffre mesure surtout la reconnaissance du patient 111 : {pc(q['q2']['part_anomalies_111'])} des "
            f"anomalies viennent de lui, et la règle « anomalie si patient 111 » fait "
            f"{pc(q['q2']['exactitude_classifieur_111']['moyenne'])}.\n"
            f"- Sur 22 patients jamais vus (DS2), la définition du projet donne {pc(a['knn']['ds2']['exactitude_equilibree'])} "
            f"(KNN) et {pc(a['svm']['ds2']['exactitude_equilibree'])} (SVM) d'exactitude équilibrée (50 % = hasard).\n"
            f"- Normal contre extrasystole ventriculaire : {pc(b['knn']['ds2']['exactitude_equilibree'])} et "
            f"{pc(b['svm']['ds2']['exactitude_equilibree'])} d'exactitude équilibrée, sensibilité "
            f"{pc(b['knn']['ds2']['sensibilite'])} et {pc(b['svm']['ds2']['sensibilite'])}, mais F1 "
            f"{pc(b['knn']['ds2']['f1'])} et {pc(b['svm']['ds2']['f1'])} : beaucoup de fausses alarmes.\n"
            "- N = 12 n'est pas un optimum, et les 13 coefficients valent à peu près les 181 échantillons bruts.\n")


def ecarts(e):
    s = e["symboles_par_enregistrement"]
    x = {r: v["x"] for r, v in s.items() if "x" in v}
    ee = {r: v["e"] for r, v in s.items() if "e" in v}
    return (
        "1. **Table des codes d'annotation de `Read_mitbih.m`.** Sa fonction `anncode2char` associe le code 37 à "
        "« e » et le code 38 à « n ». Dans le format MIT, 37 est « x » (onde P non conduite, extrasystole "
        "auriculaire bloquée : pas de QRS) et 38 est « f » (fusion stimulé/normal), alors que « e » (échappement "
        "auriculaire) est le code 34 et « n » le code 35 (table de `wfdb`, `ann_label_table`). Appliquée telle "
        f"quelle à toute la base, cette lecture compterait comme battements normaux {sum(x.values())} ondes P "
        f"non conduites ({', '.join(f'{r} : {n}' for r, n in x.items())}) et écarterait les {sum(ee.values())} "
        f"vrais échappements auriculaires (223). J'ai appliqué la table de symboles `sym2label` aux vrais "
        "symboles lus par `wfdb`, ce qui était l'intention de `Read_mitbih.m`. Sur les quatre patients du projet, aucun de ces codes "
        "n'apparaît : la Q1 n'est pas affectée.\n"
        "2. **Décalage d'un échantillon.** Reproduit en Q1-Q2 (pour retrouver les chiffres du projet), retiré en Q3-Q5 : "
        "les fenêtres y sont centrées sur le pic R annoté.\n"
        "3. **SVM.** `KernelScale 'auto'` de MATLAB est remplacé en Q1 par `gamma='scale'` de scikit-learn. En "
        "Q3-Q5, gamma est réglé par validation croisée (exprimé relativement au nombre de caractéristiques, "
        "pour que la même grille serve à 13 coefficients et à 181 échantillons).\n"
        "4. **Enregistrement 114** lu sur son second canal (MLII), le premier étant V5.\n"
        "5. **Vérification des listes** faite contre une reproduction publiée (He et al. 2018) et un code publié "
        "(Mondéjar-Guerra et al.), pas contre l'article de de Chazal lui-même.\n")


def doutes(e):
    a = e["q3"]["projet"]
    bord = [f"{COURT[d]} {CLF[k]}" for d in DEFS for k in CLF
            if e["q3"][d][k]["choix_cv"]["params"].get("k") == 25
            or e["q3"][d][k]["choix_cv"]["params"].get("C") in (0.3, 30)
            or e["q3"][d][k]["choix_cv"]["params"].get("g") in (0.3, 3)]
    return (
        f"- **Réglages au bord de la grille** ({', '.join(bord)}) : K = 25 est la plus grande valeur testée, "
        "C = 0,3 et gamma = 0,3/d les plus petites. Une grille plus large aurait peut-être trouvé mieux sur DS1. "
        "Je ne l'ai pas élargie après coup, parce que DS2 avait déjà été regardé : relancer et réévaluer "
        "aurait été un second regard sur le test.\n"
        "- **Une seule graine pour Q3-Q5** (sous-échantillonnage, plis fixes de `GroupKFold`). Avec 22 patients, "
        "l'écart entre plis (souvent 30 à 45 points d'exactitude équilibrée, voir Q4) domine toute différence "
        "de quelques points entre réglages, et les écarts de moins de 3 points entre classifieurs ou entre Nmax "
        "ne doivent pas être sur-interprétés.\n"
        "- **La définition (a) mélange des anomalies que la seule forme du QRS ne peut pas voir** : les "
        "extrasystoles auriculaires (A, très nombreuses chez 232) ont un QRS normal et se reconnaissent surtout à "
        "leur prématurité (intervalle RR). La chaîne, qui normalise chaque fenêtre et jette le rythme, ne peut pas "
        "les détecter. La littérature inter-patients ajoute les intervalles RR pour cette raison. La faible "
        f"sensibilité de (a) ({pc(a['svm']['ds2']['sensibilite'])} pour le SVM) en vient en partie.\n"
        "- **Les blocs de branche sont « normaux » en (b)** (convention AAMI) : chez 111, 214, 212 et 232, une "
        "partie des fausses alarmes vient de battements L ou R pris pour des V. Ce n'est pas faux au sens de "
        "l'AAMI, mais cela pèse sur la spécificité.\n"
        "- **Sensibilité par patient** : beaucoup de patients de DS2 n'ont que 0 à 3 battements positifs, et leurs "
        "pourcentages (0 % ou 100 %) ne mesurent presque rien. L'étendue « 0 % à 100 % » est donc en partie un "
        "effet de petits nombres. Les patients à plusieurs centaines de positifs (200, 210, 213, 214, 221, 228, "
        "233) sont les plus parlants.\n"
        "- **Comparaison à la littérature** : aucune n'est faite ici. Les chiffres publiés sur DS1/DS2 utilisent "
        "d'autres caractéristiques (RR notamment) et souvent les cinq classes AAMI, ils ne sont pas directement "
        "comparables.\n")


def controle(e):
    c = e["controle_lecture"]
    oui = lambda x: "oui" if x else "non"
    lignes = [[p, v["canal_mlii"], f"{v['ecart_max_signal_mV']:g}", f"{v['n_pics_projet']} / {v['n_pics_physionet']}",
               oui(v["pics_identiques"]), oui(v["symboles_identiques"]), oui(v.get("etiquettes_identiques", True))]
              for p, v in c.items()]
    sh = e["sommes_sha256"]
    s = (f"Sommes SHA-256 : {'vérifiées pour ' + str(sh['n_fichiers']) + ' fichiers, ' + str(len(sh['differents'])) + ' différent(s)' if sh['verifie'] else 'non vérifiées (' + sh['erreur'] + ')'}.\n\n")
    non_mlii = {r: c for r, c in e["canaux"].items() if c[0] != "MLII"}
    s += ("Canal : " + ", ".join(f"l'enregistrement {r} a pour canaux {c}" for r, c in non_mlii.items())
          + ". Partout ailleurs dans DS1 et DS2, le premier canal est MLII. Le canal est choisi par son nom "
            "(`MLII`), donc 114 est lu sur son second canal. (Les exclus 102 et 104 n'ont pas de MLII du tout.)\n\n")
    if not c:
        return s + ("Fichiers `patient_*.mat` du projet absents de `data/projet/` : Q1-Q2 relisent les "
                    "enregistrements 100, 101, 105 et 111 sur PhysioNet avec la table du projet "
                    "(`donnees.lire_comme_projet`), qui redonne exactement ces fichiers.\n")
    s += tableau(["Enregistrement", "Indice du canal MLII", "Écart max. du signal (mV)",
                  "Pics : projet / PhysioNet", "Pics identiques", "Symboles identiques",
                  "Étiquettes identiques"], lignes) + "\n"
    return s


def versions(e):
    v = e["versions"]
    return (", ".join(f"{k} {x}" for k, x in v.items()) + f". Graines : Q1-Q2 {e['graines']['q1_q2'][0]} à "
            f"{e['graines']['q1_q2'][-1]}, Q3-Q5 {e['graines']['q3_q5']}. Durée : {e['duree_s'] / 60:.0f} min.")


if __name__ == "__main__":
    ecrire(RACINE / "results" / "etude.json", RACINE / "results" / "rapport.md")
