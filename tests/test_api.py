import pytest
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_forecast():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        response = await ac.get("/forecast")
    
    assert response.status_code == 200
    data = response.json()
    
    if "error" in data:
        assert data["error"] == "Model not trained yet"
    else:
        assert "predictions" in data
        assert "risk_levels" in data
        assert "future_hours" in data
