# NFR-001 batch benchmark — KotobaCore 0.6.8

| item | measured | target | pass |
|---|---|---|---|
| 100,000 sentences (single core, 4 modules) | 97.9 s (1,021 文/s) | ≤ 600 s / 100k | ✅ |
| analyze() per sentence mean / median / p95 / p99 / max | 0.977 / 0.874 / 1.721 / 2.506 / 15.946 ms | mean ≤ 5 ms | ✅ |
| analyze_document() 10,000 chars (479 sentences → 87 chunks) | 0.627 s | ≤ 1 s | ✅ |

texts: 3,068 unique (SNS examples + annotated_v1 + golden), cycled with 10 suffix variants.
