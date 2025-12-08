# Job Scraper

Fast, modular job scraper for extracting entry-level tech job postings from multiple ATS providers (Greenhouse, Lever, Workday) and generic HTML pages.

## Features

- **Multi-ATS Support**: Greenhouse, Lever, Workday, and generic HTML fallback
- **Async Scraping**: Fast concurrent fetching with configurable concurrency
- **robots.txt Compliance**: Automatic checking and respect for robots.txt
- **Rate Limiting**: Exponential backoff and per-domain throttling
- **Normalized Output**: Structured JSONL format with consistent schema
- **Skill Extraction**: Automatic detection of technical skills
- **Experience Level Detection**: Identifies entry/mid/senior positions
- **Type-Safe**: Pydantic models with validation

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

### Using Fixtures (for testing)

```bash
# Generate sample jobs using built-in fixtures
python -m job_scraper.main --use-fixtures --out jobs.jsonl
```

### Live Scraping

```bash
# Scrape using generic scraper (works with any job board)
python -m job_scraper.main \
  --sources generic \
  --urls "https://company.com/careers,https://another-company.com/jobs" \
  --out jobs.jsonl \
  --concurrency 8 \
  --max-pages 3
```

### Specific ATS Sources

```bash
# Scrape from specific ATS providers
python -m job_scraper.main \
  --sources greenhouse,lever \
  --urls "https://boards.greenhouse.io/company,https://jobs.lever.co/company" \
  --out jobs.jsonl
```

## CLI Options

- `--sources`: Comma-separated list of scrapers: `greenhouse`, `lever`, `workday`, `generic` (default: `generic`)
- `--urls`: Comma-separated list of URLs to scrape (required unless using `--use-fixtures`)
- `--out`: Output file path (default: `jobs.jsonl`)
- `--concurrency`: Max concurrent requests (default: 8)
- `--max-pages`: Max pages per source (default: 3)
- `--use-fixtures`: Use sample fixture data for testing
- `--verbose`, `-v`: Verbose logging

## Output Format

Jobs are written as newline-delimited JSON (JSONL) with the following schema:

```json
{
  "id": "greenhouse_12345",
  "source": "greenhouse",
  "title": "Junior Backend Engineer",
  "company": "TechCorp",
  "location": "San Francisco, CA",
  "posted_date": "2025-12-01T00:00:00Z",
  "description": "Full job description text...",
  "skills": ["Python", "Django", "PostgreSQL", "Docker"],
  "experience_level": "entry",
  "apply_url": "https://boards.greenhouse.io/techcorp/jobs/12345",
  "raw": {}
}
```

## JobPosting Fields

- **id**: Unique identifier (source + job ID)
- **source**: ATS provider (`greenhouse`, `lever`, `workday`, `generic`)
- **title**: Job title
- **company**: Company name
- **location**: Job location
- **posted_date**: ISO 8601 date string (nullable)
- **description**: Full job description (plain text)
- **skills**: List of detected technical skills
- **experience_level**: `entry`, `mid`, `senior`, or `unknown`
- **apply_url**: Application URL
- **raw**: Original metadata from source

## Module Usage

```python
import asyncio
from job_scraper import JobScraperCore

async def scrape_jobs():
    scraper = JobScraperCore(
        sources=["generic"],
        concurrency=8,
        max_pages=3
    )

    urls = ["https://company.com/careers"]
    jobs = await scraper.scrape_urls(urls)

    for job in jobs:
        print(f"{job.title} at {job.company}")

asyncio.run(scrape_jobs())
```

## Testing

Run unit tests with pytest:

```bash
pytest job_scraper/tests/test_scraper.py -v
```

Tests use HTML fixtures and don't require internet access.

## Architecture

```
job_scraper/
├── main.py              # CLI entrypoint
├── core.py              # Async orchestration, rate limiting, robots.txt
├── schema.py            # Pydantic models and validation
├── utils.py             # HTML parsing, skill extraction
├── sources/             # Per-ATS scrapers
│   ├── greenhouse.py    # Greenhouse scraper
│   ├── lever.py         # Lever scraper
│   ├── workday.py       # Workday scraper
│   └── generic.py       # Generic HTML scraper
├── tests/               # Unit tests
└── fixtures/            # Sample data
```

## Extending

### Add a New ATS Scraper

1. Create a new scraper in `sources/`:

```python
class MyATSScraper:
    def __init__(self):
        self.source = "myats"

    def can_handle(self, url: str) -> bool:
        return "myats.com" in url

    def extract_jobs_from_html(self, html: str, base_url: str) -> List[JobPosting]:
        # Parse HTML and return JobPosting objects
        pass
```

2. Register in `sources/__init__.py`
3. Add to `core.py` scrapers dict

## robots.txt Compliance

The scraper automatically:
- Fetches and parses `robots.txt` for each domain
- Checks if URLs are allowed before fetching
- Logs warnings for blocked URLs
- Allows by default if `robots.txt` is unavailable

## Rate Limiting

- Default: 0.5 seconds between requests per domain
- Exponential backoff on rate limit errors (429)
- Configurable concurrency limit
- Per-domain request tracking

## Performance

- Async I/O with aiohttp for concurrent fetching
- Typical speed: 30-60 pages/minute (depending on sites)
- Connection pooling and request reuse
- Configurable concurrency (default: 8)

## Notes

- **Entry-level focus**: Designed to identify entry-level positions through keyword detection
- **Generic fallback**: Works with arbitrary job boards using common HTML patterns
- **No API keys required**: Pure web scraping approach
- **Offline testing**: Use `--use-fixtures` for development without network

## Common Issues

**No jobs found?**
- Check that URLs point to job listing pages
- Try using `--sources generic` for unknown ATS providers
- Enable verbose mode with `-v` to see parsing details

**Blocked by robots.txt?**
- The scraper respects robots.txt by design
- Check the site's robots.txt manually
- Some sites require authentication or don't allow scraping

**Rate limited?**
- Reduce `--concurrency` (try 2-4)
- The scraper has built-in exponential backoff

## Example Workflow

```bash
# 1. Scrape jobs using fixtures
python -m job_scraper.main --use-fixtures --out jobs.jsonl

# 2. Inspect output
head -n 1 jobs.jsonl | python -m json.tool

# 3. Count jobs by level
grep -o '"experience_level":"[^"]*"' jobs.jsonl | sort | uniq -c

# 4. Filter entry-level jobs
grep '"experience_level":"entry"' jobs.jsonl > entry_level_jobs.jsonl
```

## License

MIT License - See LICENSE file for details.
