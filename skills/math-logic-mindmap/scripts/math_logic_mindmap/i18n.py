from __future__ import annotations

from .common import Invalid
from .config import normalize_config

CATALOGS = {
    "zh-CN": {
        "symbol_headers": ["符号", "数学定义或角色", "取值范围 / 单位", "实际含义 / 物理解释（如适用）"],
        "status": {"proved": "已证明（数学结论）", "refuted": "原命题不成立", "needs_assumption": "缺少假设", "partial": "尚未完成"},
        "context": {"领域": "领域", "背景": "背景", "角色 / 重要性": "角色 / 重要性", "作用": "作用", "证明思路/策略": "证明思路/策略", "证明工具": "证明工具"},
        "navigation": "导航", "input_review": "输入回顾", "combine_motivation": "合并动机与意义",
        "combine_method": "合并思路与工具", "detailed_derivation": "详细推导", "combine_result": "合并结果",
        "transform_motivation": "变换动机与意义", "transform_method": "变换方法", "transform_result": "变换结果",
        "conditions": "适用条件与核验", "incoming": "传入关系", "outgoing": "传出关系", "personal": "个人补充",
        "continuous_chain": "连续主链", "step_notes": "步骤说明", "input_formula": "输入公式",
        "input_node": "输入节点", "content_formula": "内容与公式", "current_use": "本次用途",
        "complete_below": "完整公式见下方", "formal_output": "正式输出记号：", "combined_to": "合并后交给 {target}：",
        "global_scope": "全局", "nonproof": "非证明说明", "final_target": "最终目标", "proof_start": "证明起点", "intermediate": "中间步骤",
        "stage": "阶段", "role": "角色与作用", "motivation": "动机", "position": "位置", "scope": "作用域",
        "direct_predecessors": "直接前驱", "direct_successors": "直接后继", "no_predecessor": "无（题设、定义或已知依据）",
        "no_successor": "无（本支线在此结束）", "input_contribution": "输入贡献", "target_gain": "目标所得",
        "input_effect": "本输入的作用", "result_handoff": "结果交接", "merge": "汇合", "details": "详情", "in": "传入", "out": "传出",
        "type": "类型", "locate_node": "定位原节点（Advanced Canvas）", "open_map": "打开整个导图", "overview": "概览",
        "scope_warning": "作用域：`{scope}`。", "case_analysis": "分类说明", "case_condition": "本分支条件", "case_closure_line": "- {branch}：解除情况条件 {discharges}；推广符号 {generalizes}。", "bound_symbols": "引入或构造的符号", "discharge_rule": "作用域关闭规则", "generalized_symbols": "推广的符号", "existential_symbols": "存在引入的符号", "quantifier_dependencies": "结构量词依赖", "condition_line": "- 条件：{condition}；核验：{check}",
        "start_basis": "本节点提供证明起点的条件或依据。", "branch_end": "本支线到此结束；本节点陈述所得结论或说明。",
        "source": "起点", "target": "终点", "relation": "关系", "source_contribution_heading": "起点贡献",
        "transition_steps": "转换步骤", "condition_checks": "条件核验", "no_new_conditions": "无新增条件；沿用起点的已验证作用域。",
        "target_new": "终点新增内容", "global_role": "全局作用", "discharged": "解除局部假设：",
        "open_proof_map": "打开证明导图", "math_status": "数学状态", "proof_standard": "证明标准",
        "visual_notice": "视觉状态请以 {review} 及当前文件版本核验结果为准；生成不等于实际浏览通过。",
        "review_record": "验收记录", "theorem_content": "定理内容", "assumptions": "前提条件", "counterexample": "反例",
        "missing_assumptions": "缺失条件", "open_obligations": "未完成义务", "global_symbols": "全局符号", "proof_flow": "证明流程",
        "node_index": "节点索引", "edge_index": "解释边索引", "content_definitions": "内容 / 基本定义", "overview_background": "概览与背景",
        "review_title": "Obsidian 验收", "visual_state": "视觉状态", "review_intro": "基本机器检查通过后即可发布；本页用于记录后续视觉反馈，不构成发布门禁。",
        "route_convention": "路径约定", "route_text": "同列使用竖线，异列使用向下—横向—向下的两折正交线。清晰交叉是允许的；启用 Proof Routing 时，横段以圆弧桥跨过竖段，密集交点合并成长桥，不为消除交叉制造远距离走廊。",
        "environment_record": "环境与记录", "environment_text": "用 review-template 生成绑定当前文件的证据模板，记录 Obsidian、Advanced Canvas、主题、检查人及逐项证据；未经实际检查的项目保留 UNKNOWN。",
        "reviewer": "已记录检查人", "environment": "环境",
        "list_separator": "、", "stage_anchor": "阶段 {id} · {title}", "complete_reference": "（{link}）",
        "nav_stage": "阶段：{link}。{summary}", "nav_role": "角色与作用：{value}", "nav_motivation": "动机：{value}",
        "nav_position": "位置：{identity}；作用域：{scope}。", "nav_neighbors": "直接前驱：{incoming}；直接后继：{outgoing}。",
        "labeled_value": "{label}：{value}", "clause_separator": "；", "sentence_end": "。",
    },
    "en": {
        "symbol_headers": ["Symbol", "Mathematical definition or role", "Range / unit", "Meaning / interpretation (if applicable)"],
        "status": {"proved": "Proved (mathematical conclusion)", "refuted": "Original statement is false", "needs_assumption": "Missing assumptions", "partial": "Incomplete"},
        "context": {"领域": "Field", "背景": "Background", "角色 / 重要性": "Role / importance", "作用": "Purpose", "证明思路/策略": "Proof approach / strategy", "证明工具": "Proof tools"},
        "navigation": "Navigation", "input_review": "Input review", "combine_motivation": "Motivation for combining",
        "combine_method": "Combination method and tools", "detailed_derivation": "Detailed derivation", "combine_result": "Combined result",
        "transform_motivation": "Motivation for transformation", "transform_method": "Transformation method", "transform_result": "Transformation result",
        "conditions": "Conditions and verification", "incoming": "Incoming relations", "outgoing": "Outgoing relations", "personal": "Personal notes",
        "continuous_chain": "Continuous derivation", "step_notes": "Step notes", "input_formula": "Input formula",
        "input_node": "Input node", "content_formula": "Content and formula", "current_use": "Use here",
        "complete_below": "full formula below", "formal_output": "Formal output notation: ", "combined_to": "Passed after combination to {target}: ",
        "global_scope": "Global", "nonproof": "Non-proof notes", "final_target": "Final target", "proof_start": "Proof start", "intermediate": "Intermediate step",
        "stage": "Stage", "role": "Role and purpose", "motivation": "Motivation", "position": "Position", "scope": "Scope",
        "direct_predecessors": "Direct predecessors", "direct_successors": "Direct successors", "no_predecessor": "None (assumption, definition, or known result)",
        "no_successor": "None (this branch ends here)", "input_contribution": "Input contribution", "target_gain": "Target gain",
        "input_effect": "Role of this input", "result_handoff": "Result handoff", "merge": "Merge", "details": "Details", "in": "Incoming", "out": "Outgoing",
        "type": "Type", "locate_node": "Locate original node (Advanced Canvas)", "open_map": "Open full map", "overview": "Overview",
        "scope_warning": "Scope: `{scope}`.", "case_analysis": "Case analysis", "case_condition": "Branch condition", "case_closure_line": "- {branch}: discharged case condition {discharges}; generalized symbols {generalizes}.", "bound_symbols": "Introduced or constructed symbols", "discharge_rule": "Scope closing rule", "generalized_symbols": "Generalized symbols", "existential_symbols": "Existentially introduced symbols", "quantifier_dependencies": "Structural quantifier dependencies", "condition_line": "- Condition: {condition}; check: {check}",
        "start_basis": "This node supplies a starting condition or known basis.", "branch_end": "This branch ends here; the node states its result or note.",
        "source": "Source", "target": "Target", "relation": "Relation", "source_contribution_heading": "Source contribution",
        "transition_steps": "Transition steps", "condition_checks": "Condition checks", "no_new_conditions": "No new conditions; the verified scope of the source is retained.",
        "target_new": "New content at target", "global_role": "Role in the proof", "discharged": "Discharged local assumptions: ",
        "open_proof_map": "Open proof map", "math_status": "Mathematical status", "proof_standard": "Proof standard",
        "visual_notice": "See {review} and its artifact version for visual status; generation is not evidence of a successful visual review.",
        "review_record": "Review record", "theorem_content": "Theorem statement", "assumptions": "Assumptions", "counterexample": "Counterexample",
        "missing_assumptions": "Missing assumptions", "open_obligations": "Open obligations", "global_symbols": "Global symbols", "proof_flow": "Proof flow",
        "node_index": "Node index", "edge_index": "Explanatory edge index", "content_definitions": "Statement / basic definitions", "overview_background": "Overview and background",
        "review_title": "Obsidian review", "visual_state": "Visual status", "review_intro": "A bundle may be released after basic machine checks; this page records later visual feedback and is not a release gate.",
        "route_convention": "Routing convention", "route_text": "Nodes in one column use vertical edges; other edges go down, across, then down. Clear crossings are allowed; with Proof Routing enabled, horizontal segments bridge over vertical ones and dense crossings merge into one longer bridge, without adding distant corridors merely to remove crossings.",
        "environment_record": "Environment and record", "environment_text": "Use review-template to create evidence bound to the current files, then record Obsidian, Advanced Canvas, theme, reviewer, and evidence for every check. Unobserved checks remain UNKNOWN.",
        "reviewer": "Recorded reviewer", "environment": "Environment",
        "list_separator": ", ", "stage_anchor": "Stage {id} · {title}", "complete_reference": "({link})",
        "nav_stage": "Stage: {link}. {summary}", "nav_role": "Role and purpose: {value}", "nav_motivation": "Motivation: {value}",
        "nav_position": "Position: {identity}; scope: {scope}.", "nav_neighbors": "Direct predecessors: {incoming}; direct successors: {outgoing}.",
        "labeled_value": "{label}: {value}", "clause_separator": "; ", "sentence_end": ".",
    },
    "fr": {
        "symbol_headers": ["Symbole", "Définition ou rôle mathématique", "Domaine / unité", "Signification / interprétation (si applicable)"],
        "status": {"proved": "Démontré (conclusion mathématique)", "refuted": "L'énoncé initial est faux", "needs_assumption": "Hypothèses manquantes", "partial": "Incomplet"},
        "context": {"领域": "Domaine", "背景": "Contexte", "角色 / 重要性": "Rôle / importance", "作用": "Objectif", "证明思路/策略": "Approche / stratégie de preuve", "证明工具": "Outils de preuve"},
        "navigation": "Navigation", "input_review": "Rappel des entrées", "combine_motivation": "Motivation de la combinaison",
        "combine_method": "Méthode et outils de combinaison", "detailed_derivation": "Dérivation détaillée", "combine_result": "Résultat combiné",
        "transform_motivation": "Motivation de la transformation", "transform_method": "Méthode de transformation", "transform_result": "Résultat de la transformation",
        "conditions": "Conditions et vérification", "incoming": "Relations entrantes", "outgoing": "Relations sortantes", "personal": "Notes personnelles",
        "continuous_chain": "Dérivation continue", "step_notes": "Notes sur les étapes", "input_formula": "Formule d'entrée",
        "input_node": "Nœud d'entrée", "content_formula": "Contenu et formule", "current_use": "Usage ici",
        "complete_below": "formule complète ci-dessous", "formal_output": "Notation formelle de sortie : ", "combined_to": "Transmis après combinaison à {target} : ",
        "global_scope": "Global", "nonproof": "Notes hors preuve", "final_target": "Cible finale", "proof_start": "Début de la preuve", "intermediate": "Étape intermédiaire",
        "stage": "Étape", "role": "Rôle et objectif", "motivation": "Motivation", "position": "Position", "scope": "Portée",
        "direct_predecessors": "Prédécesseurs directs", "direct_successors": "Successeurs directs", "no_predecessor": "Aucun (hypothèse, définition ou résultat connu)",
        "no_successor": "Aucun (cette branche se termine ici)", "input_contribution": "Contribution de l'entrée", "target_gain": "Gain à la cible",
        "input_effect": "Rôle de cette entrée", "result_handoff": "Transmission du résultat", "merge": "Fusion", "details": "Détails", "in": "Entrées", "out": "Sorties",
        "type": "Type", "locate_node": "Localiser le nœud original (Advanced Canvas)", "open_map": "Ouvrir la carte complète", "overview": "Vue d'ensemble",
        "scope_warning": "Portée : `{scope}`.", "case_analysis": "Analyse des cas", "case_condition": "Condition de branche", "case_closure_line": "- {branch} : condition de cas levée {discharges} ; symboles généralisés {generalizes}.", "bound_symbols": "Symboles introduits ou construits", "discharge_rule": "Règle de fermeture", "generalized_symbols": "Symboles généralisés", "existential_symbols": "Symboles introduits existentiellement", "quantifier_dependencies": "Dépendances structurelles des quantificateurs", "condition_line": "- Condition : {condition} ; vérification : {check}",
        "start_basis": "Ce nœud fournit une condition initiale ou un résultat connu.", "branch_end": "Cette branche se termine ici ; le nœud énonce son résultat ou sa remarque.",
        "source": "Source", "target": "Cible", "relation": "Relation", "source_contribution_heading": "Contribution de la source",
        "transition_steps": "Étapes de transition", "condition_checks": "Vérification des conditions", "no_new_conditions": "Aucune nouvelle condition ; la portée vérifiée de la source est conservée.",
        "target_new": "Nouveau contenu à la cible", "global_role": "Rôle dans la preuve", "discharged": "Hypothèses locales levées : ",
        "open_proof_map": "Ouvrir la carte de preuve", "math_status": "Statut mathématique", "proof_standard": "Niveau de preuve",
        "visual_notice": "Consultez {review} et la version des fichiers pour le statut visuel ; la génération ne prouve pas la réussite de la revue visuelle.",
        "review_record": "Compte rendu de revue", "theorem_content": "Énoncé du théorème", "assumptions": "Hypothèses", "counterexample": "Contre-exemple",
        "missing_assumptions": "Hypothèses manquantes", "open_obligations": "Obligations ouvertes", "global_symbols": "Symboles globaux", "proof_flow": "Déroulement de la preuve",
        "node_index": "Index des nœuds", "edge_index": "Index des arêtes explicatives", "content_definitions": "Énoncé / définitions de base", "overview_background": "Vue d'ensemble et contexte",
        "review_title": "Revue Obsidian", "visual_state": "Statut visuel", "review_intro": "La publication est possible après les contrôles machine de base ; cette page consigne les retours visuels ultérieurs et ne bloque pas la publication.",
        "route_convention": "Convention de routage", "route_text": "Les nœuds d'une même colonne utilisent des traits verticaux ; les autres arêtes descendent, traversent puis redescendent. Les croisements lisibles sont permis ; avec Proof Routing, les segments horizontaux enjambent les segments verticaux et les croisements serrés fusionnent en un pont plus long, sans ajouter de couloir éloigné uniquement pour supprimer un croisement.",
        "environment_record": "Environnement et suivi", "environment_text": "Utilisez review-template pour créer une preuve liée aux fichiers courants, puis indiquez Obsidian, Advanced Canvas, le thème, la personne chargée de la revue et les éléments de chaque contrôle. Les contrôles non observés restent UNKNOWN.",
        "reviewer": "Personne ayant effectué la revue", "environment": "Environnement",
        "list_separator": ", ", "stage_anchor": "Étape {id} · {title}", "complete_reference": "({link})",
        "nav_stage": "Étape : {link}. {summary}", "nav_role": "Rôle et objectif : {value}", "nav_motivation": "Motivation : {value}",
        "nav_position": "Position : {identity} ; portée : {scope}.", "nav_neighbors": "Prédécesseurs directs : {incoming} ; successeurs directs : {outgoing}.",
        "labeled_value": "{label} : {value}", "clause_separator": " ; ", "sentence_end": ".",
    },
}

