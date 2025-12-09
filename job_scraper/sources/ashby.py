"""
Ashby ATS scraper - uses Ashby API endpoints.
"""
import re
import json
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from ..schema import JobPosting, normalize_experience_level
from ..utils import html_to_text, extract_skills, make_absolute_url
import logging

logger = logging.getLogger(__name__)


class AshbyScraper:
    """Scraper for Ashby ATS job boards."""

    def __init__(self):
        """Initialize Ashby scraper."""
        self.source = "ashby"

    def can_handle(self, url: str) -> bool:
        """
        Check if this scraper can handle the given URL.

        Args:
            url: URL to check

        Returns:
            True if URL is an Ashby board
        """
        return "ashbyhq.com" in url

    async def fetch_jobs_api(
        self, company: str, session: Any
    ) -> List[JobPosting]:
        """
        Fetch jobs from Ashby API.

        Args:
            company: Company identifier
            session: aiohttp ClientSession

        Returns:
            List of JobPosting objects
        """
        api_url = f"https://api.ashbyhq.com/posting-api/job-board/{company}"

        try:
            async with session.get(api_url, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_api_response(data, company)
                else:
                    logger.warning(f"Ashby API returned status {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching Ashby API: {e}")
            return []

    def extract_jobs_from_html(
        self, html: str, base_url: str
    ) -> List[JobPosting]:
        """
        Extract job postings from Ashby HTML page.

        Args:
            html: Raw HTML content
            base_url: Base URL for resolving relative links

        Returns:
            List of JobPosting objects
        """
        jobs = []
        soup = BeautifulSoup(html, "html.parser")

        # Try to find embedded JSON data
        scripts = soup.find_all("script")
        for script in scripts:
            if not script.string:
                continue

            # Look for Ashby data
            if "__ASHBY" in script.string or "ashbyJobPostings" in script.string:
                try:
                    # Extract JSON from script
                    json_match = re.search(
                        r"(?:__ASHBY|ashbyJobPostings)\s*[:=]\s*({.+?}|\[.+?\])",
                        script.string,
                        re.DOTALL
                    )

                    if json_match:
                        json_str = json_match.group(1)
                        # Clean up
                        json_str = re.sub(r",\s*}", "}", json_str)
                        json_str = re.sub(r",\s*\]", "]", json_str)

                        data = json.loads(json_str)

                        # Extract company from URL
                        company = self._extract_company_from_url(base_url)
                        jobs.extend(self._parse_api_response(data, company))

                except (json.JSONDecodeError, AttributeError) as e:
                    logger.debug(f"Failed to parse Ashby JSON: {e}")
                    continue

        # Fallback to HTML parsing
        if not jobs:
            jobs = self._parse_html_jobs(html, base_url)

        return jobs

    def _parse_api_response(
        self, data: Dict, company: str
    ) -> List[JobPosting]:
        """Parse Ashby API response."""
        jobs = []

        # Handle different response structures
        job_list = []

        if isinstance(data, list):
            job_list = data
        elif isinstance(data, dict):
            job_list = (
                data.get("jobs", [])
                or data.get("jobPostings", [])
                or data.get("postings", [])
                or [data]  # Single job
            )

        for job_data in job_list:
            try:
                job = self._parse_job_data(job_data, company)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug(f"Failed to parse Ashby job: {e}")
                continue

        return jobs

    def _parse_job_data(
        self, data: Dict, company: str
    ) -> Optional[JobPosting]:
        """Parse a single Ashby job object."""
        try:
            # Extract job ID
            job_id = str(
                data.get("id")
                or data.get("jobId")
                or data.get("externalId")
                or ""
            )

            # Extract title
            title = data.get("title") or data.get("name") or ""

            # Extract location
            location_data = data.get("location") or data.get("locationName") or {}
            if isinstance(location_data, dict):
                location = location_data.get("name") or location_data.get("locationName") or "Unknown"
            else:
                location = str(location_data)

            # Extract department/team
            department = (
                data.get("department", {}).get("name")
                if isinstance(data.get("department"), dict)
                else data.get("department") or ""
            )

            # Extract description
            description = (
                data.get("description")
                or data.get("descriptionHtml")
                or data.get("info", {}).get("description")
                or ""
            )

            # Extract application URL
            apply_url = (
                data.get("jobUrl")
                or data.get("applyUrl")
                or data.get("externalLink")
                or f"https://jobs.ashbyhq.com/{company}/{job_id}"
            )

            # Extract posted date
            posted_date = (
                data.get("publishedDate")
                or data.get("createdAt")
                or data.get("postedDate")
            )

            # Extract employment type
            employment_type = data.get("employmentType") or ""

            if not all([job_id, title, description]):
                return None

            # Process description
            desc_text = html_to_text(description) if description else ""

            # Extract skills and experience level
            full_text = f"{title} {desc_text} {department} {employment_type}"
            skills = extract_skills(full_text)
            exp_level = normalize_experience_level(full_text)

            job = JobPosting(
                id=f"ashby_{job_id}",
                source=self.source,
                title=title,
                company=company if company else "Unknown",
                location=location,
                posted_date=posted_date,
                description=desc_text,
                skills=skills,
                experience_level=exp_level,
                apply_url=apply_url,
                raw={"ashby_data": data},
            )

            return job

        except Exception as e:
            logger.debug(f"Failed to parse Ashby job data: {e}")
            return None

    def _parse_html_jobs(
        self, html: str, base_url: str
    ) -> List[JobPosting]:
        """Fallback HTML parsing for Ashby pages."""
        soup = BeautifulSoup(html, "html.parser")
        jobs = []

        # Common Ashby HTML patterns
        job_elements = soup.find_all(
            "div", class_=re.compile(r"job|posting|position", re.I)
        )

        company = self._extract_company_from_url(base_url)

        for element in job_elements[:50]:
            try:
                # Extract title
                title_elem = element.find(["h2", "h3", "h4"]) or element.find("a")
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                if len(title) < 10 or len(title) > 150:
                    continue

                # Extract URL
                link_elem = element.find("a", href=True)
                apply_url = (
                    make_absolute_url(base_url, link_elem.get("href"))
                    if link_elem
                    else base_url
                )

                # Extract location
                location_elem = element.find(
                    class_=re.compile(r"location", re.I)
                )
                location = (
                    location_elem.get_text(strip=True)
                    if location_elem
                    else "Unknown"
                )

                # Extract description
                description = element.get_text(separator=" ", strip=True)

                # Generate ID from URL or title
                job_id = re.sub(r"\W+", "_", apply_url.split("/")[-1] or title)[:100]

                # Extract skills and experience
                full_text = f"{title} {description}"
                skills = extract_skills(full_text)
                exp_level = normalize_experience_level(full_text)

                job = JobPosting(
                    id=f"ashby_{job_id}",
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
        """Extract company identifier from Ashby URL."""
        # Try to extract from URL pattern
        match = re.search(r"ashbyhq\.com/([^/]+)", url)
        if match:
            return match.group(1)

        return "Unknown"
