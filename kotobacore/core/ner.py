"""Entity extraction (Core): dictionary NER + pattern NER + Time + Quantity.

Per 要件定義書 v0.4 FR-030〜FR-034. Works on the *normalized* text (NFKC, so
digits are ASCII) and token list; the Analyzer remaps spans to original
coordinates afterwards.

Sources and precedence when spans overlap (longer span wins, then this order):

    time > quantity > dictionary > pattern

Conventions (aligned with the annotated evaluation set):
- PERSON keeps the honorific in the surface (田中さん, 佐藤先生); ``normalized``
  is the bare name.
- N日前 / N年後 are DATE (relative); bare durations (3日, 1週間, 3年) are
  QUANTITY with the unit.
- 4-digit + 年 is DATE; 年度 gives ``normalized="FY2025"``.
"""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass

from kotobacore.core.ir import Entity, SemanticToken, Token
from kotobacore.core.matching import SurfaceMatcher
from kotobacore.dictionary import DictionaryBundle

# ---------------------------------------------------------------------------
# Numbers
# ---------------------------------------------------------------------------

_KANJI_DIGITS = {"〇": 0, "零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_KANJI_SMALL = {"十": 10, "百": 100, "千": 1000}
_KANJI_BIG = {"万": 10**4, "億": 10**8, "兆": 10**12}
_NUM_RE = r"(?:約|およそ|ざっと|およそ|数)?(?:[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?|[〇零一二三四五六七八九十百千]+)(?:[万億兆千百]+)?"


def parse_number(text: str) -> float | None:
    """Parse ``5,000`` / ``1万`` / ``45億`` / ``百万`` / ``三千五百`` → float."""
    t = text.replace(",", "")
    for pre in ("約", "およそ", "ざっと", "数"):
        t = t.removeprefix(pre)
    if not t:
        return None
    m = re.match(r"^([0-9]+(?:\.[0-9]+)?)([万億兆千百]*)$", t)
    if m:
        value = float(m.group(1))
        for ch in m.group(2):
            value *= _KANJI_BIG.get(ch) or _KANJI_SMALL.get(ch, 1)
        return value
    # pure kanji numeral
    total = 0.0
    section = 0.0
    current = 0.0
    for ch in t:
        if ch in _KANJI_DIGITS:
            current = current * 10 + _KANJI_DIGITS[ch]
        elif ch in _KANJI_SMALL:
            section += (current or 1) * _KANJI_SMALL[ch]
            current = 0
        elif ch in _KANJI_BIG:
            total += (section + current or 1) * _KANJI_BIG[ch]
            section = 0
            current = 0
        else:
            return None
    return total + section + current


# ---------------------------------------------------------------------------
# Time (FR-032)
# ---------------------------------------------------------------------------

_RELATIVE_DAYS: dict[str, int] = {
    "今日": 0, "本日": 0, "今朝": 0, "今晩": 0, "今夜": 0, "明日": 1, "翌日": 1, "明後日": 2,
    "昨日": -1, "昨夜": -1, "前日": -1, "一昨日": -2,
}
_RELATIVE_OTHER: dict[str, str] = {
    "今週": "this_week", "先週": "last_week", "来週": "next_week", "再来週": "week_after_next",
    "今月": "this_month", "先月": "last_month", "来月": "next_month",
    "今年": "this_year", "昨年": "last_year", "去年": "last_year", "来年": "next_year", "一昨年": "two_years_ago",
    "今年度": "this_fy", "昨年度": "last_fy", "前年度": "last_fy", "来年度": "next_fy", "翌年度": "next_fy",
    "週末": "weekend", "月末": "month_end", "年末": "year_end", "年始": "year_start", "上半期": "h1", "下半期": "h2",
    # v0.6.6 (human evaluation set): colloquial / business relative expressions without an ISO value
    "先日": "recent_days", "先週末": "last_weekend", "今週末": "this_weekend", "この前": "recent", "こないだ": "recent", "この間": "recent",
    "さっき": "just_now", "先ほど": "just_now", "今期": "this_term", "来期": "next_term", "前期": "last_term", "当期": "this_term",
    "子どもの頃": "childhood", "子供の頃": "childhood", "幼い頃": "childhood", "学生時代": "student_days", "給料日前": "before_payday",
    "今度の日曜": "next_sunday", "今度の土曜": "next_saturday", "今度の週末": "next_weekend",
}
_WEEKDAYS = "月火水木金土日"
_ERA_BASE = {"令和": 2018, "平成": 1988, "昭和": 1925}

_TIME_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ymd", re.compile(r"(?P<y>[0-9]{4})年(?P<m>[0-9]{1,2})月(?P<d>[0-9]{1,2})日")),
    ("slash", re.compile(r"(?P<y>[0-9]{4})[/.-](?P<m>[0-9]{1,2})[/.-](?P<d>[0-9]{1,2})")),
    ("ym", re.compile(r"(?P<y>[0-9]{4})年(?P<m>[0-9]{1,2})月")),
    ("md", re.compile(r"(?P<m>[0-9]{1,2})月(?P<d>[0-9]{1,2})日")),
    ("fy", re.compile(r"(?P<y>[0-9]{4})年度")),
    ("era", re.compile(r"(?P<era>令和|平成|昭和)(?P<n>[0-9]{1,2}|元)年(?:度)?")),
    ("year", re.compile(r"(?P<y>[0-9]{4})年")),
    ("month", re.compile(r"(?<![0-9])(?P<m>[0-9]{1,2})月(?![0-9])")),
    ("clock", re.compile(r"(?P<pre>午前|午後|朝|夜|深夜|毎朝|毎晩|毎日)?(?P<h>[0-9]{1,2})時(?P<half>半)?(?:(?P<mi>[0-9]{1,2})分)?")),
    ("hhmm", re.compile(r"(?<![0-9:])(?P<h>[0-9]{1,2}):(?P<mi>[0-9]{2})(?![0-9])")),
    ("weekday", re.compile(r"(?P<w>[月火水木金土日])曜(?:日)?")),
    ("rel_n", re.compile(rf"(?P<n>{_NUM_RE})(?P<u>日|週間|か月|ヶ月|カ月|ヵ月|年|時間|分)(?P<dir>前|後)")),
    ("rel_word", re.compile("|".join(sorted([*_RELATIVE_DAYS, *_RELATIVE_OTHER], key=len, reverse=True)))),
]

