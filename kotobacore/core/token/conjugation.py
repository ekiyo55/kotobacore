"""N4 語形正規化 — verb / adjective lemma, conjugation type and form (FR-002 N4, FR-010).

Rule-based and dictionary-free: auxiliaries are peeled from the right of a
conjugated surface (書かせられなかった → 書か + せ + られ + なかった), the
kana row of the remaining stem ending tells the conjugation type (五段 / 一段 /
カ変 / サ変), and the lemma is rebuilt on that row. Ambiguities that only a
dictionary can settle are resolved toward the most frequent pattern
(った → ラ行五段 「〜る」, んだ → マ行「〜む」) and the type is then labelled
``五段?``. Adjectives (形容詞) reuse the い-base lemma of token_normalizer;
形容動詞 (静かだった) are detected from the copula tail.

Returns ``ConjugationInfo(lemma, conjugation_type, conjugation_form)``; forms are
labels joined with "-" in surface order (使役-受身-否定-過去).
"""

from __future__ import annotations

from dataclasses import dataclass

from kotobacore.core.token.token_normalizer import _adjective_lemma

# ---------------------------------------------------------------- kana rows
_ROWS = (
    "あいうえお", "かきくけこ", "がぎぐげご", "さしすせそ", "ざじずぜぞ", "たちつてと", "だぢづでど",
    "なにぬねの", "はひふへほ", "ばびぶべぼ", "ぱぴぷぺぽ", "まみむめも", "やいゆえよ", "らりるれろ", "わいうえお",
)
_ROW_OF: dict[str, tuple[str, int]] = {}
for _row in _ROWS:
    for _i, _ch in enumerate(_row):
        _ROW_OF.setdefault(_ch, (_row, _i))
# い / う / え / お belong to several rows — resolve ambiguous chars to the vowel row unless a consonant row is meant
_ROW_OF["い"] = ("あいうえお", 1)
_ROW_OF["う"] = ("あいうえお", 2)
_ROW_OF["え"] = ("あいうえお", 3)
_ROW_OF["お"] = ("あいうえお", 4)
_U_ROW_CHARS = frozenset("うくぐすつぬぶむる")


def _vowel(ch: str) -> int | None:
    r = _ROW_OF.get(ch)
    return r[1] if r else None


def _to_u(ch: str) -> str | None:
    """Same consonant row, う-column (書か → く, 話し → す, 書け → く, 書こ → く)."""
    r = _ROW_OF.get(ch)
    if r is None:
        return None
    row = r[0]
    if row == "あいうえお":
        return "う"
    if row == "わいうえお":
        return "う"
    if row == "やいゆえよ":
        return "ゆ"
    return row[2]


def _is_kana(ch: str) -> bool:
    return "ぁ" <= ch <= "ゖ"


# ---------------------------------------------------------------- auxiliaries (peeled right → left)
# (suffix, form label, attaches to) — "attach" describes the stem shape the suffix follows:
#   ren  = 連用形 (i-row / e-row / kanji)      neg = 未然形 (a-row / e-row / kanji)
#   te   = テ形 (音便 stem)                    any = no constraint
_AUX: tuple[tuple[str, str, str], ...] = (
    ("ませんでした", "丁寧-否定-過去", "ren"), ("ましょう", "丁寧-意志", "ren"), ("ました", "丁寧-過去", "ren"),
    ("ません", "丁寧-否定", "ren"), ("ます", "丁寧", "ren"),
    ("なかった", "否定-過去", "neg"), ("なくて", "否定-テ形", "neg"), ("なければ", "否定-仮定", "neg"),
    ("なく", "否定-連用", "neg"), ("ない", "否定", "neg"), ("ず", "否定-連用", "neg"),
    ("たかった", "希望-過去", "ren"), ("たくて", "希望-テ形", "ren"), ("たく", "希望-連用", "ren"), ("たい", "希望", "ren"),
    ("られる", "受身", "neg"), ("られた", "受身-過去", "neg"), ("られて", "受身-テ形", "neg"), ("られ", "受身", "neg"),
    ("させる", "使役", "neg"), ("させた", "使役-過去", "neg"), ("させて", "使役-テ形", "neg"), ("させ", "使役", "neg"),
    ("れる", "受身", "neg"), ("れた", "受身-過去", "neg"), ("れて", "受身-テ形", "neg"),
    ("せる", "使役", "neg"), ("せた", "使役-過去", "neg"), ("せて", "使役-テ形", "neg"),
    ("ています", "進行-丁寧", "te"), ("ていました", "進行-丁寧-過去", "te"), ("ている", "進行", "te"), ("ていた", "進行-過去", "te"),
    ("ていて", "進行-テ形", "te"), ("てる", "進行", "te"), ("てた", "進行-過去", "te"), ("てて", "進行-テ形", "te"),
    ("てきた", "方向-過去", "te"), ("てくる", "方向", "te"), ("ていく", "方向", "te"), ("ておく", "準備", "te"), ("ておいた", "準備-過去", "te"),
    ("ちゃった", "完了-過去", "te"), ("ちゃう", "完了", "te"), ("じゃった", "完了-過去", "te"), ("じゃう", "完了", "te"),
    ("たら", "条件", "te"), ("たり", "並列", "te"), ("だら", "条件", "te"), ("だり", "並列", "te"),
    ("た", "過去", "te"), ("だ", "過去", "te"), ("て", "テ形", "te"), ("で", "テ形", "te"),
    ("ば", "仮定", "hyp"), ("よう", "意志", "vol"), ("う", "意志", "vol"),
)
_AUX_LONGEST_FIRST: tuple[tuple[str, str, str], ...] = tuple(sorted(_AUX, key=lambda x: -len(x[0])))
_CONJ_TAILS: tuple[tuple[str, str], ...] = (("ので", "接続-理由"), ("のに", "接続-逆接"), ("けれど", "接続-逆接"), ("けど", "接続-逆接"), ("から", "接続-理由"), ("ながら", "接続-同時"))
_ADJ_FORMS: tuple[tuple[str, str], ...] = (
    ("くなかった", "否定-過去"), ("くなくて", "否定-テ形"), ("くない", "否定"), ("かった", "過去"), ("ければ", "仮定"),
    ("くて", "テ形"), ("かろう", "推量"), ("く", "連用"), ("さ", "名詞化"), ("い", "基本形"),
)
_COPULA: tuple[tuple[str, str], ...] = (
    ("でした", "丁寧-過去"), ("でしょう", "推量"), ("だった", "過去"), ("だろう", "推量"), ("です", "丁寧"),
    ("なら", "仮定"), ("だ", "基本形"), ("な", "連体"), ("に", "連用"), ("で", "テ形"),
)


