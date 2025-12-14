# Scheduled Scraper & Web App Guide

## 🎯 Overview

This system automatically scrapes technical job postings from 40+ top tech companies and displays them in a beautiful web interface.

### Features

✅ **Automated Scraping**: Scheduled scraping of top tech companies
✅ **Technical Roles Only**: Filters out non-technical positions
✅ **Web Interface**: Beautiful UI with search, filters, and apply buttons
✅ **Real-time Stats**: Job counts, company stats, experience levels
✅ **Auto-refresh**: Jobs update automatically on schedule

## 🏢 Supported Companies

**FAANG/Big Tech**: Google, Meta, Amazon, Apple, Netflix, Microsoft
**Cloud & Infrastructure**: Salesforce, Oracle, Adobe, Nvidia
**Unicorns**: Stripe, Databricks, Snowflake, Airbnb, Uber, Lyft, DoorDash
**AI/ML**: OpenAI, Anthropic, DeepMind, Scale AI
**FinTech**: Coinbase, Plaid, Square, Robinhood
**Developer Tools**: GitHub, GitLab, Atlassian, Vercel

...and 20+ more! See `companies.py` for full list.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd job_scraper
pip install -r requirements.txt
```

### 2. Run One-Time Scrape

```bash
# Scrape all companies once (technical roles only)
python -m job_scraper.scheduler --once

# Output: data/jobs/jobs_latest.jsonl
```

### 3. Start Web Interface

```bash
# Start web server
python -m job_scraper.web_app

# Open browser to: http://localhost:5000
```

## 📅 Scheduled Scraping

### Run on Schedule

```bash
# Every 6 hours (default)
python -m job_scraper.scheduler --schedule "0 */6 * * *"

# Daily at midnight
python -m job_scraper.scheduler --schedule "0 0 * * *"

# Twice daily (9am and 5pm)
python -m job_scraper.scheduler --schedule "0 9,17 * * *"

# Weekdays at 9am
python -m job_scraper.scheduler --schedule "0 9 * * 1-5"
```

### Cron Schedule Format

```
"minute hour day month day_of_week"

Examples:
  "0 */6 * * *"  - Every 6 hours
  "0 0 * * *"    - Daily at midnight
  "0 9 * * 1-5"  - Weekdays at 9am
  "*/30 * * * *" - Every 30 minutes
```

## 🌐 Web Application

### Starting the Server

```bash
# Development
python -m job_scraper.web_app --debug

# Production
python -m job_scraper.web_app --host 0.0.0.0 --port 5000
```

### Features

**Search & Filter**:
- Search by job title, company, or keywords
- Filter by experience level (entry/mid/senior)
- Filter by company
- Real-time filtering

**Job Cards**:
- Title, company, location
- Experience level badge
- Technical skills tags
- Job description preview
- **Apply button** → Opens original job posting

**Statistics Dashboard**:
- Total jobs
- Entry-level count
- Mid-level count
- Number of companies

**Auto-Refresh**:
- Jobs refresh every 5 minutes
- Always shows latest data

## 📊 Data Management

### Output Files

```
data/jobs/
├── jobs_latest.jsonl          # Latest scrape (used by web app)
├── jobs_20231214_093000.jsonl # Timestamped archives
├── jobs_20231214_150000.jsonl
└── scraper_stats.json         # Scraping statistics
```

### Job Data Format

```json
{
  "id": "greenhouse_12345",
  "source": "greenhouse",
  "title": "Junior Backend Engineer",
  "company": "Stripe",
  "location": "San Francisco, CA",
  "posted_date": "2025-12-14T00:00:00Z",
  "description": "...",
  "skills": ["Python", "Django", "PostgreSQL"],
  "experience_level": "entry",
  "apply_url": "https://stripe.com/jobs/listing/12345"
}
```

## ⚙️ Configuration

### Technical Role Filtering

Edit `job_scraper/companies.py`:

```python
TECHNICAL_KEYWORDS = [
    "software engineer",
    "backend engineer",
    "frontend engineer",
    "ml engineer",
    # Add more...
]

