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


def test_sumomo_classic_sentence():
    # 教科書の難文。すもも/もも は entity.csv (TOPIC) 登録 + 名詞隣接ペナルティ
    # + 同一助詞連続ペナルティ (も|も はあり得ない) の3点で完全解になる。
    a = Analyzer(pipeline="lattice")
    r = a.analyze("すもももももももものうち")
    assert [t.surface for t in r.tokens] == [
        "すもも", "も", "もも", "も", "もも", "の", "うち"
    ]
    assert [c.text for c in r.chunks] == ["すもも", "もも", "もも"]
    assert "すもも" in r.rag.keywords and "もも" in r.rag.keywords


# ---------------------------------------------------------------------------
# v0.2.5: 文学テキスト (漱石) で見つかった分割癖の修正
# ---------------------------------------------------------------------------


def test_small_kana_proper_noun_merge():
    # cascade の heuristic_proper_noun_merge を lattice に移植 (辞書非依存)。
    # 「坊っちゃん」自体は entity.csv 登録済みなので、未登録の同型で検証。
    a = Analyzer(pipeline="lattice")
    assert "嬢っちゃん" in _surfaces(a, "嬢っちゃんは正直だ")
    # 動詞活用 (った/って/っちゃう) は結合しない
    assert _surfaces(a, "言っちゃった") == ["言っちゃった"]
    assert _surfaces(a, "買った") == ["買った"]


def test_bocchan_dictionary_both_spellings():
    a = Analyzer(pipeline="lattice")
    assert _surfaces(a, "坊っちゃんを読んだ")[0] == "坊っちゃん"
    assert _surfaces(a, "坊ちゃんを読んだ")[0] == "坊ちゃん"


def test_nominal_suffix_nodes():
    a = Analyzer(pipeline="lattice")
    toks = a.tokenize("田中さんが子供たちと来た")
    pos = {t.surface: t.pos for t in toks}
    assert pos["さん"] == "接尾辞" and pos["たち"] == "接尾辞"
    assert "田中" in pos and "子供" in pos
    # 純ひらがな語は分割しない
    assert "たくさん" in "".join(_surfaces(a, "たくさんある"))
    assert "ちゃんと" in _surfaces(a, "彼はちゃんとやる")


def test_compound_particle_ni_okeru():
    # 既知の癖 (2026-08-20): における → に|おけ|る で「おけ」が trust を誤発火
    a = Analyzer(pipeline="lattice")
    assert "における" in _surfaces(a, "日本における研究")
    assert "においては" in _surfaces(a, "これにおいては")
    assert a.analyze("日本における研究").emotion.primary is None


def test_conjunction_not_glued_to_next_char():
    a = Analyzer(pipeline="lattice")
    assert _surfaces(a, "けれどもそのときは")[:2] == ["けれども", "その"]
    assert _surfaces(a, "しかしまだ来ない")[:2] == ["しかし", "まだ"]
    assert _surfaces(a, "しかしこの人は")[:2] == ["しかし", "この"]
    # 接続詞はラン先頭のみ: からだ|が を だが で割らない
    assert "だが" not in _surfaces(a, "からだが痛い")


def test_greeting_is_one_token():
    a = Analyzer(pipeline="lattice")
    toks = a.tokenize("こんにちは、元気ですか")
    assert toks[0].surface == "こんにちは" and toks[0].pos.startswith("感動詞")


def test_compound_verb_conjugation():
    a = Analyzer(pipeline="lattice")
    assert _surfaces(a, "思い出した") == ["思い出した"]
    assert _surfaces(a, "飛び込んだ") == ["飛び込んだ"]
    # サ変名詞 + した は名詞を保つ
    assert _surfaces(a, "打ち合わせした")[0] == "打ち合わせ"
    assert _surfaces(a, "思い出が多い")[0] == "思い出"


# ---------------------------------------------------------------------------
# v0.2.6: 過剰結合の抑制 + granularity="fine"
# ---------------------------------------------------------------------------


def test_prefix_noun_does_not_join_verb():
    a = Analyzer(pipeline="lattice")
    assert _surfaces(a, "突然云い出した") == ["突然", "云い出した"]
    assert _surfaces(a, "昨日買った本") == ["昨日", "買った", "本"]
    # 接頭語リストに無い漢字ランは従来通り (無条件分割で 昨|日買った を作らない)
    assert "走り出した" in _surfaces(a, "急に走り出した")


def test_hiragana_verbs_and_fixed_words():
    a = Analyzer(pipeline="lattice")
    assert _surfaces(a, "何時間かかります") == ["何時間", "かかります"]
    assert _surfaces(a, "ここにあります") == ["ここ", "に", "あります"]
    assert _surfaces(a, "同じである") == ["同じ", "である"]
    assert _surfaces(a, "初めて会った") == ["初めて", "会った"]
    # ひらがな動詞は感情語を飲み込まない
    assert "うんざり" in _surfaces(a, "順番を抜かされてうんざりしている")


def test_okurigana_length_cap():
    a = Analyzer(pipeline="lattice")
    toks = _surfaces(a, "張りのあるまでどうかやってもらいたい")
    assert toks[0] != "張りのあるまでどうかやってもらいたい"
    assert all(len(t) <= 10 for t in toks)


def test_fine_granularity_splits_assembled_nodes():
    coarse = Analyzer(pipeline="lattice")
    fine = Analyzer(pipeline="lattice", granularity="fine")
    assert _surfaces(coarse, "思い出した") == ["思い出した"]
    toks = fine.tokenize("思い出した")
    assert [t.surface for t in toks] == ["思", "い", "出", "した"]
    assert [t.pos for t in toks] == ["動詞-語幹", "送り仮名", "動詞-語幹", "動詞-活用語尾"]
    assert _surfaces(fine, "締め切り") == ["締", "め", "切", "り"]
    assert _surfaces(fine, "あります") == ["あ", "ります"]
    # 辞書エンティティ / keep_as_unit は割らない
    assert _surfaces(fine, "坊っちゃんは正直だ")[0] == "坊っちゃん"
    assert _surfaces(fine, "吾輩は猫である")[0] == "吾輩は猫である"
    # tokenize(granularity=) で都度指定もできる
    assert coarse.tokenize("思い出した", granularity="fine")[0].surface == "思"


def test_fine_granularity_splits_unknown_hiragana_runs():
    fine = Analyzer(pipeline="lattice", granularity="fine")
    toks = _surfaces(fine, "あとをわざとぼかしてしまった")
    assert "しまった" in toks
    assert all(len(t) <= 4 for t in toks)


def test_fine_analyze_keeps_semantic_layer_coarse():
    fine = Analyzer(pipeline="lattice", granularity="fine")
    r = fine.analyze("締め切りが近いのにバグが出た。もう無理かも...")
    assert r.tokens[0].surface == "締"
    assert r.emotion.primary == "anxiety"
    assert "締め切りが近い" in r.rag.keywords
    assert len(r.semantic_tokens) == len(r.tokens)
