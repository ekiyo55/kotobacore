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

from kotobacore.core.token.token_normalizer import _ADJ_STEMS, _adjective_lemma

# one-kanji adjective stems (怖-く / 遅-く / 悪-く)
_ADJ_STEMS_1 = frozenset(x for x in _ADJ_STEMS if len(x) == 1) | frozenset("厚熱温涼痒臭酸辛惜醜汚難堅鈍疎")
# く / ぐ verbs whose イ音便 stem (聞い-て / 鳴い-た) can surface as a 2-char token
_I_ONBIN_VERBS = frozenset("聞鳴湧沸引覗書置咲泣働歩動描解抱磨吹招履嘆裂輝導築乾驚急泳脱注騒嗅焼剥浮敷巻続除開着付")

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
    ("れ", "受身", "neg"), ("せ", "使役", "neg"),
    ("ています", "進行-丁寧", "te"), ("ていました", "進行-丁寧-過去", "te"), ("ている", "進行", "te"), ("ていた", "進行-過去", "te"),
    ("ていて", "進行-テ形", "te"), ("てる", "進行", "te"), ("てた", "進行-過去", "te"), ("てて", "進行-テ形", "te"),
    # v1.1: negated progressive peeled as one unit (払われ-ていない → 払う, not 払われている)
    ("ていない", "進行-否定", "te"), ("ていなかった", "進行-否定-過去", "te"), ("ていません", "進行-丁寧-否定", "te"),
    # v1.1: auxiliary verbs after the テ形 (出-てしまった → 出る, 助け-てくれて → 助ける)
    ("てしまう", "完了", "te"), ("てしまった", "完了-過去", "te"), ("てしまって", "完了-テ形", "te"),
    ("でしまう", "完了", "te"), ("でしまった", "完了-過去", "te"), ("でしまって", "完了-テ形", "te"),
    ("ちゃって", "完了-テ形", "te"), ("じゃって", "完了-テ形", "te"),
    ("てくれる", "授受", "te"), ("てくれた", "授受-過去", "te"), ("てくれて", "授受-テ形", "te"), ("てくれない", "授受-否定", "te"),
    ("てくれません", "授受-丁寧-否定", "te"), ("でくれる", "授受", "te"), ("でくれた", "授受-過去", "te"), ("でくれて", "授受-テ形", "te"),
    ("でくれない", "授受-否定", "te"),
    ("てほしい", "願望", "te"), ("でほしい", "願望", "te"),
    ("ております", "進行-謙譲", "te"), ("ておりました", "進行-謙譲-過去", "te"), ("ておりません", "進行-謙譲-否定", "te"), ("ておる", "進行-謙譲", "te"),
    ("でおります", "進行-謙譲", "te"), ("てきて", "方向-テ形", "te"), ("ていった", "方向-過去", "te"), ("ていって", "方向-テ形", "te"),
    ("なくなった", "否定-変化-過去", "neg"), ("なくなる", "否定-変化", "neg"), ("なくなって", "否定-変化-テ形", "neg"),
    ("たくない", "希望-否定", "ren"), ("たくなかった", "希望-否定-過去", "ren"), ("たくなる", "希望-変化", "ren"),
    ("てない", "進行-否定", "te"), ("てなかった", "進行-否定-過去", "te"),
    ("でいる", "進行", "te"), ("でいた", "進行-過去", "te"), ("でいます", "進行-丁寧", "te"), ("でいて", "進行-テ形", "te"),
    ("でいない", "進行-否定", "te"), ("でいなかった", "進行-否定-過去", "te"), ("でいません", "進行-丁寧-否定", "te"),
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
# v1.1 additions (DD evaluation / Sudachi agreement): 間違った → 間違う, 誓った → 誓う
_U_STEMS = _U_STEMS | frozenset(["間違", "誓", "遭", "喰ら", "手伝", "向き合", "問", "負"])
# kanji that can end a 一段 stem directly before an auxiliary (見-ない / 出-た / 来-た).
# Any other kanji-final stem is not a verb conjugation (捨|てた is 捨て-た, 冷|たい is an adjective).
_KANJI_ICHIDAN = frozenset("見出寝着居似煮得経来干射鋳")
# one-kanji サ変 verbs (愛-する / 有-する); 2+ kanji / katakana + し is always サ変 (採用し-て)
_SAHEN_1 = frozenset("愛有要関対発属反課接達察略訳律制命称擁熱信感")
# 一段 verbs that look like 五段 stem + passive れる
_ICHIDAN_RE = ("生まれ", "産まれ", "恵まれ")
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
    if last == "し" and _is_sahen_noun(stem[:-1]):
        return stem[:-1] + "する", "サ変"  # 採用し-ていない / 存在し-ない / 昇天し-そう
    if not _is_kana(last) and tail.startswith("させ") and _is_sahen_noun(stem):
        return stem + "する", "サ変"  # 勉強-させる
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
                if base.endswith("行"):
                    return base + "く", "五段"  # 行った → 行く (カ行 促音便の例外)
                if base in _TSU_STEMS or any(base.endswith(s) for s in _TSU_STEMS):
                    return base + "つ", "五段"  # 待った → 待つ
                if base in _U_STEMS or any(base.endswith(s) for s in _U_STEMS):
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
                if tail in ("れる", "れた", "れて", "せる", "せた", "せて", "れ", "せ") and (not _is_kana(stem[-1]) or _vowel(stem[-1]) != 0):
                    continue
                # bare れ / せ only inside a テ形 chain (扱われ|ている); before ない it is a potential 一段 (満たせない)
                if tail == "れ" and first_tail is None:
                    continue
                if tail == "せ" and (first_tail is None or first_tail[1] != "te"):
                    continue  # 満たせ-ない is the potential 満たせる, not 満た + causative
                if tail.startswith("れ") and (stem + "れ").endswith(_ICHIDAN_RE):
                    continue  # 生まれた → 生まれる, not 生む + passive
                # a kanji-final stem only takes an auxiliary when it is a one-kanji 一段 stem (見-た / 来-た);
                # 捨|てた is 捨て-た and 冷|たい is not a verb at all
                if not _is_kana(stem[-1]) and stem[-1] not in _KANJI_ICHIDAN and not tail.startswith("させ"):
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
            if last == "い" and not _is_kana(s[-2]):
                base = s[:-1]
                if base in _U_STEMS or any(base.endswith(x) for x in _U_STEMS) or base.endswith("行"):
                    return ConjugationInfo(base + "う", "五段", "連用形")  # 思い / 言い / 行い
                return ConjugationInfo(base + "く", "五段", "連用形")  # 聞い(て) / 鳴い(て): イ音便
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