VISUAL_CHECKS_BY_LANGUAGE = {
    "zh-CN": {
        "reading_context": "导航阶段、相邻汇合的一层输入与输出完整可读，原有传入/传出和阶段链接可达。",
        "input_tables": "输入回顾表列完整、链接正常；长公式在表下就地展示，无截断或横向滚动。",
        "derivation_bases": "连续主链中每次依据引入均有长向下箭头与右侧方框；来源编号正确，关系符正确，主链符号表统一在链后。",
        "chain_geometry": "长箭头与主链关系符对齐，高度适应多行依据框且上下留白充足；公式、框、名称无碰撞或截断。",
        "mathjax": "所有卡片与笔记数学、所选输出语言文字、boxed、Bigg downarrow、四列表格均正确渲染，无原始 TeX 或错误。",
        "containment": "每个普通卡片、圆形 COMBINE 和三角形 TRANSFORM 的 ID、正文和详情链接完整；无截断、内部滚动或溢出。",
        "headers": "普通卡片头部 ID 左、类型右；COMBINE 与 TRANSFORM 的固定短文本和 ID 顺序正确。",
        "links": "每个节点详情及两端解释边可达，定位原节点与整图回退有效。",
        "routing": "逐边检查：向下、没有穿过无关卡片；同侧箭头可追踪；无误导性合流或共享干线；普通正交交叉处横段跨线圆弧清晰且标签不遮挡。",
        "labels": "每个解释边一个标签、结构边无标签；标签归属明确，不覆盖卡片或其他边。",
        "scopes": "嵌套局部作用域分组和 CASE/COMBINE 配对正确，非证明说明不被误认为严格前提。",
        "themes": "Obsidian 默认明暗主题可读；TRANSFORM 和结果节点颜色、边框正确；停用 snippet 时仍可读；符号表无横向滚动。",
        "zoom": "100%、200%、400% 缩放时公式与所选输出语言文字清晰；平移和缩放不破坏导航。",
    },
    "en": {
        "reading_context": "Navigation stages and one-level neighbouring combination inputs and outputs are readable; incoming, outgoing, and stage links work.",
        "input_tables": "Input-review columns and links work; long formulas appear below the table without clipping or horizontal scrolling.",
        "derivation_bases": "Every applied basis in the continuous derivation has a long down arrow and a right-hand box; source IDs and relation symbols are correct; one symbol table follows the chain.",
        "chain_geometry": "Long arrows align with relation symbols and accommodate multiline basis boxes; formulas, boxes, and names do not collide or clip.",
        "mathjax": "Mathematics, selected-language text, boxed, Bigg downarrow, and four-column tables render correctly with no raw TeX or errors.",
        "containment": "Regular cards, circular COMBINE cards, and triangular TRANSFORM cards show complete IDs, content, and detail links without clipping, scrolling, or overflow.",
        "headers": "Regular cards place ID left and type right; fixed COMBINE and TRANSFORM text and IDs are ordered correctly.",
        "links": "Node details and explanatory edges are reachable from both ends; node-location and full-map fallbacks work.",
        "routing": "Each edge travels downward without crossing unrelated cards; same-side arrows are traceable and do not imply false merging or shared trunks; horizontal bridges at ordinary orthogonal crossings are clear and unobscured by labels.",
        "labels": "Every explanatory edge has one label and structural edges have none; labels are attributable and cover no card or edge.",
        "scopes": "Nested local-scope groups and CASE/COMBINE pairs are correct; non-proof notes do not look like strict premises.",
        "themes": "Default light and dark themes remain readable; TRANSFORM and result colors and borders are correct; disabled snippets degrade readably; symbol tables do not scroll horizontally.",
        "zoom": "At 100%, 200%, and 400%, formulas and selected-language text are clear; pan and zoom preserve navigation.",
    },
    "fr": {
        "reading_context": "Les étapes de navigation et le rappel direct des entrées et sorties voisines sont lisibles ; les liens entrants, sortants et d'étape fonctionnent.",
        "input_tables": "Les colonnes et liens du rappel des entrées fonctionnent ; les formules longues apparaissent sous le tableau sans coupure ni défilement horizontal.",
        "derivation_bases": "Chaque justification de la dérivation continue possède une longue flèche descendante et un cadre à droite ; les identifiants source et les relations sont corrects ; un tableau de symboles suit la chaîne.",
        "chain_geometry": "Les longues flèches sont alignées avec les relations et s'adaptent aux cadres multilignes ; formules, cadres et noms ne se chevauchent pas.",
        "mathjax": "Les mathématiques, le texte dans la langue choisie, boxed, Bigg downarrow et les tableaux à quatre colonnes s'affichent sans TeX brut ni erreur.",
        "containment": "Les cartes ordinaires, COMBINE circulaires et TRANSFORM triangulaires affichent entièrement leurs identifiants, contenus et liens sans coupure ni débordement.",
        "headers": "Les cartes ordinaires placent l'identifiant à gauche et le type à droite ; l'ordre des textes fixes et identifiants COMBINE et TRANSFORM est correct.",
        "links": "Les détails des nœuds et les arêtes explicatives sont accessibles des deux côtés ; la localisation et le retour à la carte complète fonctionnent.",
        "routing": "Chaque arête descend sans traverser de carte étrangère ; les flèches d'un même côté sont traçables et ne suggèrent aucune fusion ou ligne commune erronée ; les ponts horizontaux aux croisements orthogonaux restent nets et visibles malgré les étiquettes.",
        "labels": "Chaque arête explicative a une étiquette et les arêtes structurelles n'en ont pas ; aucune étiquette ne masque une carte ou une autre arête.",
        "scopes": "Les groupes de portées locales imbriquées et les paires CASE/COMBINE sont corrects ; les notes hors preuve ne ressemblent pas à des prémisses strictes.",
        "themes": "Les thèmes clair et sombre par défaut restent lisibles ; couleurs et bordures de TRANSFORM et des résultats sont correctes ; sans snippet, le contenu reste lisible ; les tableaux ne défilent pas horizontalement.",
        "zoom": "À 100 %, 200 % et 400 %, les formules et le texte dans la langue choisie sont nets ; déplacement et zoom préservent la navigation.",
    },
}

