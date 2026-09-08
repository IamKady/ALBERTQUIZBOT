import os
import sys
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

# Add project root directory to sys.path so bot modules can be imported
root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from fastapi import FastAPI, Request, Response, HTTPException, Header, Query
from fastapi.responses import JSONResponse, HTMLResponse
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Update
from sqlalchemy import text

_startup_error = None
try:
    from bot.config.settings import settings
    from bot.database.session import init_db, engine
    from bot.handlers import main_router
    from bot.middlewares import DbSessionMiddleware, I18nMiddleware, RateLimitMiddleware
    from bot.scheduler import run_cron_cycle
    from bot.utils.logger import setup_logger, logger
    from tools.seed_questions import seed_database
    setup_logger()
except Exception as e:
    import traceback
    _startup_error = traceback.format_exc()


# Global instances for serverless reuse across warm invocations
_bot: Optional[Bot] = None
_dp: Optional[Dispatcher] = None

def get_bot() -> Bot:
    global _bot
    if _bot is None:
        if not settings.BOT_TOKEN:
            raise HTTPException(status_code=500, detail="BOT_TOKEN is not configured in environment!")
        _bot = Bot(
            token=settings.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
        )
    return _bot

def get_dispatcher() -> Dispatcher:
    global _dp
    if _dp is None:
        _dp = Dispatcher()
        # Register Middlewares
        _dp.update.outer_middleware(DbSessionMiddleware())
        _dp.update.outer_middleware(I18nMiddleware())
        _dp.message.middleware(RateLimitMiddleware(limit_seconds=1.0))
        # Register Router Handlers
        _dp.include_router(main_router)
    return _dp

_db_initialized = False

async def ensure_db():
    global _db_initialized
    if not _db_initialized:
        try:
            await init_db()
            _db_initialized = True
        except Exception as e:
            logger.error(f"Database initialization warning: {e}")

app = FastAPI(
    title="Albert Quiz Bot Serverless API",
    description="Production Telegram Quiz Bot on Vercel Serverless",
    version="1.0.0"
)

