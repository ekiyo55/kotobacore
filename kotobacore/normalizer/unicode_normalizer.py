"""Unicode normalization that preserves SNS expressions and emoji.

Design per 04_内部設計書 §6:
- NFKC for 全角/半角 / 丸数字 unification
- Line ending: CRLF → LF
- Control characters: strip (keep \n, \t)
- DO NOT over-normalize SNS expressions like しぬwww
- DO NOT strip emoji (NFKC keeps them)
"""

from __future__ import annotations

import unicodedata

_ALLOWED_CONTROL = {"\n", "\t"}


def normalize(text: str) -> str:
    """Return the normalized form of ``text``.

    The transformation is intentionally conservative — it should not change
    user-visible semantics for SNS/emoji content.
    """
    if not text:
        return text

    # 1. Line endings: CRLF / CR → LF
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 2. Strip control characters except newline/tab
    text = "".join(
        ch
        for ch in text
        if ch in _ALLOWED_CONTROL or unicodedata.category(ch)[0] != "C"
    )

    # 3. NFKC normalization
    #    - Ｔｅｓｔ１２３ → Test123
    #    - ｶﾀｶﾅ → カタカナ
    #    - ① → 1
    #    - ㈱ → (株)  (NFKC default)
    text = unicodedata.normalize("NFKC", text)

    return text