# Small kanji-stem tables that settle what the kana row cannot (v0.6.3). Only the
# most frequent verbs; anything else keeps the frequency-based guess and "五段?".
_TSU_STEMS = frozenset(["待", "立", "持", "打", "勝", "育", "保", "建", "経", "撃", "放", "断", "絶", "討", "発", "立ち", "目立", "役立", "成り立", "思い立", "受け持", "気持"])
_U_STEMS = frozenset(["買", "会", "合", "言", "使", "思", "歌", "笑", "払", "習", "向か", "通", "追", "迷", "誘", "願", "洗", "拾", "縫", "貰", "違", "従", "救", "吸", "奪", "揃", "疑", "戦", "争", "味わ", "賑わ", "祝", "伺", "敬", "行な", "扱", "取扱", "取り扱", "繕", "沿", "舞", "這", "酔", "喰", "食ら", "賄", "償", "担", "伴", "漂", "謳", "憂", "匂", "潤", "装", "競", "集", "鍛", "憩", "適", "覆", "慕", "補", "語ら", "交わ", "出会", "出合", "間に合", "似合", "見合", "話し合", "触れ合", "付き合", "知り合", "語り合"])
_BU_STEMS = frozenset(["飛", "遊", "呼", "選", "学", "運", "結", "並", "喜", "叫", "転", "浮か", "及", "滅", "尊", "尊", "叫", "忍", "忍", "偲", "忍", "浮", "尊", "貴", "学", "弄", "弄", "結び", "及", "跳", "跳", "飛び", "遊び", "選び"])
_NU_STEMS = frozenset(["死"])
# 一段 verbs whose stem ends in an i-row kana (indistinguishable from 五段 連用形 without this)
_ICHIDAN_I_STEMS = frozenset(
    ["起き", "生き", "尽き", "飽き", "落ち", "満ち", "過ぎ", "閉じ", "信じ", "感じ", "案じ", "存じ", "応じ", "通じ", "演じ", "生じ", "論じ", "借り", "降り", "足り", "懲り", "浴び", "染み", "試み", "顧み", "省み", "鑑み", "見", "似", "煮", "着", "居", "出来", "でき", "用い", "老い", "強い", "報い", "悔い", "率い", "干", "射", "鋳", "恥じ", "混じ", "交じ", "命じ", "禁じ", "転じ", "興じ", "講じ", "動じ", "甘んじ", "重んじ", "軽んじ"]
)


def _five_or_one_from_ren(stem: str) -> bool:
    """True when an i-row stem is a known 一段 verb (起き-ます → 起きる)."""
    return stem in _ICHIDAN_I_STEMS or any(stem.endswith(s) and not _is_kana(s[0]) for s in _ICHIDAN_I_STEMS if len(s) >= 2)


