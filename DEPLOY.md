# Free Deployment Options

## Option 1: Render.com (Recommended)

**Free tier:** 750 hours/month, auto-sleeps after 15 min inactivity

### Steps:
1. Go to [render.com](https://render.com) and sign up (GitHub login works)
2. Click **New** → **Web Service**
3. Connect your GitHub repo: `Syzygyastro/kafka`
4. Settings will auto-detect from `render.yaml`, or set manually:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Click **Create Web Service**
6. Wait ~5 min for build
7. Your URL: `https://web-scraper-bot-xxxx.onrender.com`

### Test it:
```bash
curl https://YOUR-URL.onrender.com/api/v1/health
curl -X POST https://YOUR-URL.onrender.com/api/v1/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://books.toscrape.com/", "strategy": "simple"}'
```

---

## Option 2: Railway.app

**Free tier:** $5 credit/month (plenty for testing)

### Steps:
1. Go to [railway.app](https://railway.app) and sign up
2. Click **New Project** → **Deploy from GitHub repo**
3. Select `Syzygyastro/kafka`
4. Railway auto-detects Python and uses `railway.json`
5. Click **Deploy**
6. Go to **Settings** → **Generate Domain**
7. Your URL: `https://kafka-xxxx.up.railway.app`

---

## Option 3: Fly.io

**Free tier:** 3 shared VMs, 160GB outbound

### Steps:
```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Deploy from repo directory
fly launch --name web-scraper-bot

# Deploy
fly deploy
```

Your URL: `https://web-scraper-bot.fly.dev`

---

## Option 4: Hugging Face Spaces (Docker)

**Free tier:** Unlimited, but limited CPU

### Steps:
1. Go to [huggingface.co/spaces](https://huggingface.co/spaces)
2. Click **Create new Space**
3. Select **Docker** as SDK
4. Upload or connect your repo
5. It uses the existing `Dockerfile`

---

## API Endpoints to Test

Once deployed, test these endpoints:

```bash
# Health check
GET /api/v1/health

# Scrape a page (simple strategy)
POST /api/v1/scrape
{
  "url": "https://books.toscrape.com/",
  "strategy": "simple"
}

# Scrape with selectors
POST /api/v1/scrape
{
  "url": "https://quotes.toscrape.com/",
  "strategy": "simple",
  "selectors": {
    "quotes": ".quote .text",
    "authors": ".quote .author"
  }
}

# Get stats
GET /api/v1/stats

# Interactive docs
GET /docs
```

---

## Environment Variables (Optional)

Set these in your hosting dashboard:

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `PROXY_ENABLED` | Enable proxy rotation | `false` |
| `PROXY_LIST` | Comma-separated proxies | - |
| `CAPTCHA_SOLVER_ENABLED` | Enable captcha solving | `false` |
| `TWOCAPTCHA_API_KEY` | 2Captcha API key | - |

---

## Notes

- **Headless browser** requires more memory. Free tiers may struggle with `headless` and `stealth` strategies.
- **Simple strategy** works great on free tiers for most scraping needs.
- First request after sleep may take 10-30 seconds (cold start).
