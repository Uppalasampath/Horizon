"""
SmartRecruiters ATS scraper - uses SmartRecruiters API.
"""
import re
import json
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from ..schema import JobPosting, normalize_experience_level
from ..utils import html_to_text, extract_skills, make_absolute_url
import logging

logger = logging.getLogger(__name__)


class SmartRecruitersScraper:
    """Scraper for SmartRecruiters ATS."""

    def __init__(self):
        """Initialize SmartRecruiters scraper."""
        self.source = "smartrecruiters"

    def can_handle(self, url: str) -> bool:
        """Check if this scraper can handle the given URL."""
        return "smartrecruiters.com" in url

    async def fetch_jobs_api(
        self, company: str, session: Any
    ) -> List[JobPosting]:
        """
        Fetch jobs from SmartRecruiters API.

        Args:
            company: Company identifier
            session: aiohttp ClientSession

        Returns:
            List of JobPosting objects
        """
        api_url = f"https://api.smartrecruiters.com/v1/companies/{company}/postings"

        try:
            async with session.get(api_url, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_api_response(data, company)
                else:
                    logger.warning(
                        f"SmartRecruiters API returned status {response.status}"
                    )
                    return []

        except Exception as e:
            logger.error(f"Error fetching SmartRecruiters API: {e}")
            return []

    def extract_jobs_from_html(
        self, html: str, base_url: str
    ) -> List[JobPosting]:
        """Extract job postings from SmartRecruiters HTML page."""
        jobs = []

        # Try to find embedded JSON data
        try:
            soup = BeautifulSoup(html, "html.parser")
            scripts = soup.find_all("script")

            for script in scripts:
                if not script.string:
                    continue

                # Look for SmartRecruiters data
                if "postings" in script.string or "smartrecruiters" in script.string.lower():
                    json_match = re.search(
                        r"postings\s*[:=]\s*(\[.+?\])",
                        script.string,
                        re.DOTALL
                    )

                    if json_match:
                        json_str = json_match.group(1)
                        json_str = re.sub(r",\s*}", "}", json_str)
                        json_str = re.sub(r",\s*\]", "]", json_str)

                        data = json.loads(json_str)
                        company = self._extract_company_from_url(base_url)
                        jobs.extend(self._parse_api_response({"content": data}, company))

        except (json.JSONDecodeError, AttributeError) as e:
            logger.debug(f"Failed to parse SmartRecruiters JSON: {e}")

        # Fallback to HTML parsing
        if not jobs:
            jobs = self._parse_html_jobs(html, base_url)

        return jobs

    def _parse_api_response(
        self, data: Dict, company: str
    ) -> List[JobPosting]:
        """Parse SmartRecruiters API response."""
        jobs = []

        # Extract postings from response
        postings = data.get("content", []) or data.get("postings", [])

        for posting in postings:
            try:
                job = self._parse_posting_data(posting, company)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug(f"Failed to parse SmartRecruiters posting: {e}")
                continue

        return jobs

    def _parse_posting_data(
        self, data: Dict, company: str
    ) -> Optional[JobPosting]:
        """Parse a single SmartRecruiters posting."""
        try:
            # Extract job ID
            job_id = str(data.get("id") or data.get("refNumber") or "")

            # Extract title
            title = data.get("name") or data.get("title") or ""

            # Extract location
            location_data = data.get("location", {})
            if isinstance(location_data, dict):
                city = location_data.get("city", "")
                country = location_data.get("country", "")
                location = f"{city}, {country}".strip(", ") or "Unknown"
            else:
                location = str(location_data)

            # Extract department
            department = (
                data.get("department", {}).get("label")
                if isinstance(data.get("department"), dict)
                else data.get("department") or ""
            )

            # Extract description
            description = (
                data.get("jobAd", {}).get("sections", {}).get("jobDescription", {}).get("text", "")
                or data.get("description")
                or ""
            )

            # Extract application URL
            apply_url = (
                data.get("applyUrl")
                or data.get("postingUrl")
                or data.get("ref")
            )

            # Extract posted date
            posted_date = (
                data.get("releasedDate")
                or data.get("postingDate")
                or data.get("createdOn")
            )

            # Extract employment type
            employment_type = (
                data.get("typeOfEmployment", {}).get("label")
                if isinstance(data.get("typeOfEmployment"), dict)
                else data.get("employmentType") or ""
            )

            if not all([job_id, title]):
                return None

            # Process description
            desc_text = html_to_text(description) if description else ""

            # Extract skills and experience level
            full_text = f"{title} {desc_text} {department} {employment_type}"
            skills = extract_skills(full_text)
            exp_level = normalize_experience_level(full_text)

            # Build company name
            company_name = (
                data.get("company", {}).get("name")
                if isinstance(data.get("company"), dict)
                else company or "Unknown"
            )

            job = JobPosting(
                id=f"smartrecruiters_{job_id}",
                source=self.source,
                title=title,
                company=company_name,
                location=location,
                posted_date=posted_date,
                description=desc_text,
                skills=skills,
                experience_level=exp_level,
                apply_url=apply_url or f"https://jobs.smartrecruiters.com/{company}/{job_id}",
                raw={"smartrecruiters_data": data},
            )

            return job

        except Exception as e:
            logger.debug(f"Failed to parse SmartRecruiters posting data: {e}")
            return None

    def _parse_html_jobs(
        self, html: str, base_url: str
    ) -> List[JobPosting]:
        """Fallback HTML parsing for SmartRecruiters pages."""
        soup = BeautifulSoup(html, "html.parser")
        jobs = []

        # Common SmartRecruiters HTML patterns
        job_elements = (
            soup.find_all("li", class_=re.compile(r"job|opening", re.I))
            or soup.find_all("div", class_=re.compile(r"job|posting", re.I))
        )

        company = self._extract_company_from_url(base_url)

        for element in job_elements[:50]:
            try:
                # Extract title
                title_elem = element.find(["h3", "h4", "a"])
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

                # Extract description
                description = element.get_text(separator=" ", strip=True)

                # Generate ID
                job_id = re.sub(r"\W+", "_", apply_url.split("/")[-1] or title)[:100]

                # Extract skills and experience
                full_text = f"{title} {description}"
                skills = extract_skills(full_text)
                exp_level = normalize_experience_level(full_text)

                job = JobPosting(
                    id=f"smartrecruiters_{job_id}",
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
        """Extract company identifier from SmartRecruiters URL."""
        match = re.search(r"smartrecruiters\.com/([^/]+)", url)
        if match:
            return match.group(1)
        return "Unknown"
