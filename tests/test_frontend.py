def test_index_page_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.text
    assert "Start Recording" in body
    assert "Stop Recording" in body
    assert "Enable real-time preview" in body
    assert "/app.js" in body
