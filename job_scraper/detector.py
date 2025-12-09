"""
ATS Detection Module - Automatically detect job board platform from URL and HTML.
"""
import re
from typing import Optional, Type
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


def detect_ats(url: str, html: Optional[str] = None):
    """
    Detect ATS platform from URL and optionally HTML content.

    Args:
        url: URL to analyze
        html: Optional HTML content for deeper analysis

    Returns:
        Scraper class name as string, or None for generic fallback
    """
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path.lower()
    full_url = url.lower()

    # Greenhouse detection
    if _is_greenhouse(domain, path, full_url, html):
        logger.info(f"Detected Greenhouse ATS for {url}")
        return "greenhouse"

    # Lever detection
    if _is_lever(domain, path, full_url, html):
        logger.info(f"Detected Lever ATS for {url}")
        return "lever"

    # Workday detection
    if _is_workday(domain, path, full_url, html):
        logger.info(f"Detected Workday ATS for {url}")
        return "workday"

    # Ashby detection
    if _is_ashby(domain, path, full_url, html):
        logger.info(f"Detected Ashby ATS for {url}")
        return "ashby"

    # SmartRecruiters detection
    if _is_smartrecruiters(domain, path, full_url, html):
        logger.info(f"Detected SmartRecruiters ATS for {url}")
        return "smartrecruiters"

    # Workable detection
    if _is_workable(domain, path, full_url, html):
        logger.info(f"Detected Workable ATS for {url}")
        return "workable"

    # iCIMS detection
    if _is_icims(domain, path, full_url, html):
        logger.info(f"Detected iCIMS ATS for {url}")
        return "icims"

    # No specific ATS detected - use generic
    logger.info(f"No specific ATS detected for {url}, using generic scraper")
    return "generic"


def _is_greenhouse(
    domain: str, path: str, full_url: str, html: Optional[str]
) -> bool:
    """Detect Greenhouse ATS."""
    # Domain-based detection
    if "greenhouse.io" in domain:
        return True

    # Path-based detection
    if "/boards/" in path or "/embed/job_board" in path:
        return True

    # HTML-based detection
    if html:
        if re.search(r"greenhouse\.io|gh-card|greenhouse-job", html, re.I):
            return True

    return False


def _is_lever(
    domain: str, path: str, full_url: str, html: Optional[str]
) -> bool:
    """Detect Lever ATS."""
    # Domain-based detection
    if "lever.co" in domain or "jobs.lever.co" in domain:
        return True

    # HTML-based detection
    if html:
        if re.search(r"lever\.co|lever-jobs|posting-", html, re.I):
            return True
        # Check for Lever API data
        if "api.lever.co" in html:
            return True

    return False


def _is_workday(
    domain: str, path: str, full_url: str, html: Optional[str]
) -> bool:
    """Detect Workday ATS."""
    # Domain-based detection
    if "myworkdayjobs.com" in domain:
        return True

    # Path-based detection
    if any(
        pattern in path
        for pattern in ["/wday/", "/apply/", "/workday", "/careers"]
    ):
        # Additional check for workday-specific patterns
        if "workday" in domain or "wday" in path:
            return True

    # HTML-based detection
    if html:
        if re.search(
            r"workday|myworkdayjobs|data-automation-id|wday-cxs",
            html,
            re.I
        ):
            return True

    return False


def _is_ashby(
    domain: str, path: str, full_url: str, html: Optional[str]
) -> bool:
    """Detect Ashby ATS."""
    # Domain-based detection
    if "ashbyhq.com" in domain or "jobs.ashbyhq.com" in domain:
        return True

    # HTML-based detection
    if html:
        if re.search(r"ashbyhq\.com|ashby-job|__ASHBY", html, re.I):
            return True
        # Check for Ashby API calls
        if "api.ashbyhq.com" in html:
            return True

    return False


def _is_smartrecruiters(
    domain: str, path: str, full_url: str, html: Optional[str]
) -> bool:
    """Detect SmartRecruiters ATS."""
    # Domain-based detection
    if "smartrecruiters.com" in domain or "jobs.smartrecruiters.com" in domain:
        return True

    # Path-based detection
    if "/smartrecruiters/" in path:
        return True

    # HTML-based detection
    if html:
        if re.search(
            r"smartrecruiters|sr-job|smartrecruiters\.com",
            html,
            re.I
        ):
            return True

    return False


def _is_workable(
    domain: str, path: str, full_url: str, html: Optional[str]
) -> bool:
    """Detect Workable ATS."""
    # Domain-based detection
    if "workable.com" in domain or "apply.workable.com" in domain:
        return True

    # HTML-based detection
    if html:
        if re.search(
            r"workable\.com|whr-job|workable-application",
            html,
            re.I
        ):
            return True
        # Check for Workable API
        if "www.workable.com/api" in html:
            return True

    return False


def _is_icims(
    domain: str, path: str, full_url: str, html: Optional[str]
) -> bool:
    """Detect iCIMS ATS."""
    # Path-based detection
    if any(
        pattern in path
        for pattern in ["/icims/", "/careerportal/", "/jobs/intro"]
    ):
        return True

    # Domain-based detection
    if "icims.com" in domain or "icimsxr.com" in domain:
        return True

    # HTML-based detection
    if html:
        if re.search(
            r"icims|iCIMS|careerportal|icimsxr",
            html,
            re.I
        ):
            return True

    return False


def get_scraper_class(ats_name: str):
    """
    Get scraper class from ATS name.

    Args:
        ats_name: Name of ATS (e.g., 'greenhouse', 'lever', 'generic')

    Returns:
        Scraper class
    """
    # Import here to avoid circular imports
    from .sources import (
        GreenhouseScraper,
        LeverScraper,
        WorkdayScraper,
        GenericScraper,
    )

    # Try to import optional scrapers
    try:
        from .sources.ashby import AshbyScraper
    except ImportError:
        AshbyScraper = None

    try:
        from .sources.smartrecruiters import SmartRecruitersScraper
    except ImportError:
        SmartRecruitersScraper = None

    try:
        from .sources.workable import WorkableScraper
    except ImportError:
        WorkableScraper = None

    try:
        from .sources.icims import ICIMSScraper
    except ImportError:
        ICIMSScraper = None

    scraper_map = {
        "greenhouse": GreenhouseScraper,
        "lever": LeverScraper,
        "workday": WorkdayScraper,
        "generic": GenericScraper,
    }

    # Add optional scrapers if available
    if AshbyScraper:
        scraper_map["ashby"] = AshbyScraper
    if SmartRecruitersScraper:
        scraper_map["smartrecruiters"] = SmartRecruitersScraper
    if WorkableScraper:
        scraper_map["workable"] = WorkableScraper
    if ICIMSScraper:
        scraper_map["icims"] = ICIMSScraper

    return scraper_map.get(ats_name, GenericScraper)
