"""
Workable ATS scraper - uses Workable API.
"""
import re
import json
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from ..schema import JobPosting, normalize_experience_level
from ..utils import html_to_text, extract_skills, make_absolute_url
import logging

logger = logging.getLogger(__name__)


class WorkableScraper:
    """Scraper for Workable ATS."""

    def __init__(self):
        """Initialize Workable scraper."""
        self.source = "workable"

    def can_handle(self, url: str) -> bool:
        """Check if this scraper can handle the given URL."""
        return "workable.com" in url or "apply.workable.com" in url

    async def fetch_jobs_api(
        self, company: str, session: Any
    ) -> List[JobPosting]:
        """
        Fetch jobs from Workable API.

        Args:
            company: Company identifier
            session: aiohttp ClientSession

        Returns:
            List of JobPosting objects
        """
        # Workable API endpoint
        api_url = f"https://www.workable.com/api/accounts/{company}/jobs"

        try:
            async with session.get(api_url, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_api_response(data, company)
                else:
                    logger.warning(f"Workable API returned status {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching Workable API: {e}")
            return []

    def extract_jobs_from_html(
        self, html: str, base_url: str
    ) -> List[JobPosting]:
        """Extract job postings from Workable HTML page."""
        jobs = []

        # Try to find embedded JSON data
        try:
            soup = BeautifulSoup(html, "html.parser")
            scripts = soup.find_all("script", type="application/json")

            for script in scripts:
                if not script.string:
                    continue

                try:
                    data = json.loads(script.string)
                    company = self._extract_company_from_url(base_url)

                    # Check if this is job data
                    if isinstance(data, list):
                        jobs.extend(self._parse_api_response({"jobs": data}, company))
                    elif isinstance(data, dict) and ("jobs" in data or "openings" in data):
                        jobs.extend(self._parse_api_response(data, company))

                except (json.JSONDecodeError, TypeError):
                    continue

        except Exception as e:
            logger.debug(f"Failed to parse Workable JSON: {e}")

        # Fallback to HTML parsing
        if not jobs:
            jobs = self._parse_html_jobs(html, base_url)

        return jobs

    def _parse_api_response(
        self, data: Dict, company: str
    ) -> List[JobPosting]:
        """Parse Workable API response."""
        jobs = []

        # Extract jobs from response
        job_list = data.get("jobs", []) or data.get("openings", [])

        if isinstance(job_list, dict):
            job_list = [job_list]

        for job_data in job_list:
            try:
                job = self._parse_job_data(job_data, company)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug(f"Failed to parse Workable job: {e}")
                continue

        return jobs

    def _parse_job_data(
        self, data: Dict, company: str
    ) -> Optional[JobPosting]:
        """Parse a single Workable job object."""
        try:
            # Extract job ID
            job_id = str(
                data.get("id")
                or data.get("shortcode")
                or data.get("slug")
                or ""
            )

            # Extract title
            title = data.get("title") or data.get("name") or ""

            # Extract location
            location_data = data.get("location", {})
            if isinstance(location_data, dict):
                city = location_data.get("city", "")
                country = location_data.get("country", "")
                location = f"{city}, {country}".strip(", ") or "Unknown"
            else:
                location = str(location_data) if location_data else "Unknown"

            # Extract department
            department = (
                data.get("department")
                or data.get("team")
                or ""
            )

            # Extract description
            description = (
                data.get("description")
                or data.get("requirements")
                or data.get("details")
                or ""
            )

            # Extract application URL
            apply_url = (
                data.get("application_url")
                or data.get("url")
                or data.get("application_link")
                or f"https://apply.workable.com/{company}/j/{job_id}/"
            )

            # Extract posted date
            posted_date = (
                data.get("published_on")
                or data.get("created_at")
                or data.get("posted_date")
            )

            # Extract employment type
            employment_type = (
                data.get("employment_type")
                or data.get("type")
                or ""
            )

            if not all([job_id, title]):
                return None

            # Process description
            desc_text = html_to_text(description) if description else ""

            # Extract skills and experience level
            full_text = f"{title} {desc_text} {department} {employment_type}"
            skills = extract_skills(full_text)
            exp_level = normalize_experience_level(full_text)

            job = JobPosting(
                id=f"workable_{job_id}",
                source=self.source,
                title=title,
                company=company if company else "Unknown",
                location=location,
                posted_date=posted_date,
                description=desc_text,
                skills=skills,
                experience_level=exp_level,
                apply_url=apply_url,
                raw={"workable_data": data},
            )

            return job

        except Exception as e:
            logger.debug(f"Failed to parse Workable job data: {e}")
            return None

    def _parse_html_jobs(
        self, html: str, base_url: str
    ) -> List[JobPosting]:
        """Fallback HTML parsing for Workable pages."""
        soup = BeautifulSoup(html, "html.parser")
        jobs = []

        # Common Workable HTML patterns
        job_elements = (
            soup.find_all("li", class_=re.compile(r"job|opening|position", re.I))
            or soup.find_all("div", class_=re.compile(r"job|posting", re.I))
        )

        company = self._extract_company_from_url(base_url)

        for element in job_elements[:50]:
            try:
                # Extract title
                title_elem = element.find(["h2", "h3", "h4", "a"])
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                if len(title) < 10:
                    continue

                # Extract URL
                link_elem = element.find("a", href=True)
                apply_url = (
                    make_absolute_url(base_url, link_elem.get("href"))
                    if link_elem
                    else base_url
                )

                # Extract location
                location_elem = element.find(class_=re.compile(r"location|city", re.I))
                location = (
                    location_elem.get_text(strip=True)
                    if location_elem
                    else "Unknown"
                )

                # Extract department
                dept_elem = element.find(class_=re.compile(r"department|team", re.I))
                department = (
                    dept_elem.get_text(strip=True)
                    if dept_elem
                    else ""
                )

                # Extract description
                description = element.get_text(separator=" ", strip=True)

                # Generate ID
                job_id = re.sub(r"\W+", "_", apply_url.split("/")[-1] or title)[:100]

                # Extract skills and experience
                full_text = f"{title} {description} {department}"
                skills = extract_skills(full_text)
                exp_level = normalize_experience_level(full_text)

                job = JobPosting(
                    id=f"workable_{job_id}",
                    source=self.source,
                    title=title,
                    company=company,
                    location=location,
                    posted_date=None,
                    description=html_to_text(description),
                    skills=skills,
                    experience_level=exp_level,
                    apply_url=apply_url,
                    raw={"html": str(element)[:300]},
                )

                jobs.append(job)

            except Exception:
                continue

        return jobs

    def _extract_company_from_url(self, url: str) -> str:
        """Extract company identifier from Workable URL."""
        # Try different patterns
        patterns = [
            r"workable\.com/([^/]+)",
            r"apply\.workable\.com/([^/]+)",
            r"/accounts/([^/]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return "Unknown"
