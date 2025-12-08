"""
Lever ATS scraper - handles Lever job boards.
"""
import re
import json
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from ..schema import JobPosting, normalize_experience_level
from ..utils import html_to_text, extract_skills, make_absolute_url


class LeverScraper:
    """Scraper for Lever ATS job boards."""

    def __init__(self):
        """Initialize Lever scraper."""
        self.source = "lever"

    def can_handle(self, url: str) -> bool:
        """
        Check if this scraper can handle the given URL.

        Args:
            url: URL to check

        Returns:
            True if URL is a Lever board
        """
        return "lever.co" in url or "jobs.lever.co" in url

    def extract_jobs_from_html(
        self, html: str, base_url: str
    ) -> List[JobPosting]:
        """
        Extract job postings from Lever HTML page.

        Lever often embeds JSON data in script tags.

        Args:
            html: Raw HTML content
            base_url: Base URL for resolving relative links

        Returns:
            List of JobPosting objects
        """
        soup = BeautifulSoup(html, "html.parser")
        jobs = []

        # Lever commonly has JSON data in script tags
        scripts = soup.find_all("script")
        for script in scripts:
            if script.string and "postings" in script.string:
                try:
                    # Extract JSON from JavaScript variable
                    json_match = re.search(
                        r"(?:postings|jobs)\s*[=:]\s*(\[.*?\]);?",
                        script.string,
                        re.DOTALL
                    )
                    if json_match:
                        json_str = json_match.group(1)
                        data = json.loads(json_str)
                        if isinstance(data, list):
                            jobs.extend(self._parse_json_jobs(data, base_url))
                            return jobs
                except (json.JSONDecodeError, AttributeError):
                    continue

        # Fallback to HTML parsing
        posting_elements = soup.find_all(
            "div", class_=re.compile(r"posting|position")
        )

        for element in posting_elements:
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
                job_id = str(job_data.get("id", ""))
                title = job_data.get("text", "") or job_data.get("title", "")

                # Lever structure
                categories = job_data.get("categories", {})
                location = categories.get("location", "Unknown") if isinstance(
                    categories, dict
                ) else "Unknown"

                description = job_data.get("description", "") or job_data.get(
                    "descriptionPlain", ""
                )
                description_html = job_data.get("descriptionHtml", description)

                # Company
                company = "Unknown"
                if "team" in categories and isinstance(categories, dict):
                    company = categories.get("team", "Unknown")

                # Apply URL
                apply_url = job_data.get("hostedUrl", "") or job_data.get(
                    "applyUrl", ""
                )

                # Posted date
                created_at = job_data.get("createdAt")

                if not all([job_id, title]):
                    continue

                full_text = f"{title} {description}"
                skills = extract_skills(full_text)
                exp_level = normalize_experience_level(full_text)

                job = JobPosting(
                    id=f"lever_{job_id}",
                    source=self.source,
                    title=title,
                    company=company,
                    location=location,
                    posted_date=created_at,
                    description=html_to_text(description_html),
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
            title_elem = element.find("h5") or element.find("a", class_="posting-title")
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
                "span", class_=re.compile(r"location")
            ) or element.find("div", class_=re.compile(r"location"))
            location = location_elem.get_text(strip=True) if location_elem else "Unknown"

            # Extract categories (commitment, team, etc.)
            categories = []
            category_elements = element.find_all(
                "span", class_=re.compile(r"posting-category")
            )
            for cat in category_elements:
                categories.append(cat.get_text(strip=True))

            company = categories[0] if categories else "Unknown"

            # Description
            description_elem = element.find(
                "div", class_=re.compile(r"description")
            )
            description = (
                description_elem.get_text(separator=" ", strip=True)
                if description_elem
                else element.get_text(separator=" ", strip=True)
            )

            full_text = f"{title} {description}"
            skills = extract_skills(full_text)
            exp_level = normalize_experience_level(full_text)

            # Generate unique ID
            job_id = re.sub(r"\W+", "_", apply_url.split("/")[-1] or title)

            job = JobPosting(
                id=f"lever_{job_id}",
                source=self.source,
                title=title,
                company=company,
                location=location,
                posted_date=None,
                description=html_to_text(description),
                skills=skills,
                experience_level=exp_level,
                apply_url=apply_url,
                raw={"html": str(element)[:500], "categories": categories},
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
                        "div", class_=re.compile(r"posting-description")
                    ) or soup.find("div", class_=re.compile(r"content"))

                    if desc_elem:
                        return desc_elem.get_text(separator="\n", strip=True)

        except Exception:
            pass

        return None
