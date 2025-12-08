"""
Utility functions for job scraping - HTML processing, skill extraction, text cleaning.
"""
import re
from typing import List, Set
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup


def html_to_text(html: str) -> str:
    """
    Convert HTML to clean plain text.

    Args:
        html: Raw HTML string

    Returns:
        Clean text with normalized whitespace
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()

    # Get text
    text = soup.get_text(separator=" ", strip=True)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def extract_skills(text: str) -> List[str]:
    """
    Extract common tech skills from text using pattern matching.

    Args:
        text: Job description or title text

    Returns:
        List of detected skills/technologies
    """
    # Common tech skills and technologies
    skill_patterns = {
        # Programming languages
        "Python", "Java", "JavaScript", "TypeScript", "Go", "Golang",
        "Ruby", "PHP", "C\\+\\+", "C#", "Swift", "Kotlin", "Rust",
        "Scala", "R", "SQL", "Bash", "Shell",

        # Web frameworks
        "React", "Angular", "Vue\\.js", "Node\\.js", "Express",
        "Django", "Flask", "FastAPI", "Spring", "Rails",
        "Laravel", "ASP\\.NET", "Next\\.js",

        # Databases
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
        "Cassandra", "DynamoDB", "Oracle", "SQL Server",

        # Cloud & DevOps
        "AWS", "Azure", "GCP", "Google Cloud", "Docker", "Kubernetes",
        "Jenkins", "CircleCI", "GitLab CI", "Terraform", "Ansible",

        # Data & ML
        "TensorFlow", "PyTorch", "Scikit-learn", "Pandas", "NumPy",
        "Spark", "Hadoop", "Kafka", "Airflow",

        # Other
        "REST", "GraphQL", "Git", "CI/CD", "Microservices",
        "Linux", "Unix", "Agile", "Scrum"
    }

    found_skills: Set[str] = set()

    for skill in skill_patterns:
        # Case-insensitive pattern matching with word boundaries
        pattern = r"\b" + skill + r"\b"
        if re.search(pattern, text, re.IGNORECASE):
            # Normalize the matched skill
            found_skills.add(skill.replace("\\", "").replace(".", ""))

    return sorted(list(found_skills))


def clean_text(text: str) -> str:
    """
    Clean and normalize text content.

    Args:
        text: Raw text

    Returns:
        Cleaned text
    """
    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text)

    # Remove special characters but keep basic punctuation
    text = re.sub(r"[^\w\s.,;:!?()-]", "", text)

    return text.strip()


def extract_date_from_text(text: str) -> str:
    """
    Extract and normalize date from text.

    Args:
        text: Text containing date information

    Returns:
        ISO 8601 date string or empty string
    """
    # Common date patterns
    patterns = [
        r"\d{4}-\d{2}-\d{2}",  # ISO format
        r"\d{2}/\d{2}/\d{4}",  # MM/DD/YYYY
        r"\d{1,2}\s+(?:days?|weeks?|months?)\s+ago",  # Relative dates
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(0)
            # For relative dates, could compute actual date
            # For simplicity, return as-is or empty
            if "ago" in date_str.lower():
                return ""  # Skip relative dates for now
            return date_str

    return ""


def is_valid_url(url: str) -> bool:
    """
    Check if URL is valid.

    Args:
        url: URL string

    Returns:
        True if valid URL
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def make_absolute_url(base_url: str, relative_url: str) -> str:
    """
    Convert relative URL to absolute URL.

    Args:
        base_url: Base URL
        relative_url: Relative or absolute URL

    Returns:
        Absolute URL
    """
    return urljoin(base_url, relative_url)


def truncate_text(text: str, max_length: int = 300) -> str:
    """
    Truncate text to maximum length at word boundary.

    Args:
        text: Input text
        max_length: Maximum character length

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    # Truncate at word boundary
    truncated = text[:max_length].rsplit(" ", 1)[0]
    return truncated + "..."
