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

### Vercel Hobby Plan Cron Configuration
On the free Vercel Hobby plan, native cron jobs are restricted to at most **once daily**. In `vercel.json`, we configure a daily maintenance trigger at midnight UTC (`0 0 * * *`):
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
      "schedule": "0 0 * * *"
    }
  ]
}
```

### Setting Up Continuous 10-Minute Quiz Delivery

To deliver quizzes automatically every 10 minutes to your Telegram groups, use either of the two methods below:

#### Option A: Free Dedicated Cron via cron-job.org (⭐ Most Reliable)
Because GitHub Actions can delay scheduled workflows during peak hours, **cron-job.org** is the recommended free service to ping your bot every 10 minutes with second-level precision:
1. Create a free account at [cron-job.org](https://cron-job.org).
2. Click **Create Cronjob**.
3. Set the **URL**: `https://albertquizbot.vercel.app/api/cron` (or your custom domain).
4. Set the **Execution schedule**: User-defined → **Every 10 minutes**.
5. Request method: `POST` (or `GET`).
6. *(Optional)* If you set a `CRON_SECRET`, add header `Authorization: Bearer <YOUR_SECRET>` or append `?secret=<YOUR_SECRET>`.
7. Click **Create**. Quizzes will now dispatch reliably every 10 minutes, 24/7!

#### Option B: Automated Delivery via GitHub Actions
A pre-configured GitHub Actions workflow is included in `.github/workflows/quiz_cron.yml`:
1. In your GitHub repository, navigate to the **Actions** tab.
2. Enable workflows if prompted.
3. The workflow runs on a schedule and can also be triggered manually anytime by selecting **Automated Quiz Delivery Cron** → **Run workflow**.

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
