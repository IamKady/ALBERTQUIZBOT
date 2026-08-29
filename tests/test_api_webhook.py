import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from api.index import app
from bot.config.settings import settings
from bot.database.session import init_db

@pytest_asyncio.fixture(autouse=True)
async def ensure_db():
    await init_db()

@pytest.mark.asyncio
async def test_root_dashboard():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert "Albert Quiz Bot" in response.text
        assert "Serverless Active on Vercel" in response.text

@pytest.mark.asyncio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"]["connected"] is True

@pytest.mark.asyncio
async def test_webhook_secret_rejection():
    # When WEBHOOK_SECRET is set, requests without matching secret must be 403
    original_secret = settings.WEBHOOK_SECRET
    settings.WEBHOOK_SECRET = "super_secure_secret_123"

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/webhook",
                json={"update_id": 1000},
                headers={"X-Telegram-Bot-Api-Secret-Token": "wrong_secret"}
            )
            assert response.status_code == 403
            assert response.json()["detail"] == "Invalid secret token"
    finally:
        settings.WEBHOOK_SECRET = original_secret

@pytest.mark.asyncio
async def test_cron_trigger_execution():
    original_secret = settings.CRON_SECRET
    settings.CRON_SECRET = ""

    try:
        with patch("api.index.get_bot") as mock_get_bot, \
             patch("api.index.run_cron_cycle", new_callable=AsyncMock) as mock_cron:
            mock_cron.return_value = {
                "status": "success",
                "cleaned_polls": 0,
                "quizzes_sent": 1,
                "total_active_chats": 1
            }

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/cron")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"
                assert data["quizzes_sent"] == 1
                mock_cron.assert_awaited_once()
    finally:
        settings.CRON_SECRET = original_secret

@pytest.mark.asyncio
async def test_cron_trigger_unauthorized():
    original_secret = settings.CRON_SECRET
    settings.CRON_SECRET = "secret_cron_pass"

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/cron")
            assert response.status_code == 401
    finally:
        settings.CRON_SECRET = original_secret
