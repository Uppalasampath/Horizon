"""
Unit tests for job scraper using sample HTML fixtures.
"""
import pytest
from pathlib import Path
from job_scraper.sources import (
    GreenhouseScraper,
    LeverScraper,
    WorkdayScraper,
    GenericScraper,
)
from job_scraper.schema import JobPosting, normalize_experience_level
from job_scraper.utils import extract_skills, html_to_text
from job_scraper.core import deduplicate_jobs


# Sample HTML fixtures
GREENHOUSE_HTML = """
<html>
<body>
    <div class="opening">
        <h3><a href="/jobs/12345">Junior Software Engineer</a></h3>
        <span class="location">San Francisco, CA</span>
        <div class="content">
            We're looking for a junior engineer with Python and Django experience.
            Entry level position for recent graduates.
        </div>
    </div>
</body>
</html>
"""

LEVER_HTML = """
<html>
<body>
    <div class="posting">
        <h5 class="posting-title">
            <a href="/jobs/67890">Entry Level Backend Developer</a>
        </h5>
        <span class="location">Remote</span>
        <div class="posting-description">
            Looking for entry level backend developer. Requirements: Python, SQL, REST APIs.
            Recent graduates encouraged to apply.
        </div>
    </div>
</body>
</html>
"""

WORKDAY_HTML = """
<html>
<body>
    <li class="job-item">
        <h3><a data-automation-id="jobTitle" href="/job/11111">Associate Software Engineer</a></h3>
        <dd data-automation-id="location">New York, NY</dd>
        <dd data-automation-id="postedOn">2025-12-01</dd>
        <div>Java, Spring Boot, entry level position for new graduates</div>
    </li>
</body>
</html>
"""

GENERIC_HTML = """
<html>
<body>
    <article class="job-posting">
        <h2>Junior Frontend Developer</h2>
        <span class="company">TechStartup</span>
        <span class="location">Austin, TX</span>
        <p class="description">
            We're seeking a junior frontend developer with React and JavaScript experience.
            This is an entry level role perfect for recent bootcamp graduates or CS majors.
            Skills needed: React, JavaScript, HTML, CSS, Git.
        </p>
        <a href="https://techstartup.com/jobs/apply/123">Apply Now</a>
    </article>
</body>
</html>
"""


class TestScrapers:
    """Test individual ATS scrapers."""

    def test_greenhouse_scraper(self):
        """Test Greenhouse scraper with sample HTML."""
        scraper = GreenhouseScraper()
        jobs = scraper.extract_jobs_from_html(GREENHOUSE_HTML, "https://boards.greenhouse.io")

        assert len(jobs) > 0
        job = jobs[0]

        assert isinstance(job, JobPosting)
        assert "Junior" in job.title or "junior" in job.title.lower()
        assert job.source == "greenhouse"
        assert len(job.skills) > 0
        assert "Python" in job.skills or "Django" in job.skills

    def test_lever_scraper(self):
        """Test Lever scraper with sample HTML."""
        scraper = LeverScraper()
        jobs = scraper.extract_jobs_from_html(LEVER_HTML, "https://jobs.lever.co")

        assert len(jobs) > 0
        job = jobs[0]

        assert isinstance(job, JobPosting)
        assert "Entry" in job.title or "entry" in job.title.lower()
        assert job.source == "lever"
        assert len(job.skills) > 0

    def test_workday_scraper(self):
        """Test Workday scraper with sample HTML."""
        scraper = WorkdayScraper()
        jobs = scraper.extract_jobs_from_html(WORKDAY_HTML, "https://company.wd1.myworkdayjobs.com")

        assert len(jobs) > 0
        job = jobs[0]

        assert isinstance(job, JobPosting)
        assert "Associate" in job.title or "Software" in job.title
        assert job.source == "workday"
        assert job.location == "New York, NY"

    def test_generic_scraper(self):
        """Test generic scraper with sample HTML."""
        scraper = GenericScraper()
        jobs = scraper.extract_jobs_from_html(GENERIC_HTML, "https://techstartup.com")

        assert len(jobs) > 0
        job = jobs[0]

        assert isinstance(job, JobPosting)
        assert "Junior" in job.title or "Developer" in job.title
        assert job.source == "generic"
        assert job.company == "TechStartup"
        assert job.location == "Austin, TX"
        assert len(job.skills) > 0


