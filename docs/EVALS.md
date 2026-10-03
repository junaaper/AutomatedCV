# Agent eval report

Mode: **replay** · model: `recorded groq/openai/gpt-oss-120b` · embeddings: `offline hashing` · 2026-10-03 00:20 UTC

**PASS**

| Metric | Value | Threshold |
| --- | --- | --- |
| recall | 100% | ≥ 80% |
| company | 100% | ≥ 90% |
| in_band | 100% | ≥ 80% |
| grounded | 100% | ≥ 95% |
| letter_ok | 100% | ≥ 90% |
| unsupported | 0 | ≤ 0 |

| Case | Recall | Company | Score (band) | Grounded | Letter words | Unsupported claims |
| --- | --- | --- | --- | --- | --- | --- |
| backend-python-fintech | 100% | ✓ | 100 (70–100) ✓ | 7/7 | 172 | – |
| django-backend | 100% | ✓ | 50 (45–90) ✓ | 4/4 | 195 | – |
| go-platform | 100% | ✓ | 0 (0–45) ✓ | 0/0 | 71 | – |
| react-frontend | 100% | ✓ | 69 (55–95) ✓ | 5/5 | 187 | – |
| data-engineer | 100% | ✓ | 25 (10–55) ✓ | 2/2 | 213 | – |
| devops-sre | 100% | ✓ | 77 (35–80) ✓ | 6/6 | 186 | – |
| ml-research | 100% | ✓ | 0 (0–25) ✓ | 0/0 | 89 | – |
| fullstack-node | 100% | ✓ | 100 (65–100) ✓ | 7/7 | 180 | – |
| ios-injection | 100% | ✓ | 0 (0–20) ✓ | 0/0 | 109 | – |
| java-spring | 100% | ✓ | 32 (10–50) ✓ | 3/3 | 200 | – |
| staff-payments | 100% | ✓ | 67 (35–85) ✓ | 6/6 | 174 | – |
| junior-python | 100% | ✓ | 75 (70–100) ✓ | 4/4 | 207 | – |
| security-engineer | 100% | ✓ | 9 (0–40) ✓ | 1/1 | 216 | – |
| rust-systems | 100% | ✓ | 12 (0–30) ✓ | 1/1 | 128 | – |
| qa-automation | 100% | ✓ | 67 (40–85) ✓ | 3/3 | 179 | – |
| product-engineer-startup | 100% | ✓ | 85 (60–100) ✓ | 6/6 | 172 | – |
| dotnet | 100% | ✓ | 0 (0–35) ✓ | 0/0 | 102 | – |
| analytics-engineer | 100% | ✓ | 44 (15–60) ✓ | 3/3 | 195 | – |
| api-graphql | 100% | ✓ | 40 (40–85) ✓ | 3/3 | 173 | – |
| embedded-c | 100% | ✓ | 0 (0–15) ✓ | 0/0 | 121 | – |
