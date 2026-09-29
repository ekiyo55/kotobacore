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


def test_fine_granularity_splits_kanji_compounds():
    # v1.0.2 (tokenizer 1.1): 辞書にない 3 字以上の漢字連続を語単位に分割する
    coarse = Analyzer(pipeline="lattice")
    fine = Analyzer(pipeline="lattice", granularity="fine")
    assert _surfaces(coarse, "自然言語処理の研究開発") == ["自然言語処理", "の", "研究開発"]
    assert _surfaces(fine, "自然言語処理の研究開発") == ["自然", "言語", "処理", "の", "研究", "開発"]
    assert _surfaces(fine, "人工知能技術") == ["人工", "知能", "技術"]
    # 奇数長は一字接尾辞を語末側に置く
    assert _surfaces(fine, "経済産業省") == ["経済", "産業", "省"]
    assert _surfaces(fine, "感染症対策") == ["感染", "症", "対策"]
    assert _surfaces(fine, "合理的な判断") == ["合理", "的", "な", "判断"]
    assert _surfaces(fine, "満足感") == ["満足", "感"]
    assert _surfaces(fine, "少子高齢化社会") == ["少子", "高齢", "化", "社会"]
    assert _surfaces(fine, "不動産投資信託") == ["不", "動産", "投資", "信託"]
    # 漢数字の数・日付は割らない
    assert _surfaces(fine, "一九九五年一月") == _surfaces(coarse, "一九九五年一月")
    # 接辞の手がかりがない 3 字の漢字語は割らない
    for w in ("雰囲気", "出来事", "不動産", "新制度", "力不足"):
        assert _surfaces(fine, w) == [w], w
    # 辞書語は部品として残す / 辞書語そのものは割らない
    assert _surfaces(fine, "東京都知事選挙") == ["東京都", "知事", "選挙"]
    assert _surfaces(fine, "株式会社山田商事の鈴木です")[:3] == ["株式会社", "山田", "商事"]
    assert _surfaces(fine, "地方公共団体") == _surfaces(coarse, "地方公共団体")
    # 々 の直前では切らない
    assert _surfaces(fine, "代々木公園") == ["代々木", "公園"]
    # 2 字の漢字語はそのまま
    assert _surfaces(fine, "研究") == ["研究"]
    # オフセットが原文と一致する
    toks = fine.tokenize("国際連合安全保障理事会")
    assert "".join(t.surface for t in toks) == "国際連合安全保障理事会"
    assert all(toks[k].end == toks[k + 1].begin for k in range(len(toks) - 1))


def test_fine_analyze_keeps_semantic_layer_coarse():
    fine = Analyzer(pipeline="lattice", granularity="fine")
    r = fine.analyze("締め切りが近いのにバグが出た。もう無理かも...")
    assert r.tokens[0].surface == "締"
    assert r.emotion.primary == "anxiety"
    assert "締め切りが近い" in r.rag.keywords
    assert len(r.semantic_tokens) == len(r.tokens)


# ---------------------------------------------------------------------------
# v0.2.7: オノマトペ対応 (かな表記ゆれ / 反復 1 トークン化 / 促音強調形)
# ---------------------------------------------------------------------------


def test_onomatopoeia_hiragana_variants_detected():
    a = Analyzer()
    assert a.analyze("わくわくする").emotion.primary == "anticipation"  # v0.6.6: わくわく = anticipation (human evaluation set)
    assert a.analyze("いらいらする").emotion.primary == "irritation"
    assert a.analyze("どきどきした").emotion.primary == "anticipation"


def test_onomatopoeia_new_lexicon_entries():
    a = Analyzer()
    assert a.analyze("ウキウキで出かけた").emotion.primary == "joy"
    assert a.analyze("ビクビクしながら開けた").emotion.primary == "anxiety"
    assert a.analyze("メソメソ泣いてた").emotion.primary == "sadness"


