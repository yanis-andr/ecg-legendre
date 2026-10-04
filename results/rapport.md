# La classification ECG par Legendre sur des patients jamais vus

Fichier généré par `scripts/rapport.py` à partir de `results/etude.json` (ne pas éditer à la main :
le texte fixe est dans `scripts/rapport_texte.md`).

**En bref.**

- Les 98,6 % / 98,5 % du projet se reproduisent (MATLAB relancé : identique, Python : 99,2 % / 98,7 % en moyenne sur 20 graines).
- Ce chiffre mesure surtout la reconnaissance du patient 111 : 96,5 % des anomalies viennent de lui, et la règle « anomalie si patient 111 » fait 98,1 %.
- Sur 22 patients jamais vus (DS2), la définition du projet donne 63,8 % (KNN) et 69,3 % (SVM) d'exactitude équilibrée (50 % = hasard).
- Normal contre extrasystole ventriculaire : 89,3 % et 90,3 % d'exactitude équilibrée, sensibilité 87,5 % et 93,4 %, mais F1 56,4 % et 50,6 % : beaucoup de fausses alarmes.
- N = 12 n'est pas un optimum, et les 13 coefficients valent à peu près les 181 échantillons bruts.


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

**Réponse.** Oui : la chaîne Python redonne les chiffres du projet à moins d'un point (KNN K = 1 : 99,2 % [98,5 % ; 99,8 %] sur 20 graines contre 98,6 %, SVM : 98,7 % [97,7 % ; 99,3 %] contre 98,5 %), et le 98,6 % du projet est l'un des tirages les plus bas de l'étendue.

Exactitude sur l'échantillon de test (881 battements, classes équilibrées), moyenne [min ; max]. Classifieur trivial (toujours la classe majoritaire du test) : 51,1 % [50,2 % ; 53,0 %], règle « anomalie si patient 111 » : 98,1 % [97,3 % ; 99,0 %] (Q2).

| Source | KNN K = 1 | KNN « meilleur K » (choisi sur le test) | SVM RBF |
|---|---|---|---|
| Script du projet (graine 42, figure `fig1_confusion.png`) | 98,6 % | 98,6 % (K = 1) | 98,5 % |
| MATLAB R2024b, code du projet relancé, graine 42 | 98,64 % | 98,64 % | 98,52 % |
| MATLAB, 21 graines (42, 1..20) | 99,0 % [98,6 % ; 99,4 %] | 99,1 % [98,6 % ; 99,5 %] | 98,7 % [97,8 % ; 99,3 %] |
| Python, sur les mêmes découpages que MATLAB | 99,0 % [98,6 % ; 99,4 %] |  | 98,7 % [98,0 % ; 99,3 %] |
| Python, 20 graines (0..19) | 99,2 % [98,5 % ; 99,8 %] | 99,2 % [98,8 % ; 99,8 %] | 98,7 % [97,7 % ; 99,3 %] |

Contrôle MATLAB : `classification_ecg.m` relancé tel quel sur une copie redonne exactement 98,6 % et 98,5 %. Les coefficients c_0..c_12 des 8824 battements calculés en Python et en MATLAB diffèrent au plus de 1.4e-15 (arrondi numérique), les étiquettes sont identiques. Sur les mêmes découpages que MATLAB, le KNN Python donne exactement les mêmes exactitudes. Le SVM diffère de quelques battements parce que `KernelScale 'auto'` de MATLAB (heuristique sur un sous-échantillon aléatoire) n'a pas d'équivalent exact : Python utilise `gamma='scale'` (1 / nombre de caractéristiques après centrage-réduction). L'écart restant entre lignes vient donc des tirages aléatoires, pas de la chaîne.

Deux détails du script du projet, reproduits ici pour la Q1 et corrigés ensuite : (1) `classification_ecg.m` ajoute 1 aux pics R « base 0 Python → base 1 MATLAB » alors que `Read_mitbih.m` les a déjà stockés en base 1 : chaque fenêtre est centrée un échantillon (2,8 ms) après le pic R (`choix_nmax.m`, lui, ne décale pas), (2) le K du KNN est choisi parmi 1, 3, 5, 7, 11 sur l'exactitude du **test**, ce qui est un réglage sur le test (effet faible ici, voir la colonne « meilleur K »).


