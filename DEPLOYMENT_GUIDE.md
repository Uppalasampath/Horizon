# Tech Job Scraper + Web App - Deployment Guide

## 🚀 Quick Deploy (5 Minutes)

### Prerequisites

- Python 3.10+
- pip
- Internet connection

### Step-by-Step Setup

#### 1. Install Dependencies

```bash
cd job_scraper
pip install -r requirements.txt
```

#### 2. Run Initial Scrape

```bash
# Scrape technical jobs from top tech companies
python -m job_scraper.scheduler --once

# Wait 2-5 minutes for completion
# Output: data/jobs/jobs_latest.jsonl
```

#### 3. Start Web Application

```bash
# Start the web server
python -m job_scraper.web_app

# Open browser: http://localhost:5000
```

✅ **Done!** You now have a running job board with apply buttons.

## 📅 Enable Automatic Scraping

### Option 1: Built-in Scheduler

```bash
# Run scheduler (scrapes every 6 hours)
python -m job_scraper.scheduler --schedule "0 */6 * * *"
```

Keep this running in a terminal or use screen/tmux.

### Option 2: System Cron (Linux/Mac)

```bash
# Edit crontab
crontab -e

# Add line (scrape every 6 hours):
0 */6 * * * cd /path/to/Horizon/job_scraper && /usr/bin/python3 -m job_scraper.scheduler --once

# Add line (start web app on boot):
@reboot cd /path/to/Horizon/job_scraper && /usr/bin/python3 -m job_scraper.web_app &
```

### Option 3: Systemd Service (Linux Production)

Create `/etc/systemd/system/job-scraper-scheduler.service`:

```ini
[Unit]
Description=Tech Job Scraper - Scheduler
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/Horizon/job_scraper
ExecStart=/usr/bin/python3 -m job_scraper.scheduler --schedule "0 */6 * * *"
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/job-scraper-web.service`:

```ini
[Unit]
Description=Tech Job Scraper - Web App
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/Horizon/job_scraper
ExecStart=/usr/bin/python3 -m job_scraper.web_app --host 0.0.0.0 --port 5000
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable job-scraper-scheduler job-scraper-web
sudo systemctl start job-scraper-scheduler job-scraper-web

# Check status
sudo systemctl status job-scraper-scheduler
sudo systemctl status job-scraper-web
```

## 🐳 Docker Deployment

### Create Dockerfile

Create `job_scraper/Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create data directory
RUN mkdir -p data/jobs

# Expose web port
EXPOSE 5000

# Start both scheduler and web app
CMD python -m job_scraper.scheduler --once && \
    (python -m job_scraper.scheduler --schedule "0 */6 * * *" &) && \
    python -m job_scraper.web_app --host 0.0.0.0 --port 5000
```

### Create docker-compose.yml

```yaml
version: '3.8'

services:
  job-scraper:
    build: ./job_scraper
    ports:
      - "5000:5000"
    volumes:
      - ./data:/app/data
    environment:
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/api/stats"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Run with Docker Compose

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## ☁️ Cloud Deployment

### Deploy to Heroku

1. Create `Procfile`:

```
web: python -m job_scraper.web_app --host 0.0.0.0 --port $PORT
worker: python -m job_scraper.scheduler --schedule "0 */6 * * *"
```

2. Create `runtime.txt`:

```
python-3.10.13
```

3. Deploy:

```bash
heroku create your-job-scraper
git push heroku main
heroku ps:scale web=1 worker=1
```

### Deploy to AWS EC2

```bash
# 1. Launch EC2 instance (Ubuntu 22.04)

# 2. SSH into instance
ssh ubuntu@your-instance-ip

# 3. Install dependencies
sudo apt update
sudo apt install python3.10 python3-pip git

# 4. Clone repository
git clone https://github.com/yourrepo/Horizon.git
cd Horizon/job_scraper

# 5. Install Python packages
pip3 install -r requirements.txt

# 6. Set up systemd services (see above)

# 7. Configure firewall
sudo ufw allow 5000
sudo ufw enable

# 8. Optional: Set up nginx reverse proxy
sudo apt install nginx
# Configure nginx to proxy to localhost:5000
```

### Deploy to Google Cloud Run

1. Create `cloudbuild.yaml`:

```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/job-scraper', './job_scraper']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/job-scraper']
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'job-scraper'
      - '--image'
      - 'gcr.io/$PROJECT_ID/job-scraper'
      - '--platform'
      - 'managed'
      - '--region'
      - 'us-central1'
