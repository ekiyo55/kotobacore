"""Shared surface-matching layer (pure-Python Aho-Corasick).

Three consumers — ``merge_keep_as_unit``, ``detect_emotion`` and the
``chunker`` — previously each re-implemented "for every candidate surface,
``str.find`` every occurrence, claim non-overlapping spans".  That is
O(patterns × text) and three chances for the implementations to drift apart.

``SurfaceMatcher`` builds one Aho-Corasick automaton per pattern list
(deterministic from the dictionary bundle → built once, cached on it) and
returns every occurrence of every pattern in O(text + matches).

Ordering contract: ``find_all`` returns matches sorted by
``(pattern_rank, start)`` where ``pattern_rank`` is the pattern's index in
the constructor list.  Consumers that process candidates longest-first simply
pass the list already sorted that way — iterating the matches then claims
spans in exactly the same order as the previous nested-``find`` loops, so
behaviour is identical.
"""

from __future__ import annotations

from collections import deque


class SurfaceMatcher:
    """Aho-Corasick automaton over a fixed pattern list."""

    __slots__ = ("_fail", "_goto", "_out")

    def __init__(self, patterns: list[str]) -> None:
        # Trie. out[node] holds (rank, length) for every pattern ending there
        # (fail-target outputs merged in below, so one visit yields them all).
        goto: list[dict[str, int]] = [{}]
        out: list[list[tuple[int, int]]] = [[]]

        for rank, pat in enumerate(patterns):
            if not pat:
                continue
            node = 0
            for ch in pat:
                nxt = goto[node].get(ch)
                if nxt is None:
                    goto.append({})
                    out.append([])
                    nxt = len(goto) - 1
                    goto[node][ch] = nxt
                node = nxt
            out[node].append((rank, len(pat)))

        # Fail links via BFS. Depth-1 nodes fail to the root; deeper nodes
        # follow their parent's fail chain.
        fail = [0] * len(goto)
        q: deque[int] = deque(goto[0].values())
        while q:
            node = q.popleft()
            for ch, nxt in goto[node].items():
                q.append(nxt)
                f = fail[node]
                while f and ch not in goto[f]:
                    f = fail[f]
                fail[nxt] = goto[f][ch] if (ch in goto[f] and goto[f][ch] != nxt) else 0
                out[nxt].extend(out[fail[nxt]])

        self._goto = goto
        self._fail = fail
        self._out = out

    def find_all(self, text: str) -> list[tuple[int, int, int]]:
        """Return all matches as ``(rank, start, end)`` sorted by (rank, start)."""
        goto = self._goto
        fail = self._fail
        out = self._out
        matches: list[tuple[int, int, int]] = []
        node = 0
        for i, ch in enumerate(text):
            while node and ch not in goto[node]:
                node = fail[node]
            node = goto[node].get(ch, 0)
            if out[node]:
                for rank, length in out[node]:
                    matches.append((rank, i + 1 - length, i + 1))
        matches.sort()
        return matches