RESERVED_KEYS = {
    "navigation", "input_review", "combine_motivation", "combine_method", "detailed_derivation",
    "combine_result", "transform_motivation", "transform_method", "transform_result", "conditions",
    "incoming", "outgoing", "personal", "case_analysis", "case_condition", "bound_symbols",
    "quantifier_dependencies",
}


def _validate_catalogs():
    baseline = set(CATALOGS["zh-CN"])
    for language, catalog in CATALOGS.items():
        if set(catalog) != baseline:
            raise RuntimeError(f"I18N {language}: catalog keys are incomplete")
        headings = [catalog[key] for key in RESERVED_KEYS]
        if len(headings) != len(set(headings)):
            raise RuntimeError(f"I18N {language}: reserved headings are duplicated")
        anchors = headings + [catalog["input_formula"]]
        if any(any(char in value for char in "\n#|[]") for value in anchors):
            raise RuntimeError(f"I18N {language}: a heading contains unsafe characters")
        if len(catalog["merge"]) > 12 or len(catalog["details"]) > 12:
            raise RuntimeError(f"I18N {language}: an operation-card label is too long")


_validate_catalogs()


def catalog(config=None):
    return CATALOGS[normalize_config(config)["language"]]


def text(config, key, **values):
    value = catalog(config).get(key)
    if not isinstance(value, str):
        raise Invalid(f"I18N: unknown text key {key}")
    return value.format(**values)


def reserved_headings():
    return {catalog[key] for catalog in CATALOGS.values() for key in RESERVED_KEYS}


def reserved_prefixes():
    return tuple(catalog["input_formula"] + " " for catalog in CATALOGS.values())


def visual_checks(config=None):
    return VISUAL_CHECKS_BY_LANGUAGE[normalize_config(config)["language"]]
