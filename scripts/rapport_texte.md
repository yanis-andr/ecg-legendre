# La classification ECG par Legendre sur des patients jamais vus

Fichier généré par `scripts/rapport.py` à partir de `results/etude.json` (ne pas éditer à la main :
le texte fixe est dans `scripts/rapport_texte.md`).

{{RESUME}}

## Pourquoi le découpage par patient change le chiffre

Un ECG porte la signature de la personne autant que celle du battement : position des électrodes,
axe du cœur, morphologie propre du QRS. Deux battements normaux d'un même patient se ressemblent
beaucoup plus que deux battements normaux de deux patients différents.

Avec un découpage aléatoire des battements, chaque battement de test a, dans l'entraînement, des
dizaines de « frères » du même enregistrement, pris quelques secondes avant ou après. Un KNN K = 1
n'a qu'à retrouver le frère le plus proche et recopier son étiquette : il n'apprend pas ce qu'est une
anomalie, il apprend à reconnaître l'enregistrement. Dans le projet, c'est d'autant plus facile que
96 % des anomalies sont les blocs de branche gauche du seul patient 111, qui n'a aucun battement
normal : « ce battement ressemble-t-il au patient 111 ? » suffit à faire 98 %.

En usage réel, le classifieur verra un patient qu'il n'a jamais vu. La seule mesure qui l'imite est
de séparer les **patients**, pas les battements : tous les battements d'un patient sont soit dans
l'entraînement, soit dans le test. C'est le découpage DS1/DS2 de de Chazal et al. (2004), devenu la
référence sur MIT-BIH, et c'est aussi pour cela que les réglages (K, C, gamma, équilibrage) sont
choisis par validation croisée **par patient** dans DS1 (GroupKFold, 5 plis : les patients d'un pli
de validation n'apparaissent jamais dans l'entraînement de ce pli) et que DS2 n'est évalué qu'une
fois, à la fin.

Deuxième piège, indépendant : sur DS2, la classe normale fait la grande majorité des battements.
Un classifieur qui répond toujours « normal » y a déjà une exactitude brute élevée. C'est pourquoi
chaque exactitude brute est donnée avec la proportion de la classe majoritaire à côté, et pourquoi
le critère principal est l'**exactitude équilibrée** (moyenne de la sensibilité et de la
spécificité), qui vaut 50 % pour un classifieur trivial.

## Q1. Reproduction des chiffres du projet

{{Q1}}

## Q2. Le défaut, mesuré

{{Q2}}

## Q3. Évaluation inter-patients (MIT-BIH, DS1 → DS2)

{{Q3_REPONSE}}

**Protocole.** Les 44 enregistrements sans stimulateur, canal MLII, pics R et symboles des annotations
de référence (`.atr`). Même chaîne que le projet : fenêtre ±90 échantillons autour du pic (sans le décalage
d'un échantillon du script d'origine), normalisation dans [-1, 1], 13 coefficients de Legendre par trapèzes, centrage-réduction
appris sur l'entraînement. Grilles explorées par validation croisée par patient sur DS1 (5 plis,
critère : exactitude équilibrée des prédictions hors pli) : KNN K ∈ {1, 3, 5, 9, 15, 25} ×
{sans équilibrage, sous-échantillonnage de la classe majoritaire}, et SVM RBF C ∈ {0,3 ; 3 ; 30} ×
gamma ∈ {0,3 ; 1 ; 3} / d (d = nombre de caractéristiques) × {poids de classe équilibrés,
sous-échantillonnage}. Le modèle retenu est réentraîné sur tout DS1 puis appliqué une fois à DS2.

**Listes DS1/DS2.** Vérifiées contre He et al., « A pyramid-like model for heartbeat classification
from ECG recordings », *PLoS One* 2018 (PMC6235298), qui reproduit le découpage de de Chazal, O'Dwyer
et Reilly, *IEEE Trans Biomed Eng* 51(7):1196-1206, 2004 (DS1, DS2 et les quatre exclus 102, 104,
107, 217 identiques aux listes utilisées ici), et contre le code publié de Mondéjar-Guerra et al. (2019,
`github.com/mondejar/ecg-classification`, `load_MITBIH.py`). L'article de de Chazal lui-même n'a pas
été consulté (accès payant).

**Lecture des données.** {{CONTROLE}}

**Étiquettes.**
- (a) la table `sym2label` de `Read_mitbih.m` (projet) : normal = N, e, j, n, anomalie = V, L, R, A, a, J, S, E, F,
  écartés : Q, / et tout le reste.
- (b) AAMI : N = {N, L, R, e, j} contre V = {V, E}, tout le reste écarté. Attention : en (b), les
  blocs de branche (L, R) sont « normaux », alors qu'ils sont des « anomalies » en (a).

{{Q3}}

## Q4. Le choix de Nmax, refait proprement

{{Q4}}

## Q5. Contrôle de bon sens : coefficients contre échantillons bruts

{{Q5}}

## Écarts au protocole prévu

{{ECARTS}}

## Ce qui reste douteux

{{DOUTES}}

## Reproductibilité

`uv run python scripts/etude.py` rejoue tout. {{VERSIONS}}
