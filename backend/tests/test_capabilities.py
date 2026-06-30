"""Public capability manifest."""

def test_capabilities_manifest(client) -> None:
    r = client.get("/capabilities")
    assert r.status_code == 200
    data = r.json()
    assert data["product"] == "FinSight AI"
    assert data["stack"]["api"] == "FastAPI"
    assert data["agent"]["tool_count"] >= 8
    assert "search_transactions" in data["agent"]["tools"]
    assert "aggregate_spending" in data["agent"]["tools"]
