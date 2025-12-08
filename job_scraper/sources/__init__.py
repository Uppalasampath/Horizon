"""
ATS-specific scrapers for different job board platforms.
"""
from .greenhouse import GreenhouseScraper
from .lever import LeverScraper
from .workday import WorkdayScraper
from .generic import GenericScraper

__all__ = [
    "GreenhouseScraper",
    "LeverScraper",
    "WorkdayScraper",
    "GenericScraper",
]
