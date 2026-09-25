# Transaction categorizer

Compare after Phase 5 training run. Metrics below are from a **tiny synthetic train**
(`ingest.categorizer.train_and_evaluate`) — placeholder until a real labeled set ships.

| Model | Accuracy | Macro-F1 | Latency | Cost / 1k txs |
|-------|----------|----------|---------|---------------|
| TF-IDF + Logistic Regression | 1.00* | 1.00* | &lt;1 ms | ~$0 |
| Keyword rules fallback | 1.00* | 1.00* | &lt;1 ms | ~$0 |
| DistilBERT fine-tune | — | — | — | GPU train once |
| LLM zero-shot | — | — | — | API $ |

\*Synthetic hold-out (n_train=16, n_test=4). Backend used at runtime: **keyword rules** when
`scikit-learn` is not installed; TF-IDF + LR when it is. Prefer keyword fallback in prod
deps to avoid a heavy sklearn install — add sklearn only in optional/dev if comparing.

Ship the best cost/accuracy option. User corrections feed `category_rules` + retraining set.

```bash
cd backend && python -c "from ingest.categorizer import train_and_evaluate; print(train_and_evaluate().to_dict())"
```
