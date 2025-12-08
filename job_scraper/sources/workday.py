"""
Workday ATS scraper - handles Workday job boards.
"""
import re
import json
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from ..schema import JobPosting, normalize_experience_level
from ..utils import html_to_text, extract_skills, make_absolute_url


class WorkdayScraper:
    """Scraper for Workday ATS job boards."""

    def __init__(self):
        """Initialize Workday scraper."""
        self.source = "workday"

    def can_handle(self, url: str) -> bool:
        """
        Check if this scraper can handle the given URL.

        Args:
            url: URL to check

        Returns:
            True if URL is a Workday board
        """
        return "myworkdayjobs.com" in url or "workday" in url.lower()

    def extract_jobs_from_html(
        self, html: str, base_url: str
    ) -> List[JobPosting]:
        """
        Extract job postings from Workday HTML/JSON page.

        Workday often uses JSON APIs or embeds data.

        Args:
            html: Raw HTML content
            base_url: Base URL for resolving relative links

        Returns:
            List of JobPosting objects
        """
        soup = BeautifulSoup(html, "html.parser")
        jobs = []

        # Try to parse as JSON first (Workday API responses)
        try:
            data = json.loads(html)
            if isinstance(data, dict):
                # Look for job listings in common Workday response structures
                job_data = (
                    data.get("searchResults", [])
                    or data.get("jobs", [])
                    or data.get("jobPostings", [])
                )
                if job_data:
                    jobs.extend(self._parse_json_jobs(job_data, base_url))
                    return jobs
        except (json.JSONDecodeError, ValueError):
            pass

        # HTML parsing fallback
        job_elements = soup.find_all("li", class_=re.compile(r"job|position"))

        if not job_elements:
            # Try alternative selectors
            job_elements = soup.find_all("div", attrs={"data-automation-id": "job"})

        if not job_elements:
            # Try table rows (older Workday format)
            job_elements = soup.find_all("tr", class_=re.compile(r"job"))

        for element in job_elements:
            try:
                job = self._parse_html_job(element, base_url)
                if job:
                    jobs.append(job)
            except Exception:
                continue

        return jobs

    def _parse_json_jobs(
        self, jobs_data: List[Dict], base_url: str
    ) -> List[JobPosting]:
        """Parse jobs from JSON data."""
        jobs = []

        for job_data in jobs_data:
            try:
                # Workday JSON structure varies by company
                job_id = str(
                    job_data.get("bulletFields", [{}])[0].get("id", "")
                    or job_data.get("id", "")
                    or job_data.get("jobId", "")
                )

                title = (
                    job_data.get("title", "")
                    or job_data.get("jobTitle", "")
                    or job_data.get("positionTitle", "")
                )

                location = (
                    job_data.get("location", {}).get("location", "")
                    if isinstance(job_data.get("location"), dict)
                    else job_data.get("location", "Unknown")
                )

                # Extract location from bulletFields if available
                bullet_fields = job_data.get("bulletFields", [])
                for field in bullet_fields:
                    if "location" in str(field).lower():
                        location = field.get("title", location)
                        break

                description = (
                    job_data.get("jobDescription", "")
                    or job_data.get("description", "")
                    or ""
                )

                # External apply URL
                apply_url = (
                    job_data.get("externalUrl", "")
                    or job_data.get("applyUrl", "")
                    or job_data.get("url", "")
                )

                # Posted date
                posted_date = job_data.get("postedOn") or job_data.get("datePosted")

                # Company (may be in parent or missing)
                company = "Unknown"

                if not all([job_id, title]):
                    continue

                full_text = f"{title} {description}"
                skills = extract_skills(full_text)
                exp_level = normalize_experience_level(full_text)

                job = JobPosting(
                    id=f"workday_{job_id}",
                    source=self.source,
                    title=title,
                    company=company,
                    location=location,
                    posted_date=posted_date,
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
            title_elem = (
                element.find("a", attrs={"data-automation-id": "jobTitle"})
                or element.find("h3", class_=re.compile(r"title"))
                or element.find("a", class_=re.compile(r"title"))
            )

            if not title_elem:
                title_elem = element.find("h3") or element.find("h4")

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
                "dd", attrs={"data-automation-id": "location"}
            ) or element.find("span", class_=re.compile(r"location"))
            location = location_elem.get_text(strip=True) if location_elem else "Unknown"

            # Extract posted date
            date_elem = element.find(
                "dd", attrs={"data-automation-id": "postedOn"}
            ) or element.find("time")
            posted_date = None
            if date_elem:
                posted_date = (
                    date_elem.get("datetime") or date_elem.get_text(strip=True)
                )

            # Description (usually minimal in list view)
            description = element.get_text(separator=" ", strip=True)

            full_text = f"{title} {description}"
            skills = extract_skills(full_text)
            exp_level = normalize_experience_level(full_text)

            # Generate unique ID
            job_id = re.sub(r"\W+", "_", apply_url.split("/")[-1] or title)

            job = JobPosting(
                id=f"workday_{job_id}",
                source=self.source,
                title=title,
                company="Unknown",
                location=location,
                posted_date=posted_date,
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
            Full description text or None
        """
        try:
            async with session.get(job_url, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")

                    # Find description container
                    desc_elem = soup.find(
                        "div", attrs={"data-automation-id": "jobPostingDescription"}
                    ) or soup.find("div", class_=re.compile(r"description"))

                    if desc_elem:
                        return desc_elem.get_text(separator="\n", strip=True)

        except Exception:
            pass

        return None