@dataclass(frozen=True)
class ConjugationInfo:
    lemma: str
    conjugation_type: str  # 五段 / 五段? / 一段 / カ変 / サ変 / 形容詞 / 形容動詞
    conjugation_form: str  # 基本形 / 命令形 / 連用形 / 過去 / 否定-過去 / 使役-受身-否定-過去 …


# ---------------------------------------------------------------- verbs


def _lemma_from_stem(stem: str, attach: str, tail: str) -> tuple[str, str] | None:
    """(lemma, type) for the part left after peeling the first auxiliary ``tail`` (attach = its stem shape)."""
    if not stem:
        return None
    last = stem[-1]
    if not _is_kana(last):
        # kanji-final stem before an auxiliary: 一段 (見ない / 見た / 見ます / 見られる) or カ変 (来た)
        if stem == "来":
            return "来る", "カ変"
        return stem + "る", "一段"
    if stem in ("し", "せ", "さ") and len(stem) == 1:
        return "する", "サ変"
    v = _vowel(last)
    if attach == "te":
        if last == "っ":
            if tail.startswith(("た", "て", "ち")):
                base = stem[:-1]
                if base in _TSU_STEMS or any(base.endswith(s) for s in _TSU_STEMS if len(s) >= 2):
                    return base + "つ", "五段"  # 待った → 待つ
                if base in _U_STEMS or any(base.endswith(s) for s in _U_STEMS if len(s) >= 2):
                    return base + "う", "五段"  # 買った → 買う
                return base + "る", "五段?"  # った → る / つ / う: ラ行 most frequent
            return None
        if last == "ん":
            base = stem[:-1]
            if base in _BU_STEMS or any(base.endswith(s) for s in _BU_STEMS if len(s) >= 2):
                return base + "ぶ", "五段"  # 飛んだ → 飛ぶ
            if base in _NU_STEMS:
                return base + "ぬ", "五段"  # 死んだ → 死ぬ
            return base + "む", "五段?"  # んだ → む / ぶ / ぬ
        if last == "い":
            return stem[:-1] + ("ぐ" if tail.startswith(("だ", "で")) else "く"), "五段"  # 書いた / 泳いだ
        if last == "し":
            return stem[:-1] + "す", "五段"  # 話した
        if v in (1, 3):  # i-row / e-row → 一段 (起きた / 食べた)
            return stem + "る", "一段"
        return None
    if attach == "neg":
        if last == "こ" and stem.endswith("こ") and len(stem) == 1:
            return "来る", "カ変"
        if v == 0:  # a-row → 五段 (書か-ない → 書く)
            return stem[:-1] + (_to_u(last) or "う"), "五段"
        if v in (1, 3):  # 一段 (食べ-ない / 起き-ない / 食べ-られる)
            return stem + "る", "一段"
        return None
    if attach == "ren":
        if v == 1:  # i-row: 五段 連用 (書き-ます → 書く) unless a known 一段 stem (起き-ます → 起きる)
            if _five_or_one_from_ren(stem):
                return stem + "る", "一段"
            u = _to_u(last)
            return (stem[:-1] + u, "五段?") if u else None
        if v == 3:  # e-row → 一段 (食べ-ます)
            return stem + "る", "一段"
        return None
    if attach == "hyp":
        if last == "れ":
            prev = stem[-2] if len(stem) >= 2 else ""
            if _is_kana(prev) and _vowel(prev) in (1, 3):
                return stem[:-1] + "る", "一段"  # 食べれ-ば
            return stem[:-1] + "る", "五段?"  # 走れ-ば / 見れ-ば
        if v == 3:
            return stem[:-1] + (_to_u(last) or "う"), "五段"  # 書け-ば
        return None
    if attach == "vol":
        if tail == "よう":
            return stem + "る", "一段"  # 食べ-よう / 見-よう
        if v == 4:  # o-row: 書こ-う → 書く
            return stem[:-1] + (_to_u(last) or "う"), "五段"
        return None
    return None


