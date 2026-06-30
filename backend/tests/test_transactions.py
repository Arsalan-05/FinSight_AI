import io


def _make_user(client):
    r = client.post("/users/", json={"email": "test@example.com", "name": "Test"})
    assert r.status_code == 201
    return r.json()


def _make_account(client, user_id):
    r = client.post(
        "/accounts/",
        json={
            "user_id": user_id,
            "name": "Checking",
            "institution": "Chase",
            "account_type": "checking",
        },
    )
    assert r.status_code == 201
    return r.json()


def test_create_transaction(client):
    user = _make_user(client)
    account = _make_account(client, user["id"])

    r = client.post(
        "/transactions/",
        json={
            "account_id": account["id"],
            "transaction_date": "2026-04-15",
            "description": "Grocery Store",
            "amount": -52.40,
            "category": "Groceries",
            "merchant": "Whole Foods",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["description"] == "Grocery Store"
    assert data["category"] == "Groceries"
    assert float(data["amount"]) == -52.40


def test_list_transactions_filter_by_category(client):
    user = _make_user(client)
    account = _make_account(client, user["id"])

    for desc, cat in [("Coffee", "Dining"), ("Rent", "Housing"), ("Uber", "Transport")]:
        client.post(
            "/transactions/",
            json={
                "account_id": account["id"],
                "transaction_date": "2026-05-01",
                "description": desc,
                "amount": -10.0,
                "category": cat,
            },
        )

    r = client.get("/transactions/", params={"account_id": account["id"], "category": "Dining"})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["category"] == "Dining"


def test_upload_csv(client):
    user = _make_user(client)
    account = _make_account(client, user["id"])

    csv_content = (
        "date,description,amount,category,merchant\n"
        "2026-06-01,Netflix,-15.99,Subscriptions,Netflix\n"
        "2026-06-02,Salary,4500.00,Income,Acme Corp\n"
        "2026-06-03,Coffee,-5.50,Dining,Starbucks\n"
    )
    r = client.post(
        "/transactions/upload",
        params={"account_id": account["id"]},
        files={"file": ("txns.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["created"] == 3
    assert body["errors"] == []


def test_upload_csv_missing_column_returns_422(client):
    user = _make_user(client)
    account = _make_account(client, user["id"])

    bad_csv = "foo,bar\n1,2\n"
    r = client.post(
        "/transactions/upload",
        params={"account_id": account["id"]},
        files={"file": ("bad.csv", io.BytesIO(bad_csv.encode()), "text/csv")},
    )
    assert r.status_code == 422


def test_get_transaction_not_found(client):
    r = client.get("/transactions/nonexistent-id")
    assert r.status_code == 404


def test_delete_transaction(client):
    user = _make_user(client)
    account = _make_account(client, user["id"])

    create_r = client.post(
        "/transactions/",
        json={
            "account_id": account["id"],
            "transaction_date": "2026-06-10",
            "description": "Delete me",
            "amount": -9.99,
            "category": "Test",
        },
    )
    tx_id = create_r.json()["id"]

    del_r = client.delete(f"/transactions/{tx_id}")
    assert del_r.status_code == 204

    get_r = client.get(f"/transactions/{tx_id}")
    assert get_r.status_code == 404


def test_patch_transaction_category(client):
    user = _make_user(client)
    account = _make_account(client, user["id"])

    create_r = client.post(
        "/transactions/",
        json={
            "account_id": account["id"],
            "transaction_date": "2026-06-10",
            "description": "Misc purchase",
            "amount": -25.0,
            "category": "Uncategorized",
        },
    )
    tx_id = create_r.json()["id"]

    patch_r = client.patch(
        f"/transactions/{tx_id}",
        json={"category": "Groceries"},
    )
    assert patch_r.status_code == 200
    assert patch_r.json()["category"] == "Groceries"
