# RAG retrieval eval — KotobaCore 0.5.0

docs 24 / chunks 447 / questions 80 / gold missing 0

| condition | R@1 | R@3 | R@5 | MRR@10 |
|---|---|---|---|---|
| bm25_raw | 63.8 | 80.0 | 88.8 | 0.738 |
| bm25_raw+rerank | 71.2 | 87.5 | 93.8 | 0.81 |
| bm25_ir | 66.2 | 83.8 | 93.8 | 0.765 |
| bm25_ir+filter | 66.2 | 83.8 | 95.0 | 0.767 |
| bm25_ir+filter+rerank | 70.0 | 86.2 | 96.2 | 0.803 |
| tfidf_raw | 65.0 | 78.8 | 88.8 | 0.739 |
| tfidf_raw+rerank | 71.2 | 86.2 | 95.0 | 0.804 |

## By question type (R@3)

| group | n | bm25_raw | bm25_ir | bm25_ir+filter+rerank | tfidf_raw | tfidf_raw+rerank |
|---|---|---|---|---|---|---|
| compare | 6 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| date | 12 | 75.0 | 75.0 | 75.0 | 75.0 | 83.3 |
| definition | 8 | 100.0 | 100.0 | 100.0 | 87.5 | 100.0 |
| howto | 10 | 90.0 | 90.0 | 90.0 | 90.0 | 90.0 |
| list | 4 | 50.0 | 75.0 | 75.0 | 50.0 | 75.0 |
| location | 6 | 66.7 | 66.7 | 83.3 | 50.0 | 83.3 |
| person | 8 | 62.5 | 75.0 | 75.0 | 62.5 | 62.5 |
| reason | 8 | 75.0 | 75.0 | 100.0 | 75.0 | 100.0 |
| value | 14 | 78.6 | 85.7 | 78.6 | 85.7 | 78.6 |
| yesno | 4 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |

## By lexical relation (R@3)

| group | n | bm25_raw | bm25_ir | bm25_ir+filter+rerank | tfidf_raw | tfidf_raw+rerank |
|---|---|---|---|---|---|---|
| abbrev | 8 | 62.5 | 50.0 | 50.0 | 37.5 | 50.0 |
| paraphrase | 20 | 65.0 | 80.0 | 95.0 | 75.0 | 90.0 |
| relative_time | 7 | 85.7 | 85.7 | 71.4 | 85.7 | 85.7 |
| same | 30 | 90.0 | 93.3 | 93.3 | 90.0 | 93.3 |
| synonym | 15 | 86.7 | 86.7 | 86.7 | 80.0 | 86.7 |