def test_reduplication_kept_as_single_token():
    a = Analyzer()
    assert "しとしと" in _surfaces(a, "雨がしとしと降る")
    assert "もやもや" in _surfaces(a, "もやもやする")
    # 辞書 surface (slang あざ) が反復を跨いで分断しない・感情も誤検出しない
    r = a.analyze("雨がざあざあ降ってきた")
    assert "ざあざあ" in [t.surface for t in r.tokens]
    assert r.emotion.primary is None


def test_reduplication_leaves_known_words_alone():
    a = Analyzer()
    s = _surfaces(a, "わかるわかる、それな")
    assert s.count("わかる") == 2
    assert _surfaces(a, "ますます良くなった")[:2] == ["ます", "ます"]


def test_emphatic_sokuon_folds_to_base_form():
    a = Analyzer()
    assert a.analyze("ワックワクだよ").emotion.primary == "anticipation"  # v0.6.6: ワクワク = anticipation
    toks = a.tokenize("わっくわくした")
    assert toks[0].surface == "わっくわく"
    assert toks[0].dictionary_form == "わくわく"


def test_animal_cries_are_single_tokens_without_emotion():
    # 鳴き声は「感情なし・でも1語」— 長音ー入りは文字種ラン4つを跨ぐ
    a = Analyzer()
    for text, cry in [
        ("犬がわんわん吠える", "わんわん"),
        ("猫がにゃーにゃー鳴く", "にゃーにゃー"),
        ("牛がもーもー鳴く", "もーもー"),
        ("ひよこがぴよぴよ鳴いてる", "ぴよぴよ"),
    ]:
        r = a.analyze(text)
        assert cry in [t.surface for t in r.tokens], text
        assert r.emotion.primary is None, text


def test_reduplication_reachable_after_long_hiragana_prefix():
    # 反復開始位置が content_start 化され、直前のひらがな連続と癒着しない
    a = Analyzer()
    s = _surfaces(a, "ひよこがぴよぴよ鳴いてる")
    assert s[:3] == ["ひよこ", "が", "ぴよぴよ"]


def test_reduplication_phase_correction():
    # からはらはら — 左走査では らはらは が先にマッチするが、辞書語 はらはら に譲る
    a = Analyzer()
    assert _surfaces(a, "朝からはらはらしっぱなしだ")[:3] == ["朝", "から", "はらはら"]
    assert a.analyze("連絡が来なくてからいらいらが止まらない").emotion.primary == "irritation"


def test_hira_adjective_does_not_absorb_dict_word():
    # わくわく+してく が 形容詞 わくわくしてく に丸呑みされない
    a = Analyzer()
    s = _surfaces(a, "旅行のことを考えるだけでわくわくしてくる")
    assert "わくわく" in s
    assert a.analyze("うきうきしてくる").emotion.primary == "joy"
    # 正当なひらがな形容詞活用は維持
    assert "おかしく" in _surfaces(a, "様子がおかしくなっていた")


# ---------------------------------------------------------------------------
# v1.1 (DD evaluation report §5.2): 連用形名詞 / kanji compound particles
# ---------------------------------------------------------------------------


def test_renyou_nouns_are_one_token():
    a = Analyzer()
    assert _surfaces(a, "見込みは事業計画に")[0] == "見込み"
    assert _surfaces(a, "期限切れとなる") == ["期限", "切れ", "と", "なる"]
    assert _surfaces(a, "使用料支払いにかかる源泉徴収漏れの可能性") == [
        "使用料", "支払い", "に", "かかる", "源泉徴収", "漏れ", "の", "可能性"]
    assert _surfaces(a, "現金及び預金") == ["現金", "及び", "預金"]
    assert _surfaces(a, "残りは創業者一族")[0] == "残り"
    assert _surfaces(a, "攻撃を受け、一部業務が")[2] == "受け"
    assert "向け" in _surfaces(a, "みなと精機株式会社向けが全体の")
    # conjugations and 交ぜ書き compounds are untouched
    assert _surfaces(a, "高いと思う")[0] == "高い"
    assert _surfaces(a, "打ち合わせした")[0] == "打ち合わせ"
    assert _surfaces(a, "今日は疲れた")[-1] == "疲れた"
    assert _surfaces(a, "取り組みを進める")[0] == "取り組み"


