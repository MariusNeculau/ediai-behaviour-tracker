def test_dashboard_renders(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"Saplings" not in res.data