def analyze_verb(surface: str) -> ConjugationInfo | None:
    """Lemma / type / form of a conjugated verb surface (動詞-一般 token)."""
    s = surface
    if not s:
        return None
    # 形容動詞 / noun + copula (静かだった / 便利です): stem must not end with 音便 kana
    for tail, label in _COPULA:
        if s.endswith(tail) and len(s) > len(tail):
            stem = s[: -len(tail)]
            if stem[-1] not in "っんい" and not (stem[-1] in _U_ROW_CHARS) and (not _is_kana(stem[-1]) or stem.endswith(("か", "やか", "らか", "的"))):
                if tail == "だ" and _is_kana(stem[-1]) and stem[-1] in "んい":
                    break
                return ConjugationInfo(stem + "だ", "形容動詞", label)
            break
    if s in ("する", "した", "して", "します", "しました", "しません", "しない", "しなかった", "すれば", "しよう", "される", "された", "させる", "させた", "できる", "できた", "できない"):
        forms = {"する": "基本形", "した": "過去", "して": "テ形", "します": "丁寧", "しました": "丁寧-過去", "しません": "丁寧-否定", "しない": "否定",
                 "しなかった": "否定-過去", "すれば": "仮定", "しよう": "意志", "される": "受身", "された": "受身-過去", "させる": "使役", "させた": "使役-過去",
                 "できる": "可能", "できた": "可能-過去", "できない": "可能-否定"}
        return ConjugationInfo("する", "サ変", forms[s])
    labels: list[str] = []
    rest = s
    # conjunctive particles the lattice glues onto a verb (走ったので / 食べたけど): peel them first, keep as labels
    conj_labels: list[str] = []
    for tail, label in _CONJ_TAILS:
        if rest.endswith(tail) and len(rest) > len(tail) + 1:
            conj_labels.insert(0, label)
            rest = rest[: -len(tail)]
            break
    if conj_labels:
        inner = analyze_verb(rest)
        if inner is None:
            return None
        return ConjugationInfo(inner.lemma, inner.conjugation_type, "-".join([inner.conjugation_form, *conj_labels]))
    first_tail: tuple[str, str] | None = None
    changed = True
    while changed and len(rest) > 1:
        changed = False
        for tail, label, attach in _AUX_LONGEST_FIRST:
            if rest.endswith(tail) and len(rest) > len(tail):
                stem = rest[: -len(tail)]
                # a bare copula/one-char tail on a kanji-only stem is not a conjugation (山だ)
                if tail in ("だ", "で") and not _is_kana(stem[-1]):
                    continue
                # 意志の「う」は o 段にだけ付く (書こ-う)。扱う / 買う の「う」は語幹の一部
                if tail == "う" and (not _is_kana(stem[-1]) or _vowel(stem[-1]) != 4):
                    continue
                # 五段の受身・使役「れる / せる」は a 段にだけ付く (書か-れる / 書か-せる)。
                # 疲れた / 忘れた / 晴れた / 任せた の れ・せ は一段語幹の一部
                if tail in ("れる", "れた", "れて", "せる", "せた", "せて") and (not _is_kana(stem[-1]) or _vowel(stem[-1]) != 0):
                    continue
                # 「て / で」 after kanji is not a conjugation (山で / 手で)
                if tail in ("て", "で", "た") and not _is_kana(stem[-1]) and len(stem) == 1 and stem not in ("来", "見", "出", "寝", "着", "居", "似", "煮", "得", "経"):
                    continue
                labels.insert(0, label)
                first_tail = (tail, attach)
                rest = stem
                changed = True
                break
    if first_tail is None:
        # no auxiliary: 基本形 / 命令形 / 連用形 by the last kana
        last = s[-1]
        if not _is_kana(last):
            return None
        v = _vowel(last)
        if last == "る":
            prev = s[-2] if len(s) >= 2 else ""
            ctype = "一段" if (_is_kana(prev) and _vowel(prev) in (1, 3)) else "五段?"  # 見る / 走る: only a dictionary knows
            return ConjugationInfo(s, ctype, "基本形")
        if last in _U_ROW_CHARS:
            return ConjugationInfo(s, "五段", "基本形")
        if last == "ろ":
            return ConjugationInfo(s[:-1] + "る", "一段", "命令形")
        if v == 3:
            u = _to_u(last)
            return ConjugationInfo(s[:-1] + u, "五段", "命令形") if u else None
        if v == 1:
            u = _to_u(last)
            return ConjugationInfo(s[:-1] + u, "五段?", "連用形") if u else None
        return None
    tail, attach = first_tail
    got = _lemma_from_stem(rest, attach, tail)
    if got is None:
        return None
    lemma, ctype = got
    return ConjugationInfo(lemma, ctype, "-".join(labels))


# ---------------------------------------------------------------- adjectives


def analyze_adjective(surface: str) -> ConjugationInfo | None:
    lemma = _adjective_lemma(surface)
    if lemma is None:
        if len(surface) == 2 and surface.endswith("い") and not _is_kana(surface[0]):
            lemma = surface  # 高い / 良い — too short for _adjective_lemma's stem rule
        else:
            return None
    for tail, label in _ADJ_FORMS:
        if surface.endswith(tail) and len(surface) > len(tail):
            return ConjugationInfo(lemma, "形容詞", label)
    return ConjugationInfo(lemma, "形容詞", "基本形")


def analyze_conjugation(surface: str, pos: str) -> ConjugationInfo | None:
    """Dispatch on the token POS; None when the surface is not a recognisable conjugation."""
    if pos.startswith("形容詞"):
        return analyze_adjective(surface)
    if pos.startswith("動詞"):
        return analyze_verb(surface)
    return None
