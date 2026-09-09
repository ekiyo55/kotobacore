# RAG retrieval eval — KotobaCore 0.5.1

docs 24 / chunks 447 / questions 200 / gold missing 0

| condition | R@1 | R@3 | R@5 | MRR@10 |
|---|---|---|---|---|
| bm25_raw | 68.5 | 82.0 | 90.0 | 0.766 |
| bm25_raw+rerank | 75.0 | 87.5 | 94.0 | 0.824 |
| bm25_ir | 69.5 | 86.5 | 92.5 | 0.787 |
| bm25_ir+filter | 70.5 | 87.5 | 93.5 | 0.799 |
| bm25_ir+filter+rerank | 76.0 | 89.0 | 94.0 | 0.833 |
| tfidf_raw | 69.0 | 80.5 | 89.0 | 0.767 |
| tfidf_raw+rerank | 74.5 | 86.5 | 93.5 | 0.82 |

## By question type (R@3)

| group | n | bm25_raw | bm25_ir | bm25_ir+filter+rerank | tfidf_raw | tfidf_raw+rerank |
|---|---|---|---|---|---|---|
| compare | 15 | 93.3 | 93.3 | 86.7 | 93.3 | 86.7 |
| date | 30 | 80.0 | 80.0 | 93.3 | 80.0 | 90.0 |
| definition | 20 | 85.0 | 90.0 | 95.0 | 80.0 | 90.0 |
| howto | 25 | 84.0 | 88.0 | 92.0 | 88.0 | 88.0 |
| list | 10 | 80.0 | 90.0 | 90.0 | 80.0 | 90.0 |
| location | 15 | 73.3 | 86.7 | 86.7 | 60.0 | 86.7 |
| person | 20 | 75.0 | 85.0 | 85.0 | 70.0 | 80.0 |
| reason | 20 | 80.0 | 85.0 | 90.0 | 80.0 | 90.0 |
| value | 35 | 80.0 | 82.9 | 80.0 | 80.0 | 77.1 |
| yesno | 10 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |

## By lexical relation (R@3)

| group | n | bm25_raw | bm25_ir | bm25_ir+filter+rerank | tfidf_raw | tfidf_raw+rerank |
|---|---|---|---|---|---|---|
| abbrev | 20 | 85.0 | 85.0 | 80.0 | 75.0 | 80.0 |
| paraphrase | 52 | 76.9 | 86.5 | 90.4 | 78.8 | 88.5 |
| relative_time | 19 | 78.9 | 84.2 | 94.7 | 78.9 | 89.5 |
| same | 70 | 92.9 | 95.7 | 95.7 | 91.4 | 95.7 |
| synonym | 39 | 69.2 | 71.8 | 76.9 | 66.7 | 69.2 |
