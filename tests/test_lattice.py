"""Karuizawa lattice モード (v0.2) のテスト.

デフォルトパイプラインは lattice。cascade は互換用に選択可能で、
両者は 5000 例文評価で全指標同等 (チャンクは lattice が上回る)。
"""

from kotobacore import Analyzer


def _surfaces(a, text):
    return [t.surface for t in a.tokenize(text)]


def test_default_pipeline_is_lattice():
    assert Analyzer().pipeline == "lattice"


def test_cascade_still_selectable():
    a = Analyzer(pipeline="cascade")
    assert a.pipeline == "cascade"
    assert "締め切り" in _surfaces(a, "締め切りが近い")


def test_lattice_basic_segmentation():
    a = Analyzer(pipeline="lattice")
    s = _surfaces(a, "締め切りが近いのにバグが出た。もう無理かも...")
    assert "締め切り" in s
    assert "無理かも" in s
    assert "出た" in s


def test_lattice_beats_cascade_on_verb_noun_boundary():
    # cascade は 行|くの|が|楽|しみ に壊れるが lattice は正しく切る
    a = Analyzer(pipeline="lattice")
    s = _surfaces(a, "買い物に行くのが楽しみ")
    assert "買い物" in s
    assert "行く" in s
    assert "楽しみ" in s


def test_keep_as_unit_claims_absolutely():
    # 動詞組み立てが keep_as_unit 語 (好き) を跨いで飲み込まないこと
    a = Analyzer(pipeline="lattice")
    s = _surfaces(a, "全然好きじゃない")
    assert "好き" in s


def test_protected_stem_not_absorbed():
    # 満足している → 満足 は辞書既知語なので独立トークンを保つ
    a = Analyzer(pipeline="lattice")
    s = _surfaces(a, "心から満足している。")
    assert "満足" in s


def test_embedded_emotion_word_not_swallowed():
    # 送り仮名ブロック内の うんざり が動詞ノードに吸収されないこと
    a = Analyzer(pipeline="lattice")
    r = a.analyze("順番を抜かされてうんざりしている。")
    assert r.emotion.primary == "irritation"


def test_adjective_stem_guard_in_lattice():
    a = Analyzer(pipeline="lattice")
    s = _surfaces(a, "良い天気ですね")
    assert "良い" in s
    assert "天気" in s
