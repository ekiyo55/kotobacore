# Embedding × KotobaCore — intfloat/multilingual-e5-base / KotobaCore 0.5.3

docs 24 / chunks 447 / questions 200 / gold missing 0 | chunking 2.8s, index embedding 0.0s, query embedding 0.05s

| condition | R@1 | R@3 | R@5 | MRR@10 |
|---|---|---|---|---|
| bm25 | 68.5 | 82.0 | 90.0 | 0.766 |
| kotobacore_lex | 78.0 | 89.0 | 94.5 | 0.846 |
| emb | 72.5 | 86.0 | 91.0 | 0.805 |
| emb+rerank | 78.5 | 89.5 | 92.0 | 0.844 |
| rrf(bm25,emb) | 73.0 | 89.5 | 95.0 | 0.817 |
| hybrid(α=0.3) | 78.0 | 88.5 | 93.5 | 0.845 |
| hybrid+filter+rerank | 80.5 | 91.5 | 95.0 | 0.868 |
| full(rrf(lex_ir,emb)+filter+rerank) | 79.5 | 91.0 | 95.0 | 0.862 |

## hybrid α grid (α = weight of bm25)

| α | R@1 | R@3 | R@5 | MRR@10 |
|---|---|---|---|---|
| hybrid(α=0.3) | 78.0 | 88.5 | 93.5 | 0.845 |
| hybrid(α=0.5) | 76.0 | 90.0 | 93.5 | 0.837 |
| hybrid(α=0.7) | 71.0 | 87.0 | 94.0 | 0.8 |

## By lexical relation (R@3)

| group | n | bm25 | kotobacore_lex | emb | emb+rerank | hybrid+filter+rerank | full(rrf(lex_ir,emb)+filter+rerank) |
|---|---|---|---|---|---|---|---|
| abbrev | 20 | 85.0 | 80.0 | 80.0 | 80.0 | 85.0 | 85.0 |
| paraphrase | 52 | 76.9 | 90.4 | 86.5 | 92.3 | 94.2 | 92.3 |
| relative_time | 19 | 78.9 | 94.7 | 84.2 | 94.7 | 94.7 | 94.7 |
| same | 70 | 92.9 | 95.7 | 91.4 | 91.4 | 95.7 | 92.9 |
| synonym | 39 | 69.2 | 76.9 | 79.5 | 84.6 | 82.1 | 87.2 |

## By question type (R@3)

| group | n | bm25 | kotobacore_lex | emb | emb+rerank | hybrid+filter+rerank | full(rrf(lex_ir,emb)+filter+rerank) |
|---|---|---|---|---|---|---|---|
| compare | 15 | 93.3 | 86.7 | 93.3 | 86.7 | 93.3 | 93.3 |
| date | 30 | 80.0 | 93.3 | 86.7 | 90.0 | 96.7 | 93.3 |
| definition | 20 | 85.0 | 95.0 | 85.0 | 90.0 | 90.0 | 90.0 |
| howto | 25 | 84.0 | 92.0 | 96.0 | 96.0 | 96.0 | 92.0 |
| list | 10 | 80.0 | 90.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| location | 15 | 73.3 | 86.7 | 86.7 | 93.3 | 93.3 | 93.3 |
| person | 20 | 75.0 | 85.0 | 55.0 | 70.0 | 80.0 | 80.0 |
| reason | 20 | 80.0 | 90.0 | 80.0 | 85.0 | 85.0 | 85.0 |
| value | 35 | 80.0 | 80.0 | 88.6 | 91.4 | 88.6 | 91.4 |
| yesno | 10 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
