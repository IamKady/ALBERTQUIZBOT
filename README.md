# 🤖 Production-Ready Telegram Quiz Bot (Aiogram 3.x)

An automated, high-performance Telegram Quiz Bot powered by **Python (Aiogram 3.x)**, **SQLAlchemy 2.0 (SQLite / PostgreSQL)**, and **APScheduler**.

The bot automatically sends randomized, non-repeating quiz polls to Telegram Groups, Supergroups, and Channels where it is added as an administrator.

---

## 🌟 Key Features

* **🤖 Automated 24x7 Random Quiz Posting**: Detects group promotion automatically and schedules quiz questions continuously at randomized intervals (15m, 25m, 40m, 1h, 2h).
* **🎯 Native Telegram Quiz Polls**: Uses native Telegram Poll API (`type='quiz'`) with 4 choices, 1 correct answer, and detailed explanations.
* **⏳ 10-Minute Active Lifetime**: Automatically closes and deletes quiz polls after 10 minutes (configurable).
* **🔄 Exhaustive Non-Repeating Engine**: Questions never repeat per chat until the entire database pool is exhausted. Once exhausted, the cycle automatically resets and shuffles.
* **📚 50,000+ Question Dataset**: Pre-seeded across 13+ categories (General Knowledge, Science, History, Geography, English, Math, Computer, Tech, Sports, Logic, Current Affairs, Funny, Mixed).
* **🏆 Full Leaderboard & Scoring**:
  * Correct Answer: `+5` points
  * Fastest Answer Bonus: `+2` bonus points
  * Real-time Daily, Weekly, Monthly, and All-time rankings.
* **🛡️ Rate-Limiting & Anti-Spam**: Protection against accidental flooding and Telegram API rate-limit retries.
* **🌐 Multi-Language Support**: i18n support for English, Hindi, Spanish, French, German, and Arabic.
* **⚙️ Interactive Admin Panel**: Inline menu to pause/resume quizzes, set minimum/maximum intervals, adjust quiz durations, toggle mixed category mode, broadcast announcements, backup/restore database.
* **🐳 Production Deployment**: Docker & docker-compose support with PostgreSQL.

---

## 📂 Project Structure

```
ALBERTQUIZBOT/
├── bot/
│   ├── config/             # Settings & environment validation
│   ├── database/           # SQLAlchemy 2.0 Async engine & CRUD
│   ├── models/             # Database schemas (Question, Chat, User, Score, Poll)
│   ├── handlers/           # Telegram handlers (Start, User, Admin, Group, PollAnswer)
│   ├── middlewares/        # Middlewares (DB Session, i18n, Rate Limit)
│   ├── poll_manager/       # Question Selector & Poll Sending Engine
│   ├── scheduler/          # APScheduler 24x7 Async interval task scheduler
│   ├── leaderboard/        # Ranking & score aggregation service
│   ├── utils/              # Backup, export, import, logger utilities
│   ├── languages/          # JSON translation packs (en, hi, es, fr, de, ar)
│   └── main.py             # Bot entry point
├── tools/
│   └── seed_questions.py   # 50,000+ Question synthesis & seeder engine
├── tests/                  # Pytest async unit test suite
├── Dockerfile              # Docker build file
├── docker-compose.yml      # PostgreSQL + Bot compose stack
├── requirements.txt        # Dependencies
└── .env                    # Environment variables
```

---

## 🚀 Quick Setup & Installation

### 1. Clone & Install Dependencies

```bash
# Install Python 3.11+
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment (`.env`)

```env
BOT_TOKEN=8253804964:AAHx5r1-08xVGAzKgV1PMIjntwnme_Gqd4I
DATABASE_URL=sqlite+aiosqlite:///./quizbot.db
ADMIN_IDS=12345678
LOG_LEVEL=INFO
```

### 3. Seed Database (50,000+ Questions)

```bash
python tools/seed_questions.py
```

### 4. Run the Bot

```bash
python bot/main.py
```

---

## 🐳 Docker Production Deployment

To run with **PostgreSQL** in Docker:

```bash
docker-compose up -d --build
```

---

## 📜 Available Commands

### User Commands
* `/start` - Welcome message & quick guide
* `/help` - Help menu
* `/stats` - Global bot statistics
* `/categories` - Browse 13+ quiz categories & counts
* `/leaderboard` - Interactive daily/weekly/monthly/all-time leaderboards
* `/myscore` - Personal score, rank & accuracy
* `/random` - Request an instant quiz poll

### Admin Commands
* `/admin` - Open interactive Admin Control Dashboard
* `/broadcast <message>` - Broadcast announcement to all active groups

---

## 🧪 Running Unit Tests

```bash
pytest -v
```