class TestUtils:
    """Test utility functions."""

    def test_extract_skills(self):
        """Test skill extraction from text."""
        text = "We need Python, Django, React, and PostgreSQL experience"
        skills = extract_skills(text)

        assert "Python" in skills
        assert "Django" in skills
        assert "React" in skills
        assert "PostgreSQL" in skills

    def test_html_to_text(self):
        """Test HTML to text conversion."""
        html = "<div>Hello <b>World</b><script>alert('test')</script></div>"
        text = html_to_text(html)

        assert "Hello World" in text
        assert "script" not in text
        assert "alert" not in text

    def test_normalize_experience_level_entry(self):
        """Test experience level detection - entry level."""
        text = "Looking for entry level junior engineer recent graduate"
        level = normalize_experience_level(text)
        assert level == "entry"

    def test_normalize_experience_level_senior(self):
        """Test experience level detection - senior level."""
        text = "Seeking senior engineer with 7+ years experience"
        level = normalize_experience_level(text)
        assert level == "senior"

    def test_normalize_experience_level_mid(self):
        """Test experience level detection - mid level."""
        text = "Mid level engineer with 3-5 years experience"
        level = normalize_experience_level(text)
        assert level == "mid"


class TestDeduplication:
    """Test job deduplication."""

    def test_deduplicate_jobs(self):
        """Test deduplication removes duplicate IDs."""
        jobs = [
            JobPosting(
                id="job_1",
                source="generic",
                title="Engineer",
                company="Company A",
                location="NYC",
                description="Description 1",
                apply_url="https://example.com/1"
            ),
            JobPosting(
                id="job_1",  # Duplicate
                source="generic",
                title="Engineer",
                company="Company A",
                location="NYC",
                description="Description 1",
                apply_url="https://example.com/1"
            ),
            JobPosting(
                id="job_2",
                source="generic",
                title="Developer",
                company="Company B",
                location="SF",
                description="Description 2",
                apply_url="https://example.com/2"
            ),
        ]

        unique_jobs = deduplicate_jobs(jobs)
        assert len(unique_jobs) == 2
        assert unique_jobs[0].id == "job_1"
        assert unique_jobs[1].id == "job_2"


class TestSchema:
    """Test JobPosting schema validation."""

    def test_job_posting_validation(self):
        """Test JobPosting model validation."""
        job = JobPosting(
            id="test_123",
            source="greenhouse",
            title="Software Engineer",
            company="TestCo",
            location="Remote",
            description="Test description with Python and JavaScript",
            skills=["Python", "JavaScript"],
            experience_level="entry",
            apply_url="https://example.com/apply"
        )

        assert job.id == "test_123"
        assert job.source == "greenhouse"
        assert job.title == "Software Engineer"
        assert len(job.skills) == 2

    def test_job_posting_json_serialization(self):
        """Test JSON serialization."""
        job = JobPosting(
            id="test_456",
            source="lever",
            title="Engineer",
            company="Corp",
            location="NYC",
            description="Description",
            apply_url="https://example.com"
        )

        json_str = job.model_dump_json()
        assert "test_456" in json_str
        assert "lever" in json_str


def test_entry_level_filtering():
    """
    Test that we can correctly identify and filter entry-level positions.
    """
    test_jobs = [
        ("Junior Software Engineer - Recent Grads", "entry"),
        ("Senior Staff Engineer - 10+ years", "senior"),
        ("Entry Level Backend Developer", "entry"),
        ("Mid-Level Full Stack Engineer", "mid"),
        ("Software Engineer Intern", "entry"),
        ("Principal Architect", "senior"),
    ]

    for title, expected_level in test_jobs:
        detected_level = normalize_experience_level(title)
        assert detected_level == expected_level, f"Failed for: {title}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
