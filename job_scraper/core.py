"""
Core scraping orchestration - async fetching, robots.txt, rate limiting, caching.
"""
import asyncio
import logging
import time
from typing import List, Dict, Optional, Set
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import aiohttp
from .schema import JobPosting
from .sources import GreenhouseScraper, LeverScraper, WorkdayScraper, GenericScraper
from .detector import detect_ats, get_scraper_class

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter with exponential backoff."""

    def __init__(self, rate: float = 0.5):
        """
        Initialize rate limiter.

        Args:
            rate: Minimum seconds between requests (default 0.5)
        """
        self.rate = rate
        self.last_request: Dict[str, float] = {}

    async def wait(self, domain: str):
        """
        Wait if necessary to respect rate limit for domain.

        Args:
            domain: Domain name
        """
        if domain in self.last_request:
            elapsed = time.time() - self.last_request[domain]
            if elapsed < self.rate:
                await asyncio.sleep(self.rate - elapsed)

        self.last_request[domain] = time.time()


class RobotsChecker:
    """Check and cache robots.txt rules."""

    def __init__(self):
        """Initialize robots checker."""
        self.parsers: Dict[str, RobotFileParser] = {}
        self.fetch_errors: Set[str] = set()

    async def can_fetch(
        self, url: str, user_agent: str = "*", session: Optional[aiohttp.ClientSession] = None
    ) -> bool:
        """
        Check if URL can be fetched according to robots.txt.

        Args:
            url: URL to check
            user_agent: User agent string
            session: aiohttp session (optional)

        Returns:
            True if fetching is allowed
        """
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        robots_url = f"{base_url}/robots.txt"

        # If we already had an error fetching robots.txt, allow by default
        if base_url in self.fetch_errors:
            return True

        # Check cache
        if base_url not in self.parsers:
            parser = RobotFileParser()
            parser.set_url(robots_url)

            try:
                if session:
                    # Fetch with aiohttp
                    async with session.get(robots_url, timeout=5) as resp:
                        if resp.status == 200:
                            content = await resp.text()
                            parser.parse(content.splitlines())
                        else:
                            # No robots.txt or error - allow by default
                            logger.info(f"No robots.txt at {base_url}, allowing by default")
                            self.fetch_errors.add(base_url)
                            return True
                else:
                    # Synchronous fallback
                    parser.read()

                self.parsers[base_url] = parser

            except Exception as e:
                logger.warning(f"Error fetching robots.txt for {base_url}: {e}")
                self.fetch_errors.add(base_url)
                return True  # Allow by default on error

        parser = self.parsers.get(base_url)
        if parser:
            return parser.can_fetch(user_agent, url)

        return True


class JobScraperCore:
    """Core job scraper with async fetching and rate limiting."""

    def __init__(
        self,
        sources: Optional[List[str]] = None,
        concurrency: int = 8,
        max_pages: int = 3,
        user_agent: str = "JobScraperBot/1.0 (+https://github.com/jobscraper)",
    ):
        """
        Initialize job scraper.

        Args:
            sources: List of source names to use (default: all)
            concurrency: Max concurrent requests (default: 8)
            max_pages: Max pages to scrape per source (default: 3)
            user_agent: User agent string
        """
        self.sources = sources or ["greenhouse", "lever", "workday", "generic"]
        self.concurrency = concurrency
        self.max_pages = max_pages
        self.user_agent = user_agent

        # Initialize scrapers
        self.scrapers = {
            "greenhouse": GreenhouseScraper(),
            "lever": LeverScraper(),
            "workday": WorkdayScraper(),
            "generic": GenericScraper(),
        }

        # Rate limiting and robots.txt
        self.rate_limiter = RateLimiter(rate=0.5)
        self.robots_checker = RobotsChecker()

        # Stats
        self.stats = {
            "fetched": 0,
            "success": 0,
            "errors": 0,
            "robots_blocked": 0,
        }

    async def fetch_with_retry(
        self,
        session: aiohttp.ClientSession,
        url: str,
        max_retries: int = 3,
    ) -> Optional[str]:
        """
        Fetch URL with exponential backoff retry.

        Args:
            session: aiohttp ClientSession
            url: URL to fetch
            max_retries: Maximum retry attempts

        Returns:
            HTML content or None
        """
        domain = urlparse(url).netloc

        for attempt in range(max_retries):
            try:
                # Check robots.txt
                if not await self.robots_checker.can_fetch(url, self.user_agent, session):
                    logger.warning(f"Blocked by robots.txt: {url}")
                    self.stats["robots_blocked"] += 1
                    return None

                # Rate limit
                await self.rate_limiter.wait(domain)

                # Fetch
                headers = {"User-Agent": self.user_agent}
                async with session.get(url, headers=headers, timeout=15) as response:
                    self.stats["fetched"] += 1

                    if response.status == 200:
                        self.stats["success"] += 1
                        return await response.text()

                    elif response.status == 429:  # Too many requests
                        wait_time = 2 ** attempt
                        logger.warning(f"Rate limited, waiting {wait_time}s: {url}")
                        await asyncio.sleep(wait_time)
                        continue

                    else:
                        logger.warning(f"HTTP {response.status} for {url}")
                        self.stats["errors"] += 1
                        return None

            except asyncio.TimeoutError:
                logger.warning(f"Timeout on attempt {attempt + 1} for {url}")
                await asyncio.sleep(2 ** attempt)

            except Exception as e:
                logger.error(f"Error fetching {url} (attempt {attempt + 1}): {e}")
                await asyncio.sleep(2 ** attempt)

        self.stats["errors"] += 1
        return None

    async def scrape_url(
        self,
        session: aiohttp.ClientSession,
        url: str,
        scraper_name: Optional[str] = None,
    ) -> List[JobPosting]:
        """
        Scrape jobs from a single URL with automatic ATS detection.

        Args:
            session: aiohttp ClientSession
            url: URL to scrape
            scraper_name: Specific scraper to use (optional, overrides detection)

        Returns:
            List of JobPosting objects
        """
        html = await self.fetch_with_retry(session, url)
        if not html:
            return []

        # Select scraper
        if scraper_name and scraper_name in self.scrapers:
            # Use explicitly specified scraper
            scraper = self.scrapers[scraper_name]
            logger.info(f"Using explicitly specified {scraper.source} scraper for {url}")
        else:
            # Auto-detect ATS platform
            detected_ats = detect_ats(url, html)
            logger.info(f"Detected ATS: {detected_ats} for {url}")

            # Get scraper class and instantiate if not already in our cache
            if detected_ats in self.scrapers:
                scraper = self.scrapers[detected_ats]
            else:
                # Dynamically create scraper instance for detected ATS
                scraper_class = get_scraper_class(detected_ats)
                scraper = scraper_class()
                # Cache it for future use
                self.scrapers[detected_ats] = scraper

            logger.info(f"Using {scraper.source} scraper for {url}")

        try:
            jobs = scraper.extract_jobs_from_html(html, url)
            logger.info(f"Extracted {len(jobs)} jobs from {url}")
            return jobs

        except Exception as e:
            logger.error(f"Error parsing {url}: {e}")
            # Fallback to generic scraper on error
            logger.info("Falling back to generic scraper")
            try:
                generic_scraper = self.scrapers.get("generic", GenericScraper())
                jobs = generic_scraper.extract_jobs_from_html(html, url)
                logger.info(f"Generic scraper extracted {len(jobs)} jobs")
                return jobs
            except Exception as e2:
                logger.error(f"Generic scraper also failed: {e2}")
                return []

    async def scrape_urls(self, urls: List[str]) -> List[JobPosting]:
        """
        Scrape jobs from multiple URLs concurrently.

        Args:
            urls: List of URLs to scrape

        Returns:
            List of all JobPosting objects
        """
        connector = aiohttp.TCPConnector(limit=self.concurrency)
        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Create tasks with concurrency limit
            semaphore = asyncio.Semaphore(self.concurrency)

            async def scrape_with_semaphore(url: str):
                async with semaphore:
                    return await self.scrape_url(session, url)

            tasks = [scrape_with_semaphore(url) for url in urls[:self.max_pages]]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Flatten results
            all_jobs = []
            for result in results:
                if isinstance(result, list):
                    all_jobs.extend(result)
                elif isinstance(result, Exception):
                    logger.error(f"Task failed: {result}")

            return all_jobs

    def get_stats(self) -> Dict:
        """
        Get scraping statistics.

        Returns:
            Dict with stats
        """
        return self.stats.copy()


def deduplicate_jobs(jobs: List[JobPosting]) -> List[JobPosting]:
    """
    Remove duplicate jobs based on ID.

    Args:
        jobs: List of JobPosting objects

    Returns:
        Deduplicated list
    """
    seen_ids = set()
    unique_jobs = []

    for job in jobs:
        if job.id not in seen_ids:
            seen_ids.add(job.id)
            unique_jobs.append(job)

    return unique_jobs