def test_kanji_compound_particles():
    a = Analyzer()
    assert _surfaces(a, "本件に関して開示") == ["本件", "に関して", "開示"]
    assert _surfaces(a, "契約に基づき支払う") == ["契約", "に基づき", "支払う"]
    assert _surfaces(a, "顧客に対して説明") == ["顧客", "に対して", "説明"]


# ---------------------------------------------------------------------------
# v1.1 (DD evaluation report §5.1): numbers, dates, article references
# ---------------------------------------------------------------------------


def test_numeric_expressions_are_whole_tokens():
    a = Analyzer()
    assert _surfaces(a, "売上高は1,234百万円（△56百万円）") == [
        "売上高", "は", "1,234", "百万円", "(", "△", "56", "百万円", ")"]
    assert _surfaces(a, "営業損失(1,234)千円") == ["営業損失", "(", "1,234", ")", "千円"]
    assert _surfaces(a, "粗利率32.5%、2026/9/29時点") == ["粗利率", "32.5", "%", "、", "2026/9/29", "時点"]
    assert _surfaces(a, "第12条第3項第2号") == ["第12条", "第3項", "第2号"]
    assert _surfaces(a, "百万円）、第12条") == ["百万円", ")", "、", "第12条"]
    assert _surfaces(a, "一部業務が3日間停止した")[2:5] == ["3", "日間", "停止"]
    assert _surfaces(a, "1万人突破") == ["1", "万人", "突破"]
    assert _surfaces(a, "3件届いております")[:3] == ["3", "件", "届いて"]
    # unchanged: digits and units stay apart, version strings are not decimals
    assert _surfaces(a, "2026年4月1日に3億円") == ["2026", "年", "4", "月", "1", "日", "に", "3", "億円"]
    assert _surfaces(a, "2024年3月期と")[:4] == ["2024", "年", "3", "月期"]
    assert "2.3" not in _surfaces(a, "バージョン2.3.0を公開")


# ---------------------------------------------------------------------------
# v1.1 independent evaluation (2026-09-29) §6 defects
# ---------------------------------------------------------------------------


def test_independent_eval_defects_fixed():
    a = Analyzer(use_external_dictionaries=False, use_config=False)

    def toks(s):
        return [(t.surface, t.pos.split("-")[0], t.dictionary_form) for t in a.tokenize(s)]

    # 1: 難い stays an adjective (was 難く)
    assert ("難い", "形容詞", "難い") in toks("言い難い")
    # 2: a lone middle dot is punctuation; katakana names keep it
    assert ("・", "記号", "・") in toks("利払い前・税引き前")
    assert toks("トム・クルーズ")[0][0] == "トム・クルーズ"
    assert "・" not in [x.term for x in a.search_terms("利払い前・税引き前")]
    # 3: okurigana-dictionary noun is a noun with the canonical lemma (was 動詞 / 割当つ)
    assert ("割当て", "名詞", "割り当て") in toks("新株予約権の割当て")
    # 4: suffix 等 is split off, words ending with 等 are not
    assert [t[0] for t in toks("監査等の発生等")] == ["監査", "等", "の", "発生", "等"]
    assert toks("平等に扱う")[0][0] == "平等" and toks("等しい")[0][0] == "等しい" and toks("彼等は")[0][0] == "彼等"
    # 5: compound parts on word boundaries (was 設立|時募|集株|式)
    assert {"設立", "募集", "株式"} <= {x.term for x in a.search_terms("設立時募集株式")}
    # 6: legal okurigana words share one spelling
    assert a.tokenize("備付け")[0].normalized == a.tokenize("備え付け")[0].normalized == "備え付け"
