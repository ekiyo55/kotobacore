"""Business-mail boilerplate detection (v1.1, ``Analyzer.analyze_mail``).

A Japanese business mail wraps a few content sentences in fixed phrases —
salutation (株式会社○○ 田中様), greeting (いつもお世話になっております),
self-introduction (ABC株式会社の山田です), closing (よろしくお願いいたします),
signature and quoted replies. Classified as they are, the closing turns every
mail into a "request" and the greeting adds noise. ``boilerplate_kinds`` labels
each sentence so the document-level intent / sentiment / emotion can be built
from the content sentences only.

Kinds: ``salutation`` / ``greeting`` / ``self_intro`` / ``closing`` /
``signature`` / ``quote``; ``None`` for a content sentence. A phrase counts as
boilerplate only when the WHOLE sentence is the formula — 早急に確認をお願い
します is a real request and stays content.
"""

from __future__ import annotations

import re

_END_PUNCT = "。．.！!？?"
_SALUTATION_END = re.compile(r"(?:様|さま|御中|各位|殿|ご担当者様)[\s、,：:]*$")
_SEPARATOR = re.compile(r"^\s*(?:[-－ー―=＝_＿*＊~〜・━─]{2,}|-{2,}\s*Original Message\s*-{2,}.*)\s*$", re.IGNORECASE)
# a contact line is a LABEL followed by a separator (TEL: … / Mail： …) or a bare phone / address line;
# メール確認いたしました and a body line that is just a URL are content (real-mail evaluation, 1.1.0a17)
_CONTACT = re.compile(
    r"^\s*[\[【(（]?(?:TEL|Tel|tel|T|電話(?:番号)?|携帯|直通|FAX|Fax|fax|F|E-?mail|e-?mail|Mail|mail|MAIL|メール(?:アドレス)?|URL|Web|HP)"
    r"[\]】)）]?(?:\s*[:：]\s*\S|\s+[+(（]?\d)"
    r"|^\s*〒\s*\d"
    r"|^\s*[\w.+-]+@[\w-]+(?:\.[\w-]+)+\s*$"
    r"|^\s*\(?\+?\d{2,4}\)?[-‐ー－ ]?\d{1,4}[-‐ー－ ]\d{3,4}\s*$"
)
_ADDR_OR_PHONE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+|\d{2,4}[-‐－]\d{2,4}[-‐－]\d{3,4}")
_QUOTE = re.compile(r"^\s*[>＞]")
_QUOTE_HEADER = re.compile(
    r"(?:Original Message|wrote:|のメッセージ:|さんは書きました|様より:?\s*$"
    r"|^\s*\d{4}年\d{1,2}月\d{1,2}日.*[<＜][^>＞]*@[^>＞]*[>＞]\s*[:：]?\s*$"
    r"|[<＜][^>＞\s]+@[^>＞\s]+[>＞]\s*[:：]\s*$)"
)
# forwarded / Outlook-style reply header block: From: … followed closely by Sent/Date/To/Subject
_HDR_FROM = re.compile(r"^\s*(?:From|FROM|差出人|送信者|送信元)\s*[:：]")
_HDR_NEXT = re.compile(r"^\s*(?:Sent|Date|To|Cc|Subject|送信日時|日時|日付|宛先|件名|CC)\s*[:：]")
_SIGNATURE_MAX = 15  # a signature is a short block at the end (before any quote)

_P = r"(?:[。．.！!]*)$"
_GREET_CORE = (
    r"(?:お世話になって(?:おります|います)|お世話になります|お世話様です|"
    r"お世話になり(?:まして)?[、\s]*(?:誠に|本当に)?ありがとうございます|"
    r"お疲れ様です|お疲れさまです|おつかれさまです|お疲れ様でございます|"
    r"ご無沙汰しております|ご無沙汰いたしております|格別のご高配を賜り.*|格別のお引き立てを賜り.*)"
)
_GREETING = re.compile(
    r"^(?:いつも|平素(?:は|より)?|大変|日頃(?:より|は)?|この度は|このたびは)?[、\s]*(?:大変|たいへん)?" + _GREET_CORE
    # お世話になっております、山田です。 (greeting + name in one sentence)
    + r"(?:[、。\s]*[^。、\sはがを]{1,20}(?:です|でございます))?" + _P
    + r"|^(?:突然の|初めての|はじめての)?ご連絡(?:を)?(?:失礼いたします|失礼します|差し上げます)" + _P
    + r"|^(?:初めて|はじめて)ご連絡(?:いたします|させていただきます)" + _P
    + r"|^拝啓(?:[\s　、].*)?$"
)
_SELF_INTRO = re.compile(
    # the part before the organisation must not contain は / が / を (これは…テストです, …は…の商標です)
    r"^(?:(?:こんにちは|こんばんは|はじめまして|初めまして)[、。!！\s]*)?"
    r"[^。はがを]{0,40}(?:株式会社|有限会社|会社|法人|事務所|部|課|室|局|チーム|センター|支店|事業所)"
    r"(?:の|\s)*[^。、\sはがをにでと]{0,12}(?:です|でございます|と申します)" + _P
    + r"|^[^。はがを]{1,20}と申します" + _P
)
# prefixes that may pile up before よろしくお願いします: 以上、今後とも、どうぞ、ご確認の程、お手数ですが …
_PRE = (
    r"(?:(?:以上(?:です|となります)?|今後とも|引き続き|何卒|なにとぞ|どうぞ|どうか|取り急ぎ|取急ぎ|恐れ入りますが|"
    r"お手数[^。]{0,15}?(?:が|けれど)|(?:ご|お)[一-龥]{1,4}(?:の(?:ほど|程))?)[、,\s]*){0,4}"
)
_YORO = r"(?:よろしく|宜しく)(?:お願い(?:いた|致)?(?:します|しますね|申し上げます|申しあげます)|お願いします)"
_CLOSING = re.compile(
    r"^" + _PRE + _YORO + _P
    + r"|^(?:今後とも|引き続き)[、\s]*[^。]{0,20}を[、\s]*(?:どうぞ)?" + _YORO + _P
    + r"|^(?:以上(?:です|となります|になります)?|敬具|草々|かしこ|"
    r"取り急ぎ[^。]{0,20}(?:まで|とさせていただきます|申し上げます)|まずは(?:ご連絡|お礼|ご報告)まで(?:申し上げます)?)" + _P
    + r"|^(?:今後とも|引き続き)?[^。]{0,20}(?:ご愛顧|お付き合い)[^。]{0,20}(?:お願い(?:いた|致)?(?:します|申し上げます))" + _P
    # the standard invitation to ask (ご不明な点がございましたら…お問い合わせください)
    + r"|^(?:ご不明な点|ご不明点|ご質問|その他ご不明|何か(?:ご不明な点|ございましたら)|お困りの)[^。]{0,40}"
    r"(?:お問い合わせ|お問合せ|お問い合せ|ご連絡|お申し付け|お寄せ)(?:ください|下さい|くださいませ|いただけますと幸いです)" + _P
)
# a reply header block without a From line (Sent: … / Subject: …)
_HDR_WHEN = re.compile(r"^\s*(?:Sent|Date|送信日時)\s*[:：]")
_HDR_WHAT = re.compile(r"^\s*(?:Subject|To|件名|宛先)\s*[:：]")


