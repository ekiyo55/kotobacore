"""Tests for the shared Aho-Corasick surface matcher."""

from kotobacore.matching import SurfaceMatcher


def test_basic_matches_sorted_by_rank_then_pos():
    m = SurfaceMatcher(["abc", "bc", "c"])
    got = m.find_all("abcbc")
    # rank0: abc@0 / rank1: bc@1, bc@3 / rank2: c@2, c@4
    assert got == [(0, 0, 3), (1, 1, 3), (1, 3, 5), (2, 2, 3), (2, 4, 5)]


def test_overlapping_and_duplicate_patterns():
    m = SurfaceMatcher(["ww", "ww"])
    got = m.find_all("www")
    assert (0, 0, 2) in got and (0, 1, 3) in got
    assert (1, 0, 2) in got and (1, 1, 3) in got


def test_japanese_surfaces():
    m = SurfaceMatcher(["締め切り", "無理かも", "無理"])
    got = m.find_all("締め切りが近い。無理かも")
    assert (0, 0, 4) in got          # 締め切り
    assert (1, 8, 12) in got         # 無理かも
    assert (2, 8, 10) in got         # 無理 (prefix of 無理かも)


def test_empty_and_no_match():
    m = SurfaceMatcher(["xyz"])
    assert m.find_all("") == []
    assert m.find_all("abc") == []
    assert SurfaceMatcher([]).find_all("abc") == []


def test_equivalence_with_naive_scan():
    import random
    random.seed(42)
    alphabet = "あいうえおかきくけこ"
    patterns = ["".join(random.choices(alphabet, k=random.randint(1, 4))) for _ in range(30)]
    text = "".join(random.choices(alphabet, k=200))
    m = SurfaceMatcher(patterns)
    got = set(m.find_all(text))
    expected = set()
    for rank, pat in enumerate(patterns):
        start = 0
        while True:
            pos = text.find(pat, start)
            if pos < 0:
                break
            expected.add((rank, pos, pos + len(pat)))
            start = pos + 1
    assert got == expected
