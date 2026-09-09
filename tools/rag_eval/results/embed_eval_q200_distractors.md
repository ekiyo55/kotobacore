# Embedding × KotobaCore — intfloat/multilingual-e5-base / KotobaCore 0.5.2

docs 24 / chunks 447 / questions 200 / gold missing 0 | chunking 2.4s, index embedding 20.3s, query embedding 4.84s

| condition | R@1 | R@3 | R@5 | MRR@10 |
|---|---|---|---|---|
| bm25 | 68.5 | 82.0 | 90.0 | 0.766 |
| kotobacore_lex | 76.0 | 89.0 | 94.0 | 0.833 |
| emb | 72.5 | 86.0 | 91.0 | 0.805 |
| emb+rerank | 78.0 | 89.5 | 91.5 | 0.84 |
| rrf(bm25,emb) | 73.0 | 89.5 | 95.0 | 0.817 |
| hybrid(α=0.5) | 76.0 | 90.0 | 93.5 | 0.837 |
| hybrid+filter+rerank | 78.5 | 89.0 | 91.5 | 0.844 |
| full(rrf(lex_ir,emb)+filter+rerank) | 78.5 | 89.0 | 92.5 | 0.845 |

## hybrid α grid (α = weight of bm25)

| α | R@1 | R@3 | R@5 | MRR@10 |
|---|---|---|---|---|
| hybrid(α=0.3) | 78.0 | 88.5 | 93.5 | 0.845 |
| hybrid(α=0.5) | 76.0 | 90.0 | 93.5 | 0.837 |
| hybrid(α=0.7) | 71.0 | 87.0 | 94.0 | 0.8 |

## By lexical relation (R@3)

| group | n | bm25 | kotobacore_lex | emb | emb+rerank | hybrid+filter+rerank | full(rrf(lex_ir,emb)+filter+rerank) |
|---|---|---|---|---|---|---|---|
| abbrev | 20 | 85.0 | 80.0 | 80.0 | 80.0 | 80.0 | 80.0 |
| paraphrase | 52 | 76.9 | 90.4 | 86.5 | 92.3 | 92.3 | 92.3 |
| relative_time | 19 | 78.9 | 94.7 | 84.2 | 94.7 | 94.7 | 94.7 |
| same | 70 | 92.9 | 95.7 | 91.4 | 91.4 | 91.4 | 91.4 |
| synonym | 39 | 69.2 | 76.9 | 79.5 | 84.6 | 82.1 | 82.1 |

## By question type (R@3)

| group | n | bm25 | kotobacore_lex | emb | emb+rerank | hybrid+filter+rerank | full(rrf(lex_ir,emb)+filter+rerank) |
|---|---|---|---|---|---|---|---|
| compare | 15 | 93.3 | 86.7 | 93.3 | 86.7 | 86.7 | 86.7 |
| date | 30 | 80.0 | 93.3 | 86.7 | 90.0 | 90.0 | 90.0 |
| definition | 20 | 85.0 | 95.0 | 85.0 | 90.0 | 90.0 | 90.0 |
| howto | 25 | 84.0 | 92.0 | 96.0 | 96.0 | 96.0 | 96.0 |
| list | 10 | 80.0 | 90.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| location | 15 | 73.3 | 86.7 | 86.7 | 93.3 | 93.3 | 93.3 |
| person | 20 | 75.0 | 85.0 | 55.0 | 70.0 | 65.0 | 65.0 |
| reason | 20 | 80.0 | 90.0 | 80.0 | 85.0 | 85.0 | 85.0 |
| value | 35 | 80.0 | 80.0 | 88.6 | 91.4 | 91.4 | 91.4 |
| yesno | 10 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
