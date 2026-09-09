# KotobaCore

[![CI](https://github.com/ekiyo55/kotobacore/actions/workflows/ci.yml/badge.svg)](https://github.com/ekiyo55/kotobacore/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/kotobacore)](https://pypi.org/project/kotobacore/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

**English** | [日本語](README.md)

A semantic engine that turns Japanese text into structured data.
Built for LLM preprocessing, RAG, social-media analysis, and AI-agent input.

---

## What it does

```python
from kotobacore import Analyzer

result = Analyzer().analyze("クラウドAPIの課金高すぎてしぬw")
```

```
chunks   : ["クラウドAPI", "課金高すぎ", "しぬw"]
emotion  : anger / negative  (Plutchik: anger+disgust)
intent   : pricing_complaint
keywords : ["クラウドAPI", "課金"]
```

It's not just a tokenizer — it returns **emotion, intent, and RAG keywords in a single pass**.

---

## Pipeline

```
input text
  └─ normalization (NFKC / preserves SNS expressions)
       └─ tokenization — Karuizawa (built-in, zero external dependencies)
          v0.2+: single-pass lattice + Viterbi (dictionary surfaces, grammar
          morphemes, conjugation assembly and mixed-script compounds proposed
          as nodes; best path chosen with bigram connection costs)
            └─ semantic chunking
                 ├─ emotion detection (clause splitting / negation scope /
                 │   adversative weighting) + Plutchik 8-axis mapping
                 ├─ intent classification (rules + sentence-final forms +
                 │   emotion-derived fallback)
                 └─ RAG keyword extraction
```

---

## Emotion model — Plutchik's wheel of emotions

KotobaCore builds on psychologist Robert Plutchik's **8 basic emotions** model.
Emotions are classified along 8 axes (anger, fear, joy, sadness, trust, disgust, surprise, anticipation)
and returned as structured `primary / polarity / plutchik_axes`.

| Plutchik axis | KotobaCore category | Examples |
|---|---|---|
| joy | joy / moved / admiration | 嬉しい (glad), 感動した (moved), 誇らしい (proud) |
| anger | anger / refusal | ムカつく (annoyed), 無理 (no way), 許せない (unforgivable) |
| sadness | sadness / anxiety | 悲しい (sad), 不安 (anxious), 心配 (worried) |
| surprise | surprise / exaggeration | まじか (seriously), やばい (crazy), しぬw (dying lol) |
| anticipation | anticipation / desire | 楽しみ (looking forward), したい (want to), 欲しい (want) |
| trust | admiration | 尊い (precious), 信頼 (trust), 神対応 (great service) |
| fear | anxiety | 怖い (scary), 恐怖 (terror), ゾッとした (chilling) |
| disgust | refusal | 最悪 (the worst), 気持ち悪い (gross), 無理 (can't stand) |

---

## Built-in dictionaries

KotobaCore's decisions are based not on a machine-learning model but on **bundled, hand-maintained
dictionaries (plain CSV)**. No model download or training is required — edit the CSVs to add or tune
vocabulary and rules (`resources/dict/`).

| Dictionary file | Entries | Role | Key columns |
|---|---:|---|---|
| `entity.csv` | 1786 | Named entities (people, brands, organizations, places, works, services) plus TOPIC common nouns (円安, 値上げ, すもも, …). `aliases` column matches alternative spellings | surface, type, normalized, aliases, priority, keep_as_unit |
| `emotion.csv` | 521 | Emotion words. 11 categories (joy / sadness / admiration / refusal / moved / anger / anxiety / exaggeration / anticipation / irritation / agreement) mapped to Plutchik's 8 axes | surface, base_emotion, polarity, intensity, keep_as_unit |
| `slang.csv` | 203 | Social-media / internet slang (草, しぬw, ワロタ, etc.) | surface, normalized, meaning, emotion, category, intensity, keep_as_unit |
| `stopwords.csv` | 113 | Particles / adverbs / conjunctions excluded from chunks and keywords | surface, category |
| `normalization.csv` | 21 | Spelling normalization ((株) → 株式会社, etc.) | source, target, type |
| `intent_rules.csv` | 9 | Intent-classification rules (pricing_complaint / support_request / positive_feedback / negative_feedback / agreement / admiration / desire / question / request) | intent, pattern, score, priority |
| `emotion_examples.csv` | 17 | Hand-written seed for example-based emotion matching | surface, base_emotion, plutchik_emotion, polarity, intensity, example |
| `Japanese-SNS-Emotion-Examples-v1.txt` | 546 words / ~2,746 examples | SNS emotion-example corpus. Used for example-based Jaccard-similarity matching | word, emotion, intensity, context, examples, emojis |

`entity.csv` breaks down as organizations 571 (400+ major Japanese companies, government bodies, international organizations) / topics 363 (history, religion, language, food, holidays) / places 279 (117 countries) / people 272 / brands 195 / works 59 / services 39, and more.

`Japanese-SNS-Emotion-Examples-v1.txt` ships under `resources/dict/` and loads by default
(example matching works without any external dictionary). Each row's `examples` (multiple sentences
separated by 「、」) is expanded and matched against the input via bigram Jaccard similarity to
strengthen emotion confidence.

### Optional external dictionary (NRC, not bundled)

The one **non-bundled** dictionary is the **NRC Emotion Intensity Lexicon** (~9,800 words / intensity
scores for the 8 Plutchik emotions). Place it under `dic/` (configurable via the `KOTOBACORE_DIC_DIR`
environment variable) and it **adds detection vocabulary** for emotion words absent from the internal
dictionary (at a lower weight, `lex_weight=0.5` vs. internal `1.0`, to supplement rare/literary words).
**It is optional — KotobaCore runs fully on the built-in dictionaries without it.**

Emotion confidence is computed as `lex_weight × 0.5 + ex_sim × 0.3 + intensity × 0.2`, where NRC feeds
the first term (detection vocabulary) and the bundled SNS examples feed the second (similarity).

#### How to obtain the NRC lexicon

> **⚠️ License note**: The NRC Emotion Intensity Lexicon **may not be redistributed**, so it is not
> included in this repository. Obtain it yourself from the official page. **Non-commercial research use
> is free**, but **commercial use requires a separate commercial license from NRC**. Citation and
> attribution are required. Always review the
> [official terms of use](https://saifmohammad.com/WebPages/AffectIntensity.htm) yourself.

1. Obtain the lexicon from the official **NRC Emotion/Affect Intensity Lexicon** page (the multilingual
   auto-translated edition includes Japanese).
   - https://saifmohammad.com/WebPages/AffectIntensity.htm
2. Arrange the Japanese data into the following **tab-separated (TSV), 4-column** format and place it in `dic/`.
   ```
   English Word<TAB>Emotion<TAB>Emotion-Intensity-Score<TAB>Japanese Word
   ```
   - Filename: `dic/Japanese-NRC-Emotion-Intensity-Lexicon-v1.txt`
   - `Emotion` is one of the 8 axes (anger / anticipation / disgust / fear / joy / sadness / surprise / trust)
3. The `dic/` location is resolved in this order: `KOTOBACORE_DIC_DIR` env var → `<project>/dic` → `<project>/../dic`.

**Citation (required)**:

```bibtex
@inproceedings{LREC18-AIL,
  author    = {Mohammad, Saif M.},
  title     = {Word Affect Intensities},
  booktitle = {Proceedings of the 11th Edition of the Language Resources
               and Evaluation Conference (LREC-2018)},
  year      = {2018},
  address   = {Miyazaki, Japan}
}
```

**Attribution example**: "This product makes use of the NRC Emotion Intensity Lexicon, created by Saif M. Mohammad at the National Research Council Canada."

```python
from kotobacore.dictionary import load_user_bundle
bundle = load_user_bundle()   # internal seed + bundled SNS examples + (if present) NRC from dic/
```

---

## Install

```bash
git clone https://github.com/ekiyo55/kotobacore.git
cd kotobacore
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .[dev,ui]
```

---

## Python API

```python
from kotobacore import Analyzer

result = Analyzer().analyze("クラウドAPIの課金高すぎてしぬw")
print(result.to_json())
```

### Token granularity (`granularity`)

The default `coarse` keeps semantic units as single tokens (思い出した / 締め切り).
For language-model vocabularies and other surface-level uses, `fine` splits the
assembled verbs / adjectives / mixed-script compounds / unknown hiragana runs into
stem, okurigana and inflection pieces (dictionary entities are never split).

```python
Analyzer(granularity="fine").tokenize("思い出した")
# 思(動詞-語幹) い(送り仮名) 出(動詞-語幹) した(動詞-活用語尾)
```

`analyze()` always computes chunks / emotion / intent / rag on coarse tokens,
whatever the granularity. The segmentation standard is documented in `docs/TOKENIZATION.md`.

### N4 lemmas and conjugation (v0.6.3)

```python
[(t.surface, t.dictionary_form, t.conjugation_type, t.conjugation_form) for t in a.tokenize("食べさせられなかったので待っています")]
# [('食べさせられなかったので', '食べる', '一段', '使役-受身-否定-過去-接続-理由'), ('待っています', '待つ', '五段', '進行-丁寧')]
[(t.surface, t.normalized) for t in a.tokenize("申込みと見積と引落")]   # okurigana variants → canonical spelling
# [('申込み', '申し込み'), ('と', 'と'), ('見積', '見積もり'), ('と', 'と'), ('引落', '引き落とし')]
```

Rule-based, dictionary-free lemmatization with conjugation type (五段 / 一段 / カ変 / サ変 / 形容詞 / 形容動詞) and form; ambiguities only a dictionary could settle are resolved to the most frequent pattern and marked `五段?`.

## Entities, attribution, documents and Query IR (v0.4+)

```python
a = Analyzer(reference_date=datetime.date(2026, 9, 8))
r = a.analyze("株式会社山田商事の佐藤部長は10月5日に45億円の契約を発表した。")
[(e.surface, e.type, e.value) for e in r.entities]
# [('株式会社山田商事','ORGANIZATION',None), ('佐藤部長','PERSON',None), ('10月5日','DATE','2026-10-05'), ('45億円','MONEY',4500000000.0)]

r = a.analyze("コーヒーはいまいちだけどケーキは神。")
[(s.text, s.polarity, s.target_text) for s in r.sentiment.expressions]   # evaluations carry their target
# [('いまいちだ','negative','コーヒー'), ('神','positive','ケーキ')]

d = a.analyze_document(markdown_text)     # paragraphs / sentences / document_chunks (heading path, table header, code lead-in as context)
q = a.analyze_query("東京支店の今年度の売上目標はいくら？")
(q.intent, q.answer_type, q.target, q.constraints)
# ('search_value', 'MONEY', '売上目標', {'organization': ['東京支店'], 'time': ['FY2026']})
```

Sentiment (evaluative words, `sentiment.csv`) and emotion (affect words, `emotion.csv`) are kept apart: `sentiment.polarity` is the evaluation, `affect_polarity` the feeling. Emotions cover Plutchik's eight primaries plus KotobaCore's finer labels (irritation, anxiety, admiration, moved, refusal, agreement, exaggeration). Intents include feedback / pricing_complaint / request / question / desire / agreement plus `inform` and `share_experience`.

## Predicates, events and reranking (v0.5)

```python
r = a.analyze("株式会社山田商事は2025年度に大阪支社を設立した。")
r.events[0]      # Event(type='FOUND', agent_text='株式会社山田商事', object_text='大阪支社', time_text='2025年度', ...)

from kotobacore.rag import ChunkView, rerank, InMemoryRetriever, HYBRID_ALPHA
views = [ChunkView.from_chunk(c, d) for c in d.document_chunks]
rerank(q, views)                                  # [(chunk_index, score, {entity_match, keyword_overlap, intent_match, time_match, ...}), ...]
ret = InMemoryRetriever(embed=my_embedding_fn)    # embeddings are injected, never bundled
ret.index("doc1", d); ret.search(q, k=3)
```

Retrieval evaluation: MRR 0.769 → 0.846 on a 200-question synthetic set (447 chunks incl. distractors) and 0.570 → 0.720 on 30 real business documents (5,174 chunks, 120 questions); with an external e5-base embedding the hybrid path reaches 0.868 / 0.777. The hybrid weight `HYBRID_ALPHA` is fixed at 0.3 (query-time switching was evaluated and rejected).

## Document-level coreference (v0.6.2)

```python
d = a.analyze_document("株式会社北斗物流は新倉庫を開設した。\n北斗は来年も投資する。\n同社の社長は佐藤氏だ。")
[(e.surface, e.source, e.canonical_id) for e in d.entities if e.type == "ORGANIZATION"]
# [('株式会社北斗物流','pattern','e1'), ('北斗','coreference','e1'), ('同社','coreference','e1')]
```

Mentions of the same thing (honorifics stripped, legal forms stripped, abbreviations, 同社 / 同氏 / 彼 anaphora) share a `canonical_id`; ids stay unique.

## Vocab — vocabulary tables and token ids (v0.6, optional module)

```python
from kotobacore.vocab import build_vocab, extend_vocab, VocabEncoder, vocab_report

vocab = build_vocab(open("corpus.txt", encoding="utf-8"), min_freq=2)   # ids 0-9 = <pad> <unk> <bos> <eos> <sep> <mask> <cls> <nl> <sp> <reserved>
enc = VocabEncoder(vocab)
ids = enc.encode("東京に行った。\n私は走った", add_special=True)         # every character is a piece → no OOV loss
enc.decode(ids)                                                          # '東京に行った。\n私は走った' (normalized text)
extend_vocab(vocab, more_texts)                                          # append-only: existing ids never change
vocab_report(vocab, held_out_texts)                                      # coverage / OOV / <unk> / frequency profile / contamination candidates
```

Vocabulary *data* is not bundled (it is corpus-specific); reference vocabularies are planned as a separate repository. CLI: `kotobacore vocab build|encode|decode|report`.

## HTTP API (v0.6.1, extra `api`)

```bash
pip install "kotobacore[api]"
KOTOBACORE_API_TOKEN=secret kotobacore serve --port 8590 --rate-limit 120   # OpenAPI at /docs
curl -s -X POST http://127.0.0.1:8590/query -H "Authorization: Bearer secret" \
     -H "Content-Type: application/json" -d '{"text":"東京支店の今年度の売上目標はいくら？","reference_date":"2026-09-08"}'
```

`POST /analyze` (`document` / `reference_date` / `semantic_only`), `/query`, `/chunk`, `/tokenize`; `GET /health`, `/version`. Optional bearer auth and per-client rate limit; no access log, input text never echoed in errors; error shape `{"error": {"code": "E701 unauthorized", "message": "…"}}`. See `docs/API.md`.

## Output JSON structure

```json
{
  "chunks": [
    {"id": 0, "text": "クラウドAPI", "type": "service",      "score": 0.96},
    {"id": 1, "text": "課金高すぎ",  "type": "complaint",    "score": 0.88},
    {"id": 2, "text": "しぬw",       "type": "slang_emotion","score": 0.88}
  ],
  "emotion": {
    "primary": "anger",
    "polarity": "negative",
    "intensity": 0.82,
    "plutchik_axes": ["anger", "disgust"]
  },
  "intent": {"label": "pricing_complaint", "score": 0.85},
  "rag": {
    "keywords": ["クラウドAPI", "課金"],
    "search_query": "クラウドAPI 課金",
    "summary_hint": "pricing complaint about cloud API"
  }
}
```

---

## CLI

```bash
kotobacore analyze "今日のランチが絶品だった" --pretty
kotobacore analyze report.md --document --file --reference-date 2026-09-08
kotobacore tokenize "思い出した" --granularity fine
kotobacore query "東京支店の今年度の売上目標はいくら？"
kotobacore chunk report.md --max-chars 400
kotobacore vocab build corpus/ --out vocab.json --min-freq 2
kotobacore serve --port 8590 --token secret
kotobacore eval annotated
kotobacore version --matrix
```

---

## Demo UI

```bash
streamlit run tools/demo_ui/streamlit_app.py
# → http://localhost:8501
```

Live demo: https://kotobacore.mooma.style/

---

## Comparison with other libraries

| Library | Tokenize | Emotion | Intent | RAG keywords | External deps |
|---|:---:|:---:|:---:|:---:|---|
| MeCab / SudachiPy | ✅ | ❌ | ❌ | ❌ | C++/dictionaries |
| GiNZA (spaCy) | ✅ | ❌ | ❌ | ❌ | spaCy model |
| oseti / asari | ❌ | pos/neg only | ❌ | ❌ | dictionary/ML |
| BERT-based (transformers) | ✅ | ✅ | △ | ❌ | multi-GB models |
| **KotobaCore** | ✅ | **Plutchik 8-axis** | **✅** | **✅** | **none** |

KotobaCore fills the niche of "structuring emotion, intent, and RAG keywords into one JSON pipeline."

Measured (`tools/benchmark/compare_baselines.py`, boundary F1 on 100 human-annotated sentences — the gold follows KotobaCore's coarse semantic units, so short-unit analyzers score high recall / lower precision; speed = 300 sentences × 3 warm passes):

| tool | boundary F1 | ms / sentence | dictionary size |
|---|---|---|---|
| KotobaCore coarse (Karuizawa 1.0) | 0.894 | 0.27 | 0.3 MB |
| SudachiPy C | 0.875 | 0.04 | 218 MB |
| janome (IPADIC) | 0.865 | 0.71 | 211 MB |

---

## Status

**v1.0.0** (2026-09-09) — the Semantic IR schema is frozen at **1.0** and every component (tokenizer, dictionary set, modules, HTTP API) is versioned 1.0. Published on PyPI (`pip install kotobacore`) and GitHub (tag v1.0.0); the live demo runs the same build.

- 6,500-sentence template evaluation: emotion accuracy 96.8% / polarity 96.7% / intent 75.1%, 0 processing errors, 0% false positives on the animal-sound canary set.
- 300 human-annotated sentences (v1, five genres): segmentation F1 0.90 / entity F1 0.86 / sentiment 83.0% / emotion 84.1% / intent 70.0%. With the bundled dictionaries alone (plain `pip install`, no external NRC lexicon): emotion 83.5% / intent 69.7%, the rest unchanged. Against MeCab-based baselines on the same set: polarity 83.0% vs pymlask 61.0% / oseti 47.7%, emotion 83.5% vs pymlask 23.1% (`tools/benchmark/sentiment_baselines.md`).
- Retrieval: MRR 0.846 (synthetic 200 q) / 0.720 (30 real business documents, 120 q); hybrid with an external e5-base embedding 0.868 / 0.777.
- Performance (NFR-001, single core, all four modules): 100,000 sentences in 98 s (1,021 sentences/s), 1.0 ms mean per sentence, a 10,000-character document in 0.63 s.
- **352 tests pass** (incl. the 36-sentence golden set, error-handling E1xx–E7xx, vocabulary contamination). Zero runtime dependencies beyond PyYAML and typer.

Highlights since 0.2: Karuizawa lattice tokenizer with N4 lemmatization and okurigana normalization, entity extraction (dictionary / pattern / time / quantity / quoted names) with document-level coreference, targeted sentiment and emotion (holder / about), predicate-argument structure → events / relations, Query IR + semantic chunking + reranking features, Vocab module, HTTP API, recoverable error handling in the IR, and a component compatibility matrix. See the [CHANGELOG](CHANGELOG.md).

---

## Documentation

- `docs/API.md` — Python API / CLI / HTTP API (auth, rate limit, error shape)
- `docs/openapi.json` — OpenAPI 3.1 for the HTTP API (generated by `tools/gen_openapi.py`, same as `/docs`)
- `docs/IR_SCHEMA.md` — every field of the Semantic IR (generated from the dataclasses by `tools/gen_schema_doc.py`; schema 1.0)
- `docs/TOKENIZATION.md` — segmentation criteria (coarse = semantic units / fine = stem, okurigana, inflection) and known quirks
- `CHANGELOG.md` — changes and measurements per release

## Compatibility matrix (v1.0.0, output of `kotobacore version --matrix`)

1.0.0 unifies every component at 1.0 (the IR schema is frozen; the old numbering lineage is kept in module comments and in the `history` field of `resources/dict/versions.json`).

| Target | Version | Compatibility policy |
|---|---|---|
| KotobaCore package | 1.0.0 | SemVer. From 1.0 on, breaking changes only in a major release |
| IR schema | 1.0 (frozen) | Adding fields is backward compatible; removing or retyping is a major change |
| Tokenizer (Karuizawa) | 1.0 | Bumped whenever segmentation results change |
| Dictionary set | 1.0 | Additions are patch, meaning changes are minor. Per-CSV versions in resources/dict/versions.json |
| Intent / Emotion / Sentiment / Topic modules | 1.0 | Versioned independently per module |
| Vocabulary format | kotobacore-vocab-1.0 | Append-only within a major. Vocabulary data is not bundled; a reference vocabulary will be distributed from a separate repository |
| HTTP API | 1.0 | Major on breaking changes to paths or response shapes |
| Legacy import paths | deprecated 0.6.4 → removed 1.1 | kotobacore.schema / normalizer / tokenizer / semantic / emotion / intent / clause / matching |

Every analysis result records the tokenizer / dictionary set / module versions in `meta.components` for reproducibility. The legacy import paths keep working with a `DeprecationWarning` through v1.0 and are removed in v1.1. `kotobacore.compat` (the Karuizawa-compatible API) stays.

## License

Apache License 2.0
