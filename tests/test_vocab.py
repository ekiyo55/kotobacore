"""v0.6.0: vocab module — vocabulary build / Token IDs / encode-decode / report (FR-070〜072)."""

import json

from typer.testing import CliRunner

from kotobacore import Analyzer
from kotobacore.cli.main import app
from kotobacore.vocab import (
    SPECIAL_TOKENS,
    VOCAB_FORMAT_VERSION,
    VocabEncoder,
    Vocabulary,
    build_vocab,
    extend_vocab,
    report_markdown,
    vocab_report,
)
from kotobacore.vocab.build import BOS, EOS, FIRST_ID, NL, SP, UNK

CORPUS = [
    "吾輩は猫である。名前はまだ無い。",
    "どこで生れたかとんと見当がつかぬ。",
    "何でも薄暗いじめじめした所でニャーニャー泣いていた事だけは記憶している。",
    "吾輩はここで始めて人間というものを見た。",
    "東京に行った。東京で走った。",
]

_FINE = Analyzer(granularity="fine", enable_emotion=False, enable_sentiment=False, enable_intent=False, enable_rag=False)


def test_build_vocab_ids_and_specials():
    v = build_vocab(CORPUS, analyzer=_FINE, min_freq=1)
    assert v.version == VOCAB_FORMAT_VERSION and v.granularity == "fine"
    assert list(v.special_tokens) == list(SPECIAL_TOKENS) and v.piece_id("<unk>") == UNK and v.piece_id("<nl>") == NL
    ids = [e.id for e in v.entries]
    assert ids == list(range(FIRST_ID, FIRST_ID + len(ids)))  # dense, starting after the specials
    # frequency-descending among word pieces (ties by piece text); characters come after the words
    words = [e for e in v.entries if "char" not in e.flags]
    assert all(words[i].freq >= words[i + 1].freq for i in range(len(words) - 1))
    assert words[0].freq == max(e.freq for e in words) and words[0].freq >= 2
    assert all("char" in e.flags for e in v.entries[len(words):])
    # every character of the corpus is a piece (fallback alphabet)
    for ch in set("".join(CORPUS)):
        assert v.piece_id(ch) is not None, ch
    # deterministic
    assert build_vocab(CORPUS, analyzer=_FINE).to_dict() == v.to_dict()


def test_build_vocab_min_freq_and_max_size_keep_characters():
    v = build_vocab(CORPUS, analyzer=_FINE, min_freq=2)
    words = {e.piece for e in v.entries if "char" not in e.flags}
    assert "東京" in words and "った" in words and "薄暗い" not in words  # 東京 / った appear twice, 薄暗い once
    v2 = build_vocab(CORPUS, analyzer=_FINE, max_size=3)
    assert sum(1 for e in v2.entries if "char" not in e.flags) == 3
    assert v2.piece_id("ャ") is not None  # characters survive the cap


def test_encode_decode_roundtrip_and_whitespace():
    v = build_vocab(CORPUS, analyzer=_FINE)
    enc = VocabEncoder(v, _FINE)
    text = "吾輩は猫である。\n名前は　まだ無い。"
    ids = enc.encode(text)
    assert NL in ids and SP in ids and UNK not in ids
    assert enc.decode(ids) == "吾輩は猫である。\n名前は まだ無い。"  # normalized text (full-width space folded)
    wrapped = enc.encode(text, add_special=True)
    assert wrapped[0] == BOS and wrapped[-1] == EOS and enc.decode(wrapped) == enc.decode(ids)
    # the fine tokenizer splits 行った → 行 / った, and both are pieces
    assert "行" in enc.pieces("東京に行った") and "った" in enc.pieces("東京に行った")


