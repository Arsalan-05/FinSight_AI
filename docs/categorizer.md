# Transaction categorizer

Every imported transaction gets one of FinSight's categories (Dining, Groceries,
Transport, Housing, Subscriptions, Income, Transfers, Savings, and so on).

## How a category is chosen

1. **User rules** (`category_rules`): changing a category on the Transactions page
   saves a `merchant_contains` rule for that merchant, moves the user's other
   transactions from the same merchant to the new category, and applies to every
   future CSV import and Plaid sync. The newest correction for a merchant replaces
   the old one and is checked first. Pass `?learn=false` on the PATCH for a one-off
   change. Rules can also be added by hand in Settings and re-run with
   `POST /transactions/rules/apply`.
2. **Merchant aliases** (`ingest/merchants.py`): raw descriptors such as
   `TIM HORTONS #1234 TORONTO` normalize to a canonical merchant first.
3. **Keyword rules** (`ingest/categorizer.py`): ordered keyword lists tuned for
   Canadian merchants (Loblaws, Presto, Rogers, Interac e-Transfer, and others).
4. **Fallback**: `Uncategorized`, which the agent treats as its own bucket.

Keyword rules are deterministic, explainable and free, which matters more here
than squeezing out the last few points of accuracy.

## Optional learned model

`ingest.categorizer.train_and_evaluate` trains a TF-IDF + logistic regression
baseline when scikit-learn is installed. scikit-learn is deliberately not a
production dependency, so the deployed API always uses the rules above.

```bash
cd backend && uv run --with scikit-learn python -c \
  "from ingest.categorizer import train_and_evaluate; print(train_and_evaluate().to_dict())"
```
