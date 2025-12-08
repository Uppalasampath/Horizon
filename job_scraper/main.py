"""
Job Scraper CLI - Main entrypoint for scraping jobs.
"""
import asyncio
import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List
from .core import JobScraperCore, deduplicate_jobs
from .schema import JobPosting

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Sample company career pages for testing
SAMPLE_URLS = {
    "greenhouse": [
        "https://boards.greenhouse.io/embed/job_board?for=example",
    ],
    "lever": [
        "https://jobs.lever.co/example",
    ],
    "workday": [
        "https://example.wd1.myworkdayjobs.com/Example_Careers",
    ],
}


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Scrape entry-level tech jobs from ATS providers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape using generic scraper with custom URLs
  python -m job_scraper.main --urls "https://company.com/jobs" --out jobs.jsonl

  # Scrape with specific sources (requires valid URLs)
  python -m job_scraper.main --sources greenhouse,lever --urls <urls> --out jobs.jsonl

  # Use sample URLs for testing (mock data)
  python -m job_scraper.main --use-fixtures --out jobs.jsonl
        """
    )

    parser.add_argument(
        "--sources",
        type=str,
        default="generic",
        help="Comma-separated list of sources: greenhouse,lever,workday,generic (default: generic)"
    )

    parser.add_argument(
        "--urls",
        type=str,
        help="Comma-separated list of URLs to scrape"
    )

    parser.add_argument(
        "--queries",
        type=str,
        help="Search queries (not implemented - requires API access or search functionality)"
    )

    parser.add_argument(
        "--out",
        type=str,
        default="jobs.jsonl",
        help="Output file path (default: jobs.jsonl)"
    )

    parser.add_argument(
        "--concurrency",
        type=int,
        default=8,
        help="Max concurrent requests (default: 8)"
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=3,
        help="Max pages to scrape per source (default: 3)"
    )

    parser.add_argument(
        "--use-fixtures",
        action="store_true",
        help="Use fixture data instead of live scraping (for testing)"
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )

    return parser.parse_args()


def load_fixtures() -> List[JobPosting]:
    """
    Load sample jobs from fixtures.

    Returns:
        List of sample JobPosting objects
    """
    # Create sample fixture data
    sample_jobs = [
        JobPosting(
            id="greenhouse_12345",
            source="greenhouse",
            title="Junior Backend Engineer",
            company="TechCorp",
            location="San Francisco, CA",
            posted_date="2025-12-01T00:00:00Z",
            description="We're looking for a junior backend engineer to join our team. "
                       "You'll work with Python, Django, and PostgreSQL to build scalable APIs. "
                       "Recent graduates welcome! Requirements: Python, SQL, REST APIs, Docker. "
                       "Nice to have: AWS, Kubernetes.",
            skills=["Python", "Django", "PostgreSQL", "REST", "Docker", "AWS"],
            experience_level="entry",
            apply_url="https://boards.greenhouse.io/techcorp/jobs/12345",
            raw={"fixture": True}
        ),
        JobPosting(
            id="lever_67890",
            source="lever",
            title="Entry Level Software Engineer - Full Stack",
            company="StartupXYZ",
            location="Remote",
            posted_date="2025-12-05T00:00:00Z",
            description="Join our engineering team as an entry-level full stack engineer. "
                       "Work with React, Node.js, and MongoDB. We're looking for new grads with "
                       "a passion for learning. Requirements: JavaScript, React, Node.js, Git. "
                       "You'll build features, write tests, and collaborate with the team.",
            skills=["JavaScript", "React", "Node.js", "MongoDB", "Git"],
            experience_level="entry",
            apply_url="https://jobs.lever.co/startupxyz/67890",
            raw={"fixture": True}
        ),
        JobPosting(
            id="workday_11111",
            source="workday",
            title="Associate Software Developer",
            company="BigCompany",
            location="New York, NY",
            posted_date="2025-11-28T00:00:00Z",
            description="We're hiring associate software developers for our engineering team. "
                       "You'll work on backend services using Java, Spring Boot, and Microservices. "
                       "0-2 years experience required. Requirements: Java, Spring, SQL, REST APIs, "
                       "CI/CD. Great opportunity for recent CS graduates.",
            skills=["Java", "Spring", "SQL", "REST", "Microservices", "CI/CD"],
            experience_level="entry",
            apply_url="https://bigcompany.wd1.myworkdayjobs.com/careers/job/11111",
            raw={"fixture": True}
        ),
        JobPosting(
            id="generic_22222",
            source="generic",
            title="Junior Data Engineer",
            company="DataCo",
            location="Austin, TX",
            posted_date="2025-12-02T00:00:00Z",
            description="Looking for a junior data engineer to work on ETL pipelines and data "
                       "infrastructure. You'll use Python, SQL, Spark, and Airflow. Entry level "
                       "position for recent graduates or those with 1 year experience. "
                       "Requirements: Python, SQL, Spark, AWS, data modeling.",
            skills=["Python", "SQL", "Spark", "Airflow", "AWS"],
            experience_level="entry",
            apply_url="https://dataco.com/careers/junior-data-engineer",
            raw={"fixture": True}
        ),
        JobPosting(
            id="generic_33333",
            source="generic",
            title="Senior Frontend Architect",
            company="DesignStudio",
            location="Seattle, WA",
            posted_date="2025-11-20T00:00:00Z",
            description="Senior frontend architect needed with 7+ years experience. "
                       "Lead our frontend team and design scalable React applications. "
                       "Requirements: React, TypeScript, GraphQL, 7+ years experience, "
                       "system design expertise.",
            skills=["React", "TypeScript", "GraphQL", "JavaScript"],
            experience_level="senior",
            apply_url="https://designstudio.com/careers/senior-frontend-architect",
            raw={"fixture": True}
        ),
    ]

    return sample_jobs


async def main_async(args):
    """
    Async main function.

    Args:
        args: Parsed command line arguments
    """
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Use fixtures for testing
    if args.use_fixtures:
        logger.info("Using fixture data (not live scraping)")
        jobs = load_fixtures()

    else:
        # Parse sources
        sources = [s.strip() for s in args.sources.split(",")]

        # Parse URLs
        if not args.urls:
            logger.error("Error: --urls required (or use --use-fixtures for testing)")
            sys.exit(1)

        urls = [u.strip() for u in args.urls.split(",")]

        logger.info(f"Scraping {len(urls)} URLs with sources: {sources}")
        logger.info(f"Concurrency: {args.concurrency}, Max pages: {args.max_pages}")

        # Initialize scraper
        scraper = JobScraperCore(
            sources=sources,
            concurrency=args.concurrency,
            max_pages=args.max_pages,
        )

        # Scrape
        jobs = await scraper.scrape_urls(urls)

        # Stats
        stats = scraper.get_stats()
        logger.info(f"Scraping complete. Stats: {stats}")

    # Deduplicate
    jobs = deduplicate_jobs(jobs)
    logger.info(f"Found {len(jobs)} unique jobs")

    # Filter by experience level if needed (focus on entry level)
    # Uncomment to filter:
    # jobs = [j for j in jobs if j.experience_level == "entry"]

    # Write output
    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for job in jobs:
            json_line = job.model_dump_json()
            f.write(json_line + "\n")

    logger.info(f"Wrote {len(jobs)} jobs to {output_path}")

    # Print summary
    print(f"\n✓ Scraped {len(jobs)} jobs")
    print(f"✓ Output: {output_path}")

    # Print sample
    if jobs:
        print(f"\nSample job:")
        sample = jobs[0]
        print(f"  Title: {sample.title}")
        print(f"  Company: {sample.company}")
        print(f"  Location: {sample.location}")
        print(f"  Level: {sample.experience_level}")
        print(f"  Skills: {', '.join(sample.skills[:5])}")


def main():
    """Main CLI entrypoint."""
    args = parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