## Q2. Le défaut, mesuré

**Réponse.** 96,5 % des anomalies viennent du patient 111. Une règle qui répond « anomalie » si et seulement si le battement vient du patient 111 obtient 98,1 % [97,3 % ; 99,0 %] sur les mêmes découpages (attendu : 98,2 %), presque autant que les 98,6 % du projet. Sur les anomalies des patients 100, 101 et 105 seules, le KNN n'a raison que dans 77,3 % des cas et le SVM dans 46,2 %.

| Patient | Normaux | Anomalies | Part des anomalies |
|---|---|---|---|
| 100 | 2237 | 34 | 1,5 % |
| 101 | 1859 | 3 | 0,1 % |
| 105 | 2526 | 41 | 1,9 % |
| 111 | 0 | 2124 | 96,5 % |

Battements retenus après fenêtrage (8824 au total). Anomalies de 100/101/105 tombées dans le test, cumulées sur les 20 graines : 331, dont justes : KNN 256, SVM 153.

Complément : chaque patient retiré à son tour (entraînement équilibré sur les trois autres, mêmes classifieurs, test sur le patient retiré). Le patient 111 n'a aucun battement normal : sa spécificité n'existe pas.

| Patient testé | Classifieur | Anomalies trouvées | Sensibilité | Spécificité | Exactitude | Classe majoritaire |
|---|---|---|---|---|---|---|
| 100 | KNN | 2/34 | 5,9 % | 100,0 % | 98,6 % | 98,5 % |
| 100 | SVM RBF | 0/34 | 0,0 % | 100,0 % | 98,5 % | 98,5 % |
| 101 | KNN | 1/3 | 33,3 % | 99,9 % | 99,8 % | 99,8 % |
| 101 | SVM RBF | 0/3 | 0,0 % | 100,0 % | 99,8 % | 99,8 % |
| 105 | KNN | 32/41 | 78,0 % | 94,1 % | 93,8 % | 98,4 % |
| 105 | SVM RBF | 36/41 | 87,8 % | 71,0 % | 71,3 % | 98,4 % |
| 111 | KNN | 2123/2124 | 100,0 % | n.d. | 100,0 % | 100,0 % |
| 111 | SVM RBF | 2124/2124 | 100,0 % | n.d. | 100,0 % | 100,0 % |

Même retiré de l'entraînement, le patient 111 est classé « anomalie » à 100,0 % (KNN) et 100,0 % (SVM) : ses blocs de branche gauche ne ressemblent à aucun normal des trois autres. Ce sont les anomalies discrètes (extrasystoles auriculaires A de 100 et 101) qui ne sont presque jamais trouvées : le score de 98 % ne dit presque rien des anomalies de 100, 101 et 105, qui ne font que 3,5 % de la classe « anomalie ».


## Q3. Évaluation inter-patients (MIT-BIH, DS1 → DS2)

**Réponse.** Sur des patients jamais vus, la définition (a) du projet tombe à 63,8 % (KNN) et 69,3 % (SVM) d'exactitude équilibrée, avec une sensibilité de 37,3 % et 48,8 %. La question (b), normal contre extrasystole ventriculaire, tient mieux : 89,3 % et 90,3 % d'exactitude équilibrée (sensibilité 87,5 % et 93,4 %, spécificité 91,1 % et 87,2 %), mais son exactitude brute (90,8 % et 87,6 %) reste sous les 93,2 % d'un classifieur qui répondrait toujours « normal », le F1 ne dépasse pas 56,4 %, et la sensibilité par patient va de 12 % à 100 % (9 patients) pour le KNN et de 10 % à 100 % (9 patients) pour le SVM, en ne comptant que les patients à 20 extrasystoles ou plus.


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

**Lecture des données.** Sommes SHA-256 : vérifiées pour 132 fichiers, 0 différent(s).

Canal : l'enregistrement 114 a pour canaux ['V5', 'MLII']. Partout ailleurs dans DS1 et DS2, le premier canal est MLII. Le canal est choisi par son nom (`MLII`), donc 114 est lu sur son second canal. (Les exclus 102 et 104 n'ont pas de MLII du tout.)