def _is_sahen_noun(x: str) -> bool:
    """True for a サ変 noun stem: 2+ kanji / katakana (採用 / ツイート) or a one-kanji サ変 (愛 / 有)."""
    if not x or any("ぁ" <= c <= "ゖ" for c in x):
        return False
    return len(x) >= 2 or x in _SAHEN_1


# v1.1: ない-adjectives and other adjectives the kana rules read as verbs (情けない → 情ける)
_KNOWN_ADJ = frozenset([
    "情けない", "揺るぎない", "極まりない", "仕方ない", "仕様がない", "切ない", "やるせない", "危ない", "少ない",
    "味気ない", "素っ気ない", "呆気ない", "頼りない", "物足りない", "申し訳ない", "もったいない", "勿体ない",
    "だらしない", "くだらない", "つまらない", "間違いない", "絶え間ない", "忙しない", "心許ない", "心もとない",
    "容赦ない", "他愛ない", "あどけない", "はしたない", "とんでもない", "途方もない", "限りない", "数限りない",
    "抜け目ない", "冷たい", "重たい", "眠たい", "平たい", "煙たい", "野暮ったい",
    "大きい", "小さい", "羨ましい", "恥ずかしい", "懐かしい", "騒がしい", "愛おしい", "腹立たしい", "苛立たしい",
    "素晴らしい", "甚だしい", "望ましい", "好ましい", "恐ろしい", "汚らしい", "可愛らしい", "目覚ましい",
    "美味しい", "可笑しい", "大人しい", "図々しい", "仰々しい", "清々しい", "毒々しい", "馬鹿馬鹿しい", "馬鹿らしい",
    "慌ただしい", "喧しい", "疑わしい", "紛らわしい", "煩わしい", "嘆かわしい", "ふさわしい", "相応しい",
])
# kanji + か verbs that are not か-adjectives (向か-い / 分か-る / 助か-った)
_KA_VERBS = frozenset("向分助受浮掛懸預授儲")
_ADJ_TAILS = ("くなかった", "くなって", "くなった", "くなる", "くない", "かった", "ければ", "くて", "く", "さ", "い")
_NAI_TAILS = ("なかった", "なくて", "なく", "ない")