_DURATION_UNITS = {"日": ("days", 1), "週間": ("days", 7), "か月": ("months", 1), "ヶ月": ("months", 1),
                   "カ月": ("months", 1), "ヵ月": ("months", 1), "年": ("years", 1), "時間": ("hours", 1), "分": ("minutes", 1)}


def _shift(ref: _dt.date, n: float, unit: str) -> str | None:
    kind, mult = _DURATION_UNITS[unit]
    n = int(n)
    if kind == "days":
        return (ref + _dt.timedelta(days=n * mult)).isoformat()
    if kind == "months":
        m = ref.month - 1 + n
        y = ref.year + m // 12
        return f"{y:04d}-{m % 12 + 1:02d}"
    if kind == "years":
        return f"{ref.year + n:04d}"
    return None


def _rel_word_value(word: str, ref: _dt.date | None) -> tuple[str | None, str]:
    """(iso value or None, normalized label)"""
    if word in _RELATIVE_DAYS:
        off = _RELATIVE_DAYS[word]
        return ((ref + _dt.timedelta(days=off)).isoformat() if ref else None), f"{off:+d}d"
    label = _RELATIVE_OTHER[word]
    if ref is None:
        return None, label
    if label.endswith("_week"):
        delta = {"this_week": 0, "last_week": -7, "next_week": 7}.get(label, 14)
        monday = ref - _dt.timedelta(days=ref.weekday()) + _dt.timedelta(days=delta)
        return monday.isoformat(), label
    if label.endswith("_month"):
        delta = {"this_month": 0, "last_month": -1, "next_month": 1}[label]
        return _shift(ref, delta, "か月"), label
    if label.endswith("_year") or label == "two_years_ago":
        delta = {"this_year": 0, "last_year": -1, "next_year": 1, "two_years_ago": -2}[label]
        return f"{ref.year + delta:04d}", label
    if label.endswith("_fy"):
        fy = ref.year if ref.month >= 4 else ref.year - 1
        delta = {"this_fy": 0, "last_fy": -1, "next_fy": 1}[label]
        return f"FY{fy + delta}", label
    return None, label


@dataclass
class _Cand:
    type: str
    begin: int
    end: int
    normalized: str | None
    source: str
    value: object = None
    unit: str | None = None
    currency: str | None = None
    priority: int = 0  # lower wins on equal length


