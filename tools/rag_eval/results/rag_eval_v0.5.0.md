# RAG retrieval eval — KotobaCore 0.5.0

docs 24 / chunks 147 / questions 80 / gold missing 0

| condition | R@1 | R@3 | R@5 | MRR@10 |
|---|---|---|---|---|
| bm25_raw | 65.0 | 91.2 | 97.5 | 0.785 |
| bm25_raw+rerank | 72.5 | 88.8 | 96.2 | 0.822 |
| bm25_ir | 73.8 | 87.5 | 96.2 | 0.826 |
| bm25_ir+filter | 72.5 | 88.8 | 96.2 | 0.822 |
| bm25_ir+filter+rerank | 72.5 | 88.8 | 95.0 | 0.824 |
| tfidf_raw | 70.0 | 87.5 | 96.2 | 0.8 |
| tfidf_raw+rerank | 71.2 | 87.5 | 96.2 | 0.814 |

## By question type (R@3)

| group | n | bm25_raw | bm25_ir | bm25_ir+filter+rerank | tfidf_raw | tfidf_raw+rerank |
|---|---|---|---|---|---|---|
| compare | 6 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| date | 12 | 83.3 | 83.3 | 83.3 | 83.3 | 83.3 |
| definition | 8 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| howto | 10 | 90.0 | 90.0 | 90.0 | 90.0 | 90.0 |
| list | 4 | 75.0 | 100.0 | 100.0 | 75.0 | 75.0 |
| location | 6 | 83.3 | 83.3 | 83.3 | 83.3 | 83.3 |
| person | 8 | 87.5 | 75.0 | 75.0 | 75.0 | 75.0 |
| reason | 8 | 100.0 | 75.0 | 100.0 | 87.5 | 100.0 |
| value | 14 | 92.9 | 85.7 | 78.6 | 85.7 | 78.6 |
| yesno | 4 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |

## By lexical relation (R@3)

| group | n | bm25_raw | bm25_ir | bm25_ir+filter+rerank | tfidf_raw | tfidf_raw+rerank |
|---|---|---|---|---|---|---|
| abbrev | 8 | 75.0 | 62.5 | 50.0 | 62.5 | 50.0 |
| paraphrase | 20 | 95.0 | 80.0 | 95.0 | 85.0 | 95.0 |
| relative_time | 7 | 85.7 | 85.7 | 85.7 | 85.7 | 85.7 |
| same | 30 | 93.3 | 96.7 | 96.7 | 93.3 | 93.3 |
| synonym | 15 | 93.3 | 93.3 | 86.7 | 93.3 | 86.7 |