| Enregistrement | Indice du canal MLII | Écart max. du signal (mV) | Pics : projet / PhysioNet | Pics identiques | Symboles identiques | Étiquettes identiques |
|---|---|---|---|---|---|---|
| 100 | 0 | 0 | 2273 / 2273 | oui | oui | oui |
| 101 | 0 | 0 | 1865 / 1865 | oui | oui | oui |
| 105 | 0 | 0 | 2572 / 2572 | oui | oui | oui |
| 111 | 0 | 0 | 2124 / 2124 | oui | oui | oui |


**Étiquettes.**
- (a) la table `sym2label` de `Read_mitbih.m` (projet) : normal = N, e, j, n, anomalie = V, L, R, A, a, J, S, E, F,
  écartés : Q, / et tout le reste.
- (b) AAMI : N = {N, L, R, e, j} contre V = {V, E}, tout le reste écarté. Attention : en (b), les
  blocs de branche (L, R) sont « normaux », alors qu'ils sont des « anomalies » en (a).

### (a) définition du projet : normal contre anomalie

DS1 : 51002 battements dont 12875 positifs, DS2 : 49691 battements dont 13046 positifs.

| Classifieur | Réglage choisi (CV par patient sur DS1) | Exact. équil. CV DS1 | VP / FN / FP / VN (DS2) | Sensibilité | Spécificité | Exact. équilibrée | F1 | Exactitude brute | Classe majoritaire | Sensibilité par patient (min à max) | Idem, patients à 20 positifs ou plus |
|---|---|---|---|---|---|---|---|---|---|---|---|
| KNN | K = 25, équilibrage : aucun | 76,1 % | 4862 / 8184 / 3571 / 33074 | 37,3 % | 90,3 % | 63,8 % | 45,3 % | 76,3 % | 73,7 % | 0 % à 100 % | 0 % à 100 % (17 patients) |
| SVM RBF | C = 0.3, gamma = 0.3/d, équilibrage : sous-échantillonnage | 78,7 % | 6360 / 6686 / 3700 / 32945 | 48,8 % | 89,9 % | 69,3 % | 55,1 % | 79,1 % | 73,7 % | 0 % à 100 % | 0 % à 99 % (17 patients) |

Par patient de DS2 (sensibilité « n.d. » : aucun battement positif chez ce patient. À lire avec le nombre de positifs, une sensibilité sur 1 battement ne vaut rien) :

| Patient | Normaux | Positifs | Sens. KNN | Spéc. KNN | Sens. SVM | Spéc. SVM |
|---|---|---|---|---|---|---|
| 100 | 2237 | 34 | 11,8 % | 93,6 % | 2,9 % | 100,0 % |
| 103 | 2082 | 2 | 0,0 % | 99,9 % | 0,0 % | 100,0 % |
| 105 | 2526 | 41 | 36,6 % | 96,5 % | 12,2 % | 95,3 % |
| 111 | 0 | 2124 | 21,3 % | n.d. | 10,0 % | n.d. |
| 113 | 1788 | 6 | 100,0 % | 99,8 % | 0,0 % | 100,0 % |
| 117 | 1533 | 1 | 0,0 % | 76,7 % | 0,0 % | 86,4 % |
| 121 | 1861 | 2 | 50,0 % | 98,4 % | 50,0 % | 96,8 % |
| 123 | 1514 | 3 | 100,0 % | 99,9 % | 100,0 % | 100,0 % |
| 200 | 1742 | 858 | 93,7 % | 38,1 % | 93,4 % | 94,3 % |
| 202 | 2061 | 75 | 45,3 % | 96,7 % | 53,3 % | 93,2 % |
| 210 | 2421 | 227 | 83,3 % | 56,8 % | 83,7 % | 93,5 % |
| 212 | 922 | 1825 | 5,7 % | 99,9 % | 43,2 % | 99,9 % |
| 213 | 2640 | 610 | 35,7 % | 99,9 % | 35,7 % | 100,0 % |
| 214 | 0 | 2259 | 44,4 % | n.d. | 88,4 % | n.d. |
| 219 | 2082 | 72 | 79,2 % | 97,6 % | 88,9 % | 9,2 % |
| 221 | 2031 | 396 | 99,7 % | 98,5 % | 99,2 % | 100,0 % |
| 222 | 2273 | 209 | 41,1 % | 90,0 % | 56,5 % | 83,5 % |
| 228 | 1688 | 365 | 97,3 % | 95,1 % | 99,2 % | 95,6 % |
| 231 | 314 | 1257 | 0,4 % | 100,0 % | 0,4 % | 100,0 % |
| 232 | 1 | 1779 | 22,4 % | 100,0 % | 19,4 % | 0,0 % |
| 233 | 2229 | 848 | 86,0 % | 90,4 % | 95,9 % | 74,2 % |
| 234 | 2700 | 53 | 5,7 % | 94,6 % | 5,7 % | 100,0 % |