def _time_candidates(text: str, ref: _dt.date | None) -> list[_Cand]:
    out: list[_Cand] = []
    claimed = bytearray(len(text))
    for kind, pat in _TIME_PATTERNS:
        for m in pat.finditer(text):
            b, e = m.start(), m.end()
            if any(claimed[b:e]):
                continue
            g = m.groupdict()
            typ, norm, value = "DATE", None, None
            try:
                if kind in ("ymd", "slash"):
                    value = norm = f"{int(g['y']):04d}-{int(g['m']):02d}-{int(g['d']):02d}"
                elif kind == "ym":
                    value = norm = f"{int(g['y']):04d}-{int(g['m']):02d}"
                elif kind == "md":
                    norm = f"--{int(g['m']):02d}-{int(g['d']):02d}"
                    value = f"{ref.year:04d}-{int(g['m']):02d}-{int(g['d']):02d}" if ref else None
                elif kind == "fy":
                    value = norm = f"FY{int(g['y'])}"
                elif kind == "era":
                    n = 1 if g["n"] == "元" else int(g["n"])
                    y = _ERA_BASE[g["era"]] + n
                    value = norm = (f"FY{y}" if m.group(0).endswith("度") else f"{y:04d}")
                elif kind == "year":
                    value = norm = f"{int(g['y']):04d}"
                elif kind == "month":
                    norm = f"--{int(g['m']):02d}"
                    value = f"{ref.year:04d}-{int(g['m']):02d}" if ref else None
                elif kind == "clock":
                    typ = "TIME"
                    h = int(g["h"])
                    if g["pre"] in ("午後", "夜", "深夜", "毎晩") and h < 12:
                        h += 12
                    mi = 30 if g["half"] else int(g["mi"] or 0)
                    if h > 24 or mi > 59:
                        continue
                    value = norm = f"{h % 24:02d}:{mi:02d}"
                elif kind == "hhmm":
                    typ = "TIME"
                    h, mi = int(g["h"]), int(g["mi"])
                    if h > 24 or mi > 59:
                        continue
                    value = norm = f"{h:02d}:{mi:02d}"
                elif kind == "weekday":
                    norm = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][_WEEKDAYS.index(g["w"])]
                    value = norm
                elif kind == "rel_n":
                    n = parse_number(g["n"])
                    if n is None:
                        continue
                    sign = -1 if g["dir"] == "前" else 1
                    unit = g["u"]
                    typ = "TIME" if unit in ("時間", "分") else "DATE"
                    norm = f"{sign * int(n):+d}{unit}"
                    value = _shift(ref, sign * n, unit) if (ref and typ == "DATE") else None
                elif kind == "rel_word":
                    value, norm = _rel_word_value(m.group(0), ref)
            except (ValueError, KeyError):
                continue
            for i in range(b, e):
                claimed[i] = 1
            out.append(_Cand(typ, b, e, norm, "time", value, priority=0))
    return out


# ---------------------------------------------------------------------------
# Quantity / Money (FR-033)
# ---------------------------------------------------------------------------