```

2. Deploy:

```bash
gcloud builds submit --config cloudbuild.yaml
```

## 🔒 Production Security

### 1. Environment Variables

Create `.env` file:

```bash
FLASK_SECRET_KEY=your-secret-key-here
FLASK_ENV=production
JOBS_DIR=/path/to/jobs
```

Load in app:

```python
from dotenv import load_dotenv
load_dotenv()
```

### 2. Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. SSL/HTTPS (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### 4. Rate Limiting

Add to web_app.py:

```python
from flask_limiter import Limiter

limiter = Limiter(
    app,
    key_func=lambda: request.remote_addr,
    default_limits=["100 per hour"]
)

@app.route("/api/jobs")
@limiter.limit("30 per minute")
def get_jobs():
    # ...
```

## 📊 Monitoring & Analytics

### Add Google Analytics

In `web_app.py` template:

```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'GA_ID');
</script>
```

### Application Monitoring

```bash
# Install sentry for error tracking
pip install sentry-sdk[flask]
```

Add to `web_app.py`:

```python
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    dsn="your-sentry-dsn",
    integrations=[FlaskIntegration()],
)
```

## 🎨 Customization

### Change Companies

Edit `job_scraper/companies.py`:

```python
TECH_COMPANIES = [
    {
        "name": "YourCompany",
        "url": "https://yourcompany.com/careers",
        "ats": "greenhouse",
    },
    # Add more...
]
```

### Customize UI

Edit HTML template in `web_app.py`:

```python
# Change colors
.header {
    background: linear-gradient(135deg, #your-color 0%, #your-color2 100%);
}

# Change title
<h1>🚀 Your Job Board</h1>
```

### Add Features

```python
# Add job alerts
@app.route("/api/subscribe", methods=["POST"])
def subscribe():
    email = request.json.get("email")
    # Send email with new jobs
    pass

# Add bookmarking
@app.route("/api/bookmark", methods=["POST"])
def bookmark():
    job_id = request.json.get("job_id")
    # Save to user's bookmarks
    pass
```

## 🔧 Maintenance

### Update Job Data

```bash
# Manual refresh
python -m job_scraper.scheduler --once

# Check latest data
ls -lh data/jobs/
```

### Clean Old Data

```bash
# Keep only last 30 days
find data/jobs/ -name "jobs_*.jsonl" -mtime +30 -delete
```

### Backup Data

```bash
# Daily backup script
tar -czf backups/jobs-$(date +%Y%m%d).tar.gz data/jobs/

# Upload to S3
aws s3 cp backups/jobs-$(date +%Y%m%d).tar.gz s3://your-bucket/
```

## 📱 Mobile App (Optional)

The API can power a mobile app:

```swift
// iOS Example
func fetchJobs() {
    let url = URL(string: "https://yourserver.com/api/jobs?level=entry")!
    URLSession.shared.dataTask(with: url) { data, response, error in
        // Parse and display jobs
    }.resume()
}
```

```kotlin
// Android Example
val retrofit = Retrofit.Builder()
    .baseUrl("https://yourserver.com/")
    .build()

val jobs = retrofit.create(JobsAPI::class.java).getJobs("entry")
```

## 🎯 Performance Optimization

### 1. Cache Jobs in Memory

```python
from functools import lru_cache
from datetime import datetime, timedelta

@lru_cache(maxsize=1)
def load_jobs_cached():
    return load_jobs()

# Expire cache every 5 minutes
```

### 2. Database Storage (Optional)

```python
# Use SQLite for faster queries
import sqlite3

def store_jobs_in_db(jobs):
    conn = sqlite3.connect('jobs.db')
    c = conn.cursor()
    # Insert jobs...
    conn.commit()
```

### 3. CDN for Static Assets

Use Cloudflare or similar for faster asset delivery.

## ✅ Deployment Checklist

- [ ] Install all dependencies
- [ ] Run initial scrape successfully
- [ ] Test web app locally
- [ ] Set up scheduled scraping
- [ ] Configure production server
- [ ] Set up SSL/HTTPS
- [ ] Configure monitoring
- [ ] Set up backups
- [ ] Test apply buttons work
- [ ] Add analytics (optional)
- [ ] Set up alerting
- [ ] Document custom config
- [ ] Test mobile responsiveness
- [ ] Load testing
- [ ] Security audit

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Find process using port 5000
lsof -i :5000

# Kill process
kill -9 <PID>

# Or use different port
python -m job_scraper.web_app --port 8080
```

### Permission Errors

```bash
# Fix data directory permissions
chmod -R 755 data/
chown -R $USER:$USER data/
```

### Memory Issues

```bash
# Limit concurrent scraping
python -m job_scraper.scheduler --once --concurrency 2

# Or add swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## 📞 Support

For issues:
1. Check logs
2. Verify internet connection
3. Test with `--verbose` flag
4. Review this guide
5. Check GitHub issues

Happy deploying! 🚀
