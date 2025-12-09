"""
Enhanced Generic HTML scraper with JSON-LD, JavaScript data, and SPA support.
"""
import re
import json
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
from ..schema import JobPosting, normalize_experience_level
from ..utils import html_to_text, extract_skills, make_absolute_url
import logging

logger = logging.getLogger(__name__)


class GenericScraper:
    """Enhanced generic scraper with JSON-LD and SPA data extraction."""

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
        Extract job postings using hybrid strategy:
        1. JSON-LD structured data
        2. Inline JavaScript variables
        3. SPA hydration data
        4. Static HTML parsing

        Args:
            html: Raw HTML content
            base_url: Base URL for resolving relative links

        Returns:
            List of JobPosting objects
        """
        jobs = []

        # Strategy 1: JSON-LD extraction
        jsonld_jobs = self._extract_jsonld_jobs(html, base_url)
        if jsonld_jobs:
            logger.info(f"Found {len(jsonld_jobs)} jobs via JSON-LD")
            jobs.extend(jsonld_jobs)

        # Strategy 2: Inline JavaScript data
        if not jobs:
            js_jobs = self._extract_javascript_data(html, base_url)
            if js_jobs:
                logger.info(f"Found {len(js_jobs)} jobs via JavaScript data")
                jobs.extend(js_jobs)

        # Strategy 3: SPA hydration data
        if not jobs:
            spa_jobs = self._extract_spa_hydration(html, base_url)
            if spa_jobs:
                logger.info(f"Found {len(spa_jobs)} jobs via SPA hydration")
                jobs.extend(spa_jobs)

        # Strategy 4: Static HTML parsing (fallback)
        if not jobs:
            html_jobs = self._extract_html_jobs(html, base_url)
            if html_jobs:
                logger.info(f"Found {len(html_jobs)} jobs via HTML parsing")
                jobs.extend(html_jobs)

        # Filter and validate
        validated_jobs = [job for job in jobs if self._is_valid_job(job)]
        logger.info(f"Validated {len(validated_jobs)} jobs out of {len(jobs)}")

        return validated_jobs

    def _extract_jsonld_jobs(
        self, html: str, base_url: str
    ) -> List[JobPosting]:
        """Extract jobs from JSON-LD structured data."""
        soup = BeautifulSoup(html, "html.parser")
        jobs = []

        # Find all JSON-LD script tags
        jsonld_scripts = soup.find_all(
            "script", type="application/ld+json"
        )

        for script in jsonld_scripts:
            try:
                data = json.loads(script.string)

                # Handle single object or array
                if isinstance(data, dict):
                    data = [data]
                elif not isinstance(data, list):
                    continue

                for item in data:
                    # Check if it's a JobPosting schema
                    if self._is_job_posting_schema(item):
                        job = self._parse_jsonld_job(item, base_url)
                        if job:
                            jobs.append(job)

            except (json.JSONDecodeError, TypeError, AttributeError) as e:
                logger.debug(f"Failed to parse JSON-LD: {e}")
                continue

        return jobs

    def _is_job_posting_schema(self, data: Dict) -> bool:
        """Check if data is a JobPosting schema.org object."""
        type_val = data.get("@type", "")
        if isinstance(type_val, list):
            return "JobPosting" in type_val
        return type_val == "JobPosting"

    def _parse_jsonld_job(
        self, data: Dict, base_url: str
    ) -> Optional[JobPosting]:
        """Parse a JSON-LD JobPosting object."""
        try:
            # Extract fields according to schema.org JobPosting spec
            title = data.get("title", "") or data.get("name", "")

            # Company
            hiring_org = data.get("hiringOrganization", {})
            company = (
                hiring_org.get("name", "Unknown")
                if isinstance(hiring_org, dict)
                else "Unknown"
            )

            # Location
            job_location = data.get("jobLocation", {})
            if isinstance(job_location, dict):
                address = job_location.get("address", {})
                if isinstance(address, dict):
                    location = (
                        address.get("addressLocality", "")
                        + ", "
                        + address.get("addressRegion", "")
                    )
                else:
                    location = str(job_location.get("name", "Unknown"))
            else:
                location = "Unknown"

            location = location.strip(", ") or "Unknown"

            # Description
            description = data.get("description", "")

            # Date posted
            posted_date = data.get("datePosted")

            # Apply URL
            apply_url = data.get("url", "") or data.get("applicationContact", {}).get(
                "url", base_url
            )

            if not all([title, description]):
                return None

            # Generate ID
            job_id = self._generate_job_id(title, company, location)

            # Extract skills and experience level
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
                description=html_to_text(description),
                skills=skills,
                experience_level=exp_level,
                apply_url=make_absolute_url(base_url, apply_url),
                raw={"jsonld": data},
            )

            return job

        except Exception as e:
            logger.debug(f"Failed to parse JSON-LD job: {e}")
            return None

    def _extract_javascript_data(
        self, html: str, base_url: str
    ) -> List[JobPosting]:
        """Extract jobs from inline JavaScript variables."""
        jobs = []

        # Common JavaScript variable patterns
        patterns = [
            r"window\.__INITIAL_STATE__\s*=\s*({.+?});",
            r"window\.__JOBS__\s*=\s*(\[.+?\]);",
            r"window\.__DATA__\s*=\s*({.+?});",
            r"var\s+jobs\s*=\s*(\[.+?\]);",
            r"const\s+jobs\s*=\s*(\[.+?\]);",
            r"let\s+jobs\s*=\s*(\[.+?\]);",
            r"jobPostings\s*[:=]\s*(\[.+?\])",
            r"positions\s*[:=]\s*(\[.+?\])",
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, html, re.DOTALL | re.MULTILINE)

            for match in matches:
                try:
                    json_str = match.group(1)
                    # Clean up JavaScript (remove trailing commas, etc.)
                    json_str = re.sub(r",\s*}", "}", json_str)
                    json_str = re.sub(r",\s*\]", "]", json_str)

                    data = json.loads(json_str)

                    # Extract jobs from the data structure
                    extracted = self._extract_jobs_from_data(data, base_url)
                    jobs.extend(extracted)

                except (json.JSONDecodeError, AttributeError) as e:
                    logger.debug(f"Failed to parse JavaScript data: {e}")
                    continue

        return jobs

    def _extract_spa_hydration(
        self, html: str, base_url: str
    ) -> List[JobPosting]:
        """Extract jobs from SPA hydration data (React/Next.js/Vue/Angular)."""
        jobs = []

        # Next.js specific
        nextjs_pattern = r'<script\s+id="__NEXT_DATA__"[^>]*>(.+?)</script>'
        matches = re.finditer(nextjs_pattern, html, re.DOTALL)

        for match in matches:
            try:
                data = json.loads(match.group(1))

                # Navigate through Next.js data structure
                page_props = data.get("props", {}).get("pageProps", {})
                jobs_data = (
                    page_props.get("jobs", [])
                    or page_props.get("positions", [])
                    or page_props.get("listings", [])
                )

                extracted = self._extract_jobs_from_data(jobs_data, base_url)
                jobs.extend(extracted)

            except (json.JSONDecodeError, KeyError) as e:
                logger.debug(f"Failed to parse Next.js data: {e}")
                continue

        # React/Vue hydration in script tags
        script_patterns = [
            r'window\.__INITIAL_DATA__\s*=\s*({.+?})\s*;',
            r'window\.__APP_STATE__\s*=\s*({.+?})\s*;',
        ]

        for pattern in script_patterns:
            matches = re.finditer(pattern, html, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match.group(1))
                    extracted = self._extract_jobs_from_data(data, base_url)
                    jobs.extend(extracted)
                except (json.JSONDecodeError, KeyError):
                    continue

        return jobs

    def _extract_jobs_from_data(
        self, data: Any, base_url: str
    ) -> List[JobPosting]:
        """Recursively extract job postings from nested data structures."""
        jobs = []

        if isinstance(data, dict):
            # Check if this dict is a job posting
            if self._looks_like_job(data):
                job = self._parse_data_job(data, base_url)
                if job:
                    jobs.append(job)
            else:
                # Recursively search nested dicts
                for value in data.values():
                    jobs.extend(self._extract_jobs_from_data(value, base_url))

        elif isinstance(data, list):
            # Check if this is a list of jobs
            if data and all(self._looks_like_job(item) for item in data[:3]):
                for item in data:
                    job = self._parse_data_job(item, base_url)
                    if job:
                        jobs.append(job)
            else:
                # Recursively search list items
                for item in data:
                    jobs.extend(self._extract_jobs_from_data(item, base_url))

        return jobs

    def _looks_like_job(self, data: Any) -> bool:
        """Check if data structure looks like a job posting."""
        if not isinstance(data, dict):
            return False

        # Check for common job fields
        job_indicators = [
            "title",
            "job_title",
            "jobTitle",
            "position",
            "role",
        ]

        description_indicators = [
            "description",
            "job_description",
            "jobDescription",
            "summary",
        ]

        has_title = any(key in data for key in job_indicators)
        has_description = any(key in data for key in description_indicators)

        return has_title and (has_description or "company" in data or "location" in data)

    def _parse_data_job(
        self, data: Dict, base_url: str
    ) -> Optional[JobPosting]:
        """Parse a job from extracted data structure."""
        try:
            # Extract title (try multiple field names)
            title = (
                data.get("title")
                or data.get("job_title")
                or data.get("jobTitle")
                or data.get("position")
                or data.get("role")
                or ""
            )

            # Extract company
            company = (
                data.get("company")
                or data.get("company_name")
                or data.get("companyName")
                or data.get("employer")
                or "Unknown"
            )

            # Extract location
            location = (
                data.get("location")
                or data.get("job_location")
                or data.get("jobLocation")
                or data.get("city")
                or "Unknown"
            )

            # Extract description
            description = (
                data.get("description")
                or data.get("job_description")
                or data.get("jobDescription")
                or data.get("summary")
                or ""
            )

            # Extract URL
            apply_url = (
                data.get("url")
                or data.get("apply_url")
                or data.get("applyUrl")
                or data.get("link")
                or base_url
            )

            # Posted date
            posted_date = (
                data.get("posted_date")
                or data.get("postedDate")
                or data.get("created_at")
                or data.get("createdAt")
            )

            # Skills
            skills_data = data.get("skills", []) or data.get("required_skills", [])
            if isinstance(skills_data, list):
                extracted_skills = skills_data
            else:
                extracted_skills = []

            if not all([title, description]):
                return None

            # Generate ID
            job_id = self._generate_job_id(title, company, location)

            # Extract additional skills from text
            full_text = f"{title} {description}"
            text_skills = extract_skills(full_text)
            all_skills = list(set(extracted_skills + text_skills))

            exp_level = normalize_experience_level(full_text)

            job = JobPosting(
                id=f"generic_{job_id}",
                source=self.source,
                title=title,
                company=company if isinstance(company, str) else str(company),
                location=location if isinstance(location, str) else str(location),
                posted_date=posted_date,
                description=html_to_text(description) if description else "",
                skills=all_skills,
                experience_level=exp_level,
                apply_url=make_absolute_url(base_url, apply_url),
                raw={"data": data},
            )

            return job

        except Exception as e:
            logger.debug(f"Failed to parse data job: {e}")
            return None

    def _extract_html_jobs(
        self, html: str, base_url: str
    ) -> List[JobPosting]:
        """Extract jobs from static HTML (original implementation)."""
        soup = BeautifulSoup(html, "html.parser")
        jobs = []

        # Try multiple common selectors
        job_containers = (
            soup.find_all("div", class_=re.compile(r"job|position|opening|vacancy", re.I))
            or soup.find_all("li", class_=re.compile(r"job|position|opening", re.I))
            or soup.find_all("article", class_=re.compile(r"job|position", re.I))
            or soup.find_all(attrs={"data-job": True})
            or soup.find_all(attrs={"data-position": True})
            or soup.find_all("article")
        )

        # If we find too many or too few, try different strategy
        if len(job_containers) < 1 or len(job_containers) > 100:
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

        for element in job_containers[:50]:
            try:
                job = self._parse_job_element(element, base_url)
                if job:
                    jobs.append(job)
            except Exception:
                continue

        return jobs

    def _parse_job_element(
        self, element: Any, base_url: str
    ) -> Optional[JobPosting]:
        """Parse a single job element from HTML."""
        # Extract title
        title = self._extract_title(element)
        if not title:
            return None

        # Extract other fields
        apply_url = self._extract_url(element, base_url)
        location = self._extract_location(element)
        company = self._extract_company(element)
        description = self._extract_description(element)
        posted_date = self._extract_date(element)

        # Generate ID
        job_id = self._generate_job_id(title, company, location)

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

    def _extract_title(self, element: Any) -> Optional[str]:
        """Extract job title from element."""
        for tag in ["h1", "h2", "h3", "h4"]:
            header = element.find(tag)
            if header:
                title = header.get_text(strip=True)
                if 10 < len(title) < 150:
                    return title

        anchor = element.find("a", class_=re.compile(r"title|job|position", re.I))
        if anchor:
            title = anchor.get_text(strip=True)
            if 10 < len(title) < 150:
                return title

        anchor = element.find("a")
        if anchor:
            title = anchor.get_text(strip=True)
            if 10 < len(title) < 150:
                return title

        return None

    def _extract_url(self, element: Any, base_url: str) -> str:
        """Extract apply URL from element."""
        anchor = element.find("a", href=True)
        if anchor:
            href = anchor.get("href", "")
            return make_absolute_url(base_url, href)
        return base_url

    def _extract_location(self, element: Any) -> str:
        """Extract location from element."""
        location_elem = (
            element.find("span", class_=re.compile(r"location", re.I))
            or element.find("div", class_=re.compile(r"location", re.I))
            or element.find(attrs={"data-location": True})
        )

        if location_elem:
            location = location_elem.get_text(strip=True)
            if location and len(location) < 100:
                return location

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

    def _extract_company(self, element: Any) -> str:
        """Extract company name from element."""
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

    def _extract_description(self, element: Any) -> str:
        """Extract job description from element."""
        desc_elem = (
            element.find("div", class_=re.compile(r"description|summary", re.I))
            or element.find("p", class_=re.compile(r"description|summary", re.I))
        )

        if desc_elem:
            return html_to_text(str(desc_elem))

        return html_to_text(str(element))

    def _extract_date(self, element: Any) -> Optional[str]:
        """Extract posted date from element."""
        time_elem = element.find("time")
        if time_elem:
            return time_elem.get("datetime") or time_elem.get_text(strip=True)

        date_elem = element.find(class_=re.compile(r"date|posted|time", re.I))
        if date_elem:
            date_text = date_elem.get_text(strip=True)
            if date_text and len(date_text) < 50:
                return date_text

        return None

    def _generate_job_id(self, title: str, company: str, location: str) -> str:
        """Generate a stable job ID from key fields."""
        combined = f"{company}_{title}_{location}".lower()
        # Remove special characters and limit length
        job_id = re.sub(r"\W+", "_", combined)[:100]
        return job_id

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

        # Title shouldn't be too generic
        generic_titles = ["job", "position", "opening", "vacancy", "career"]
        if job.title.lower().strip() in generic_titles:
            return False

        return True
