# RAG retrieval eval — KotobaCore 0.5.1

docs 24 / chunks 447 / questions 200 / gold missing 0

| condition | R@1 | R@3 | R@5 | MRR@10 |
|---|---|---|---|---|
| bm25_raw | 68.5 | 82.0 | 89.5 | 0.769 |
| bm25_raw+rerank | 74.5 | 87.5 | 93.5 | 0.824 |
| bm25_ir | 69.0 | 85.0 | 92.5 | 0.779 |
| bm25_ir+filter | 70.0 | 86.5 | 93.5 | 0.791 |
| bm25_ir+filter+rerank | 74.0 | 87.5 | 93.5 | 0.822 |
| tfidf_raw | 69.5 | 81.5 | 89.5 | 0.773 |
| tfidf_raw+rerank | 74.5 | 86.5 | 93.5 | 0.82 |

## By question type (R@3)

| group | n | bm25_raw | bm25_ir | bm25_ir+filter+rerank | tfidf_raw | tfidf_raw+rerank |
|---|---|---|---|---|---|---|
| compare | 15 | 93.3 | 93.3 | 86.7 | 93.3 | 86.7 |
| date | 30 | 80.0 | 80.0 | 90.0 | 80.0 | 90.0 |
| definition | 20 | 85.0 | 85.0 | 95.0 | 80.0 | 90.0 |
| howto | 25 | 84.0 | 84.0 | 88.0 | 88.0 | 88.0 |
| list | 10 | 80.0 | 90.0 | 90.0 | 80.0 | 90.0 |
| location | 15 | 73.3 | 80.0 | 86.7 | 60.0 | 86.7 |
| person | 20 | 75.0 | 85.0 | 85.0 | 75.0 | 80.0 |
| reason | 20 | 80.0 | 85.0 | 90.0 | 80.0 | 90.0 |
| value | 35 | 80.0 | 82.9 | 77.1 | 82.9 | 77.1 |
| yesno | 10 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |

## By lexical relation (R@3)

| group | n | bm25_raw | bm25_ir | bm25_ir+filter+rerank | tfidf_raw | tfidf_raw+rerank |
|---|---|---|---|---|---|---|
| abbrev | 20 | 85.0 | 85.0 | 75.0 | 75.0 | 75.0 |
| paraphrase | 52 | 76.9 | 82.7 | 90.4 | 82.7 | 88.5 |
| relative_time | 19 | 78.9 | 78.9 | 94.7 | 78.9 | 89.5 |
| same | 70 | 92.9 | 94.3 | 95.7 | 91.4 | 95.7 |
| synonym | 39 | 69.2 | 74.4 | 71.8 | 66.7 | 71.8 |
