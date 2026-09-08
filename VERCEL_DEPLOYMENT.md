# 🚀 Vercel Serverless Deployment Guide

This guide walks you through deploying **Albert Quiz Bot** to **Vercel** serverless hosting in under 5 minutes.

---

## 🏗️ Architecture Overview

* **Webhook Handling**: Handled via `/api/webhook` using a high-performance **FastAPI ASGI application** on Vercel Python runtime.
* **Database**: Managed **Cloud PostgreSQL** (e.g., [Neon](https://neon.tech), [Supabase](https://supabase.com), or Vercel Postgres).
* **Automated Quizzes**: Triggered via `/api/cron` by **Vercel Crons** or external cron monitors (e.g., cron-job.org).
* **Zero VPS Costs**: Runs completely within the free tiers of Vercel and Neon/Supabase.

---

## 📋 Step 1: Prerequisites

1. **Telegram Bot Token**: Get your bot token from [@BotFather](https://t.me/BotFather) on Telegram.
2. **Cloud PostgreSQL Database (Free)**:
   * Create a free database at [Neon.tech](https://neon.tech) or [Supabase](https://supabase.com).
   * Copy the connection string (format: `postgresql://user:password@host/dbname?sslmode=require`).
3. **Vercel Account**: Sign up at [vercel.com](https://vercel.com).

---

## 🚀 Step 2: Deploy to Vercel

### Option A: Deploy via GitHub (Recommended)

1. Push this repository to your GitHub account:
   ```bash
   git add .
   git commit -m "Configure Vercel serverless deployment"
   git push origin main
   ```
2. Go to your [Vercel Dashboard](https://vercel.com/dashboard) and click **"Add New..."** → **"Project"**.
3. Select your repository and click **Import**.
4. In the **Environment Variables** section, add:
   * `BOT_TOKEN`: Your bot token from @BotFather.
   * `DATABASE_URL`: Your cloud PostgreSQL connection string.
   * `WEBHOOK_URL`: `https://<your-project-name>.vercel.app` (you can update this after Vercel assigns your domain).
   * `WEBHOOK_SECRET`: *(Optional)* A random secret string to secure webhook calls.
   * `CRON_SECRET`: *(Optional)* A random secret string to protect the cron endpoint.
   * `ADMIN_IDS`: *(Optional)* Your Telegram user ID (from [@userinfobot](https://t.me/userinfobot)).
5. Click **Deploy**.

---

### Option B: Deploy via Vercel CLI

1. Install the Vercel CLI:
   ```bash
   npm install -g vercel
   ```
2. Run `vercel` in the project root:
   ```bash
   vercel
   ```
3. Follow the CLI prompts to link and deploy the project.
4. Set environment variables using:
   ```bash
   vercel env add BOT_TOKEN
   vercel env add DATABASE_URL
   vercel env add WEBHOOK_URL
   ```
5. Deploy to production:
   ```bash
   vercel --prod
   ```

---

## 🎯 Step 3: Register the Webhook (1 Click)

Once deployed, you can connect Telegram to your Vercel deployment with a single click:

1. Open your browser and visit:
   ```
   https://<your-project-name>.vercel.app/api/set-webhook
   ```
2. You will see a JSON response confirming:
   ```json
   {
     "ok": true,
     "webhook_url": "https://<your-project-name>.vercel.app/api/webhook",
     "message": "Webhook successfully registered with Telegram!"
   }
   ```
3. Check webhook status anytime:
   ```
   https://<your-project-name>.vercel.app/api/webhook-info
   ```

---

## 📚 Step 4: Seed Question Bank (Initial Setup)

To populate your cloud database with quiz questions:

### Method 1: Using the Web API
Send a `POST` request to `/api/seed`:
```bash
curl -X POST "https://<your-project-name>.vercel.app/api/seed?count=5000"
```
*(If `CRON_SECRET` is set, append `&secret=YOUR_CRON_SECRET`)*

### Method 2: Locally via CLI
Run the seeder directly against your cloud database:
```bash
# In your local .env, set DATABASE_URL to your cloud PostgreSQL URL
python tools/seed_questions.py
```

---

## ⏰ Step 5: Automated Quizzes & Cron Jobs

### Built-in Vercel Cron
`vercel.json` schedules `/api/cron` to run every 10 minutes:
```json
{
  "functions": {
    "api/index.py": {
      "maxDuration": 60
    }
  },
  "crons": [
    {
      "path": "/api/cron",
      "schedule": "*/10 * * * *"
    }
  ]
}
```

### Option A: Free 24/7 Delivery via GitHub Actions (Recommended for Vercel Hobby)
*Vercel Hobby plan limits native cron executions to once daily.* A pre-configured GitHub Actions workflow is included in `.github/workflows/quiz_cron.yml` that runs every 10 minutes for free:
1. In your GitHub repository, go to **Settings** → **Secrets and variables** → **Actions**.
2. Under **Variables** (or Secrets), add:
   - `VERCEL_APP_URL`: `https://<your-project-name>.vercel.app`
   - `CRON_SECRET`: *(Optional)* Your `CRON_SECRET` if configured in `.env`.
3. Go to the **Actions** tab in GitHub and ensure workflows are enabled. Quizzes will now dispatch automatically every 10 minutes around the clock!

### Option B: Free External Cron via cron-job.org
1. Create a free account at [cron-job.org](https://cron-job.org).
2. Create a new cron job pointing to:
   ```
   https://<your-project-name>.vercel.app/api/cron
   ```
3. Set the schedule to every 10, 15, or 30 minutes.
4. If `CRON_SECRET` is configured, add header `Authorization: Bearer <CRON_SECRET>` or append `?secret=<CRON_SECRET>`.

---

## 🧪 Step 6: Testing & Verification

1. Open Telegram and send `/start` to your bot.
2. Try commands:
   * `/random` - Receive an instant quiz poll.
   * `/leaderboard` - View daily, weekly, monthly, and all-time scores.
   * `/stats` - View global statistics.
   * `/categories` - Browse 13+ question categories.
3. Add the bot as an administrator in a Telegram group to enable automatic quiz posting.

---

## 🔄 Switching Back to Local Polling

If you want to run the bot locally on your computer with long-polling:
1. Visit `https://<your-project-name>.vercel.app/api/delete-webhook` to deactivate the webhook.
2. Run locally:
   ```bash
   python bot/main.py
   ```
