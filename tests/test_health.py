def test_health_check(client):
    """Test that the /health endpoint responds with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["app"] == "CineBook"
