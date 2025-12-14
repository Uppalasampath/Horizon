"""
Scheduled Job Scraping System - Automatically scrape top tech companies on schedule.
"""
import asyncio
import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from .core import JobScraperCore, deduplicate_jobs
from .companies import get_all_companies, is_technical_role
from .schema import JobPosting

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ScheduledScraper:
    """Scheduled scraper for top tech companies."""

    def __init__(
        self,
        output_dir: str = "data/jobs",
        concurrency: int = 4,
        technical_only: bool = True,
    ):
        """
        Initialize scheduled scraper.

        Args:
            output_dir: Directory to save scraped jobs
            concurrency: Max concurrent requests
            technical_only: Filter for technical roles only
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.concurrency = concurrency
        self.technical_only = technical_only

        self.scraper = JobScraperCore(
            concurrency=concurrency,
            max_pages=5,  # Scrape up to 5 pages per company
        )

        self.stats = {
            "total_runs": 0,
            "total_jobs": 0,
            "total_technical": 0,
            "last_run": None,
        }

    async def scrape_all_companies(self):
        """Scrape all configured companies."""
        logger.info("=" * 80)
        logger.info("Starting scheduled scrape of top tech companies")
        logger.info("=" * 80)

        companies = get_all_companies()
        urls = [company["url"] for company in companies]

        logger.info(f"Scraping {len(companies)} companies...")

        # Scrape all URLs
        all_jobs = await self.scraper.scrape_urls(urls)

        # Deduplicate
        all_jobs = deduplicate_jobs(all_jobs)
        logger.info(f"Found {len(all_jobs)} unique jobs")

        # Filter for technical roles if enabled
        if self.technical_only:
            technical_jobs = [
                job for job in all_jobs
                if is_technical_role(job.title, job.description)
            ]
            logger.info(
                f"Filtered to {len(technical_jobs)} technical roles "
                f"({len(all_jobs) - len(technical_jobs)} non-technical excluded)"
            )
            all_jobs = technical_jobs

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"jobs_{timestamp}.jsonl"

        with open(output_file, "w", encoding="utf-8") as f:
            for job in all_jobs:
                json_line = job.model_dump_json()
                f.write(json_line + "\n")

        logger.info(f"Saved {len(all_jobs)} jobs to {output_file}")

        # Also save to "latest" file
        latest_file = self.output_dir / "jobs_latest.jsonl"
        with open(latest_file, "w", encoding="utf-8") as f:
            for job in all_jobs:
                json_line = job.model_dump_json()
                f.write(json_line + "\n")

        logger.info(f"Updated latest jobs file: {latest_file}")

        # Update stats
        self.stats["total_runs"] += 1
        self.stats["total_jobs"] += len(all_jobs)
        if self.technical_only:
            self.stats["total_technical"] += len(all_jobs)
        self.stats["last_run"] = datetime.now().isoformat()

        # Save stats
        stats_file = self.output_dir / "scraper_stats.json"
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(self.stats, f, indent=2)

        logger.info("=" * 80)
        logger.info("Scrape completed successfully!")
        logger.info(f"Stats: {self.stats}")
        logger.info("=" * 80)

        return all_jobs

    def run_once(self):
        """Run scraper once (synchronous wrapper)."""
        logger.info("Running one-time scrape...")
        return asyncio.run(self.scrape_all_companies())

    def run_scheduled(self, cron_schedule: str = "0 */6 * * *"):
        """
        Run scraper on a schedule.

        Args:
            cron_schedule: Cron expression (default: every 6 hours)

        Common schedules:
            "0 */6 * * *"  - Every 6 hours
            "0 0 * * *"    - Daily at midnight
            "0 0 * * 0"    - Weekly on Sunday
            "0 9,17 * * *" - Twice daily at 9am and 5pm
        """
        scheduler = BlockingScheduler()

        # Add scheduled job
        scheduler.add_job(
            self.run_once,
            trigger=CronTrigger.from_crontab(cron_schedule),
            id="tech_company_scraper",
            name="Tech Company Job Scraper",
            replace_existing=True,
        )

        logger.info(f"Scheduled scraper with cron: {cron_schedule}")
        logger.info("Starting scheduler...")

        # Run once immediately
        self.run_once()

        # Start scheduler
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped")


def main():
    """CLI entrypoint for scheduled scraper."""
    parser = argparse.ArgumentParser(
        description="Scheduled scraper for top tech companies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run once
  python -m job_scraper.scheduler --once

  # Schedule every 6 hours
  python -m job_scraper.scheduler --schedule "0 */6 * * *"

  # Schedule daily at midnight
  python -m job_scraper.scheduler --schedule "0 0 * * *"

  # Include non-technical roles
  python -m job_scraper.scheduler --once --all-roles

Cron Schedule Format:
  "minute hour day month day_of_week"

  Examples:
    "0 */6 * * *"  - Every 6 hours
    "0 0 * * *"    - Daily at midnight
    "0 9 * * 1-5"  - Weekdays at 9am
    "0 0 * * 0"    - Sundays at midnight
        """
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="Run scraper once and exit (no scheduling)"
    )

    parser.add_argument(
        "--schedule",
        type=str,
        default="0 */6 * * *",
        help="Cron schedule (default: every 6 hours)"
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/jobs",
        help="Output directory for jobs (default: data/jobs)"
    )

    parser.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="Max concurrent requests (default: 4)"
    )

    parser.add_argument(
        "--all-roles",
        action="store_true",
        help="Include non-technical roles (default: technical only)"
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize scraper
    scraper = ScheduledScraper(
        output_dir=args.output_dir,
        concurrency=args.concurrency,
        technical_only=not args.all_roles,
    )

    # Run
    if args.once:
        logger.info("Running one-time scrape...")
        scraper.run_once()
        logger.info("Done!")
    else:
        logger.info(f"Starting scheduled scraper: {args.schedule}")
        scraper.run_scheduled(cron_schedule=args.schedule)


if __name__ == "__main__":
    main()
