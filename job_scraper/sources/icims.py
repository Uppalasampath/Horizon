"""
iCIMS ATS scraper - handles iCIMS career portals.
"""
import re
import json
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from ..schema import JobPosting, normalize_experience_level
from ..utils import html_to_text, extract_skills, make_absolute_url
import logging

logger = logging.getLogger(__name__)


class ICIMSScraper:
    """Scraper for iCIMS ATS career portals."""

    def __init__(self):
        """Initialize iCIMS scraper."""
        self.source = "icims"

    def can_handle(self, url: str) -> bool:
        """Check if this scraper can handle the given URL."""
        return (
            "icims.com" in url
            or "icimsxr.com" in url
            or "/icims/" in url.lower()
            or "careerportal" in url.lower()
        )

    def extract_jobs_from_html(
        self, html: str, base_url: str
    ) -> List[JobPosting]:
        """Extract job postings from iCIMS HTML page."""
        jobs = []

        # Try to find embedded JSON data
        try:
            soup = BeautifulSoup(html, "html.parser")
            scripts = soup.find_all("script")

            for script in scripts:
                if not script.string:
                    continue

                # Look for iCIMS job data
                if "iCIMS" in script.string or "jobs" in script.string:
                    # Try to extract JSON arrays
                    json_match = re.search(
                        r"(?:jobs|postings|openings)\s*[:=]\s*(\[.+?\])",
                        script.string,
                        re.DOTALL
                    )

                    if json_match:
                        json_str = json_match.group(1)
                        # Clean up
                        json_str = re.sub(r",\s*}", "}", json_str)
                        json_str = re.sub(r",\s*\]", "]", json_str)

                        try:
                            data = json.loads(json_str)
                            jobs.extend(self._parse_json_jobs(data, base_url))
                        except json.JSONDecodeError:
                            pass

        except Exception as e:
            logger.debug(f"Failed to parse iCIMS JSON: {e}")

        # Fallback to HTML parsing
        if not jobs:
            jobs = self._parse_html_jobs(html, base_url)

        return jobs

    def _parse_json_jobs(
        self, data: List[Dict], base_url: str
    ) -> List[JobPosting]:
        """Parse jobs from JSON data."""
        jobs = []

        if not isinstance(data, list):
            data = [data]

        for job_data in data:
            try:
                job = self._parse_job_data(job_data, base_url)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug(f"Failed to parse iCIMS job: {e}")
                continue

        return jobs

    def _parse_job_data(
        self, data: Dict, base_url: str
    ) -> Optional[JobPosting]:
        """Parse a single iCIMS job object."""
        try:
            # Extract job ID
            job_id = str(
                data.get("id")
                or data.get("jobId")
                or data.get("requisitionId")
                or data.get("jobnumber")
                or ""
            )

            # Extract title
            title = (
                data.get("title")
                or data.get("jobTitle")
                or data.get("positionTitle")
                or ""
            )

            # Extract location
            location = (
                data.get("location")
                or data.get("jobLocation")
                or data.get("city")
                or "Unknown"
            )

            # Handle nested location
            if isinstance(location, dict):
                city = location.get("city", "")
                state = location.get("state", "")
                location = f"{city}, {state}".strip(", ") or "Unknown"

            # Extract company
            company = data.get("company") or data.get("companyName") or "Unknown"

            # Extract department
            department = data.get("department") or data.get("jobCategory") or ""

            # Extract description
            description = (
                data.get("description")
                or data.get("jobDescription")
                or data.get("summary")
                or ""
            )

            # Extract application URL
            apply_url = (
                data.get("applyUrl")
                or data.get("jobUrl")
                or data.get("url")
                or base_url
            )

            # Extract posted date
            posted_date = (
                data.get("postedDate")
                or data.get("postingDate")
                or data.get("datePosted")
            )

            # Extract employment type
            employment_type = (
                data.get("employmentType")
                or data.get("jobType")
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
                id=f"icims_{job_id}",
                source=self.source,
                title=title,
                company=company,
                location=location,
                posted_date=posted_date,
                description=desc_text,
                skills=skills,
                experience_level=exp_level,
                apply_url=make_absolute_url(base_url, apply_url),
                raw={"icims_data": data},
            )

            return job

        except Exception as e:
            logger.debug(f"Failed to parse iCIMS job data: {e}")
            return None

    def _parse_html_jobs(
        self, html: str, base_url: str
    ) -> List[JobPosting]:
        """Fallback HTML parsing for iCIMS pages."""
        soup = BeautifulSoup(html, "html.parser")
        jobs = []

        # iCIMS often uses tables or specific div structures
        job_elements = (
            soup.find_all("tr", class_=re.compile(r"job|row", re.I))
            or soup.find_all("div", class_=re.compile(r"job|posting|position", re.I))
            or soup.find_all("li", class_=re.compile(r"job|position", re.I))
        )

        # Also try to find job containers
        job_table = soup.find("table", class_=re.compile(r"job|search", re.I))
        if job_table:
            job_elements = job_table.find_all("tr")[1:]  # Skip header row

        for element in job_elements[:50]:
            try:
                # Extract title (can be in different structures)
                title_elem = (
                    element.find("a", class_=re.compile(r"title|job", re.I))
                    or element.find(["h2", "h3", "h4"])
                    or element.find("a", href=re.compile(r"job|position", re.I))
                    or element.find("a")
                )

                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                if len(title) < 10:
                    continue

                # Extract URL
                if title_elem.name == "a":
                    apply_url = make_absolute_url(base_url, title_elem.get("href", ""))
                else:
                    link = element.find("a", href=True)
                    apply_url = (
                        make_absolute_url(base_url, link.get("href"))
                        if link
                        else base_url
                    )

                # Extract location (can be in td or span)
                location_elem = (
                    element.find("td", class_=re.compile(r"location", re.I))
                    or element.find("span", class_=re.compile(r"location", re.I))
                    or element.find("div", class_=re.compile(r"location", re.I))
                )

                location = (
                    location_elem.get_text(strip=True)
                    if location_elem
                    else "Unknown"
                )

                # Extract department/category
                dept_elem = (
                    element.find("td", class_=re.compile(r"category|department", re.I))
                    or element.find("span", class_=re.compile(r"category|department", re.I))
                )

                department = (
                    dept_elem.get_text(strip=True)
                    if dept_elem
                    else ""
                )

                # Extract date
                date_elem = (
                    element.find("td", class_=re.compile(r"date|posted", re.I))
                    or element.find("span", class_=re.compile(r"date|posted", re.I))
                )

                posted_date = (
                    date_elem.get_text(strip=True)
                    if date_elem
                    else None
                )

                # Extract description
                description = element.get_text(separator=" ", strip=True)

                # Generate ID from URL or title
                job_id = re.sub(r"\W+", "_", apply_url.split("/")[-1] or title)[:100]

                # Extract skills and experience
                full_text = f"{title} {description} {department}"
                skills = extract_skills(full_text)
                exp_level = normalize_experience_level(full_text)

                job = JobPosting(
                    id=f"icims_{job_id}",
                    source=self.source,
                    title=title,
                    company="Unknown",  # Usually not in list view
                    location=location,
                    posted_date=posted_date,
                    description=html_to_text(description),
                    skills=skills,
                    experience_level=exp_level,
                    apply_url=apply_url,
                    raw={"html": str(element)[:300]},
                )

                jobs.append(job)

            except Exception as e:
                logger.debug(f"Failed to parse iCIMS HTML job: {e}")
                continue

        return jobs