### (b) normal (AAMI N) contre extrasystole ventriculaire (AAMI V)

DS1 : 49644 battements dont 3788 positifs, DS2 : 47466 battements dont 3220 positifs.

| Classifieur | Réglage choisi (CV par patient sur DS1) | Exact. équil. CV DS1 | VP / FN / FP / VN (DS2) | Sensibilité | Spécificité | Exact. équilibrée | F1 | Exactitude brute | Classe majoritaire | Sensibilité par patient (min à max) | Idem, patients à 20 positifs ou plus |
|---|---|---|---|---|---|---|---|---|---|---|---|
| KNN | K = 25, équilibrage : sous-échantillonnage | 81,0 % | 2816 / 404 / 3955 / 40291 | 87,5 % | 91,1 % | 89,3 % | 56,4 % | 90,8 % | 93,2 % | 0 % à 100 % | 12 % à 100 % (9 patients) |
| SVM RBF | C = 3, gamma = 0.3/d, équilibrage : poids de classe | 83,6 % | 3006 / 214 / 5657 / 38589 | 93,4 % | 87,2 % | 90,3 % | 50,6 % | 87,6 % | 93,2 % | 0 % à 100 % | 10 % à 100 % (9 patients) |

Par patient de DS2 (sensibilité « n.d. » : aucun battement positif chez ce patient. À lire avec le nombre de positifs, une sensibilité sur 1 battement ne vaut rien) :

| Patient | Normaux | Positifs | Sens. KNN | Spéc. KNN | Sens. SVM | Spéc. SVM |
|---|---|---|---|---|---|---|
| 100 | 2237 | 1 | 0,0 % | 100,0 % | 0,0 % | 100,0 % |
| 103 | 2082 | 0 | n.d. | 100,0 % | n.d. | 99,9 % |
| 105 | 2526 | 41 | 12,2 % | 95,4 % | 9,8 % | 93,0 % |
| 111 | 2123 | 1 | 100,0 % | 50,4 % | 100,0 % | 23,4 % |
| 113 | 1788 | 0 | n.d. | 100,0 % | n.d. | 100,0 % |
| 117 | 1533 | 0 | n.d. | 67,9 % | n.d. | 95,9 % |
| 121 | 1861 | 1 | 100,0 % | 99,5 % | 100,0 % | 97,6 % |
| 123 | 1514 | 3 | 100,0 % | 100,0 % | 100,0 % | 99,9 % |
| 200 | 1742 | 826 | 94,7 % | 96,3 % | 97,1 % | 96,6 % |
| 202 | 2061 | 19 | 100,0 % | 100,0 % | 100,0 % | 99,9 % |
| 210 | 2421 | 195 | 83,6 % | 99,0 % | 91,8 % | 99,1 % |
| 212 | 2747 | 0 | n.d. | 71,2 % | n.d. | 35,1 % |
| 213 | 2640 | 220 | 90,0 % | 100,0 % | 94,1 % | 100,0 % |
| 214 | 2002 | 256 | 72,3 % | 77,1 % | 75,4 % | 40,0 % |
| 219 | 2082 | 64 | 81,2 % | 88,1 % | 98,4 % | 90,0 % |
| 221 | 2031 | 396 | 99,7 % | 100,0 % | 100,0 % | 100,0 % |
| 222 | 2273 | 0 | n.d. | 99,6 % | n.d. | 91,0 % |
| 228 | 1688 | 362 | 74,6 % | 99,5 % | 88,4 % | 97,4 % |
| 231 | 1568 | 2 | 50,0 % | 99,6 % | 100,0 % | 99,7 % |
| 232 | 398 | 0 | n.d. | 86,4 % | n.d. | 53,3 % |
| 233 | 2229 | 830 | 88,9 % | 72,1 % | 98,0 % | 99,0 % |
| 234 | 2700 | 3 | 100,0 % | 100,0 % | 100,0 % | 100,0 % |



