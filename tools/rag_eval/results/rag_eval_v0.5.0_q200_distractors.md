# RAG retrieval eval — KotobaCore 0.5.0

docs 24 / chunks 447 / questions 200 / gold missing 0

| condition | R@1 | R@3 | R@5 | MRR@10 |
|---|---|---|---|---|
| bm25_raw | 68.5 | 82.0 | 89.5 | 0.769 |
| bm25_raw+rerank | 74.5 | 88.0 | 93.0 | 0.824 |
| bm25_ir | 70.5 | 86.0 | 93.5 | 0.792 |
| bm25_ir+filter | 72.5 | 87.0 | 94.5 | 0.808 |
| bm25_ir+filter+rerank | 74.5 | 89.5 | 94.0 | 0.826 |
| tfidf_raw | 69.5 | 81.5 | 89.5 | 0.773 |
| tfidf_raw+rerank | 74.0 | 87.0 | 93.5 | 0.817 |

## By question type (R@3)

| group | n | bm25_raw | bm25_ir | bm25_ir+filter+rerank | tfidf_raw | tfidf_raw+rerank |
|---|---|---|---|---|---|---|
| compare | 15 | 93.3 | 93.3 | 86.7 | 93.3 | 86.7 |
| date | 30 | 80.0 | 80.0 | 93.3 | 80.0 | 90.0 |
| definition | 20 | 85.0 | 90.0 | 95.0 | 80.0 | 90.0 |
| howto | 25 | 84.0 | 88.0 | 92.0 | 88.0 | 88.0 |
| list | 10 | 80.0 | 90.0 | 90.0 | 80.0 | 90.0 |
| location | 15 | 73.3 | 80.0 | 86.7 | 60.0 | 86.7 |
| person | 20 | 75.0 | 85.0 | 85.0 | 75.0 | 80.0 |
| reason | 20 | 80.0 | 85.0 | 90.0 | 80.0 | 90.0 |
| value | 35 | 80.0 | 82.9 | 82.9 | 82.9 | 80.0 |
| yesno | 10 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |

## By lexical relation (R@3)

| group | n | bm25_raw | bm25_ir | bm25_ir+filter+rerank | tfidf_raw | tfidf_raw+rerank |
|---|---|---|---|---|---|---|
| abbrev | 20 | 85.0 | 80.0 | 80.0 | 75.0 | 80.0 |
| paraphrase | 52 | 76.9 | 86.5 | 90.4 | 82.7 | 88.5 |
| relative_time | 19 | 78.9 | 84.2 | 94.7 | 78.9 | 89.5 |
| same | 70 | 92.9 | 95.7 | 95.7 | 91.4 | 95.7 |
| synonym | 39 | 69.2 | 71.8 | 79.5 | 66.7 | 71.8 |
