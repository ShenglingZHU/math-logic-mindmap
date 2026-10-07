# Math Logic Mindmap

[English](../README.md) · [Français](README.fr.md) · [中文](README.zh-CN.md)

**Partir de ce que l’on sait, comprendre pourquoi chaque étape a lieu et laisser la logique mener à la conclusion.**

## 1. Présentation du projet

Math Logic Mindmap est un projet dans lequel des outils d’IA comme Codex et Claude Code **décomposent la logique** d’une démonstration ou d’une solution et créent une **carte du cheminement logique de la preuve**. Guidé par les règles du projet, l’assistant élabore d’abord l’argument mathématique et le vérifie lui-même, identifie ensuite ses dépendances, puis génère un Obsidian Canvas et des notes Markdown liées. La lecture prévue se fait dans Obsidian avec Advanced Canvas.

## 2. Démarrage rapide

### ① Ouvrir un exemple existant

1. Téléchargez le [dépôt complet](https://github.com/ShenglingZHU/math-logic-mindmap) avec **Code → Download ZIP**, ou l’archive **Source code** d’une Release pour une version publiée. Conservez les dossiers cachés à l’extraction. Git n’est pas nécessaire ; un paquet Python wheel ne remplace pas le coffre complet et ses exemples.
2. Avant d’ouvrir le coffre, téléchargez `main.js`, `manifest.json` et `styles.css` depuis la [Release Advanced Canvas 7.0.0](https://github.com/Developer-Mike/obsidian-advanced-canvas/releases/tag/7.0.0). Placez ces trois fichiers directement dans `.obsidian/plugins/advanced-canvas/`, en conservant le `data.json` fourni. Advanced Canvas s’installe séparément ; son programme n’est pas distribué ici.
3. Ouvrez **la racine du projet comme coffre** dans Obsidian sur ordinateur. Si une demande de confiance apparaît, autorisez les extensions communautaires seulement si vous faites confiance au projet et au code des extensions ; sinon, activez-les dans **Paramètres → Extensions communautaires**. Elles disposent des permissions locales d’Obsidian ; examinez le code local de Proof Routing avant de l’activer.
4. Vérifiez que le module de base Canvas, **Advanced Canvas 7.0.0**, **Proof Routing 0.6.1** et l’extrait **Apparence → Extraits CSS → math-logic-mindmap** sont activés. Les réglages fournis sélectionnent déjà ces deux extensions et l’extrait ; activez-les si nécessaire. Ouvrez [la carte AM–GM](../mindmap/two-variable-am-gm.canvas), puis le lien de détail d’un nœud.

Lire les exemples ne nécessite **ni Python ni assistant IA**. L’aperçu GitHub ne remplace pas un lecteur Canvas. Pour reproduire l’environnement vérifié, conservez Advanced Canvas 7.0.0 ; une installation depuis le catalogue communautaire ou une mise à jour peut sélectionner une version plus récente non examinée. D’autres lecteurs permettent une lecture élémentaire sans toutes les formes ni les ponts de lignes. Consultez la [configuration d’Obsidian](obsidian-setup.md) pour les réglages détaillés.

### ② Préparer l’environnement de génération

Installez **Python 3.11 ou plus récent**, puis exécutez ces commandes depuis la racine du projet. L’installation fournit `jsonschema>=4.18,<5` ; aucune activation de l’environnement virtuel n’est nécessaire.

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe skills/math-logic-mindmap/scripts/canvas_tool.py --help
```

Si `python` renvoie vers un alias Microsoft Store inutilisable, créez l’environnement avec un `py -3.11` installé ou le chemin réel de votre exécutable Python.

**macOS / Linux**

```sh
python3 -m venv .venv
./.venv/bin/python -m pip install -e .
./.venv/bin/python skills/math-logic-mindmap/scripts/canvas_tool.py --help
```

### ③ Demander une nouvelle carte

Ouvrez ce dossier dans Codex, Claude Code ou un assistant capable de lire et écrire des fichiers locaux et d’exécuter des commandes. S’il ne charge pas `AGENTS.md` ou `CLAUDE.md`, demandez-lui de lire [le Skill du projet](../skills/math-logic-mindmap/SKILL.md). Avant la génération, réglez `language` dans [la configuration](../math-logic-mindmap.config.json) sur `fr`, `en` ou `zh-CN` ; le fichier fourni utilise `en`. Le champ `presentation.language` du nouveau modèle et les textes rédigés doivent correspondre à ce choix. Changer la configuration ne traduit pas les cartes existantes.

> Démontre que, pour tout entier strictement positif n, la somme des n premiers entiers impairs positifs vaut n², puis génère une carte du raisonnement. Utilise le Skill math-logic-mindmap de ce projet et la langue configurée ; élabore indépendamment l’argument, puis termine la validation, la construction et la publication.

Examinez le plan de l’assistant avant la génération. Le modèle formel est `proof/<slug>/<slug>.proof.json`, la carte est `mindmap/<slug>.canvas` et les notes sont dans `note/<slug>/`. Pour votre propre problème, précisez l’énoncé, les hypothèses, la méthode souhaitée et le niveau du lecteur. La [maintenance](maintenance.md) décrit les commandes manuelles et les mises à niveau.

## 3. Motivation

Le projet prend la logique comme **premier principe** de l’apprentissage d’une preuve. À partir des hypothèses, des définitions et des outils mathématiques externes, des déductions et transformations orientées vers un but font converger naturellement les différentes voies vers l’énoncé à démontrer. Le lecteur peut suivre ce que chaque étape établit et pourquoi elle devient utile à ce moment-là.

## 4. Ce qui distingue le projet

**La question centrale est de savoir comment le « connu » d’une preuve chemine vers la « conclusion » au fil d’inférences orientées vers un but.** Beaucoup de cartes mentales rangent le texte par thèmes et niveaux. Leur structure ressemble parfois à une table des matières : elle indique de quoi parle un passage, mais montre plus rarement comment les conditions précédentes produisent une conclusion ou pourquoi cette étape est choisie maintenant. Le projet tente de présenter à la fois le flux logique et la motivation du raisonnement.

Hypothèses, définitions et théorèmes externes constituent des points de départ possibles. Résultats intermédiaires, transformations, distinctions de cas, constructions et véritables réunions de conditions font progresser la preuve. Chaque connexion permet de suivre une dépendance logique ; les dérivations et les notes de relation expliquent sa justification, tandis que les étapes générales et les notes des opérations éclairent aussi la direction choisie. Un objet auxiliaire peut préparer l’emploi d’un théorème, une reformulation peut rendre la cible plus familière, et plusieurs résultats intermédiaires peuvent se rejoindre pour fournir toutes les conditions nécessaires. Ces motivations rapprochent la carte de l’orientation réelle du raisonnement, au-delà d’une liste d’étapes dressée après coup. Le but est de comprendre comment le connu devient la conclusion et pourquoi la preuve suit cette voie.

## 5. Exemples

Les exemples fournis et la capture sont en anglais. Ouvrez-les dans Obsidian ; l’aperçu du dépôt ne remplace pas un lecteur Canvas.

### Inégalité arithmético-géométrique à deux variables

Ouvrez [la carte d’exemple](../mindmap/two-variable-am-gm.canvas) et [ses notes](../note/two-variable-am-gm/index.md) pour la preuve complète.

![Carte en anglais de la preuve de l’inégalité arithmético-géométrique](two-variable-am-gm.png)

Suivez le graphe de haut en bas : `K1` (positivité des carrés) et `A1` (entrées non négatives) se rejoignent en `C1`, qui produit le résultat indépendant `R1` : $(a+b)^2\ge 4ab$. Puis `R1`, `A1` et `K2` (croissance de la racine carrée) se rejoignent en `C2` et mènent à `T1`, la cible. Voilà pourquoi une opération `COMBINE` est suivie d’une carte de résultat distincte. Cet exemple précis ne comporte pas de carte `TRANSFORM` ; ailleurs, cette opération apparaît comme un triangle pointant vers le bas lorsque l’extrait CSS du projet est activé.

### Irrationalité de √2

Ouvrez [la carte de preuve par l’absurde](../mindmap/sqrt-2-irrationality.canvas) et [ses notes](../note/sqrt-2-irrationality/index.md). Cet exemple montre une hypothèse provisoire, des témoins locaux, une contradiction et la fermeture des portées correspondantes avant d’atteindre la cible.

Dans Canvas sur ordinateur, utilisez **Ctrl + molette** pour zoomer (**Cmd + molette** sur macOS) et **Maj + molette** pour défiler horizontalement ; les réglages de la molette peuvent modifier ce comportement.

## 6. Guide des nœuds

Les noms de type restent des identifiants anglais dans les trois versions. Une preuve stricte peut commencer par `ASSUMPTION`, `DEFINITION`, `KNOWN_RESULT` ou une `HYPOTHESIS_LOCAL` ouvrant une portée ; cette dernière doit être levée avant la cible. Toute dépendance stricte suit un flux visible vers une unique `TARGET`.

| Type | Rôle dans la preuve |
| --- | --- |
| `ASSUMPTION` | Une condition donnée, par exemple une restriction de domaine, de signe ou d’intervalle. |
| `DEFINITION` | Une définition ou une notation utilisée dans une inférence ultérieure. |
| `KNOWN_RESULT` | Un théorème, lemme ou principe externe effectivement utilisé. |
| `CONSTRUCTION` | Un objet auxiliaire construit volontairement pour l’argument. |
| `CASE` | Une opération circulaire qui sépare visiblement les cas, réunis plus tard par `COMBINE`. |
| `LOCAL_INTRODUCTION` | Une valeur arbitraire, un témoin ou d’autres données fixées dans une portée locale. |
| `HYPOTHESIS_LOCAL` | Une hypothèse provisoire, par exemple pour une preuve par l’absurde ou par récurrence. |
| `DERIVATION` | Une inférence locale substantielle qui fait avancer l’argument. |
| `LEMMA` | Une proposition intermédiaire utile, démontrée dans cette preuve. |
| `COMBINE` | Un cercle où se réunissent les données indépendantes nécessaires ; sa conclusion figure dans une carte de résultat ou de cible distincte. |
| `TRANSFORM` | Un triangle pointant vers le bas pour une opération justifiée à une entrée, telle qu’une substitution ou une simplification ; les conditions indépendantes doivent d’abord être réunies. |
| `CONTRADICTION` | Une incohérence explicite employée dans une preuve indirecte. |
| `BOUND` | Une borne supérieure ou inférieure établie. |
| `EXISTENCE_WITNESS` | Un objet construit avec la vérification de la propriété demandée. |
| `TARGET` | L’énoncé que la preuve cherche à établir. |
| `INTUITION` | Une explication utile, hors de la preuve stricte ; elle ne justifie aucune étape de preuve. |

Les six rôles de couleur configurables sont **external**, **combine**, **transform**, **result**, **target** et **given**. Ils ne correspondent pas un à un aux 16 types : `KNOWN_RESULT` ou tout nœud marqué `external: true` prend external ; `COMBINE` et `CASE` prennent combine ; `TRANSFORM` prend transform ; `TARGET` prend target avant result ; tout nœud `result: true` prend result ; les nœuds stricts `ASSUMPTION` et `LOCAL_INTRODUCTION` prennent given. Les autres nœuds, dont `DEFINITION` par défaut, n’ont pas de couleur de rôle. `INTUITION` a un fond transparent ou par défaut et une bordure grise en pointillés. La couleur aide à lire, sans garantir la validité de la preuve.

## 7. Personnalisation

Modifiez [`math-logic-mindmap.config.json`](../math-logic-mindmap.config.json) avant une nouvelle construction. Cet exemple montre toutes les clés disponibles ; choisissez vos propres couleurs hexadécimales à six chiffres :

```json
{
  "language": "fr",
  "node_colors": {
    "external": "#B39DDB",
    "combine": "#E5C85B",
    "transform": "#D9DEE7",
    "result": "#CFE8CC",
    "target": "#E69A9A",
    "given": "#88BBDD"
  }
}
```

Sans fichier de configuration, la langue chinoise et la palette d’origine sont utilisées. La langue et les couleurs sont fixées lors de la construction ; modifier le fichier global ne change pas les cartes déjà publiées. La partie « ajouts personnels » des notes Markdown est conservée lors d’une nouvelle génération. [Maintenance et récupération](maintenance.md) explique comment conserver une disposition modifiée à la main.

## 8. Garder un regard critique

Un LLM peut commettre des erreurs mathématiques ou fournir des explications irrégulières. Sur une carte générée en français, « Démontré (conclusion mathématique) » exprime la conclusion mathématique rédigée dans le modèle ; les vérifications automatiques contrôlent la structure et la cohérence des fichiers, **pas la vérité mathématique**. La capture d’exemple, en anglais, affiche la mention anglaise. L’examen visuel est distinct et commence à `UNREVIEWED`.

Pour un travail difficile, utilisez le mode Plan de l’assistant pour examiner la stratégie, les hypothèses et outils de départ, toutes les conditions d’application et un découpage des nœuds adapté à votre niveau. Intervenez à ce stade si la carte prévue est trop sommaire ou trop détaillée : cela peut éviter de dépenser des tokens pour une carte peu utile à votre apprentissage. Ensuite, ouvrez les détails des nœuds et les notes des relations explicatives et vérifiez la chaîne de déduction étape par étape. Une vérification humaine ou par un autre modèle peut aider ; plusieurs essais peuvent être nécessaires.

La capacité d’un langage graphique stable, composable et lisible par l’humain à exprimer des raisonnements mathématiques complexes reste une question ouverte. La représentation formelle des preuves par machine est déjà assez mûre. Il reste à savoir si des règles d’abstraction répétables et vérifiables peuvent transformer une preuve rigoureuse en graphe délimité et lisible sans dépendre surtout de l’intuition et du jugement esthétique de sa conception. Une approche centrée sur l’humain introduit aussi la diversité des lecteurs : les limites d’expression et le niveau de détail de la carte ne correspondent pas forcément aux connaissances de chacun, et plusieurs essais peuvent être nécessaires.

## 9. Vision

Nous espérons que les lecteurs partageront leurs cartes et qu’une future communauté pourra évaluer à la fois leur exactitude et leur lisibilité pour aider davantage de personnes à apprendre les preuves. Le projet ne fournit pas encore de plateforme de partage ou d’évaluation.

## 10. Pistes futures

Cette approche pourrait un jour servir à visualiser d’autres problèmes ayant une structure logique, comme les algorithmes, les protocoles expérimentaux ou l’analyse d’articles. Actuellement, le projet et son Skill servent aux preuves mathématiques et aux solutions de problèmes.

## Signaler un problème

Utilisez [GitHub Issues](https://github.com/ShenglingZHU/math-logic-mindmap/issues), disponible lorsque le dépôt sera public et les Issues activées. Joignez :

- La version du projet ou la Release/le tag ; à défaut, la source et la date du téléchargement.
- Le système d’exploitation et les versions concernées de Python, Obsidian, Advanced Canvas et Proof Routing.
- Les étapes de reproduction, les résultats attendu et obtenu, ainsi que les erreurs pertinentes.
- Un exemple minimal : l’entrée ou le modèle pour un problème de génération ; le Canvas, les notes et la capture nécessaires pour un problème d’affichage.

Exécutez `--version` sur l’outil avec le même interpréteur que ci-dessus ; la version d’Obsidian figure dans **Paramètres → À propos**, celles des extensions dans la liste des extensions communautaires. Pour un problème d’installation, utilisez aussi cet interpréteur avec `-m pip show math-logic-mindmap`.

Ne transmettez pas votre coffre personnel entier. Vérifiez les notes, captures et journaux et masquez les informations privées sans rapport avec le problème ; les noms d’utilisateur dans les chemins peuvent être anonymisés en conservant la structure utile à la reproduction.

## Maintenance et licence

Pour l’importation d’une disposition, les examens, les aperçus exportés, la synchronisation de l’extension, les sauvegardes, la suppression et la récupération, consultez [Maintenance and Recovery](maintenance.md). Le projet est publié sous [licence MIT](../LICENSE) par ZHU Shengling ; les logiciels externes et les dépendances sont décrits dans [Third-Party Notices](../THIRD_PARTY_NOTICES.md).