## Q4. Le choix de Nmax, refait proprement

**Réponse.** Non, N = 12 n'est l'optimum pour aucune des deux questions : pour la définition (a) l'exactitude équilibrée monte avec plus de coefficients (meilleur Nmax 22 pour le KNN, 27 pour le SVM, +7,0 pt et +5,9 pt par rapport à 12), pour la définition (b) elle est meilleure avec moins de coefficients (Nmax 4 et 4, +4,0 pt et +3,2 pt). Ces écarts vont dans le même sens dans 4 ou 5 plis sur 5, mais restent petits devant la dispersion entre patients (un même réglage varie de 30 à 45 points d'un pli à l'autre). Pour (a), le meilleur Nmax est au bord de la plage testée. À Nmax = 12 la reconstruction laisse 39,8 % d'erreur relative sur le battement normalisé.

| Définition | Classifieur | Meilleur Nmax | Exact. équil. au meilleur | À Nmax = 12 | Écart (12 − meilleur) | Plis où le meilleur bat 12 | 12 à moins de 1 point |
|---|---|---|---|---|---|---|---|
| (a) | KNN | 22 | 83,0 % | 76,1 % | −7,0 pt | 5/5 | non |
| (a) | SVM RBF | 27 | 84,6 % | 78,7 % | −5,9 pt | 4/5 | non |
| (b) | KNN | 4 | 85,0 % | 81,0 % | −4,0 pt | 4/5 | non |
| (b) | SVM RBF | 4 | 86,8 % | 83,6 % | −3,2 pt | 4/5 | non |

Hyperparamètres re-choisis par validation croisée par patient pour chaque Nmax. « Plis » : étendue de l'exactitude équilibrée entre les 5 plis. Erreur de reconstruction : moyenne de ‖f − f_N‖ / ‖f‖ sur 5 000 battements de DS1 tirés au hasard, f étant le battement normalisé lui-même. La dernière colonne reprend la mesure de `choix_nmax.m` (écart à la reconstruction d'ordre 27, qui est nulle par construction à 27 et sous-estime l'erreur). Le complexe QRS occupe une trentaine d'échantillons sur 181 : une base polynomiale globale de degré 12 ne peut pas le suivre finement, d'où des erreurs de reconstruction élevées à tous les ordres testés.

#### (a) définition du projet : normal contre anomalie

| Nmax | KNN : exact. équil. CV DS1 | SVM : exact. équil. CV DS1 | Erreur de reconstruction | Erreur rel. à Nmax = 27 (mesure du projet) |
|---|---|---|---|---|
| 2 | 66,8 % (plis : 53 % à 93 %) | 73,6 % (plis : 55 % à 94 %) | 58,7 % | 53,9 % |
| 4 | 64,3 % (plis : 37 % à 93 %) | 66,0 % (plis : 31 % à 94 %) | 55,0 % | 50,3 % |
| 6 | 63,3 % (plis : 42 % à 92 %) | 65,9 % (plis : 33 % à 90 %) | 51,3 % | 45,3 % |
| 8 | 72,6 % (plis : 48 % à 92 %) | 74,8 % (plis : 50 % à 90 %) | 47,2 % | 41,8 % |
| 10 | 74,5 % (plis : 48 % à 94 %) | 77,6 % (plis : 50 % à 94 %) | 43,4 % | 35,9 % |
| 12 | 76,1 % (plis : 53 % à 94 %) | 78,7 % (plis : 50 % à 95 %) | 39,8 % | 33,3 % |
| 15 | 76,1 % (plis : 48 % à 96 %) | 78,7 % (plis : 47 % à 95 %) | 36,4 % | 27,3 % |
| 18 | 78,2 % (plis : 53 % à 96 %) | 81,1 % (plis : 50 % à 97 %) | 30,8 % | 20,0 % |
| 22 | 83,0 % (plis : 53 % à 97 %) | 84,2 % (plis : 50 % à 97 %) | 26,4 % | 12,8 % |
| 27 | 82,7 % (plis : 53 % à 97 %) | 84,6 % (plis : 50 % à 97 %) | 23,5 % | 0,0 % |