def _adj_by_shape(s: str) -> ConjugationInfo | None:
    """Adjective lemma from the surface shape alone, whatever POS the lattice gave.

    激しく → 激しい / 怖く → 怖い / 暖かかった → 暖かい / 情けない → 情けない /
    必要ない → 必要ない (noun + ない stays one adjective-like lemma).
    """
    for adj in _KNOWN_ADJ:
        head = adj[:-1]
        if s.startswith(head) and s[len(head):] in _ADJ_TAILS:
            return ConjugationInfo(adj, "形容詞", _adj_label(s[len(head):]))
    for tail in _ADJ_TAILS:
        if not s.endswith(tail) or len(s) <= len(tail):
            continue
        x = s[: -len(tail)]
        if len(x) >= 2 and x[-1] == "し" and (not _is_kana(x[-2]) or x.endswith("らし")):
            return ConjugationInfo(x + "い", "形容詞", _adj_label(tail))  # 激し-く / 悲し-くなった / 誇らし-く
        if not _is_kana(x[-1]) and x[-1] in _ADJ_STEMS_1:
            return ConjugationInfo(x + "い", "形容詞", _adj_label(tail))  # 怖-く / 気持ち悪-く
        if len(x) >= 2 and x[-1] == "か" and not _is_kana(x[-2]) and x[-2] not in _KA_VERBS                 and tail in ("い", "く", "くて", "かった"):
            return ConjugationInfo(x + "い", "形容詞", _adj_label(tail))  # 暖か-い / 細か-く
    # noun + ない (必要ない / 仕方なく / 躊躇なく): kanji-final, not a 一段 stem
    for tail in _NAI_TAILS:
        if s.endswith(tail) and len(s) > len(tail):
            x = s[: -len(tail)]
            if not _is_kana(x[-1]) and x[-1] not in _KANJI_ICHIDAN:
                return ConjugationInfo(x + "ない", "形容詞", _adj_label("く" if tail == "なく" else "い"))
    return None


def _adj_label(tail: str) -> str:
    for t, label in _ADJ_FORMS:
        if t == tail:
            return label
    return {"くなった": "変化-過去", "くなる": "変化", "くなって": "変化-テ形"}.get(tail, "基本形")


# outer tails peeled before the verb / adjective analysis: modality after a dictionary / past form
_MODAL_TAILS: tuple[tuple[str, str], ...] = (
    ("んです", "説明-丁寧"), ("のです", "説明-丁寧"), ("んだ", "説明"), ("のだ", "説明"),
    # v1.1: polite copula after an adjective (遅いです / 美味しかったです / 高いでしょう) — only after い / た
    ("でしょう", "丁寧-推量"), ("でした", "丁寧-過去"), ("です", "丁寧"),
    ("ようだ", "様態"), ("ように", "様態"), ("ような", "様態"), ("よう", "様態"),
    ("らしい", "推定"), ("みたい", "推定"), ("だけで", "限定"), ("だけ", "限定"),
)
# すぎる / そう attach to an adjective stem or a verb 連用形 (面白-すぎて / 泣き-そう)
_SUGI_TAILS = ("すぎる", "すぎた", "すぎて", "すぎてる", "すぎてた", "すぎない", "すぎます", "すぎました", "すぎ",
               "過ぎる", "過ぎた", "過ぎて", "過ぎてる")
_SOU_TAILS = ("そうになってる", "そうになって", "そうになった", "そうになる", "そうで", "そうだ", "そうに", "そうな", "そう")


