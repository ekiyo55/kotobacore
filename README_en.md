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
kotobacore tokenize "東京都に行った"
kotobacore version
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

---

## Status

**v0.2.2** pre-alpha. On a 5,000-sentence quality evaluation: emotion accuracy 95.2% / polarity accuracy
96.0% / intent accuracy 68.1% / intent detection 70.8%, with 0 processing errors. Throughput on a
production server averages **1.81ms** per sentence (p99 2.35ms, zero external dependencies).
**All 186 tests pass** (including a 36-sentence real-text golden set).

Highlights of v0.2: Karuizawa's single-pass lattice + Viterbi tokenization (with bigram connection
costs — even the classic すもももももももものうち parses perfectly), negation-scope handling
(好きじゃない → negative), clause-based adversative weighting (〜でしたが成功しました → positive),
and a unified Aho-Corasick matching layer. See the [CHANGELOG](CHANGELOG.md) for details.

---

## License

Apache License 2.0