_CURRENCY = {"円": "JPY", "ドル": "USD", "ユーロ": "EUR", "元": "CNY", "ウォン": "KRW", "ポンド": "GBP", "$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}
_MONEY_RE = re.compile(rf"(?P<n>{_NUM_RE})(?P<u>円|ドル|ユーロ|ウォン|ポンド)|(?P<sym>[$€£¥])(?P<n2>[0-9]+(?:,[0-9]{{3}})*(?:\.[0-9]+)?)")
_QTY_UNITS = (
    "人|名|個|件|台|枚|本|冊|回|度|軒|社|店|品|点|通|箱|袋|缶|杯|皿|着|足|頭|匹|羽|部|巻|話|曲|問|行|字|文字|語|ページ|頁|"
    "kg|g|t|km|m|cm|mm|L|l|ml|GB|MB|TB|KB|バイト|%|％|パーセント|割|倍|時間|分|秒|日|週間|か月|ヶ月|カ月|ヵ月|年|歳|才|世紀|"
    "km/h|畳|坪|㎡|㎥|℃|度|ポイント|pt|px|インチ|フィート|マイル|カロリー|kcal|号|番|位|級|段|世帯|校|局|隻|機|両|席|室|階"
)
_QTY_RE = re.compile(rf"(?P<n>{_NUM_RE})(?P<u>{_QTY_UNITS})(?![0-9])")


def _quantity_candidates(text: str, claimed: bytearray) -> list[_Cand]:
    out: list[_Cand] = []
    for m in _MONEY_RE.finditer(text):
        b, e = m.start(), m.end()
        if any(claimed[b:e]):
            continue
        n = parse_number(m.group("n") or m.group("n2"))
        if n is None:
            continue
        unit = m.group("u") or m.group("sym")
        out.append(_Cand("MONEY", b, e, None, "quantity", n, unit, _CURRENCY.get(unit), priority=1))
        for i in range(b, e):
            claimed[i] = 1
    for m in _QTY_RE.finditer(text):
        b, e = m.start(), m.end()
        if any(claimed[b:e]):
            continue
        n = parse_number(m.group("n"))
        if n is None:
            continue
        out.append(_Cand("QUANTITY", b, e, None, "quantity", n, m.group("u"), None, priority=1))
        for i in range(b, e):
            claimed[i] = 1
    return out


# ---------------------------------------------------------------------------
# Pattern NER (FR-031)
# ---------------------------------------------------------------------------

_ORG_SUFFIX = ("株式会社", "有限会社", "合同会社", "ホールディングス", "グループ", "商事", "電機", "電気", "工業", "産業", "物産",
               "銀行", "証券", "保険", "大学", "高校", "中学校", "小学校", "病院", "協会", "組合", "連盟", "財団", "研究所",
               "支社", "支店", "本社", "本店", "工場", "法人", "学園", "学院", "委員会", "事務所", "商店", "書店", "放送",
               "新聞", "出版", "省", "庁", "社",
               "物流", "運輸", "建設", "不動産", "製作所", "製薬", "鉄道", "商会")  # v0.6.2
_LOC_SUFFIX = ("都", "道", "府", "県", "市", "区", "町", "村", "郡", "駅", "空港", "港", "山", "川", "湖", "島", "公園", "通り",
               "交差点", "ビル", "タワー", "海岸", "温泉", "神社", "寺", "城", "橋", "商店街", "街")
_PERSON_SUFFIX = ("さん", "氏", "様", "君", "くん", "ちゃん", "先生", "社長", "副社長", "部長", "課長", "係長", "主任", "専務",
                  "常務", "会長", "教授", "博士", "監督", "選手", "議員", "大臣", "首相", "知事", "市長", "店長", "編集長")
_EVENT_SUFFIX = ("大会", "祭り", "祭", "フェス", "展", "セミナー", "研修", "総会", "会議", "発表会", "説明会", "譲渡会", "万博",
                 "フェア", "イベント", "コンテスト", "選手権", "オリンピック", "式典", "講演会", "勉強会", "交流会", "懇親会",
                 "展示会", "ライブ", "コンサート", "キャンペーン")
_SUFFIX_TABLE: list[tuple[tuple[str, ...], str]] = [
    (_ORG_SUFFIX, "ORGANIZATION"), (_LOC_SUFFIX, "LOCATION"), (_PERSON_SUFFIX, "PERSON"), (_EVENT_SUFFIX, "EVENT"),
]
_ONE_CHAR_SUFFIX = {s for group, _ in _SUFFIX_TABLE for s in group if len(s) == 1}
_PERSON_BLOCK = {
    "お客", "客", "皆", "みな", "皆さま", "皆様", "店員", "社員", "担当", "担当者", "上司", "部下", "先方", "相手", "奥",
    "母", "父", "兄", "姉", "弟", "妹", "息子", "娘", "子供", "子ども", "患者", "生徒", "学生", "利用者", "ユーザ", "ユーザー",
    "新人", "後輩", "先輩", "同僚", "友達", "友人", "彼", "彼女", "俺", "私", "僕", "自分", "本人", "各位", "関係者", "みんな",
    "お母", "お父", "お兄", "お姉", "おじ", "おば", "お嬢", "お坊", "諸君", "一同", "誰", "だれ", "どなた", "皆さん",
}
_HIRAGANA_RE = re.compile(r"^[ぁ-ゖー]+$")
_LEGAL_PREFIX = ("株式会社", "有限会社", "合同会社", "一般社団法人", "公益社団法人", "一般財団法人", "公益財団法人", "社会福祉法人", "学校法人", "医療法人", "特定非営利活動法人")


def _is_nounish(tok: Token) -> bool:
    return "名詞" in tok.pos and "代名詞" not in tok.pos and "数詞" not in tok.pos


_PRODUCT_CODE_RE = re.compile(r"(?<![A-Za-z0-9])(?:[A-Z]{1,5}-?[0-9]{2,5}[A-Z]{0,2}|[A-Z]{1,3}-[A-Z]{1,3}[0-9]{2,5})(?![A-Za-z0-9])")
# quoted names (v0.6.6)
_QUOTED_NAME_RE = re.compile(r"[「『](?P<q>[^「」『』\n]{1,20})[」』]")
_QUOTE_DIALOGUE_RE = re.compile(r"^\s*(?:と(?:言|云|呟|叫|頼|答|返|聞|尋|囁|思)|って(?:言|叫))")
_QUOTE_NAME_AFTER_RE = re.compile(r"^(?:は|が|を|って|という|と呼|の|も|に|へ|、|:|：|\s*$|\s*[（(])")
_QUOTE_NAME_BEFORE_RE = re.compile(r"(?:名前の|名の|新サービス|新製品|製品|商品|ブランド|タイトル|作品|コーナー|機能|アプリ|サービス|ライブラリ|シリーズ|企画|番組|曲|本|映画|ゲーム)\s*$")
_QUOTE_TYPE_HINTS: tuple[tuple[str, str], ...] = (
    ("パン屋", "ORGANIZATION"), ("店", "ORGANIZATION"), ("会社", "ORGANIZATION"), ("部門", "ORGANIZATION"),
    ("ブランド", "BRAND"), ("タイトル", "WORK"), ("作品", "WORK"), ("コーナー", "WORK"), ("番組", "WORK"), ("曲", "WORK"), ("本", "WORK"), ("映画", "WORK"), ("小説", "WORK"),
    ("サービス", "SERVICE"), ("アプリ", "SERVICE"),
    ("商品", "PRODUCT"), ("製品", "PRODUCT"), ("機能", "PRODUCT"), ("ライブラリ", "PRODUCT"), ("加湿器", "PRODUCT"), ("ゲーム", "WORK"),
)


def _pattern_candidates(text: str, tokens: list[Token], claimed: bytearray, stopwords: set[str]) -> list[_Cand]:
    out: list[_Cand] = []
    n = len(tokens)
    # Product / model codes (MX-500, X200, TN-X200, E-52): the tokenizer splits
    # them into letters / hyphen / digits, so match on the text.
    for m in _PRODUCT_CODE_RE.finditer(text):
        b, e = m.start(), m.end()
        if any(claimed[b:e]):
            continue
        out.append(_Cand("PRODUCT", b, e, m.group(0), "pattern", priority=3))
        for i in range(b, e):
            claimed[i] = 1

    def _free(b: int, e: int) -> bool:
        return not any(claimed[b:e])

    def _push(typ: str, b: int, e: int, normalized: str | None) -> None:
        if not _free(b, e) or e <= b:
            return
        out.append(_Cand(typ, b, e, normalized, "pattern", priority=3))
        for i in range(b, e):
            claimed[i] = 1

    # Quoted names (v0.6.6): 「感動」という名のパン屋 / 『月影の庭』 / 新サービス「Kanso」 — a short
    # quoted string used as a name is an entity, typed by the noun that follows / precedes it.
    # Dialogue quotes (…と言った) are left alone. The Analyzer also mutes affect words inside.
    for m in _QUOTED_NAME_RE.finditer(text):
        b, e = m.start("q"), m.end("q")
        inner = m.group("q")
        after = text[m.end(): m.end() + 14]
        before = text[max(0, m.start() - 10): m.start()]
        if not (2 <= len(inner) <= 12) or _QUOTE_DIALOGUE_RE.match(after) or any(c in inner for c in "。！？!?、,"):
            continue
        if not (_QUOTE_NAME_AFTER_RE.match(after) or _QUOTE_NAME_BEFORE_RE.search(before) or m.group(0)[0] == "『"):
            continue
        typ = "WORK" if m.group(0)[0] == "『" else "PRODUCT"
        for key, t in _QUOTE_TYPE_HINTS:
            if key in after or key in before:
                typ = t
                break
        if _free(b, e):
            out.append(_Cand(typ, b, e, inner, "quoted", priority=2))
            for i in range(b, e):
                claimed[i] = 1

    for i, tok in enumerate(tokens):
        surf = tok.surface
        # legal-form prefix glued into one token by the lattice: 株式会社北斗物流 (v0.6.2)
        glued = next((p for p in _LEGAL_PREFIX if surf.startswith(p) and len(surf) >= len(p) + 2), None)
        if glued and _is_nounish(tok) and surf not in _LEGAL_PREFIX:
            j = i
            while j + 1 < n and _is_nounish(tokens[j + 1]) and tokens[j + 1].begin == tokens[j].end and tokens[j + 1].surface not in _PERSON_SUFFIX:
                j += 1
            _push("ORGANIZATION", tok.begin, tokens[j].end, text[tok.begin + len(glued):tokens[j].end])
            continue
        # legal-form prefix: 株式会社 + Name
        if surf in _LEGAL_PREFIX and i + 1 < n and _is_nounish(tokens[i + 1]) and tokens[i + 1].begin == tok.end:
            j = i + 1
            while j + 1 < n and _is_nounish(tokens[j + 1]) and tokens[j + 1].begin == tokens[j].end and tokens[j + 1].surface not in _PERSON_SUFFIX:
                j += 1
            _push("ORGANIZATION", tok.begin, tokens[j].end, text[tokens[i + 1].begin:tokens[j].end])
            continue
        for suffixes, typ in _SUFFIX_TABLE:
            hit = None
            # (a) the token itself is the suffix → merge with preceding noun token(s)
            if surf in suffixes and i > 0:
                prev = tokens[i - 1]
                if prev.end == tok.begin and _is_nounish(prev) and prev.surface not in stopwords:
                    name = prev.surface
                    if typ == "PERSON" and (name in _PERSON_BLOCK or _HIRAGANA_RE.match(name) or len(name) > 5 or name.startswith(("お", "ご"))):
                        continue
                    if surf in _ONE_CHAR_SUFFIX and (len(name) < 2 or _HIRAGANA_RE.match(name)):
                        continue
                    b = prev.begin
                    # extend left over adjacent proper-noun tokens (東京 + 本社 already one; 山田 + 商事)
                    k = i - 1
                    while typ != "PERSON" and k - 1 >= 0 and tokens[k - 1].end == tokens[k].begin and "固有名詞" in tokens[k - 1].pos:
                        k -= 1
                        b = tokens[k].begin
                    hit = (b, tok.end, text[b:prev.end] if typ == "PERSON" else text[b:tok.end])
            # (a') a standalone multi-char EVENT word is an event by itself (説明会 / 会議)
            if hit is None and surf in suffixes and typ == "EVENT" and len(surf) >= 2:
                hit = (tok.begin, tok.end, surf)
            # (b) the token ends with the suffix and has a name part in front
            elif surf not in suffixes:
                for sfx in suffixes:
                    if len(surf) > len(sfx) and surf.endswith(sfx) and _is_nounish(tok):
                        name = surf[: -len(sfx)]
                        if typ == "PERSON" and (name in _PERSON_BLOCK or _HIRAGANA_RE.match(name) or name.startswith(("お", "ご"))):
                            break
                        if sfx in _ONE_CHAR_SUFFIX and (len(name) < 2 or _HIRAGANA_RE.match(name) or name in stopwords):
                            break
                        if name in stopwords:
                            break
                        b = tok.begin
                        # extend left over adjacent noun tokens (代々 + 木公園 → 代々木公園)
                        k = i
                        while (
                            typ != "PERSON" and k - 1 >= 0 and tokens[k - 1].end == tokens[k].begin
                            and not tokens[k - 1].pos.startswith(("助詞", "助動詞", "動詞", "形容詞", "記号", "接続詞", "感動詞"))
                            and tokens[k - 1].surface not in stopwords and not _HIRAGANA_RE.match(tokens[k - 1].surface)
                            and not tokens[k - 1].surface.isdigit()
                        ):
                            k -= 1
                            b = tokens[k].begin
                        hit = (b, tok.end, text[b:tok.end - len(sfx)] if typ == "PERSON" else text[b:tok.end])
                        break
            if hit:
                b, e, norm = hit
                # EVENT followed by a 4-digit year (テックフェア2026)
                if typ == "EVENT" and i + 1 < n and tokens[i + 1].begin == e and re.fullmatch(r"[0-9]{4}", tokens[i + 1].surface):
                    e = tokens[i + 1].end
                _push(typ, b, e, norm)
                break
    return out


# ---------------------------------------------------------------------------
# Dictionary entities (FR-030)
# ---------------------------------------------------------------------------


# Token tails that may follow a dictionary entity inside one token (東京だ / 大阪で).
_ENTITY_TAILS = ("だ", "です", "だった", "でした", "で", "に", "は", "も", "を", "の", "と", "が", "から", "へ", "まで", "って", "です")


def _get_entity_matcher(bundle: DictionaryBundle):
    """Aho-Corasick over entity surfaces + aliases → (matcher, payload[type, normalized])."""
    cached = bundle._cache.get("ner_entity_matcher")
    if cached is not None:
        return cached
    surfaces: list[str] = []
    payload: list[tuple[str, str]] = []
    seen: set[str] = set()
    for e in bundle.entity:
        for surf in [e.surface, *e.aliases]:
            if not surf or len(surf) < 2 or surf in seen:
                continue
            seen.add(surf)
            surfaces.append(surf)
            payload.append((e.type, e.normalized or e.surface))
    res = (SurfaceMatcher(surfaces), payload)
    bundle._cache["ner_entity_matcher"] = res
    return res


def _dictionary_candidates(text: str, tokens: list[Token], semantic_tokens: list[SemanticToken], bundle: DictionaryBundle) -> list[_Cand]:
    out: list[_Cand] = []
    entity_map = bundle.entity_by_surface()
    by_id = {t.id: t for t in tokens}
    seen_spans: set[tuple[int, int]] = set()
    for st in semantic_tokens:
        if not st.entity_type:
            continue
        tok = by_id.get(st.token_id)
        if tok is None:
            continue
        ent = entity_map.get(tok.surface) or entity_map.get(tok.normalized)
        normalized = ent.normalized if ent and ent.normalized else tok.surface
        out.append(_Cand(st.entity_type, tok.begin, tok.end, normalized, "dictionary", priority=2))
        seen_spans.add((tok.begin, tok.end))

    # Text-level matching for entities the tokenizer split (クラウド|API) or fused
    # with a tail (東京だ). A match must start at a token boundary and end at a
    # token boundary or right before a known tail inside the same token.
    token_begins = {t.begin: t for t in tokens}
    token_ends = {t.end for t in tokens}
    matcher, payload = _get_entity_matcher(bundle)
    for rank, b, e in matcher.find_all(text):
        if (b, e) in seen_spans or b not in token_begins:
            continue
        if e not in token_ends:
            tok = next((t for t in tokens if t.begin <= b < t.end), None)
            if tok is None or e >= tok.end or text[e:tok.end] not in _ENTITY_TAILS:
                continue
        typ, normalized = payload[rank]
        out.append(_Cand(typ, b, e, normalized, "dictionary", priority=2))
        seen_spans.add((b, e))
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_entities(
    text: str,
    tokens: list[Token],
    semantic_tokens: list[SemanticToken],
    bundle: DictionaryBundle,
    reference_date: _dt.date | None = None,
) -> list[Entity]:
    """Extract entities from normalized ``text``; spans are normalized-text coords."""
    if not text:
        return []
    cands: list[_Cand] = []
    cands += _time_candidates(text, reference_date)
    claimed = bytearray(len(text))
    for c in cands:
        for i in range(c.begin, c.end):
            claimed[i] = 1
    cands += _quantity_candidates(text, claimed)
    stopwords = bundle.stopword_set()
    cands += _dictionary_candidates(text, tokens, semantic_tokens, bundle)
    cands += _pattern_candidates(text, tokens, claimed, stopwords)

    # Resolve overlaps: longer span first, then source priority.
    cands.sort(key=lambda c: (-(c.end - c.begin), c.priority, c.begin))
    taken = bytearray(len(text))
    chosen: list[_Cand] = []
    for c in cands:
        if any(taken[c.begin:c.end]):
            continue
        for i in range(c.begin, c.end):
            taken[i] = 1
        chosen.append(c)
    chosen.sort(key=lambda c: c.begin)

    entities: list[Entity] = []
    for idx, c in enumerate(chosen, 1):
        token_ids = [t.id for t in tokens if t.begin < c.end and t.end > c.begin]
        entities.append(
            Entity(
                id=f"e{idx}", type=c.type, surface=text[c.begin:c.end], begin=c.begin, end=c.end,
                normalized=c.normalized, token_ids=token_ids, source=c.source,
                value=c.value, unit=c.unit, currency=c.currency,
                confidence=1.0 if c.source in ("dictionary", "time", "quantity") else 0.8,
            )
        )
    return entities