def test_encode_oov_falls_back_to_characters_then_unk():
    v = build_vocab(CORPUS, analyzer=_FINE, min_freq=2)  # 薄暗い is not a word piece
    enc = VocabEncoder(v, _FINE)
    pieces = enc.pieces("薄暗い部屋")
    assert "薄暗い" not in pieces and "薄" in pieces and "暗" in pieces  # character fallback
    assert "<unk>" in pieces  # 部 / 屋 never appeared in the corpus
    assert "�" in enc.decode(enc.encode("薄暗い部屋"))
    assert enc.annotate(_FINE.tokenize("吾輩は部屋"))[-1] is None


def test_extend_vocab_appends_only():
    v = build_vocab(CORPUS, analyzer=_FINE)
    before = {e.piece: e.id for e in v.entries}
    freq_before = next(e for e in v.entries if e.piece == "吾輩").freq
    n = len(v)
    extend_vocab(v, ["部屋の隅で吾輩は寝た。"], analyzer=_FINE)
    after = {e.piece: e.id for e in v.entries}
    assert all(after[p] == i for p, i in before.items())  # no id moved
    assert len(v) > n and v.piece_id("部屋") is not None and v.piece_id("部") is not None
    assert next(e for e in v.entries if e.piece == "吾輩").freq == freq_before + 1  # frequency metadata updated
    assert min(after[p] for p in after if p not in before) == n  # new ids continue after the old maximum


def test_vocab_save_load(tmp_path):
    v = build_vocab(CORPUS, analyzer=_FINE)
    path = tmp_path / "v.json"
    v.save(path)
    loaded = Vocabulary.load(path)
    assert loaded.to_dict() == v.to_dict() and loaded.piece_id("吾輩") == v.piece_id("吾輩")


def test_vocab_report_and_contamination():
    v = build_vocab(CORPUS, analyzer=_FINE)
    extend_vocab(v, ["ｷﾃｷ!!!!! あああああ"], analyzer=_FINE)  # halfwidth kana survives? NFKC folds it — but symbol run / repeats remain
    rep = vocab_report(v, [*CORPUS, "吾輩は部屋にいる。"], analyzer=_FINE)
    assert rep["vocab"]["size"] == len(v) and rep["texts"] == len(CORPUS) + 1
    cov = rep["coverage"]
    assert 0 < cov["whole_piece_rate"] <= 1 and cov["oov_token_rate"] >= 0 and cov["unk_id_rate"] > 0  # 部屋 unseen at build time
    reasons = {r for c in rep["contamination"]["candidates"] for r in c["reasons"]}
    assert "repeated_char" in reasons or "symbol_run" in reasons
    md = report_markdown(rep)
    assert md.startswith("# Vocabulary report") and "contamination candidates" in md


def test_cli_vocab_build_encode_decode_report(tmp_path):
    corpus = tmp_path / "corpus.txt"
    corpus.write_text("\n".join(CORPUS), encoding="utf-8")
    vocab = tmp_path / "vocab.json"
    runner = CliRunner()
    r = runner.invoke(app, ["vocab", "build", str(corpus), "--out", str(vocab), "--min-freq", "1"])
    assert r.exit_code == 0, r.output
    assert vocab.exists()
    r = runner.invoke(app, ["vocab", "encode", "吾輩は猫である。", "--vocab", str(vocab)])
    assert r.exit_code == 0, r.output
    ids = json.loads(r.output)
    assert ids and all(isinstance(i, int) for i in ids)
    r = runner.invoke(app, ["vocab", "decode", json.dumps(ids), "--vocab", str(vocab)])
    assert r.exit_code == 0 and r.output.strip() == "吾輩は猫である。"
    r = runner.invoke(app, ["vocab", "report", str(corpus), "--vocab", str(vocab), "--md", str(tmp_path / "r.md")])
    assert r.exit_code == 0, r.output
    assert (tmp_path / "r.md").exists() and "coverage" in r.output
    r = runner.invoke(app, ["vocab", "build", str(corpus), "--out", str(vocab), "--extend", str(vocab)])
    assert r.exit_code == 0, r.output