#### (b) normal (AAMI N) contre extrasystole ventriculaire (AAMI V)

| Nmax | KNN : exact. équil. CV DS1 | SVM : exact. équil. CV DS1 | Erreur de reconstruction | Erreur rel. à Nmax = 27 (mesure du projet) |
|---|---|---|---|---|
| 2 | 83,3 % (plis : 63 % à 94 %) | 85,9 % (plis : 66 % à 96 %) | 58,7 % | 53,9 % |
| 4 | 85,0 % (plis : 68 % à 99 %) | 86,8 % (plis : 72 % à 100 %) | 55,0 % | 50,3 % |
| 6 | 84,0 % (plis : 64 % à 99 %) | 85,5 % (plis : 69 % à 100 %) | 51,3 % | 45,3 % |
| 8 | 81,7 % (plis : 66 % à 99 %) | 82,6 % (plis : 64 % à 100 %) | 47,2 % | 41,8 % |
| 10 | 81,2 % (plis : 65 % à 95 %) | 83,1 % (plis : 65 % à 97 %) | 43,4 % | 35,9 % |
| 12 | 81,0 % (plis : 66 % à 96 %) | 83,6 % (plis : 64 % à 97 %) | 39,8 % | 33,3 % |
| 15 | 81,3 % (plis : 69 % à 97 %) | 83,3 % (plis : 67 % à 95 %) | 36,4 % | 27,3 % |
| 18 | 80,9 % (plis : 69 % à 98 %) | 83,2 % (plis : 65 % à 96 %) | 30,8 % | 20,0 % |
| 22 | 80,1 % (plis : 68 % à 99 %) | 83,1 % (plis : 69 % à 99 %) | 26,4 % | 12,8 % |
| 27 | 80,8 % (plis : 69 % à 94 %) | 83,1 % (plis : 65 % à 97 %) | 23,5 % | 0,0 % |



## Q5. Contrôle de bon sens : coefficients contre échantillons bruts

**Réponse.** Oui, à peu près : en validation croisée par patient sur DS1, les 13 coefficients font aussi bien ou mieux que les 181 échantillons bruts dans 3 cas sur 4, et l'écart (bruts − coefficients) reste entre −4,2 pt et +1,3 pt ((a) KNN −4,2 pt, (a) SVM RBF +1,3 pt, (b) KNN −0,9 pt, (b) SVM RBF −1,1 pt), petit devant la dispersion entre patients. Sur DS2, regardé pour information seulement, le SVM sur échantillons bruts de la définition (a) fait nettement mieux (75,8 % contre 69,3 %) : la comparaison sur DS1 ne le prévoyait pas, ce qui rappelle que ces écarts de quelques points dépendent des patients tirés.

| Définition | Classifieur | Caractéristiques | Exact. équil. CV DS1 | Exact. équil. DS2 | Sensibilité DS2 | Spécificité DS2 | F1 DS2 |
|---|---|---|---|---|---|---|---|
| (a) | KNN | 13 coefficients | 76,1 % | 63,8 % | 37,3 % | 90,3 % | 45,3 % |
| (a) | KNN | 181 échantillons | 71,9 % | 59,9 % | 29,4 % | 90,4 % | 37,6 % |
| (a) | SVM RBF | 13 coefficients | 78,7 % | 69,3 % | 48,8 % | 89,9 % | 55,1 % |
| (a) | SVM RBF | 181 échantillons | 79,9 % | 75,8 % | 56,7 % | 94,8 % | 66,3 % |
| (b) | KNN | 13 coefficients | 81,0 % | 89,3 % | 87,5 % | 91,1 % | 56,4 % |
| (b) | KNN | 181 échantillons | 80,1 % | 88,9 % | 83,6 % | 94,2 % | 63,6 % |
| (b) | SVM RBF | 13 coefficients | 83,6 % | 90,3 % | 93,4 % | 87,2 % | 50,6 % |
| (b) | SVM RBF | 181 échantillons | 82,5 % | 89,8 % | 93,4 % | 86,1 % | 48,6 % |


## Écarts au protocole prévu

