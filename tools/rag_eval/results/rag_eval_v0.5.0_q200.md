# RAG retrieval eval — KotobaCore 0.5.0

docs 24 / chunks 147 / questions 200 / gold missing 0

| condition | R@1 | R@3 | R@5 | MRR@10 |
|---|---|---|---|---|
| bm25_raw | 73.0 | 90.5 | 95.0 | 0.821 |
| bm25_raw+rerank | 77.0 | 92.0 | 96.0 | 0.849 |
| bm25_ir | 78.0 | 89.5 | 95.5 | 0.85 |
| bm25_ir+filter | 77.5 | 89.0 | 94.5 | 0.847 |
| bm25_ir+filter+rerank | 78.5 | 91.5 | 95.5 | 0.856 |
| tfidf_raw | 75.5 | 89.0 | 94.5 | 0.83 |
| tfidf_raw+rerank | 78.0 | 91.0 | 96.0 | 0.848 |

## By question type (R@3)

| group | n | bm25_raw | bm25_ir | bm25_ir+filter+rerank | tfidf_raw | tfidf_raw+rerank |
|---|---|---|---|---|---|---|
| compare | 15 | 93.3 | 93.3 | 93.3 | 93.3 | 93.3 |
| date | 30 | 90.0 | 86.7 | 86.7 | 90.0 | 93.3 |
| definition | 20 | 95.0 | 95.0 | 95.0 | 95.0 | 95.0 |
| howto | 25 | 92.0 | 92.0 | 92.0 | 92.0 | 88.0 |
| list | 10 | 90.0 | 100.0 | 100.0 | 90.0 | 90.0 |
| location | 15 | 86.7 | 86.7 | 86.7 | 86.7 | 86.7 |
| person | 20 | 85.0 | 85.0 | 90.0 | 80.0 | 90.0 |
| reason | 20 | 95.0 | 85.0 | 95.0 | 90.0 | 95.0 |
| value | 35 | 85.7 | 85.7 | 88.6 | 82.9 | 85.7 |
| yesno | 10 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |

## By lexical relation (R@3)

| group | n | bm25_raw | bm25_ir | bm25_ir+filter+rerank | tfidf_raw | tfidf_raw+rerank |
|---|---|---|---|---|---|---|
| abbrev | 20 | 90.0 | 85.0 | 85.0 | 85.0 | 90.0 |
| paraphrase | 52 | 92.3 | 86.5 | 92.3 | 88.5 | 90.4 |
| relative_time | 19 | 94.7 | 94.7 | 84.2 | 94.7 | 94.7 |
| same | 70 | 95.7 | 98.6 | 98.6 | 95.7 | 97.1 |
| synonym | 39 | 76.9 | 76.9 | 84.6 | 76.9 | 79.5 |
