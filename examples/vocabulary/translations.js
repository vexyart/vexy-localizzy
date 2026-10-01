// this_file: examples/vocabulary/translations.js
// Typography Localization Vocabulary Dictionary (EN, DE, FR, JA)
const vocabularyTranslations = {
  // Metadata & System Languages
  "languages.en": {
    "translation": "English",
    "context": "System language name"
  },
  "languages.de": {
    "translation": "Deutsch",
    "context": "System language name"
  },
  "languages.fr": {
    "translation": "Français",
    "context": "System language name"
  },
  "languages.ja": {
    "translation": "日本語",
    "context": "System language name"
  },

  // Menus & Actions
  "menu.file": {
    "en": "&File",
    "de": "&Datei",
    "fr": "&Fichier",
    "ja": "&ファイル",
    "context": "Main application menu header"
  },
  "menu.file.new": {
    "en": "&New Font...",
    "de": "&Neuer Schriftart...",
    "fr": "&Nouvelle police...",
    "ja": "&新規フォント...",
    "context": "File menu action to create a new font"
  },
  "menu.file.open": {
    "en": "&Open Font...",
    "de": "Schriftart &öffnen...",
    "fr": "&Ouvrir la police...",
    "ja": "フォントを開く(&O)...",
    "context": "File menu action to open an existing font file"
  },
  "menu.file.save": {
    "en": "&Save Font",
    "de": "Schriftart &speichern",
    "fr": "Enregi&strer la police",
    "ja": "フォントを保存(&S)",
    "context": "File menu action to save current font"
  },
  "menu.file.export": {
    "en": "&Export Font Masters...",
    "de": "Schrift-Master &exportieren...",
    "fr": "&Exporter les masters de police...",
    "ja": "フォントマスターを書き出し(&E)...",
    "context": "File menu action to export multiple masters"
  },
  "menu.edit": {
    "en": "&Edit",
    "de": "&Bearbeiten",
    "fr": "&Édition",
    "ja": "編集(&E)",
    "context": "Main application menu header"
  },
  "menu.edit.undo": {
    "en": "&Undo",
    "de": "&Rückgängig",
    "fr": "Ann&uler",
    "ja": "元に戻す(&U)",
    "context": "Standard edit undo action"
  },
  "menu.edit.redo": {
    "en": "&Redo",
    "de": "&Wiederholen",
    "fr": "&Rétablir",
    "ja": "やり直し(&R)",
    "context": "Standard edit redo action"
  },
  "menu.contour": {
    "en": "&Contour",
    "de": "&Kontur",
    "fr": "&Contour",
    "ja": "輪郭(&C)",
    "context": "Main menu for vector path manipulation"
  },
  "menu.contour.addNode": {
    "en": "Add &Node",
    "de": "&Knoten hinzufügen",
    "fr": "Ajouter un &nœud",
    "ja": "ノードを追加(&N)",
    "context": "Contour menu action to insert a vector node"
  },
  "menu.contour.removeNode": {
    "en": "&Delete Node",
    "de": "Knoten &löschen",
    "fr": "&Supprimer le nœud",
    "ja": "ノードを削除(&D)",
    "context": "Contour menu action to delete selected node"
  },
  "menu.contour.simplify": {
    "en": "&Simplify Path",
    "de": "Pfad &vereinfachen",
    "fr": "&Simplifier le tracé",
    "ja": "パスを単純化(&S)",
    "context": "Reduce the number of nodes in a path"
  },
  "menu.contour.makeCorner": {
    "en": "Make &Corner",
    "de": "Zu &Ecke machen",
    "fr": "Rendre &droit",
    "ja": "コーナーに変換(&C)",
    "context": "Convert curve node to corner node"
  },
  "menu.metrics": {
    "en": "&Metrics",
    "de": "&Metrik",
    "fr": "&Métriques",
    "ja": "メトリクス(&M)",
    "context": "Main menu for spacing and kerning options"
  },
  "menu.metrics.autoKern": {
    "en": "&Auto-Kern Pair",
    "de": "&Auto-Unterschneidung-Paar",
    "fr": "&Auto-crénage de paire",
    "ja": "ペアカーニングを自動調整(&A)",
    "context": "Metrics menu action to calculate kerning between two glyphs"
  },
  "menu.hinting": {
    "en": "&Hinting",
    "de": "&Hinting",
    "fr": "&Instructions (Hinting)",
    "ja": "ヒンティング(&H)",
    "context": "Main menu for screen rasterization grid-fitting instructions"
  },
  "menu.hinting.autoHint": {
    "en": "Generate Autohints",
    "de": "Autohints generieren",
    "fr": "Générer autohints",
    "ja": "自動ヒンティングを生成",
    "context": "Generate hints for all glyphs automatically"
  },
  "menu.varfont": {
    "en": "&Variable Font",
    "de": "&Variabler Schriftstil",
    "fr": "&Police variable",
    "ja": "バリアブルフォント(&V)",
    "context": "Main menu for variable font / designspace operations"
  },
  "menu.varfont.addInstance": {
    "en": "Add &Instance...",
    "de": "&Instanz hinzufügen...",
    "fr": "Ajouter une &instance...",
    "ja": "インスタンスを追加(&I)...",
    "context": "Variable font menu: create a named instance at current axis coordinates"
  },
  "menu.varfont.interpolatemasters": {
    "en": "I&nterpolate Masters",
    "de": "Master &interpolieren",
    "fr": "&Interpoler les masters",
    "ja": "マスターを補間(&N)",
    "context": "Variable font menu: run interpolation check across all masters"
  },
  "menu.encoding": {
    "en": "Encodi&ng",
    "de": "Ko&dierung",
    "fr": "&Encodage",
    "ja": "エンコーディング(&N)",
    "context": "Main menu for glyph encoding, Unicode, and cmap operations"
  },
  "menu.encoding.setUnicode": {
    "en": "Set &Unicode Value...",
    "de": "&Unicode-Wert setzen...",
    "fr": "Définir la valeur &Unicode...",
    "ja": "Unicode 値を設定(&U)...",
    "context": "Encoding menu: assign a Unicode codepoint to the selected glyph"
  },
  "menu.fontinfo": {
    "en": "Font &Info...",
    "de": "Schriftart-&Informationen...",
    "fr": "&Informations sur la police...",
    "ja": "フォント情報(&I)...",
    "context": "Open the Font Info / name-table editor dialog"
  },

  // Vocabulary Glossary Terms
  "vocab.contour": {
    "en": "Contour",
    "de": "Kontur",
    "fr": "Contour",
    "ja": "輪郭",
    "context": "Glossary term: A closed or open path consisting of nodes and handles."
  },
  "vocab.node": {
    "en": "Node",
    "de": "Knoten",
    "fr": "Nœud",
    "ja": "ノード",
    "context": "Glossary term: A point on a contour that defines shape."
  },
  "vocab.tangent": {
    "en": "Tangent",
    "de": "Tangente",
    "fr": "Tangente",
    "ja": "接線ノード",
    "context": "Glossary term: A node type that connects a straight line and a curve smoothly."
  },
  "vocab.controlPoint": {
    "en": "Control Point",
    "de": "Kontrollpunkt",
    "fr": "Point de contrôle",
    "ja": "コントロールポイント",
    "context": "Glossary term: Off-curve handle determining vector direction and tension."
  },
  "vocab.boundingBox": {
    "en": "Bounding Box",
    "de": "Begrenzungsrahmen",
    "fr": "Boîte englobante",
    "ja": "バウンディングボックス",
    "context": "Glossary term: The smallest enclosing box containing all coordinates of a glyph."
  },
  "vocab.baseline": {
    "en": "Baseline",
    "de": "Grundlinie",
    "fr": "Ligne de base",
    "ja": "ベースライン",
    "context": "Glossary term: The imaginary line upon which most glyphs sit."
  },
  "vocab.leftSidebearing": {
    "en": "Left Sidebearing",
    "de": "Linke Vorbreite",
    "fr": "Approche gauche",
    "ja": "左サイドベアリング",
    "context": "Glossary term: The horizontal distance between the leftmost boundary of a glyph and its origin."
  },
  "vocab.rightSidebearing": {
    "en": "Right Sidebearing",
    "de": "Rechte Vorbreite",
    "fr": "Approche droite",
    "ja": "右サイドベアリング",
    "context": "Glossary term: The horizontal distance from the rightmost boundary to the advance width."
  },
  "vocab.advanceWidth": {
    "en": "Advance Width",
    "de": "Dickte",
    "fr": "Chasse",
    "ja": "送り幅",
    "context": "Glossary term: The total width allocated to a character including spacing."
  },
  "vocab.kerningPair": {
    "en": "Kerning Pair",
    "de": "Unterschneidungspaar",
    "fr": "Paire de crénage",
    "ja": "カーニングペア",
    "context": "Glossary term: Adjustment of spacing between two adjacent characters."
  },
  "vocab.kerningClass": {
    "en": "Kerning Class",
    "de": "Unterschneidungsklasse",
    "fr": "Classe de crénage",
    "ja": "カーニングクラス",
    "context": "Glossary term: Group of glyphs sharing identical spacing characteristics."
  },
  "vocab.fontMaster": {
    "en": "Font Master",
    "de": "Schriftart-Master",
    "fr": "Master de police",
    "ja": "フォントマスター",
    "context": "Glossary term: Source design representation representing a specific style (e.g. Regular, Bold)."
  },
  "vocab.designspace": {
    "en": "Designspace",
    "de": "Designspace",
    "fr": "Designspace",
    "ja": "デザインスペース",
    "context": "Glossary term: The multidimensional parameter space defining a variable font."
  },
  "vocab.axisInstance": {
    "en": "Axis Instance",
    "de": "Achseninstanz",
    "fr": "Instance d'axe",
    "ja": "軸インスタンス",
    "context": "Glossary term: A discrete coordinate selection along variation axes."
  },
  "vocab.hinting": {
    "en": "Hinting",
    "de": "Hinting",
    "fr": "Instructions (Hinting)",
    "ja": "ヒンティング",
    "context": "Glossary term: Aligning vector paths to pixel grids at small sizes."
  },
  "vocab.trueTypeInstructing": {
    "en": "TrueType Instructing",
    "de": "TrueType-Instruieren",
    "fr": "Instructions TrueType",
    "ja": "TrueType命令",
    "context": "Glossary term: Grid-fitting instructions optimized for rasterization engines."
  },

  // ── OpenType Features ──────────────────────────────────────────────────────
  // Feature tags are non-translatable tokens; they appear as {tag} placeholders
  // in labels so pseudo-localizers preserve them.

  "vocab.otfeature.liga": {
    "en": "Standard Ligatures (liga)",
    "de": "Standardligaturen (liga)",
    "fr": "Ligatures standard (liga)",
    "ja": "標準合字 (liga)",
    "context": "Glossary term: OpenType feature tag 'liga' — substitutes sequences like fi/fl with prebuilt ligature glyphs. Tag token 'liga' must remain unchanged in all locales."
  },
  "vocab.otfeature.dlig": {
    "en": "Discretionary Ligatures (dlig)",
    "de": "Freie Ligaturen (dlig)",
    "fr": "Ligatures facultatives (dlig)",
    "ja": "任意合字 (dlig)",
    "context": "Glossary term: OpenType feature tag 'dlig' — optional decorative ligatures enabled by user choice. Tag 'dlig' is a non-translatable token."
  },
  "vocab.otfeature.smcp": {
    "en": "Small Capitals (smcp)",
    "de": "Kapitälchen (smcp)",
    "fr": "Petites capitales (smcp)",
    "ja": "スモールキャピタル (smcp)",
    "context": "Glossary term: OpenType feature tag 'smcp' — substitutes lowercase letters with small-cap variants. Tag 'smcp' must not be translated."
  },
  "vocab.otfeature.c2sc": {
    "en": "Capitals to Small Caps (c2sc)",
    "de": "Großbuchstaben zu Kapitälchen (c2sc)",
    "fr": "Capitales en petites capitales (c2sc)",
    "ja": "大文字をスモールキャップに (c2sc)",
    "context": "Glossary term: OpenType feature tag 'c2sc' — converts uppercase letters to small-cap form. Tag 'c2sc' is a non-translatable token."
  },
  "vocab.otfeature.onum": {
    "en": "Oldstyle Figures (onum)",
    "de": "Mediävalziffern (onum)",
    "fr": "Chiffres elzéviriens (onum)",
    "ja": "オールドスタイル数字 (onum)",
    "context": "Glossary term: OpenType feature tag 'onum' — activates text figures with ascenders and descenders. DE 'Mediävalziffern' is the standard German term. Tag 'onum' must stay as-is."
  },
  "vocab.otfeature.lnum": {
    "en": "Lining Figures (lnum)",
    "de": "Versalziffern (lnum)",
    "fr": "Chiffres alignés (lnum)",
    "ja": "ライニング数字 (lnum)",
    "context": "Glossary term: OpenType feature tag 'lnum' — activates uppercase-height numerals all resting on the baseline. DE 'Versalziffern' is the standard term."
  },
  "vocab.otfeature.tnum": {
    "en": "Tabular Figures (tnum)",
    "de": "Tabellenziffern (tnum)",
    "fr": "Chiffres tabulaires (tnum)",
    "ja": "表形数字 (tnum)",
    "context": "Glossary term: OpenType feature tag 'tnum' — fixed-width numerals that align vertically in tables."
  },
  "vocab.otfeature.pnum": {
    "en": "Proportional Figures (pnum)",
    "de": "Proportionalziffern (pnum)",
    "fr": "Chiffres proportionnels (pnum)",
    "ja": "プロポーショナル数字 (pnum)",
    "context": "Glossary term: OpenType feature tag 'pnum' — variable-width numerals suited for running text."
  },
  "vocab.otfeature.kern": {
    "en": "Kerning (kern)",
    "de": "Unterschneidung (kern)",
    "fr": "Crénage (kern)",
    "ja": "カーニング (kern)",
    "context": "Glossary term: OpenType feature tag 'kern' — activates pair/class kerning adjustments. Note disambiguation: this is the OT feature, not the general spacing concept."
  },
  "vocab.otfeature.calt": {
    "en": "Contextual Alternates (calt)",
    "de": "Kontextbedingte Alternativformen (calt)",
    "fr": "Variantes contextuelles (calt)",
    "ja": "文脈依存の字形 (calt)",
    "context": "Glossary term: OpenType feature tag 'calt' — substitutes glyphs based on surrounding characters. DE compound is correct industry usage."
  },
  "vocab.otfeature.salt": {
    "en": "Stylistic Alternates (salt)",
    "de": "Stilistische Alternativformen (salt)",
    "fr": "Variantes stylistiques (salt)",
    "ja": "スタイル代替字形 (salt)",
    "context": "Glossary term: OpenType feature tag 'salt' — a catch-all for glyph design alternates not covered by more specific features."
  },
  "vocab.otfeature.ss01": {
    "en": "Stylistic Set 1 (ss01)",
    "de": "Stilistischer Satz 1 (ss01)",
    "fr": "Jeu stylistique 1 (ss01)",
    "ja": "スタイルセット 1 (ss01)",
    "context": "Glossary term: OpenType feature tag 'ss01' — the first of up to 20 named stylistic set features. The numeric suffix increments ss02..ss20."
  },
  "vocab.otfeature.frac": {
    "en": "Fractions (frac)",
    "de": "Brüche (frac)",
    "fr": "Fractions (frac)",
    "ja": "分数 (frac)",
    "context": "Glossary term: OpenType feature tag 'frac' — converts sequences like 1/2 into built fraction glyphs."
  },
  "vocab.otfeature.sups": {
    "en": "Superscript (sups)",
    "de": "Hochgestellt (sups)",
    "fr": "Exposant (sups)",
    "ja": "上付き文字 (sups)",
    "context": "Glossary term: OpenType feature tag 'sups' — activates superscript glyph substitutions."
  },
  "vocab.otfeature.subs": {
    "en": "Subscript (subs)",
    "de": "Tiefgestellt (subs)",
    "fr": "Indice (subs)",
    "ja": "下付き文字 (subs)",
    "context": "Glossary term: OpenType feature tag 'subs' — activates subscript glyph substitutions."
  },
  "vocab.otfeature.ordn": {
    "en": "Ordinals (ordn)",
    "de": "Ordinalzeichen (ordn)",
    "fr": "Ordinaux (ordn)",
    "ja": "序数記号 (ordn)",
    "context": "Glossary term: OpenType feature tag 'ordn' — activates ordinal suffixes such as 1st, 2nd (a, o raised)."
  },
  "vocab.otfeature.aalt": {
    "en": "Access All Alternates (aalt)",
    "de": "Alle Alternativformen (aalt)",
    "fr": "Accès à toutes les variantes (aalt)",
    "ja": "全代替字形へのアクセス (aalt)",
    "context": "Glossary term: OpenType feature tag 'aalt' — a meta-feature listing every alternate for a glyph, used by layout UIs."
  },

  // ── Variable Font / Designspace UI ────────────────────────────────────────

  "vocab.varfont.axis": {
    "en": "Variation Axis",
    "de": "Variationsachse",
    "fr": "Axe de variation",
    "ja": "バリエーション軸",
    "context": "Glossary term: A named dimension in a variable font's designspace (e.g. Weight, Width, Optical Size)."
  },
  "vocab.varfont.axisTag": {
    "en": "Axis Tag",
    "de": "Achsen-Tag",
    "fr": "Étiquette d'axe",
    "ja": "軸タグ",
    "context": "Glossary term: The four-character identifier for a registered or custom axis (e.g. wght, wdth, opsz). Tags are non-translatable tokens."
  },
  "vocab.varfont.axisMin": {
    "en": "Axis Minimum",
    "de": "Achsenminimum",
    "fr": "Minimum d'axe",
    "ja": "軸の最小値",
    "context": "Glossary term: The lower bound of a variation axis coordinate range."
  },
  "vocab.varfont.axisMax": {
    "en": "Axis Maximum",
    "de": "Achsenmaximum",
    "fr": "Maximum d'axe",
    "ja": "軸の最大値",
    "context": "Glossary term: The upper bound of a variation axis coordinate range."
  },
  "vocab.varfont.axisDefault": {
    "en": "Axis Default",
    "de": "Achsen-Standardwert",
    "fr": "Valeur par défaut d'axe",
    "ja": "軸のデフォルト値",
    "context": "Glossary term: The default position on a variation axis, used when no explicit value is specified."
  },
  "vocab.varfont.wght": {
    "en": "Weight Axis (wght)",
    "de": "Gewichts-Achse (wght)",
    "fr": "Axe de graisse (wght)",
    "ja": "ウェイト軸 (wght)",
    "context": "Glossary term: Registered OpenType variation axis tag 'wght' controlling stroke weight. Range typically 100–900."
  },
  "vocab.varfont.wdth": {
    "en": "Width Axis (wdth)",
    "de": "Breiten-Achse (wdth)",
    "fr": "Axe de chasse (wdth)",
    "ja": "幅軸 (wdth)",
    "context": "Glossary term: Registered OpenType variation axis tag 'wdth' controlling glyph width. FR 'chasse' is the standard typographic term for glyph width."
  },
  "vocab.varfont.opsz": {
    "en": "Optical Size Axis (opsz)",
    "de": "Optische-Größe-Achse (opsz)",
    "fr": "Axe de corps optique (opsz)",
    "ja": "オプティカルサイズ軸 (opsz)",
    "context": "Glossary term: Registered axis tag 'opsz' — adjusts letterform details for different type sizes."
  },
  "vocab.varfont.slnt": {
    "en": "Slant Axis (slnt)",
    "de": "Neigungsachse (slnt)",
    "fr": "Axe d'inclinaison (slnt)",
    "ja": "スラント軸 (slnt)",
    "context": "Glossary term: Registered axis tag 'slnt' — controls the slant angle of glyphs, distinct from italic substitution."
  },
  "vocab.varfont.ital": {
    "en": "Italic Axis (ital)",
    "de": "Kursiv-Achse (ital)",
    "fr": "Axe italique (ital)",
    "ja": "イタリック軸 (ital)",
    "context": "Glossary term: Registered axis tag 'ital' — binary or continuous switch between roman and italic glyph sets."
  },
  "vocab.varfont.instance": {
    "en": "Named Instance",
    "de": "Benannte Instanz",
    "fr": "Instance nommée",
    "ja": "名前付きインスタンス",
    "context": "Glossary term: A predefined set of axis coordinates saved with a human-readable name (e.g. 'SemiBold Condensed')."
  },
  "vocab.varfont.master": {
    "en": "Designspace Master",
    "de": "Designspace-Master",
    "fr": "Master de designspace",
    "ja": "デザインスペースマスター",
    "context": "Glossary term: A source layer in the designspace that anchors the interpolation at a specific axis location."
  },
  "vocab.varfont.delta": {
    "en": "Delta",
    "de": "Delta",
    "fr": "Delta",
    "ja": "デルタ",
    "context": "Glossary term: The coordinate offset applied during interpolation at a given axis position. Greek letter Delta universally used in typography engineering across all locales."
  },
  "vocab.varfont.interpolation": {
    "en": "Interpolation",
    "de": "Interpolation",
    "fr": "Interpolation",
    "ja": "補間",
    "context": "Glossary term: The mathematical process of computing intermediate glyph shapes between masters."
  },
  "vocab.varfont.extrapolation": {
    "en": "Extrapolation",
    "de": "Extrapolation",
    "fr": "Extrapolation",
    "ja": "外挿",
    "context": "Glossary term: Computing glyph shapes beyond the defined master boundaries, extending the designspace."
  },
  "vocab.varfont.gvar": {
    "en": "Glyph Variation Table (gvar)",
    "de": "Glyph-Variationstabelle (gvar)",
    "fr": "Table de variation de glyphe (gvar)",
    "ja": "グリフバリエーションテーブル (gvar)",
    "context": "Glossary term: The TrueType binary table storing per-glyph variation deltas for variable fonts. Table name 'gvar' is a non-translatable token."
  },
  "vocab.varfont.fvar": {
    "en": "Font Variation Table (fvar)",
    "de": "Schriftart-Variationstabelle (fvar)",
    "fr": "Table de variation de police (fvar)",
    "ja": "フォントバリエーションテーブル (fvar)",
    "context": "Glossary term: The OpenType table listing all variation axes and named instances. Table name 'fvar' is a non-translatable token."
  },

  // ── TrueType Hinting ──────────────────────────────────────────────────────

  "vocab.hinting.alignmentZone": {
    "en": "Alignment Zone",
    "de": "Ausrichtungszone",
    "fr": "Zone d'alignement",
    "ja": "アライメントゾーン",
    "context": "Glossary term: A horizontal band in PostScript/TrueType hinting that snaps key metrics (baseline, x-height, cap-height) to pixel boundaries."
  },
  "vocab.hinting.blueValue": {
    "en": "Blue Value",
    "de": "Blue-Wert",
    "fr": "Valeur blue",
    "ja": "ブルー値",
    "context": "Glossary term: PostScript hinting term for the top and bottom coordinates of an alignment zone pair. 'Blue' is a technical term; no standard DE/FR/JA equivalent exists — retain as loan word with explanation."
  },
  "vocab.hinting.stem": {
    "en": "Stem",
    "de": "Stamm",
    "fr": "Fût",
    "ja": "ステム",
    "context": "Glossary term: The main straight stroke of a letterform. Used in hinting as a reference width for snapping to pixel grids. FR 'fût' is the standard typographic term."
  },
  "vocab.hinting.stemWidth": {
    "en": "Stem Width",
    "de": "Stammbreite",
    "fr": "Largeur de fût",
    "ja": "ステム幅",
    "context": "Glossary term: The measured thickness of a stem, used to define snap values in hinting tables (cvt, fpgm)."
  },
  "vocab.hinting.cvt": {
    "en": "Control Value Table (cvt)",
    "de": "Steuerwerttabelle (cvt)",
    "fr": "Table des valeurs de contrôle (cvt)",
    "ja": "制御値テーブル (cvt)",
    "context": "Glossary term: A TrueType table holding reference measurements (stem widths, zone positions) referenced by hinting instructions. Table tag 'cvt' is a non-translatable token."
  },
  "vocab.hinting.fpgm": {
    "en": "Font Program (fpgm)",
    "de": "Schriftprogramm (fpgm)",
    "fr": "Programme de police (fpgm)",
    "ja": "フォントプログラム (fpgm)",
    "context": "Glossary term: A TrueType table containing function definitions shared by all glyph programs. Table tag 'fpgm' is a non-translatable token."
  },
  "vocab.hinting.prep": {
    "en": "Pre-Program (prep)",
    "de": "Vorprogramm (prep)",
    "fr": "Pré-programme (prep)",
    "ja": "プリプログラム (prep)",
    "context": "Glossary term: The TrueType pre-program table executed once at each size change to initialize state. Table tag 'prep' is a non-translatable token."
  },
  "vocab.hinting.deltaHint": {
    "en": "Delta Hint",
    "de": "Delta-Hint",
    "fr": "Instruction delta",
    "ja": "デルタヒント",
    "context": "Glossary term: A hinting instruction that moves a specific point by a sub-pixel amount at a defined ppem size range."
  },
  "vocab.hinting.ppem": {
    "en": "Pixels Per Em (ppem)",
    "de": "Pixel pro Em (ppem)",
    "fr": "Pixels par em (ppem)",
    "ja": "ピクセル/em (ppem)",
    "context": "Glossary term: The resolution at which a font is rendered, expressed as pixels per em square. Abbreviation 'ppem' is a non-translatable token."
  },
  "vocab.hinting.gridFitting": {
    "en": "Grid Fitting",
    "de": "Rasteranpassung",
    "fr": "Ajustement à la grille",
    "ja": "グリッドフィッティング",
    "context": "Glossary term: The process of aligning outline points to the pixel grid to improve screen legibility at small sizes."
  },
  "vocab.hinting.dropoutControl": {
    "en": "Dropout Control",
    "de": "Dropout-Kontrolle",
    "fr": "Contrôle de brisure de trait",
    "ja": "ドロップアウト制御",
    "context": "Glossary term: A TrueType hinting mode that prevents thin strokes from disappearing (dropping out) at low ppem. FR 'brisure de trait' describes the stroke interruption; 'dropout' is also used as a loan word."
  },
  "vocab.hinting.gasp": {
    "en": "Grid-fitting and Scan-conversion Procedure Table (gasp)",
    "de": "GASP-Tabelle (Rasteranpassung und Abtastumwandlung)",
    "fr": "Table gasp (ajustement à la grille et conversion de balayage)",
    "ja": "gaspテーブル (グリッドフィッティングとスキャン変換手順)",
    "context": "Glossary term: An OpenType table specifying per-ppem range behaviour for hinting and anti-aliasing. Table tag 'gasp' is a non-translatable token."
  },
  "vocab.hinting.roundToGrid": {
    "en": "Round to Grid",
    "de": "Auf Raster runden",
    "fr": "Arrondir à la grille",
    "ja": "グリッドに丸める",
    "context": "Glossary term: A TrueType instruction flag (RTG) that snaps a point coordinate to the nearest full pixel position."
  },
  "vocab.hinting.touchedPoint": {
    "en": "Touched Point",
    "de": "Berührter Punkt",
    "fr": "Point touché",
    "ja": "タッチされた点",
    "context": "Glossary term: In TrueType hinting, a point that has been explicitly repositioned by an instruction and is locked for the current rendering."
  },

  // ── Glyph Encoding / Unicode ──────────────────────────────────────────────

  "vocab.encoding.codepoint": {
    "en": "Codepoint",
    "de": "Codepunkt",
    "fr": "Point de code",
    "ja": "コードポイント",
    "context": "Glossary term: A numerical value in the Unicode standard assigned to a character, written as U+XXXX."
  },
  "vocab.encoding.unicodeBlock": {
    "en": "Unicode Block",
    "de": "Unicode-Block",
    "fr": "Bloc Unicode",
    "ja": "Unicodeブロック",
    "context": "Glossary term: A named contiguous range of Unicode codepoints (e.g. Basic Latin U+0000–U+007F)."
  },
  "vocab.encoding.cmap": {
    "en": "Character Map (cmap)",
    "de": "Zeichenzuordnungstabelle (cmap)",
    "fr": "Table de correspondance de caractères (cmap)",
    "ja": "文字マップテーブル (cmap)",
    "context": "Glossary term: The OpenType table that maps codepoints to glyph IDs. Table tag 'cmap' is a non-translatable token."
  },
  "vocab.encoding.glyphName": {
    "en": "Glyph Name",
    "de": "Glyphenname",
    "fr": "Nom de glyphe",
    "ja": "グリフ名",
    "context": "Glossary term: The PostScript-style identifier for a glyph (e.g. 'A', 'uni0041', 'afii10017'). Names follow the Adobe Glyph List for New Fonts (AGLFN)."
  },
  "vocab.encoding.aglfn": {
    "en": "Adobe Glyph List for New Fonts (AGLFN)",
    "de": "Adobe-Glyphennamenliste für neue Schriften (AGLFN)",
    "fr": "Liste de glyphes Adobe pour nouvelles polices (AGLFN)",
    "ja": "Adobe グリフリスト新版 (AGLFN)",
    "context": "Glossary term: The recommended naming convention mapping glyph names to Unicode codepoints. Abbreviation 'AGLFN' is a non-translatable token."
  },
  "vocab.encoding.pua": {
    "en": "Private Use Area (PUA)",
    "de": "Privatnutzungsbereich (PUA)",
    "fr": "Zone d'utilisation privée (PUA)",
    "ja": "私用領域 (PUA)",
    "context": "Glossary term: Unicode codepoints U+E000–U+F8FF (and two supplementary planes) reserved for vendor-specific or application-specific glyph assignments."
  },
  "vocab.encoding.surrogatePair": {
    "en": "Surrogate Pair",
    "de": "Ersatzzeichenpaar",
    "fr": "Paire de substitution",
    "ja": "サロゲートペア",
    "context": "Glossary term: Two UTF-16 code units (U+D800–U+DFFF) encoding a single supplementary-plane codepoint above U+FFFF."
  },
  "vocab.encoding.markGlyph": {
    "en": "Mark Glyph",
    "de": "Markierungsglyphe",
    "fr": "Glyphe de marque",
    "ja": "マークグリフ",
    "context": "Glossary term: A glyph representing a combining mark (diacritic) that positions itself relative to a base glyph using OpenType GPOS Mark-to-Base rules."
  },
  "vocab.encoding.baseGlyph": {
    "en": "Base Glyph",
    "de": "Basisglyphe",
    "fr": "Glyphe de base",
    "ja": "ベースグリフ",
    "context": "Glossary term: A glyph that acts as the attachment point for combining marks in OpenType GPOS positioning."
  },
  "vocab.encoding.ligatureGlyph": {
    "en": "Ligature Glyph",
    "de": "Ligaturglyphe",
    "fr": "Glyphe de ligature",
    "ja": "合字グリフ",
    "context": "Glossary term: A glyph resulting from the merger of two or more base glyphs into a single designed form."
  },
  "vocab.encoding.unicodeCategory": {
    "en": "Unicode Category",
    "de": "Unicode-Kategorie",
    "fr": "Catégorie Unicode",
    "ja": "Unicodeカテゴリ",
    "context": "Glossary term: The Unicode character property class (e.g. Letter, Mark, Number, Separator) assigned to each codepoint."
  },
  "vocab.encoding.glyphID": {
    "en": "Glyph ID",
    "de": "Glyphen-ID",
    "fr": "Identifiant de glyphe",
    "ja": "グリフ ID",
    "context": "Glossary term: The zero-based index of a glyph within a font's internal glyph table. Distinct from the Unicode codepoint."
  },

  // ── Font Info / name-table strings ────────────────────────────────────────
  // Strings marked [unchanged-translation] must not be translated; they are
  // brand or legal strings that stay identical across all locales.

  "vocab.fontinfo.familyName": {
    "en": "Family Name",
    "de": "Schriftfamilienname",
    "fr": "Nom de famille de police",
    "ja": "ファミリー名",
    "context": "Font info field: OpenType name ID 1 / 16. The shared typographic family name (e.g. 'Helvetica Neue'). Value itself is brand data — unchanged-translation."
  },
  "vocab.fontinfo.subfamilyName": {
    "en": "Subfamily Name",
    "de": "Schriftschnittname",
    "fr": "Nom de sous-famille",
    "ja": "サブファミリー名",
    "context": "Font info field: OpenType name ID 2 / 17. The style name within the family (e.g. 'Bold Italic'). DE 'Schriftschnittname' uses 'Schnitt' (cut/style) — the standard German typographic term."
  },
  "vocab.fontinfo.fullName": {
    "en": "Full Name",
    "de": "Vollständiger Name",
    "fr": "Nom complet",
    "ja": "フルネーム",
    "context": "Font info field: OpenType name ID 4. The concatenated family + subfamily string (e.g. 'Helvetica Neue Bold')."
  },
  "vocab.fontinfo.postScriptName": {
    "en": "PostScript Name",
    "de": "PostScript-Name",
    "fr": "Nom PostScript",
    "ja": "PostScript名",
    "context": "Font info field: OpenType name ID 6. The ASCII-safe identifier used in PostScript and PDF documents. Must contain no spaces. Value is unchanged-translation."
  },
  "vocab.fontinfo.copyright": {
    "en": "Copyright Notice",
    "de": "Urheberrechtsvermerk",
    "fr": "Mention de copyright",
    "ja": "著作権表示",
    "context": "Font info field: OpenType name ID 0. Legal copyright string. The string value is brand/legal data and must not be translated (unchanged-translation); only the field label is localized."
  },
  "vocab.fontinfo.trademark": {
    "en": "Trademark",
    "de": "Warenzeichen",
    "fr": "Marque déposée",
    "ja": "商標",
    "context": "Font info field: OpenType name ID 7. Trademark notice. Value is unchanged-translation — legal text that stays in source language."
  },
  "vocab.fontinfo.designer": {
    "en": "Designer",
    "de": "Schriftgestalter",
    "fr": "Créateur",
    "ja": "デザイナー",
    "context": "Font info field: OpenType name ID 9. The name of the typeface designer. DE 'Schriftgestalter' (font designer) is precise; 'Schriftentwerfer' is also acceptable."
  },
  "vocab.fontinfo.designerURL": {
    "en": "Designer URL",
    "de": "Schriftgestalter-URL",
    "fr": "URL du créateur",
    "ja": "デザイナーURL",
    "context": "Font info field: OpenType name ID 12. URL to the designer's web presence. URL value is unchanged-translation."
  },
  "vocab.fontinfo.manufacturer": {
    "en": "Manufacturer",
    "de": "Schriftenhersteller",
    "fr": "Fabricant",
    "ja": "製造元",
    "context": "Font info field: OpenType name ID 8. The font vendor or foundry name. Value is unchanged-translation."
  },
  "vocab.fontinfo.manufacturerURL": {
    "en": "Manufacturer URL",
    "de": "Herstellerwebsite",
    "fr": "URL du fabricant",
    "ja": "製造元URL",
    "context": "Font info field: OpenType name ID 11. URL to the font vendor's website. Value is unchanged-translation."
  },
  "vocab.fontinfo.licenseDescription": {
    "en": "License Description",
    "de": "Lizenzbeschreibung",
    "fr": "Description de la licence",
    "ja": "ライセンス説明",
    "context": "Font info field: OpenType name ID 13. Human-readable license text. Value is legal text and unchanged-translation."
  },
  "vocab.fontinfo.licenseURL": {
    "en": "License URL",
    "de": "Lizenz-URL",
    "fr": "URL de la licence",
    "ja": "ライセンスURL",
    "context": "Font info field: OpenType name ID 14. URL pointing to the full license document. Value is unchanged-translation."
  },
  "vocab.fontinfo.vendorID": {
    "en": "Vendor ID",
    "de": "Hersteller-ID",
    "fr": "Identifiant de l'éditeur",
    "ja": "ベンダーID",
    "context": "Font info field: OS/2 table achVendID — a four-character code identifying the type foundry (e.g. 'ADBE', 'GOOG'). Value is unchanged-translation; it is a registered code."
  },
  "vocab.fontinfo.version": {
    "en": "Version String",
    "de": "Versionskennung",
    "fr": "Chaîne de version",
    "ja": "バージョン文字列",
    "context": "Font info field: OpenType name ID 5. Version identifier, conventionally 'Version X.XXX'. Value format is unchanged-translation."
  },
  "vocab.fontinfo.unitsPerEm": {
    "en": "Units Per Em",
    "de": "Einheiten pro Em",
    "fr": "Unités par em",
    "ja": "1em あたりのユニット数",
    "context": "Font info field: head table unitsPerEm. The coordinate grid resolution of the font, typically 1000 (PostScript) or 2048 (TrueType)."
  },

  // ── Dynamic Placeholders & Messages ───────────────────────────────────────

  "msg.exportSuccess": {
    "en": "Exported {0} font master(s) to directory: {1}",
    "de": "{0} Schrift-Master erfolgreich exportiert in das Verzeichnis: {1}",
    "fr": "Exportation réussie de {0} master(s) de police vers le dossier: {1}",
    "ja": "{0} 個のフォントマスターを次のディレクトリに書き出しました: {1}",
    "context": "Success message. {0} is the count of masters, {1} is the target path."
  },
  "msg.selectedGlyphsCount": {
    "en": "Selected {count, plural, =0 {no glyphs} one {one glyph} other {{count} glyphs}} out of {total} total.",
    "de": "Ausgewählt: {count, plural, =0 {keine Glyphen} one {eine Glyphe} other {{count} Glyphen}} von insgesamt {total}.",
    "fr": "Sélection: {count, plural, =0 {aucun glyphe} one {un glyphe} other {{count} glyphes}} sur un total de {total}.",
    "ja": "全 {total} 個中 {count, plural, =0 {選択中のグリフはありません} one {1 個のグリフを選択中} other {{count} 個のグリフを選択中}}。",
    "context": "Info status. Uses ICU format for pluralization of {count}. {total} is total glyphs in font."
  },
  "msg.kerningPairValue": {
    "en": "The kerning pair '{0}' - '{1}' has a spacing value of {2} units.",
    "de": "Das Unterschneidungspaar '{0}' - '{1}' hat einen Spaltenwert von {2} Einheiten.",
    "fr": "La paire de crénage '{0}' - '{1}' a une valeur d'ajustement de {2} unités.",
    "ja": "カーニングペア '{0}' - '{1}' の調整値は {2} ユニットです。",
    "context": "Kerning pair description. {0} and {1} are glyph names, {2} is numerical spacing value."
  },
  "msg.glyphSelfIntersect": {
    "en": "Warning: Glyph '{0}' has self-intersecting contours.",
    "de": "Warnung: Glyphe '{0}' hat sich selbst überschneidende Konturen.",
    "fr": "Attention: Le glyphe '{0}' contient des contours qui s'intersectent.",
    "ja": "警告: グリフ '{0}' に自己交差する輪郭があります。",
    "context": "Linter message. {0} is glyph name."
  },
  "msg.pathNotWritable": {
    "en": "Error: Font path '{0}' is not writable.",
    "de": "Fehler: Schriftart-Pfad '{0}' ist schreibgeschützt.",
    "fr": "Erreur: Le chemin de police '{0}' n'est pas accessible en écriture.",
    "ja": "エラー: フォントのパス '{0}' に書き込み権限がありません。",
    "context": "File system error. {0} is file path."
  },
  "msg.axisRangeInfo": {
    "en": "Axis '{0}': minimum {min}, default {default}, maximum {max}.",
    "de": "Achse '{0}': Minimum {min}, Standard {default}, Maximum {max}.",
    "fr": "Axe '{0}': minimum {min}, défaut {default}, maximum {max}.",
    "ja": "軸 '{0}': 最小値 {min}、デフォルト {default}、最大値 {max}。",
    "context": "Axis info line in designspace inspector. {0} is the axis tag (non-translatable token e.g. wght). {min}, {default}, {max} are numeric values."
  },
  "msg.instanceCreated": {
    "en": "Named instance '{0}' created at {1} axis coordinates.",
    "de": "Benannte Instanz '{0}' bei {1} Achsenkoordinaten erstellt.",
    "fr": "L'instance nommée '{0}' a été créée avec {1} coordonnée(s) d'axe.",
    "ja": "名前付きインスタンス '{0}' を {1} 個の軸座標で作成しました。",
    "context": "Confirmation after adding a named instance. {0} is instance name, {1} is count of axis coordinates."
  },
  "msg.hintingWarningPpem": {
    "en": "Warning: No delta hints defined for glyph '{0}' at ppem {1}.",
    "de": "Warnung: Keine Delta-Hints für Glyphe '{0}' bei ppem {1} definiert.",
    "fr": "Attention: Aucune instruction delta définie pour le glyphe '{0}' au ppem {1}.",
    "ja": "警告: グリフ '{0}' の ppem {1} にデルタヒントが定義されていません。",
    "context": "Hinting linter message. {0} is glyph name, {1} is ppem value. 'ppem' is a non-translatable token."
  },
  "msg.unicodeNotAssigned": {
    "en": "Glyph '{0}' has no Unicode codepoint assigned.",
    "de": "Glyphe '{0}' hat keinen zugewiesenen Unicode-Codepunkt.",
    "fr": "Le glyphe '{0}' n'a pas de point de code Unicode assigné.",
    "ja": "グリフ '{0}' に Unicode コードポイントが割り当てられていません。",
    "context": "Encoding validation message. {0} is glyph name."
  },
  "msg.otfeatureEnabled": {
    "en": "OpenType feature '{0}' enabled for {count, plural, one {one glyph} other {{count} glyphs}}.",
    "de": "OpenType-Feature '{0}' für {count, plural, one {eine Glyphe} other {{count} Glyphen}} aktiviert.",
    "fr": "La fonctionnalité OpenType '{0}' est activée pour {count, plural, one {un glyphe} other {{count} glyphes}}.",
    "ja": "OpenType フィーチャー '{0}' が {count, plural, one {1 個のグリフ} other {{count} 個のグリフ}} で有効化されました。",
    "context": "Status message after enabling an OT feature. {0} is feature tag (non-translatable, e.g. liga). Uses ICU plural on {count}."
  },
  "msg.mastersCount": {
    "en": "{count, plural, =0 {No masters} one {One master} other {{count} masters}} in designspace.",
    "de": "{count, plural, =0 {Keine Master} one {Ein Master} other {{count} Master}} im Designspace.",
    "fr": "{count, plural, =0 {Aucun master} one {Un master} other {{count} masters}} dans le designspace.",
    "ja": "デザインスペース内のマスター: {count, plural, =0 {なし} one {1 個} other {{count} 個}}。",
    "context": "Designspace panel count. ICU plural on {count} across all four locales; JA uses numeric-only plural (no grammatical category distinction beyond zero)."
  },
  "msg.stemCountPerGlyph": {
    "en": "Glyph '{0}' has {count, plural, =0 {no stems} one {one stem} other {{count} stems}} defined.",
    "de": "Glyphe '{0}' hat {count, plural, =0 {keine Stämme} one {einen Stamm} other {{count} Stämme}} definiert.",
    "fr": "Le glyphe '{0}' possède {count, plural, =0 {aucun fût} one {un fût} other {{count} fûts}} défini(s).",
    "ja": "グリフ '{0}' には {count, plural, =0 {ステムがありません} one {1 本のステム} other {{count} 本のステム}} が定義されています。",
    "context": "Hinting inspector. {0} is glyph name. ICU plural on {count}; FR uses 'fût/fûts' (standard typographic term for stem)."
  },

  // ── Disambiguated UI Labels ───────────────────────────────────────────────

  "label.disambig.kern.noun": {
    "en": "Kern (Noun)",
    "de": "Unterschnitt (Nomen)",
    "fr": "Crénage (Nom)",
    "ja": "カーン値 (名詞)",
    "context": "Label header for spacing adjustment data"
  },
  "label.disambig.kern.noun.desc": {
    "en": "Kern",
    "de": "Unterschneidungspaar",
    "fr": "Crénage",
    "ja": "カーニング値",
    "context": "Disambiguated word: Noun context"
  },
  "label.disambig.kern.verb": {
    "en": "Kern (Verb)",
    "de": "Unterschneiden (Verb)",
    "fr": "Créner (Verbe)",
    "ja": "カーニングする (動詞)",
    "context": "Label header for spacing action button"
  },
  "label.disambig.kern.verb.desc": {
    "en": "Kern",
    "de": "Unterschneiden",
    "fr": "Créner",
    "ja": "カーニング",
    "context": "Disambiguated word: Verb context"
  },
  "label.disambig.weight.font": {
    "en": "Weight (Font Style)",
    "de": "Gewicht (Strichstärke)",
    "fr": "Graisse (Style de police)",
    "ja": "ウェイト (フォントの太さ)",
    "context": "Label header for font weight property (Bold, Regular, Light)"
  },
  "label.disambig.weight.font.desc": {
    "en": "Weight",
    "de": "Gewicht (Stärke)",
    "fr": "Graisse",
    "ja": "太さ",
    "context": "Disambiguated word: Font weight context"
  },
  "label.disambig.weight.visual": {
    "en": "Weight (Visual Density)",
    "de": "Gewicht (Optische Dichte)",
    "fr": "Poids (Densité visuelle)",
    "ja": "視覚的ウェイト (黒み)",
    "context": "Label header for glyph visual density"
  },
  "label.disambig.weight.visual.desc": {
    "en": "Weight",
    "de": "Gewicht (Dichte)",
    "fr": "Poids",
    "ja": "黒み",
    "context": "Disambiguated word: Visual balance context"
  },
  "label.disambig.instance.noun": {
    "en": "Instance (Named Position)",
    "de": "Instanz (benannte Position)",
    "fr": "Instance (position nommée)",
    "ja": "インスタンス (名前付き位置)",
    "context": "Label header: 'instance' as a named coordinate in a variable font (noun)"
  },
  "label.disambig.instance.noun.desc": {
    "en": "Instance",
    "de": "Instanz",
    "fr": "Instance",
    "ja": "インスタンス",
    "context": "Disambiguated word: Variable font named instance (noun). Same source word 'Instance' has a different meaning in OOP contexts."
  },
  "label.disambig.master.source": {
    "en": "Master (Source Design)",
    "de": "Master (Quellentwurf)",
    "fr": "Master (dessin source)",
    "ja": "マスター (ソースデザイン)",
    "context": "Label header: 'master' in the font-editor sense — a source layer, not a print master or a person"
  },
  "label.disambig.master.source.desc": {
    "en": "Master",
    "de": "Schrift-Master",
    "fr": "Master de police",
    "ja": "フォントマスター",
    "context": "Disambiguated word: Font engineering source master (not a print production master)"
  },
  "label.disambig.stem.hinting": {
    "en": "Stem (Hinting Reference)",
    "de": "Stamm (Hinting-Referenz)",
    "fr": "Fût (référence d'instruction)",
    "ja": "ステム (ヒンティング基準)",
    "context": "Label header: 'stem' as a measured stroke used in hinting CVT entries"
  },
  "label.disambig.stem.glyph": {
    "en": "Stem (Glyph Stroke)",
    "de": "Stamm (Strich des Buchstabens)",
    "fr": "Fût (trait de lettre)",
    "ja": "ステム (文字のストローク)",
    "context": "Label header: 'stem' as a visual element of letterform design"
  },
  "label.disambig.delta.varfont": {
    "en": "Delta (Variation Offset)",
    "de": "Delta (Variationsversatz)",
    "fr": "Delta (décalage de variation)",
    "ja": "デルタ (バリエーションオフセット)",
    "context": "Label header: 'delta' as a coordinate offset in variable font interpolation"
  },
  "label.disambig.delta.hint": {
    "en": "Delta (Hinting Adjustment)",
    "de": "Delta (Hinting-Korrektur)",
    "fr": "Delta (correction d'instruction)",
    "ja": "デルタ (ヒンティング調整)",
    "context": "Label header: 'delta' as a per-ppem point shift in TrueType hinting"
  },

  // ── Editor View Labels ────────────────────────────────────────────────────

  "editor.title": {
    "en": "Typography Localization Vocabulary Sandbox",
    "de": "Typografie-Lokalisierung: Vokabel-Sandbox",
    "fr": "Bac à sable de vocabulaire typographique",
    "ja": "タイポグラフィ ローカライズ用語サンドボックス",
    "context": "Window title"
  },
  "editor.statusBar.ready": {
    "en": "Ready to edit font contours.",
    "de": "Bereit zum Bearbeiten von Schriftkonturen.",
    "fr": "Prêt pour l'édition de contours.",
    "ja": "グリフの輪郭を編集できます。",
    "context": "Status bar ready state text"
  },
  "editor.vocabTitle": {
    "en": "Active Font Engineering Vocabulary",
    "de": "Aktiver Schriftentwicklungs-Wortschatz",
    "fr": "Vocabulaire d'ingénierie de police",
    "ja": "使用中のフォント開発用語集",
    "context": "Vocabulary glossary panel title"
  },
  "editor.vocabExplanation": {
    "en": "Select a term below to view its localized description and metadata context.",
    "de": "Wählen Sie einen Begriff, um die Übersetzung und den Kontext anzuzeigen.",
    "fr": "Sélectionnez un terme pour voir sa traduction et sa description.",
    "ja": "用語を選択すると、翻訳とローカライズの文脈説明が表示されます。",
    "context": "Help text explaining vocabulary selection list"
  },
  "editor.btn.autoKernClass": {
    "en": "&Auto-Kern Class",
    "de": "&Klassen-Autounterschnitt",
    "fr": "Crénage de &classe automatique",
    "ja": "クラスカーニングを自動調整(&A)",
    "context": "Button label to perform auto-kerning on selected classes"
  },
  "editor.tooltip.autoKernClass": {
    "en": "Apply automatic kerning metrics between selected glyph classes.",
    "de": "Automatische Unterschneidungswerte zwischen Glyphenklassen anwenden.",
    "fr": "Appliquer des valeurs de crénage automatiques entre classes de glyphes.",
    "ja": "選択中のグリフクラスの間に自動カーニング設定を適用します。",
    "context": "Tooltip for class kerning button"
  },
  "editor.btn.generateHints": {
    "en": "Generate &Hints",
    "de": "&Hints generieren",
    "fr": "Générer les &instructions",
    "ja": "ヒントを生成(&H)",
    "context": "Button label to trigger hinting generation"
  },
  "editor.tooltip.generateHints": {
    "en": "Create grid-fitting delta hints automatically for low-resolution rasterization.",
    "de": "Automatisch rasterausrichtende Hints für Bildschirmanzeigen erzeugen.",
    "fr": "Créer des instructions de lissage pour la pixellisation basse résolution.",
    "ja": "低解像度のラスタライズ用に、グリッドに沿わせるデルタヒントを自動生成します。",
    "context": "Tooltip for hinting button"
  },
  "editor.panel.review.title": {
    "en": "Localization Review Tool",
    "de": "Lokalisierungs-Review-Tool",
    "fr": "Outil de révision de traduction",
    "ja": "ローカライズ査読ツール",
    "context": "Review sidebar title"
  },
  "editor.panel.review.save": {
    "en": "Save Translation",
    "de": "Übersetzung speichern",
    "fr": "Enregistrer la traduction",
    "ja": "翻訳を保存",
    "context": "Save button in review sidebar"
  },
  "editor.panel.review.export": {
    "en": "Export JSON Vocabulary",
    "de": "Wortschatz-JSON exportieren",
    "fr": "Exporter le vocabulaire JSON",
    "ja": "JSON 用語集を書き出し",
    "context": "Export vocabulary button"
  },
  "editor.panel.designspace.title": {
    "en": "Designspace Inspector",
    "de": "Designspace-Inspektor",
    "fr": "Inspecteur de designspace",
    "ja": "デザインスペースインスペクター",
    "context": "Panel title for the variable font designspace/axis editor"
  },
  "editor.panel.designspace.axesLabel": {
    "en": "Variation Axes",
    "de": "Variationsachsen",
    "fr": "Axes de variation",
    "ja": "バリエーション軸",
    "context": "Section heading listing the font's variation axes"
  },
  "editor.panel.designspace.instancesLabel": {
    "en": "Named Instances",
    "de": "Benannte Instanzen",
    "fr": "Instances nommées",
    "ja": "名前付きインスタンス",
    "context": "Section heading listing pre-defined named instances in the variable font"
  },
  "editor.panel.encoding.title": {
    "en": "Encoding & Unicode",
    "de": "Kodierung & Unicode",
    "fr": "Encodage & Unicode",
    "ja": "エンコーディングと Unicode",
    "context": "Panel title for the glyph encoding and Unicode assignment inspector"
  },
  "editor.panel.encoding.codepointLabel": {
    "en": "Unicode Codepoint",
    "de": "Unicode-Codepunkt",
    "fr": "Point de code Unicode",
    "ja": "Unicode コードポイント",
    "context": "Field label for the codepoint input field in the encoding panel (displays e.g. U+0041)"
  },
  "editor.panel.encoding.glyphNameLabel": {
    "en": "Glyph Name",
    "de": "Glyphenname",
    "fr": "Nom de glyphe",
    "ja": "グリフ名",
    "context": "Field label for the PostScript glyph name input in the encoding panel"
  },
  "editor.panel.hinting.title": {
    "en": "Hinting Inspector",
    "de": "Hinting-Inspektor",
    "fr": "Inspecteur d'instructions",
    "ja": "ヒンティングインスペクター",
    "context": "Panel title for the TrueType/PostScript hinting editor"
  },
  "editor.panel.hinting.zonesLabel": {
    "en": "Alignment Zones",
    "de": "Ausrichtungszonen",
    "fr": "Zones d'alignement",
    "ja": "アライメントゾーン",
    "context": "Section heading listing the hinting alignment zones (blue values)"
  },
  "editor.panel.hinting.stemsLabel": {
    "en": "Stem Definitions",
    "de": "Stammdefinitionen",
    "fr": "Définitions de fûts",
    "ja": "ステム定義",
    "context": "Section heading listing the stem width definitions used in CVT"
  },
  "editor.panel.otfeatures.title": {
    "en": "OpenType Features",
    "de": "OpenType-Features",
    "fr": "Fonctionnalités OpenType",
    "ja": "OpenType フィーチャー",
    "context": "Panel title for the OpenType feature code editor"
  },
  "editor.panel.otfeatures.enabledLabel": {
    "en": "Enabled Features",
    "de": "Aktivierte Features",
    "fr": "Fonctionnalités activées",
    "ja": "有効なフィーチャー",
    "context": "Section heading listing which OT features are currently turned on for preview"
  },
  "editor.panel.fontinfo.title": {
    "en": "Font Information",
    "de": "Schriftart-Informationen",
    "fr": "Informations sur la police",
    "ja": "フォント情報",
    "context": "Panel/dialog title for the font name-table and metadata editor"
  },
  "editor.btn.addAxis": {
    "en": "&Add Axis...",
    "de": "&Achse hinzufügen...",
    "fr": "Ajouter un &axe...",
    "ja": "軸を追加(&A)...",
    "context": "Button to add a new variation axis to the designspace"
  },
  "editor.btn.removeAxis": {
    "en": "&Remove Axis",
    "de": "&Achse entfernen",
    "fr": "&Supprimer l'axe",
    "ja": "軸を削除(&R)",
    "context": "Button to remove the selected variation axis from the designspace"
  },
  "editor.btn.addInstance": {
    "en": "Add &Instance",
    "de": "&Instanz hinzufügen",
    "fr": "Ajouter une &instance",
    "ja": "インスタンスを追加(&I)",
    "context": "Button to create a new named instance at current axis coordinates"
  },
  "editor.tooltip.addAxis": {
    "en": "Add a new variation axis to the designspace. Standard registered axes: wght, wdth, opsz, slnt, ital.",
    "de": "Eine neue Variationsachse zum Designspace hinzufügen. Registrierte Standardachsen: wght, wdth, opsz, slnt, ital.",
    "fr": "Ajouter un nouvel axe de variation au designspace. Axes enregistrés standard: wght, wdth, opsz, slnt, ital.",
    "ja": "デザインスペースに新しいバリエーション軸を追加します。標準登録軸: wght、wdth、opsz、slnt、ital。",
    "context": "Tooltip for the Add Axis button. Axis tag tokens (wght etc.) are non-translatable."
  },
  "editor.tooltip.addInstance": {
    "en": "Save the current axis position as a named instance (e.g. SemiBold Condensed).",
    "de": "Die aktuelle Achsenposition als benannte Instanz speichern (z. B. Halbfett Schmal).",
    "fr": "Enregistrer la position d'axe actuelle comme instance nommée (ex. Demi-gras Condensé).",
    "ja": "現在の軸位置を名前付きインスタンス（例: セミボールド コンデンスド）として保存します。",
    "context": "Tooltip for the Add Instance button"
  },
  "editor.statusBar.varfontMode": {
    "en": "Variable Font mode — {0} axis/axes active.",
    "de": "Modus Variabler Schriftstil — {0} Achse(n) aktiv.",
    "fr": "Mode Police variable — {0} axe(s) actif(s).",
    "ja": "バリアブルフォントモード — {0} 軸が有効です。",
    "context": "Status bar text when the font has a variable designspace. {0} is axis count."
  },

  // ── Additional vocabulary: glyph metrics & typographic measurements ───────

  "vocab.capHeight": {
    "en": "Cap Height",
    "de": "Versalhöhe",
    "fr": "Hauteur de capitale",
    "ja": "大文字高",
    "context": "Glossary term: The vertical distance from baseline to the top of flat uppercase letters (H, I). One of the key alignment-zone anchors in hinting."
  },
  "vocab.xHeight": {
    "en": "x-Height",
    "de": "x-Höhe",
    "fr": "Hauteur d'x",
    "ja": "x字高",
    "context": "Glossary term: The height of lowercase letters without ascenders, measured from baseline to the top of 'x'. A primary optical-size reference."
  },
  "vocab.ascender": {
    "en": "Ascender",
    "de": "Oberlänge",
    "fr": "Ascendante",
    "ja": "アセンダー",
    "context": "Glossary term: The portion of a lowercase letter that extends above the x-height (e.g. in b, d, h). DE 'Oberlänge' is the standard German typographic term."
  },
  "vocab.descender": {
    "en": "Descender",
    "de": "Unterlänge",
    "fr": "Descendante",
    "ja": "ディセンダー",
    "context": "Glossary term: The portion of a lowercase letter that extends below the baseline (e.g. in g, p, y). DE 'Unterlänge' is the standard German term."
  },
  "vocab.overshoot": {
    "en": "Overshoot",
    "de": "Überschwinger",
    "fr": "Débordement optique",
    "ja": "オーバーシュート",
    "context": "Glossary term: The amount by which round letters (O, o, C) extend beyond a flat metric line to appear optically equal in height."
  },
  "vocab.sidebearing": {
    "en": "Sidebearing",
    "de": "Vorbreite",
    "fr": "Approche",
    "ja": "サイドベアリング",
    "context": "Glossary term: Generic term for either left or right sidebearing — the spacing between the glyph boundary and the advance-width edge."
  },
  "vocab.trackingSpacing": {
    "en": "Tracking",
    "de": "Laufweite",
    "fr": "Approche globale",
    "ja": "トラッキング",
    "context": "Glossary term: Uniform spacing adjustment applied across a range of text, distinct from kerning which is pair-specific. DE 'Laufweite' is the standard German term. FR 'approche globale' distinguishes from pair kerning ('crénage')."
  },
  "vocab.leadingLineSpacing": {
    "en": "Leading",
    "de": "Zeilenabstand",
    "fr": "Interlignage",
    "ja": "行送り",
    "context": "Glossary term: The vertical spacing between consecutive baselines. DE 'Zeilenabstand' (line distance); FR 'interlignage' (interline). JA '行送り' (gyō-okuri) is the standard publishing term."
  },
  "vocab.glyphSet": {
    "en": "Glyph Set",
    "de": "Glyphensatz",
    "fr": "Jeu de glyphes",
    "ja": "グリフセット",
    "context": "Glossary term: The complete collection of glyphs available in a font, encompassing all Unicode assignments and PUA entries."
  },
  "vocab.openTypeLayout": {
    "en": "OpenType Layout",
    "de": "OpenType-Satzlayout",
    "fr": "Composition OpenType",
    "ja": "OpenType レイアウト",
    "context": "Glossary term: The set of OpenType tables (GSUB, GPOS, GDEF) governing glyph substitution and positioning in complex scripts."
  },
  "vocab.gsub": {
    "en": "Glyph Substitution Table (GSUB)",
    "de": "Glyph-Ersetzungstabelle (GSUB)",
    "fr": "Table de substitution de glyphes (GSUB)",
    "ja": "グリフ置換テーブル (GSUB)",
    "context": "Glossary term: The OpenType table containing glyph substitution rules (ligatures, alternates, small caps, etc.). Table tag 'GSUB' is a non-translatable token."
  },
  "vocab.gpos": {
    "en": "Glyph Positioning Table (GPOS)",
    "de": "Glyph-Positionierungstabelle (GPOS)",
    "fr": "Table de positionnement de glyphes (GPOS)",
    "ja": "グリフ配置テーブル (GPOS)",
    "context": "Glossary term: The OpenType table containing glyph positioning rules (kerning, mark attachment, cursive). Table tag 'GPOS' is a non-translatable token."
  },
  "vocab.anchor": {
    "en": "Anchor Point",
    "de": "Ankerpunkt",
    "fr": "Point d'ancrage",
    "ja": "アンカーポイント",
    "context": "Glossary term: A named coordinate on a glyph used in GPOS Mark-to-Base and Cursive attachment lookups."
  },
  "vocab.lookup": {
    "en": "Lookup",
    "de": "Suchtabelle",
    "fr": "Table de correspondance",
    "ja": "ルックアップ",
    "context": "Glossary term: A discrete rule set within GSUB or GPOS that performs one type of substitution or positioning."
  },
  "vocab.featureCode": {
    "en": "Feature Code",
    "de": "Feature-Code",
    "fr": "Code de fonctionnalité",
    "ja": "フィーチャーコード",
    "context": "Glossary term: The OpenType feature definition language (Adobe FDK syntax) text that describes substitution and positioning rules."
  },

  // ── Additional menu entries ────────────────────────────────────────────────

  "menu.view": {
    "en": "&View",
    "de": "&Ansicht",
    "fr": "&Affichage",
    "ja": "表示(&V)",
    "context": "Main application View menu header"
  },
  "menu.view.showMetrics": {
    "en": "Show &Metrics Lines",
    "de": "&Metriklinien anzeigen",
    "fr": "Afficher les lignes de &métriques",
    "ja": "メトリクス線を表示(&M)",
    "context": "View menu toggle to show/hide typographic guideline overlays (baseline, x-height, cap-height)"
  },
  "menu.view.showHints": {
    "en": "Show &Hints",
    "de": "&Hints anzeigen",
    "fr": "Afficher les &instructions",
    "ja": "ヒントを表示(&H)",
    "context": "View menu toggle to show/hide TrueType/PostScript hint overlays in the glyph editor"
  },
  "menu.view.showKerning": {
    "en": "Show &Kerning Pairs",
    "de": "&Unterschneidungspaare anzeigen",
    "fr": "Afficher les &paires de crénage",
    "ja": "カーニングペアを表示(&K)",
    "context": "View menu toggle to highlight active kerning pairs for the glyph under the cursor"
  },
  "menu.varfont.exportVF": {
    "en": "&Export Variable Font...",
    "de": "Variablen Schriftstil &exportieren...",
    "fr": "&Exporter la police variable...",
    "ja": "バリアブルフォントを書き出し(&E)...",
    "context": "Variable Font menu action to compile and export a .ttf variable font binary"
  },

  // ── Additional messages ───────────────────────────────────────────────────

  "msg.interpolationError": {
    "en": "Error: Master '{0}' is incompatible with master '{1}' — contour counts differ.",
    "de": "Fehler: Master '{0}' ist inkompatibel mit Master '{1}' — Konturanzahl weicht ab.",
    "fr": "Erreur: Le master '{0}' est incompatible avec le master '{1}' — le nombre de contours diffère.",
    "ja": "エラー: マスター '{0}' とマスター '{1}' の互換性がありません — 輪郭の数が異なります。",
    "context": "Designspace validation error. {0} and {1} are master names. Incompatible masters cannot be interpolated."
  },
  "msg.codepointConflict": {
    "en": "Warning: Codepoint U+{0} is assigned to {count, plural, one {one glyph} other {{count} glyphs}}.",
    "de": "Warnung: Codepunkt U+{0} ist {count, plural, one {einer Glyphe} other {{count} Glyphen}} zugewiesen.",
    "fr": "Attention: Le point de code U+{0} est assigné à {count, plural, one {un glyphe} other {{count} glyphes}}.",
    "ja": "警告: コードポイント U+{0} が {count, plural, one {1 個のグリフ} other {{count} 個のグリフ}} に割り当てられています。",
    "context": "Encoding validation. {0} is hex codepoint (4–6 uppercase hex digits, non-translatable). ICU plural on {count} for number of conflicting glyphs."
  },
  "msg.featureCompileError": {
    "en": "OpenType feature compilation failed at line {0}: {1}",
    "de": "Kompilierung der OpenType-Features fehlgeschlagen in Zeile {0}: {1}",
    "fr": "Échec de la compilation des fonctionnalités OpenType à la ligne {0}: {1}",
    "ja": "OpenType フィーチャーのコンパイルが行 {0} で失敗しました: {1}",
    "context": "Feature code editor error. {0} is line number, {1} is the compiler error message text."
  },
  "msg.cvtValueChanged": {
    "en": "CVT entry {0} changed from {1} to {2} units.",
    "de": "CVT-Eintrag {0} von {1} auf {2} Einheiten geändert.",
    "fr": "L'entrée CVT {0} a été modifiée de {1} à {2} unités.",
    "ja": "CVT エントリ {0} を {1} から {2} ユニットに変更しました。",
    "context": "Hinting inspector undo/redo description. {0} is CVT index (integer), {1} is old value, {2} is new value. 'CVT' is a non-translatable token."
  },
  "msg.zoneCount": {
    "en": "{count, plural, =0 {No alignment zones} one {One alignment zone} other {{count} alignment zones}} defined.",
    "de": "{count, plural, =0 {Keine Ausrichtungszonen} one {Eine Ausrichtungszone} other {{count} Ausrichtungszonen}} definiert.",
    "fr": "{count, plural, =0 {Aucune zone d'alignement} one {Une zone d'alignement} other {{count} zones d'alignement}} définie(s).",
    "ja": "アライメントゾーン: {count, plural, =0 {未定義} one {1 個定義済み} other {{count} 個定義済み}}。",
    "context": "Hinting inspector count. ICU plural on {count} for alignment zones. JA restructures naturally around the count."
  }
};