EXCLUDE_KEYWORDS = [
    "sales",
    "marketing",
    # Add more...
]
```

### Company List

Add companies to `TECH_COMPANIES` in `companies.py`:

```python
{
    "name": "YourCompany",
    "url": "https://yourcompany.com/careers",
    "ats": "greenhouse",  # or lever, workday, generic, etc.
}
```

### Scraper Settings

```python
# In scheduler.py or when running
scraper = ScheduledScraper(
    output_dir="data/jobs",      # Output directory
    concurrency=4,                # Concurrent requests
    technical_only=True,          # Filter technical roles
)
```

## 🔧 Advanced Usage

### Include Non-Technical Roles

```bash
python -m job_scraper.scheduler --once --all-roles
```

### Custom Output Directory

```bash
python -m job_scraper.scheduler --once --output-dir /path/to/jobs
```

### Higher Concurrency

```bash
python -m job_scraper.scheduler --once --concurrency 8
```

### Verbose Logging

```bash
python -m job_scraper.scheduler --once --verbose
```

## 📱 API Endpoints

The web app provides REST APIs:

### GET /api/jobs

Get filtered jobs:

```bash
curl "http://localhost:5000/api/jobs?search=python&level=entry&limit=10"
```

Parameters:
- `search`: Search term
- `source`: Filter by ATS source
- `level`: Experience level (entry/mid/senior)
- `company`: Filter by company
- `limit`: Results per page (default: 100)
- `offset`: Pagination offset

Response:
```json
{
  "jobs": [...],
  "total": 250,
  "offset": 0,
  "limit": 100
}
```

### GET /api/stats

Get statistics:

```bash
curl "http://localhost:5000/api/stats"
```

Response:
```json
{
  "total": 500,
  "by_source": {"greenhouse": 200, "lever": 150, ...},
  "by_level": {"entry": 180, "mid": 200, "senior": 120},
  "by_company": {"Google": 25, "Meta": 20, ...}
}
```

### GET /api/companies

Get company list:

```bash
curl "http://localhost:5000/api/companies"
```

## 🐳 Docker Deployment (Optional)

### Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run scheduler in background and web app in foreground
CMD python -m job_scraper.scheduler --schedule "0 */6 * * *" & \
    python -m job_scraper.web_app --host 0.0.0.0 --port 5000
```

### Docker Compose

```yaml
version: '3.8'

services:
  job-scraper:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./data:/app/data
    environment:
      - FLASK_ENV=production
    restart: unless-stopped
```

## 🔄 Systemd Service (Linux)

Create `/etc/systemd/system/job-scraper.service`:

```ini
[Unit]
Description=Tech Job Scraper
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/job_scraper
ExecStart=/usr/bin/python3 -m job_scraper.scheduler --schedule "0 */6 * * *"
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable job-scraper
sudo systemctl start job-scraper
sudo systemctl status job-scraper
```

## 📈 Monitoring

### Check Scraper Stats

```bash
cat data/jobs/scraper_stats.json
```

```json
{
  "total_runs": 10,
  "total_jobs": 5000,
  "total_technical": 4500,
  "last_run": "2025-12-14T09:30:00"
}
```

### View Logs

```bash
# If using systemd
sudo journalctl -u job-scraper -f

# If running manually
tail -f scraper.log
```

## 🎨 Customizing the Web UI

Edit the HTML template in `web_app.py`:

- Change colors in the `<style>` section
- Modify layout in the `<body>` section
- Add custom JavaScript features
- Integrate with your own backend

## 🤝 Integration with Job Ranker

### Pipeline: Scraper → Ranker → Web UI

```bash
# 1. Scrape jobs
python -m job_scraper.scheduler --once

# 2. Rank jobs for a candidate
python -m job_ranker.main \
  --profile profile.txt \
  --jobs data/jobs/jobs_latest.jsonl \
  --topk 50 \
  --output ranked_jobs.json

# 3. Display ranked jobs in custom UI
# (Parse ranked_jobs.json and display with apply buttons)
```

## 🐛 Troubleshooting

### No Jobs Found

1. Check internet connection
2. Verify company URLs are accessible
3. Run with `--verbose` flag
4. Check `data/jobs/scraper_stats.json`

### Web App Not Loading Jobs

1. Ensure scraper has run at least once
2. Check `data/jobs/jobs_latest.jsonl` exists
3. Verify file permissions
4. Check browser console for errors

### Scheduler Not Running

1. Verify cron syntax
2. Check system time
3. Run `--once` first to test
4. Review logs for errors

## 📝 Best Practices

1. **Schedule wisely**: Don't scrape too frequently (respect rate limits)
2. **Monitor robots.txt**: System automatically checks, but be aware
3. **Review filters**: Ensure technical role filters are accurate
4. **Archive old data**: Keep timestamped files for history
5. **Use version control**: Track changes to company lists

## 🎯 Production Checklist

- [ ] Install all dependencies
- [ ] Configure company list
- [ ] Test scraper with `--once`
- [ ] Verify web app works
- [ ] Set up scheduled scraping
- [ ] Configure monitoring/logging
- [ ] Set up backups for data directory
- [ ] Document custom configurations
- [ ] Test apply buttons work correctly
- [ ] Set up SSL for production (if public)

## 📚 Additional Resources

- Main scraper README: `../README.md`
- Job ranker README: `../../job_ranker/README.md`
- Company database: `companies.py`
- Scheduler code: `scheduler.py`
- Web app code: `web_app.py`

## 💡 Tips

- **Start small**: Test with a few companies first
- **Monitor costs**: If deploying to cloud, watch bandwidth
- **Cache aggressively**: Reduce redundant scraping
- **User feedback**: Add analytics to understand usage
- **Mobile-friendly**: Web UI is responsive by default

Happy job hunting! 🚀
