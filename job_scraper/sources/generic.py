"""
Generic HTML scraper - fallback for any job posting page.
"""
import re
from typing import List, Optional
from bs4 import BeautifulSoup
from ..schema import JobPosting, normalize_experience_level
from ..utils import html_to_text, extract_skills, make_absolute_url


class GenericScraper:
    """Generic scraper for arbitrary job posting pages."""

    def __init__(self):
        """Initialize generic scraper."""
        self.source = "generic"

    def can_handle(self, url: str) -> bool:
        """
        Generic scraper can handle any URL as fallback.

        Args:
            url: URL to check

        Returns:
            Always True (fallback scraper)
        """
        return True

    def extract_jobs_from_html(
        self, html: str, base_url: str
    ) -> List[JobPosting]:
        """
        Extract job postings from generic HTML using common patterns.

        Args:
            html: Raw HTML content
            base_url: Base URL for resolving relative links

        Returns:
            List of JobPosting objects
        """
        soup = BeautifulSoup(html, "html.parser")
        jobs = []

        # Try multiple common selectors for job listings
        job_containers = (
            # Common class names
            soup.find_all("div", class_=re.compile(r"job|position|opening|vacancy", re.I))
            or soup.find_all("li", class_=re.compile(r"job|position|opening", re.I))
            or soup.find_all("article", class_=re.compile(r"job|position", re.I))
            # Data attributes
            or soup.find_all(attrs={"data-job": True})
            or soup.find_all(attrs={"data-position": True})
            # Semantic tags
            or soup.find_all("article")
        )

        # If we find too many or too few, try different strategy
        if len(job_containers) < 1 or len(job_containers) > 100:
            # Try finding a main container first
            main_container = (
                soup.find("main")
                or soup.find("div", id=re.compile(r"jobs|positions|listings", re.I))
                or soup.find("div", class_=re.compile(r"jobs-list|job-list", re.I))
            )

            if main_container:
                job_containers = (
                    main_container.find_all("div", class_=re.compile(r"job|position", re.I))
                    or main_container.find_all("article")
                    or main_container.find_all("li")
                )

        for element in job_containers[:50]:  # Limit to 50 to avoid parsing entire page
            try:
                job = self._parse_job_element(element, base_url)
                if job and self._is_valid_job(job):
                    jobs.append(job)
            except Exception:
                continue

        return jobs

    def _parse_job_element(
        self, element: any, base_url: str
    ) -> Optional[JobPosting]:
        """
        Parse a single job element using heuristics.

        Args:
            element: BeautifulSoup element
            base_url: Base URL

        Returns:
            JobPosting or None
        """
        # Extract title (usually in h1-h4 or anchor)
        title = self._extract_title(element)
        if not title:
            return None

        # Extract URL
        apply_url = self._extract_url(element, base_url)

        # Extract location
        location = self._extract_location(element)

        # Extract company
        company = self._extract_company(element)

        # Extract description
        description = self._extract_description(element)

        # Extract posted date
        posted_date = self._extract_date(element)

        # Generate unique ID
        job_id = re.sub(r"\W+", "_", f"{company}_{title}_{location}")[:100]

        full_text = f"{title} {description}"
        skills = extract_skills(full_text)
        exp_level = normalize_experience_level(full_text)

        job = JobPosting(
            id=f"generic_{job_id}",
            source=self.source,
            title=title,
            company=company,
            location=location,
            posted_date=posted_date,
            description=description,
            skills=skills,
            experience_level=exp_level,
            apply_url=apply_url,
            raw={"html_snippet": str(element)[:300]},
        )

        return job

    def _extract_title(self, element: any) -> Optional[str]:
        """Extract job title from element."""
        # Try headers
        for tag in ["h1", "h2", "h3", "h4"]:
            header = element.find(tag)
            if header:
                title = header.get_text(strip=True)
                if 10 < len(title) < 150:  # Reasonable title length
                    return title

        # Try anchors with job-related classes
        anchor = element.find("a", class_=re.compile(r"title|job|position", re.I))
        if anchor:
            title = anchor.get_text(strip=True)
            if 10 < len(title) < 150:
                return title

        # Try any anchor
        anchor = element.find("a")
        if anchor:
            title = anchor.get_text(strip=True)
            if 10 < len(title) < 150:
                return title

        return None

    def _extract_url(self, element: any, base_url: str) -> str:
        """Extract apply URL from element."""
        # Find first anchor
        anchor = element.find("a", href=True)
        if anchor:
            href = anchor.get("href", "")
            return make_absolute_url(base_url, href)

        return base_url

    def _extract_location(self, element: any) -> str:
        """Extract location from element."""
        # Try location-specific elements
        location_elem = (
            element.find("span", class_=re.compile(r"location", re.I))
            or element.find("div", class_=re.compile(r"location", re.I))
            or element.find(attrs={"data-location": True})
        )

        if location_elem:
            location = location_elem.get_text(strip=True)
            if location and len(location) < 100:
                return location

        # Try to find location patterns in text
        text = element.get_text()
        location_patterns = [
            r"(?:Location|Office|Based in|City):\s*([A-Z][a-z\s,]+(?:,\s*[A-Z]{2})?)",
            r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?,\s*(?:[A-Z]{2}|Remote))\b",
        ]

        for pattern in location_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()

        return "Unknown"

    def _extract_company(self, element: any) -> str:
        """Extract company name from element."""
        # Try company-specific elements
        company_elem = (
            element.find("span", class_=re.compile(r"company", re.I))
            or element.find("div", class_=re.compile(r"company", re.I))
            or element.find(attrs={"data-company": True})
        )

        if company_elem:
            company = company_elem.get_text(strip=True)
            if company and len(company) < 100:
                return company

        return "Unknown"

    def _extract_description(self, element: any) -> str:
        """Extract job description from element."""
        # Try description-specific elements
        desc_elem = (
            element.find("div", class_=re.compile(r"description|summary", re.I))
            or element.find("p", class_=re.compile(r"description|summary", re.I))
        )

        if desc_elem:
            return html_to_text(str(desc_elem))

        # Fall back to entire element text
        return html_to_text(str(element))

    def _extract_date(self, element: any) -> Optional[str]:
        """Extract posted date from element."""
        # Try time elements
        time_elem = element.find("time")
        if time_elem:
            return time_elem.get("datetime") or time_elem.get_text(strip=True)

        # Try date-related classes
        date_elem = element.find(class_=re.compile(r"date|posted|time", re.I))
        if date_elem:
            date_text = date_elem.get_text(strip=True)
            if date_text and len(date_text) < 50:
                return date_text

        return None

    def _is_valid_job(self, job: JobPosting) -> bool:
        """
        Validate that parsed job has minimum required fields.

        Args:
            job: JobPosting object

        Returns:
            True if job is valid
        """
        # Must have title
        if not job.title or len(job.title) < 10:
            return False

        # Description should have some content
        if not job.description or len(job.description) < 50:
            return False

        # URL should be valid
        if not job.apply_url or "http" not in job.apply_url:
            return False

        return True