def _from_stem_part(x: str) -> ConjugationInfo | None:
    """Lemma of the part before すぎる / そう: adjective stem or verb 連用形."""
    if not x:
        return None
    if x in ("な", "よ"):
        return None
    for adj in _KNOWN_ADJ:
        if x in (adj[:-1], adj[:-1] + "さ"):
            return ConjugationInfo(adj, "形容詞", "語幹")  # 美味し-そう / 情けな-さ-そう
    if (len(x) >= 2 and x[-1] == "し" and not _is_kana(x[-2]) and not _is_sahen_noun(x[:-1])
            and x[:-1] not in _VERB_SHI_STEMS) \
            or (not _is_kana(x[-1]) and x[-1] in _ADJ_STEMS_1) \
            or (len(x) >= 2 and x[-1] == "か" and not _is_kana(x[-2]) and x[-2] not in _KA_VERBS):
        return ConjugationInfo(x + "い", "形容詞", "語幹")  # 面白-すぎ / 美味し-そう
    if _is_kana(x[-1]) and _vowel(x[-1]) in (1, 3):
        got = _lemma_from_stem(x, "ren", "")
        if got:
            return ConjugationInfo(got[0], got[1], "連用形")  # 泣き-そう → 泣く / 昇天し-そう → 昇天する
    return None


# 1-kanji + し verbs (押し-すぎ / 話し-そう) that must not be read as し-adjectives
_VERB_SHI_STEMS = frozenset("押話出探残返消渡貸隠刺指差推回落起倒壊流移写増減通直試示表記")


# Words that look like a conjugated adjective / verb but are not one (v1.1): 若しく(は) is the
# conjunction もしくは, not 若しい (the kanji+し+く adjective shape rule would read it that way)
_NOT_CONJUGATED = frozenset(("若しく", "若しくは", "若し"))


def analyze_conjugation(surface: str, pos: str) -> ConjugationInfo | None:
    """Lemma / type / form of a verb or adjective token (None when not recognisable).

    v1.1: the surface shape decides before the lattice POS does — the lattice
    labels some adjectives 動詞 (激しく / 情けない) and some verbs 形容詞
    (思い / 受かった / 関わりたくない) — and outer tails (〜んだ / 〜よう /
    〜すぎる / 〜そう) are peeled first so the lemma is the content word.
    """
    if not pos.startswith(("形容詞", "動詞")) or not surface or surface in _NOT_CONJUGATED:
        return None
    s = surface
    for tail, label in _MODAL_TAILS:
        if s.endswith(tail) and len(s) > len(tail) + 1:
            inner = s[: -len(tail)]
            if inner[-1] in _U_ROW_CHARS or inner.endswith(("た", "だ", "ない", "い")):
                got = analyze_conjugation(inner, pos)
                if got is not None:
                    return ConjugationInfo(got.lemma, got.conjugation_type, got.conjugation_form + "-" + label)
            break
    for tails in (_SUGI_TAILS, _SOU_TAILS):
        for tail in tails:
            k = s.find(tail)
            if k > 0 and s[k:] in tails:
                got = _from_stem_part(s[:k])
                if got is not None:
                    return ConjugationInfo(got.lemma, got.conjugation_type, "過度" if tails is _SUGI_TAILS else "様態")
                break
    adj = _adj_by_shape(s)
    if adj is not None:
        return adj
    if pos.startswith("形容詞") and not _verb_shaped(s):
        return analyze_adjective(s)  # やばい / すごく / 誇らしく — the lattice was right
    verb = analyze_verb(s)
    if verb is not None:
        return verb
    if pos.startswith("形容詞"):
        return analyze_adjective(s)
    return None


def _verb_shaped(s: str) -> bool:
    """A 形容詞 token that is really a verb: 思い / 言い (kanji ∈ う-verb stems + い),
    受かった (kanji stem that is no adjective), 関わりたくない (verb 連用 + たい)."""
    if len(s) == 2 and s[1] == "い" and not _is_kana(s[0]):
        # 思い / 言い (う-verbs) and 聞い / 鳴い (イ音便) are verbs; 高い / 難い / 厚い stay adjectives
        return s[0] in _U_STEMS or s[0] == "行" or s[0] in _I_ONBIN_VERBS
    lemma = _adjective_lemma(s)
    if lemma is None and len(s) >= 2 and not _is_kana(s[0]):
        lemma = s[0] + "い" if s[1:] in ("かった", "く", "くて", "くない", "ければ") else None
    if lemma is None:
        return False
    if len(lemma) == 2 and not _is_kana(lemma[0]) and lemma[0] not in _ADJ_STEMS_1 and lemma != s:
        return True  # 受かった → 受い is no adjective
    return lemma.endswith("たい") and len(lemma) > 3 and _is_kana(lemma[-3]) and _vowel(lemma[-3]) in (1, 3)
