"""
Greenhouse ATS scraper - handles Greenhouse job boards.
"""
import re
import json
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from ..schema import JobPosting, normalize_experience_level
from ..utils import html_to_text, extract_skills, make_absolute_url


class GreenhouseScraper:
    """Scraper for Greenhouse ATS job boards."""

    def __init__(self):
        """Initialize Greenhouse scraper."""
        self.source = "greenhouse"

    def can_handle(self, url: str) -> bool:
        """
        Check if this scraper can handle the given URL.

        Args:
            url: URL to check

        Returns:
            True if URL is a Greenhouse board
        """
        return "greenhouse.io" in url or "/boards/" in url

    def extract_jobs_from_html(
        self, html: str, base_url: str
    ) -> List[JobPosting]:
        """
        Extract job postings from Greenhouse HTML page.

        Args:
            html: Raw HTML content
            base_url: Base URL for resolving relative links

        Returns:
            List of JobPosting objects
        """
        soup = BeautifulSoup(html, "html.parser")
        jobs = []

        # Try to find embedded JSON data first (common in Greenhouse)
        scripts = soup.find_all("script", type="application/json")
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and "jobs" in data:
                    jobs.extend(self._parse_json_jobs(data["jobs"], base_url))
                    return jobs
            except (json.JSONDecodeError, KeyError):
                continue

        # Fallback to HTML parsing
        # Common Greenhouse selectors
        job_elements = soup.find_all("div", class_=re.compile(r"opening|job"))

        for element in job_elements:
            try:
                job = self._parse_html_job(element, base_url)
                if job:
                    jobs.append(job)
            except Exception as e:
                continue  # Skip malformed entries

        return jobs

    def _parse_json_jobs(
        self, jobs_data: List[Dict], base_url: str
    ) -> List[JobPosting]:
        """Parse jobs from JSON data."""
        jobs = []

        for job_data in jobs_data:
            try:
                job_id = str(job_data.get("id", ""))
                title = job_data.get("title", "")
                location_obj = job_data.get("location", {})
                location = location_obj.get("name", "") if isinstance(
                    location_obj, dict
                ) else str(location_obj)

                # Description may need to be fetched separately
                description = job_data.get("content", "") or job_data.get(
                    "description", ""
                )

                company = job_data.get("company", {}).get("name", "Unknown")
                apply_url = job_data.get("absolute_url", "")

                if not all([job_id, title]):
                    continue

                full_text = f"{title} {description}"
                skills = extract_skills(full_text)
                exp_level = normalize_experience_level(full_text)

                job = JobPosting(
                    id=f"greenhouse_{job_id}",
                    source=self.source,
                    title=title,
                    company=company,
                    location=location,
                    posted_date=job_data.get("updated_at"),
                    description=html_to_text(description) if description else "",
                    skills=skills,
                    experience_level=exp_level,
                    apply_url=make_absolute_url(base_url, apply_url),
                    raw=job_data,
                )
                jobs.append(job)

            except Exception:
                continue

        return jobs

    def _parse_html_job(
        self, element: Any, base_url: str
    ) -> Optional[JobPosting]:
        """Parse single job from HTML element."""
        try:
            # Extract title
            title_elem = element.find("a", class_=re.compile(r"job-title|opening-title"))
            if not title_elem:
                title_elem = element.find("h3") or element.find("h2")

            if not title_elem:
                return None

            title = title_elem.get_text(strip=True)

            # Extract URL
            link = title_elem.get("href", "") if title_elem.name == "a" else ""
            if not link:
                link_elem = element.find("a")
                link = link_elem.get("href", "") if link_elem else ""

            apply_url = make_absolute_url(base_url, link) if link else base_url

            # Extract location
            location_elem = element.find(
                "span", class_=re.compile(r"location")
            ) or element.find("div", class_=re.compile(r"location"))
            location = location_elem.get_text(strip=True) if location_elem else "Unknown"

            # Extract company (may be in parent container)
            company = "Unknown"
            company_elem = element.find("span", class_=re.compile(r"company"))
            if company_elem:
                company = company_elem.get_text(strip=True)

            # Description (usually need to fetch detail page)
            description = element.get_text(separator=" ", strip=True)

            full_text = f"{title} {description}"
            skills = extract_skills(full_text)
            exp_level = normalize_experience_level(full_text)

            # Generate unique ID from URL or title
            job_id = re.sub(r"\W+", "_", apply_url.split("/")[-1] or title)

            job = JobPosting(
                id=f"greenhouse_{job_id}",
                source=self.source,
                title=title,
                company=company,
                location=location,
                posted_date=None,
                description=html_to_text(description),
                skills=skills,
                experience_level=exp_level,
                apply_url=apply_url,
                raw={"html": str(element)[:500]},
            )

            return job

        except Exception:
            return None

    async def fetch_job_detail(
        self, job_url: str, session: Any
    ) -> Optional[str]:
        """
        Fetch full job description from detail page.

        Args:
            job_url: URL to job detail page
            session: aiohttp ClientSession

        Returns:
            Full description HTML or None
        """
        try:
            async with session.get(job_url, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")

                    # Find description container
                    desc_elem = soup.find(
                        "div", id=re.compile(r"content|description")
                    ) or soup.find("div", class_=re.compile(r"content|description"))

                    if desc_elem:
                        return desc_elem.get_text(separator="\n", strip=True)

        except Exception:
            pass

        return None
