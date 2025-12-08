"""
Job Scraper - Fast, modular job scraping from multiple ATS providers.
"""
from .schema import JobPosting, normalize_experience_level
from .core import JobScraperCore, deduplicate_jobs

__version__ = "1.0.0"
__all__ = [
    "JobPosting",
    "normalize_experience_level",
    "JobScraperCore",
    "deduplicate_jobs",
]