1. **Table des codes d'annotation de `Read_mitbih.m`.** Sa fonction `anncode2char` associe le code 37 à « e » et le code 38 à « n ». Dans le format MIT, 37 est « x » (onde P non conduite, extrasystole auriculaire bloquée : pas de QRS) et 38 est « f » (fusion stimulé/normal), alors que « e » (échappement auriculaire) est le code 34 et « n » le code 35 (table de `wfdb`, `ann_label_table`). Appliquée telle quelle à toute la base, cette lecture compterait comme battements normaux 193 ondes P non conduites (108 : 11, 118 : 10, 201 : 37, 219 : 133, 231 : 2) et écarterait les 16 vrais échappements auriculaires (223). J'ai appliqué la table de symboles `sym2label` aux vrais symboles lus par `wfdb`, ce qui était l'intention de `Read_mitbih.m`. Sur les quatre patients du projet, aucun de ces codes n'apparaît : la Q1 n'est pas affectée.
2. **Décalage d'un échantillon.** Reproduit en Q1-Q2 (pour retrouver les chiffres du projet), retiré en Q3-Q5 : les fenêtres y sont centrées sur le pic R annoté.
3. **SVM.** `KernelScale 'auto'` de MATLAB est remplacé en Q1 par `gamma='scale'` de scikit-learn. En Q3-Q5, gamma est réglé par validation croisée (exprimé relativement au nombre de caractéristiques, pour que la même grille serve à 13 coefficients et à 181 échantillons).
4. **Enregistrement 114** lu sur son second canal (MLII), le premier étant V5.
5. **Vérification des listes** faite contre une reproduction publiée (He et al. 2018) et un code publié (Mondéjar-Guerra et al.), pas contre l'article de de Chazal lui-même.


## Ce qui reste douteux

- **Réglages au bord de la grille** ((a) KNN, (a) SVM RBF, (b) KNN, (b) SVM RBF) : K = 25 est la plus grande valeur testée, C = 0,3 et gamma = 0,3/d les plus petites. Une grille plus large aurait peut-être trouvé mieux sur DS1. Je ne l'ai pas élargie après coup, parce que DS2 avait déjà été regardé : relancer et réévaluer aurait été un second regard sur le test.
- **Une seule graine pour Q3-Q5** (sous-échantillonnage, plis fixes de `GroupKFold`). Avec 22 patients, l'écart entre plis (souvent 30 à 45 points d'exactitude équilibrée, voir Q4) domine toute différence de quelques points entre réglages, et les écarts de moins de 3 points entre classifieurs ou entre Nmax ne doivent pas être sur-interprétés.
- **La définition (a) mélange des anomalies que la seule forme du QRS ne peut pas voir** : les extrasystoles auriculaires (A, très nombreuses chez 232) ont un QRS normal et se reconnaissent surtout à leur prématurité (intervalle RR). La chaîne, qui normalise chaque fenêtre et jette le rythme, ne peut pas les détecter. La littérature inter-patients ajoute les intervalles RR pour cette raison. La faible sensibilité de (a) (48,8 % pour le SVM) en vient en partie.
- **Les blocs de branche sont « normaux » en (b)** (convention AAMI) : chez 111, 214, 212 et 232, une partie des fausses alarmes vient de battements L ou R pris pour des V. Ce n'est pas faux au sens de l'AAMI, mais cela pèse sur la spécificité.
- **Sensibilité par patient** : beaucoup de patients de DS2 n'ont que 0 à 3 battements positifs, et leurs pourcentages (0 % ou 100 %) ne mesurent presque rien. L'étendue « 0 % à 100 % » est donc en partie un effet de petits nombres. Les patients à plusieurs centaines de positifs (200, 210, 213, 214, 221, 228, 233) sont les plus parlants.
- **Comparaison à la littérature** : aucune n'est faite ici. Les chiffres publiés sur DS1/DS2 utilisent d'autres caractéristiques (RR notamment) et souvent les cinq classes AAMI, ils ne sont pas directement comparables.


## Reproductibilité

`uv run python scripts/etude.py` rejoue tout. python 3.12.13, plateforme macOS-15.7.5-arm64-arm-64bit, numpy 2.5.3, scipy 1.18.1, scikit-learn 1.9.1, wfdb 4.3.1. Graines : Q1-Q2 0 à 19, Q3-Q5 0. Durée : 45 min.