_ACTION_CLOSING = re.compile(
    r"(?:ご|お)(?:確認|検討|調整|対応|返信|回答|返答|査収|手配|承認|判断|連絡|記入|提出|送付|指示|教示|手続き|手続|入金|支払い|支払)"
)


def is_action_closing(sentence: str) -> bool:
    """A closing that asks for an action (ご確認のほどよろしくお願いいたします) rather than a pure sign-off."""
    return bool(_ACTION_CLOSING.search(sentence))


def _quote_start(sentences: list[str]) -> int:
    n = len(sentences)
    for i in range(n):
        s = sentences[i].strip()
        if _QUOTE.match(s) or _QUOTE_HEADER.search(s):
            return i
        if _HDR_FROM.match(s) and any(_HDR_NEXT.match(sentences[j].strip()) for j in range(i + 1, min(n, i + 6))):
            return i
        if _HDR_WHEN.match(s) and any(_HDR_WHAT.match(sentences[j].strip()) for j in range(i + 1, min(n, i + 4))):
            # include a separator line right above the header block
            return i - 1 if i > 0 and _SEPARATOR.match(sentences[i - 1].strip()) else i
    return n


def _signature_start(sentences: list[str], lo: int, hi: int) -> int | None:
    """First contact / separator line in [lo, hi) that opens a short block ending at hi."""
    for i in range(lo, hi):
        s = sentences[i].strip()
        if not s:
            continue
        body = sum(1 for j in range(i, hi) if sentences[j].strip())
        if body > _SIGNATURE_MAX:
            continue
        if _CONTACT.match(s):
            start = i
            # the company / name line right above a contact line belongs to the signature
            if i > lo:
                prev = sentences[i - 1].strip()
                if prev and prev[-1] not in _END_PUNCT and len(prev) <= 40:
                    start = i - 1
            return start
        # a separator opens the signature only when contact details follow it
        if _SEPARATOR.match(s) and any(
            _CONTACT.match(sentences[j].strip()) or _ADDR_OR_PHONE.search(sentences[j])
            for j in range(i + 1, min(hi, i + 9))
        ):
            return i
    return None


def boilerplate_kinds(sentences: list[str]) -> list[str | None]:
    """Label each sentence of a mail (in order) with its boilerplate kind, or None for content."""
    n = len(sentences)
    kinds: list[str | None] = [None] * n
    # salutation: leading lines without sentence-final punctuation, up to one ending with 様 / 御中 …
    lead = 0
    while lead < n and sentences[lead].strip() and sentences[lead].strip()[-1] not in _END_PUNCT and len(sentences[lead].strip()) <= 40:
        lead += 1
    last_sal = max((i for i in range(lead) if _SALUTATION_END.search(sentences[i].strip())), default=-1)
    for i in range(last_sal + 1):
        kinds[i] = "salutation"
    # quoted reply / forwarded message: from its header to the end
    q = _quote_start(sentences)
    for j in range(max(q, last_sal + 1), n):
        kinds[j] = "quote"
    # signature: a short block with contact details right before the quote (or the end)
    sig = _signature_start(sentences, last_sal + 1, q)
    if sig is not None:
        for j in range(sig, q):
            kinds[j] = "signature"
    # fixed phrases (the whole sentence must be the formula)
    for i in range(n):
        if kinds[i] is not None:
            continue
        s = sentences[i].strip()
        if not s:
            continue
        if _GREETING.search(s):
            kinds[i] = "greeting"
        elif _CLOSING.search(s):
            kinds[i] = "closing"
        elif _SELF_INTRO.search(s):
            kinds[i] = "self_intro"
    # a bare name line after the last closing (…よろしくお願いします。 / 佐藤) is the sign-off
    last_closing = max((i for i in range(q) if kinds[i] == "closing"), default=-1)
    for i in range(last_closing + 1, q):
        s = sentences[i].strip()
        if kinds[i] is None and last_closing >= 0 and s and s[-1] not in _END_PUNCT and len(s) <= 20:
            kinds[i] = "signature"
    return kinds