@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        import traceback
        trace = traceback.format_exc()
        logger.error(f"Unhandled serverless error: {trace}")
        return HTMLResponse(content=f"<h1>500 Serverless Error</h1><pre>{trace}</pre>", status_code=500)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Visual Dashboard and Status Page for Albert Quiz Bot on Vercel."""
    if _startup_error:
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head><title>Startup Error - Albert Quiz Bot</title></head>
            <body style="background:#0f172a; color:#f8fafc; font-family:system-ui,sans-serif; padding:40px; line-height:1.6;">
                <div style="max-width:800px; margin:0 auto;">
                    <h1 style="color:#f43f5e; margin-top:0;">⚠️ Serverless Startup Error</h1>
                    <p style="color:#94a3b8;">The following Python exception was caught during startup on Vercel:</p>
                    <pre style="background:#1e293b; color:#fda4af; padding:20px; border-radius:8px; border:1px solid #334155; overflow:auto; font-size:14px;">{_startup_error}</pre>
                </div>
            </body>
            </html>
            """,
            status_code=500
        )

    base_url = str(request.base_url).rstrip("/")
    bot_configured = bool(settings.BOT_TOKEN) if 'settings' in globals() else False
    db_type = "PostgreSQL" if 'settings' in globals() and "postgres" in settings.DATABASE_URL else "SQLite"


    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Albert Quiz Bot - Vercel Serverless</title>
        <style>
            :root {{
                --bg: #0f172a;
                --card-bg: #1e293b;
                --text: #f8fafc;
                --text-muted: #94a3b8;
                --accent: #38bdf8;
                --accent-hover: #0284c7;
                --success: #22c55e;
                --border: #334155;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background-color: var(--bg);
                color: var(--text);
                margin: 0;
                padding: 40px 20px;
                display: flex;
                justify-content: center;
            }}
            .container {{
                max-width: 720px;
                width: 100%;
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .header h1 {{
                font-size: 2.2rem;
                margin: 0 0 10px 0;
                background: linear-gradient(135deg, #38bdf8, #818cf8);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}
            .badge {{
                display: inline-block;
                padding: 4px 12px;
                border-radius: 9999px;
                font-size: 0.85rem;
                font-weight: 600;
                background-color: rgba(34, 197, 94, 0.2);
                color: var(--success);
                border: 1px solid rgba(34, 197, 94, 0.4);
            }}
            .card {{
                background-color: var(--card-bg);
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 24px;
                margin-bottom: 20px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            }}
            .card h2 {{
                font-size: 1.2rem;
                margin-top: 0;
                color: var(--accent);
            }}
            .grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
                margin-top: 15px;
            }}
            .stat-item {{
                background: rgba(15, 23, 42, 0.6);
                padding: 12px;
                border-radius: 8px;
                border: 1px solid var(--border);
            }}
            .stat-label {{
                font-size: 0.8rem;
                color: var(--text-muted);
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}
            .stat-value {{
                font-size: 1.1rem;
                font-weight: 600;
                margin-top: 4px;
            }}
            ul {{
                padding-left: 20px;
                margin: 10px 0;
                color: var(--text-muted);
            }}
            li {{
                margin-bottom: 8px;
            }}
            code {{
                background: rgba(15, 23, 42, 0.8);
                color: #f43f5e;
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 0.9em;
            }}
            .btn {{
                display: inline-block;
                padding: 10px 20px;
                background-color: var(--accent);
                color: #0f172a;
                font-weight: 600;
                border-radius: 8px;
                text-decoration: none;
                margin-top: 10px;
                margin-right: 10px;
                transition: background-color 0.2s;
            }}
            .btn:hover {{
                background-color: var(--accent-hover);
            }}
            .btn-outline {{
                background: transparent;
                color: var(--accent);
                border: 1px solid var(--accent);
            }}
            .btn-outline:hover {{
                background: rgba(56, 189, 248, 0.1);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 Albert Quiz Bot</h1>
                <div class="badge">● Serverless Active on Vercel</div>
                <p style="color: var(--text-muted); margin-top: 8px;">Continuous, non-repeating Telegram quiz engine powered by Aiogram 3 & SQLAlchemy</p>
            </div>

            <div class="card">
                <h2>⚡ Deployment Status</h2>
                <div class="grid">
                    <div class="stat-item">
                        <div class="stat-label">Bot Token</div>
                        <div class="stat-value" style="color: {'var(--success)' if bot_configured else '#f43f5e'}">
                            {'Configured ✓' if bot_configured else 'Missing ✗'}
                        </div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Database Type</div>
                        <div class="stat-value">{db_type}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Webhook Endpoint</div>
                        <div class="stat-value"><code>/api/webhook</code></div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Cron Interval Endpoint</div>
                        <div class="stat-value"><code>/api/cron</code></div>
                    </div>
                </div>
            </div>

            <div class="card">
                <h2>🚀 Quick Webhook Setup</h2>
                <p>Register this Vercel deployment with Telegram Bot API in 1 click:</p>
                <a href="/api/set-webhook" class="btn">Set Webhook Now</a>
                <a href="/api/webhook-info" class="btn btn-outline">Check Webhook Info</a>
            </div>

            <div class="card">
                <h2>📡 Available API Endpoints</h2>
                <ul>
                    <li><b>POST</b> <code>/api/webhook</code> - Telegram incoming webhook updates</li>
                    <li><b>GET</b> <code>/api/set-webhook</code> - Automatically registers webhook URL with Telegram</li>
                    <li><b>GET</b> <code>/api/webhook-info</code> - Inspects Telegram webhook delivery stats & pending updates</li>
                    <li><b>GET</b> <code>/api/delete-webhook</code> - Removes webhook (when switching back to local polling)</li>
                    <li><b>GET / POST</b> <code>/api/cron</code> - Triggers scheduled quiz dispatch and expired poll cleanup</li>
                    <li><b>GET</b> <code>/api/health</code> - Serverless health check & DB connectivity probe</li>
                    <li><b>POST</b> <code>/api/seed</code> - Seeds initial question bank into cloud PostgreSQL</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/api/health")
async def health():
    """Health check endpoint probing database connectivity and bot readiness."""
    db_ok = False
    error_msg = None
    try:
        await ensure_db()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Database health check failed: {e}")

    return {
        "status": "healthy" if db_ok else "unhealthy",
        "bot_configured": bool(settings.BOT_TOKEN),
        "database": {
            "connected": db_ok,
            "type": "postgresql" if "postgres" in settings.DATABASE_URL else "sqlite",
            "error": error_msg
        },
        "webhook_url": settings.WEBHOOK_URL or "not_set"
    }

@app.post("/api/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None)
):
    """
    Telegram Webhook Receiver:
    Processes updates forwarded by Telegram Bot API.
    """
    # Verify secret token if WEBHOOK_SECRET is configured
    if settings.WEBHOOK_SECRET:
        if x_telegram_bot_api_secret_token != settings.WEBHOOK_SECRET:
            logger.warning("Rejected webhook request: Invalid secret token")
            raise HTTPException(status_code=403, detail="Invalid secret token")

    bot = get_bot()
    dp = get_dispatcher()
    await ensure_db()

    try:
        payload = await request.json()
        update = Update.model_validate(payload, context={"bot": bot})
        await dp.feed_update(bot, update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error handling webhook update: {e}")
        # Always return HTTP 200 to Telegram so it doesn't repeatedly retry failing updates
        return {"ok": False, "error": str(e)}

@app.get("/api/set-webhook")
async def set_webhook(
    request: Request,
    url: Optional[str] = Query(None, description="Custom Webhook base URL (e.g., https://your-project.vercel.app)")
):
    """
    Registers the webhook URL with Telegram Bot API.
    Uses query ?url=... or environment WEBHOOK_URL or request base_url.
    """
    bot = get_bot()
    
    base = url or settings.WEBHOOK_URL or str(request.base_url).rstrip("/")
    if base.startswith("http://") and "localhost" not in base and "127.0.0.1" not in base:
        # Telegram Webhooks strictly require HTTPS in production
        base = base.replace("http://", "https://", 1)

    webhook_url = f"{base.rstrip('/')}/api/webhook"

    kwargs = {
        "url": webhook_url,
        "allowed_updates": ["message", "edited_message", "callback_query", "poll_answer", "my_chat_member"],
        "drop_pending_updates": False
    }
    if settings.WEBHOOK_SECRET:
        kwargs["secret_token"] = settings.WEBHOOK_SECRET

    logger.info(f"Registering Telegram webhook: {webhook_url}")
    result = await bot.set_webhook(**kwargs)

    return {
        "ok": result,
        "webhook_url": webhook_url,
        "secret_token_configured": bool(settings.WEBHOOK_SECRET),
        "message": "Webhook successfully registered with Telegram!"
    }

@app.get("/api/webhook-info")
async def webhook_info():
    """Inspects the current webhook status directly from Telegram."""
    bot = get_bot()
    info = await bot.get_webhook_info()
    return {
        "url": info.url,
        "has_custom_certificate": info.has_custom_certificate,
        "pending_update_count": info.pending_update_count,
        "last_error_date": info.last_error_date,
        "last_error_message": info.last_error_message,
        "max_connections": info.max_connections,
        "allowed_updates": info.allowed_updates
    }

@app.get("/api/delete-webhook")
async def delete_webhook():
    """Removes the registered webhook from Telegram (useful when switching back to polling)."""
    bot = get_bot()
    result = await bot.delete_webhook(drop_pending_updates=False)
    return {
        "ok": result,
        "message": "Webhook removed. You can now use local polling."
    }

def verify_cron_auth(request: Request, secret: Optional[str] = None):
    """Validates authorization for cron endpoint."""
    if not settings.CRON_SECRET:
        return True
    
    # Check Authorization header (Bearer token)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split("Bearer ")[1].strip()
        if token == settings.CRON_SECRET:
            return True

    # Check custom header x-cron-secret
    if request.headers.get("x-cron-secret") == settings.CRON_SECRET:
        return True

    # Check query param
    if secret == settings.CRON_SECRET:
        return True

    raise HTTPException(status_code=401, detail="Unauthorized: Invalid CRON_SECRET")

@app.get("/api/cron")
@app.post("/api/cron")
async def cron_trigger(
    request: Request,
    secret: Optional[str] = Query(None)
):
    """
    Serverless Cron Trigger:
    Periodically called by Vercel Cron or an external cron scheduler.
    Performs:
    1. Cleanup of expired polls.
    2. Scheduled quiz poll dispatch to active groups.
    """
    verify_cron_auth(request, secret)
    bot = get_bot()
    await ensure_db()
    result = await run_cron_cycle(bot)
    return result

@app.post("/api/seed")
async def seed_data(
    request: Request,
    count: int = Query(5000, description="Target question count to seed"),
    secret: Optional[str] = Query(None)
):
    """
    Database Seeder:
    Populates questions into cloud PostgreSQL if empty.
    Protected by CRON_SECRET or ADMIN_IDS.
    """
    if settings.CRON_SECRET:
        verify_cron_auth(request, secret)

    await seed_database(target_count=count)
    return {"ok": True, "message": f"Seeding completed with target count {count}."}
