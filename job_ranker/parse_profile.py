"""
Profile Parser - Extract structured data from resumes and profiles.
"""
import re
import json
import logging
from pathlib import Path
from typing import List, Optional
from .schema import CandidateProfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Common tech skills for extraction
TECH_SKILLS = {
    "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go", "Golang",
    "Ruby", "PHP", "Swift", "Kotlin", "Rust", "Scala", "SQL",
    "React", "Angular", "Vue", "Node.js", "Django", "Flask", "Spring",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Docker", "Kubernetes",
    "AWS", "Azure", "GCP", "Git", "Linux", "REST", "GraphQL",
    "TensorFlow", "PyTorch", "Pandas", "NumPy", "Spark", "Kafka",
}


class ProfileParser:
    """Parse resumes and profiles to structured format."""

    def __init__(self):
        """Initialize profile parser."""
        self.skills_set = TECH_SKILLS

    def parse_text(self, text: str) -> CandidateProfile:
        """
        Parse plain text resume/profile.

        Args:
            text: Raw resume text

        Returns:
            CandidateProfile object
        """
        # Extract sections using common headers
        sections = self._split_sections(text)

        # Extract fields
        title = self._extract_title(text, sections)
        summary = self._extract_summary(sections)
        skills = self._extract_skills(text)
        experience = self._extract_experience(sections)
        education = self._extract_education(sections)

        profile = CandidateProfile(
            title=title,
            summary=summary,
            skills=skills,
            experience=experience,
            education=education,
            raw_text=text,
        )

        logger.info(
            f"Parsed profile: title={title}, "
            f"skills={len(skills)}, "
            f"experience={len(experience)}, "
            f"education={len(education)}"
        )

        return profile

    def parse_json(self, json_str: str) -> CandidateProfile:
        """
        Parse JSON profile.

        Args:
            json_str: JSON string

        Returns:
            CandidateProfile object
        """
        data = json.loads(json_str)

        profile = CandidateProfile(
            title=data.get("title"),
            summary=data.get("summary"),
            skills=data.get("skills", []),
            experience=data.get("experience", []),
            education=data.get("education", []),
            raw_text=json_str,
        )

        return profile

    def parse_file(self, file_path: str) -> CandidateProfile:
        """
        Parse profile from file.

        Args:
            file_path: Path to text or JSON file

        Returns:
            CandidateProfile object
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Profile file not found: {file_path}")

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Try JSON first
        if path.suffix == ".json" or content.strip().startswith("{"):
            try:
                return self.parse_json(content)
            except json.JSONDecodeError:
                pass

        # Fall back to text parsing
        return self.parse_text(content)

    def _split_sections(self, text: str) -> dict:
        """
        Split text into sections based on common headers.

        Args:
            text: Resume text

        Returns:
            Dict of section_name -> section_text
        """
        sections = {}

        # Common section headers
        section_patterns = [
            (r"(?i)^(summary|profile|about|objective)[:\s]*$", "summary"),
            (r"(?i)^(experience|work experience|employment)[:\s]*$", "experience"),
            (r"(?i)^(education|academic|qualifications)[:\s]*$", "education"),
            (r"(?i)^(skills|technical skills|technologies)[:\s]*$", "skills"),
            (r"(?i)^(projects)[:\s]*$", "projects"),
        ]

        lines = text.split("\n")
        current_section = "header"
        section_content = []

        for line in lines:
            # Check if line is a section header
            is_header = False
            for pattern, section_name in section_patterns:
                if re.match(pattern, line.strip()):
                    # Save previous section
                    if section_content:
                        sections[current_section] = "\n".join(section_content)

                    current_section = section_name
                    section_content = []
                    is_header = True
                    break

            if not is_header:
                section_content.append(line)

        # Save last section
        if section_content:
            sections[current_section] = "\n".join(section_content)

        return sections

    def _extract_title(self, text: str, sections: dict) -> Optional[str]:
        """Extract job title/role from resume."""
        # Try to find title in header (usually first few lines)
        header = sections.get("header", "")
        lines = [l.strip() for l in header.split("\n") if l.strip()]

        # Look for role indicators
        role_keywords = [
            "engineer", "developer", "designer", "analyst", "scientist",
            "architect", "manager", "lead", "specialist", "consultant"
        ]

        for line in lines[:5]:  # Check first 5 lines
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in role_keywords):
                # Clean and return (limit length)
                if 5 < len(line) < 100:
                    return line

        return None

    def _extract_summary(self, sections: dict) -> Optional[str]:
        """Extract professional summary."""
        summary = sections.get("summary", "").strip()

        if summary and len(summary) > 20:
            # Take first 500 characters
            return summary[:500]

        return None

    def _extract_skills(self, text: str) -> List[str]:
        """Extract technical skills from text."""
        found_skills = set()
        text_lower = text.lower()

        for skill in self.skills_set:
            # Case-insensitive search with word boundaries
            pattern = r"\b" + re.escape(skill.lower()) + r"\b"
            if re.search(pattern, text_lower):
                found_skills.add(skill)

        return sorted(list(found_skills))

    def _extract_experience(self, sections: dict) -> List[str]:
        """Extract experience bullets."""
        experience_text = sections.get("experience", "")

        if not experience_text:
            return []

        # Split into bullets (lines that start with bullet points or dashes)
        lines = experience_text.split("\n")
        bullets = []

        for line in lines:
            line = line.strip()
            # Check if line looks like a bullet or experience item
            if (
                line.startswith("•")
                or line.startswith("-")
                or line.startswith("*")
                or re.match(r"^\d+[\.\)]", line)  # Numbered lists
            ):
                # Clean and add
                bullet = re.sub(r"^[•\-*\d\.\)]+\s*", "", line)
                if len(bullet) > 20:  # Minimum length
                    bullets.append(bullet)

            elif len(line) > 50 and not line.isupper():
                # Might be a regular sentence describing experience
                bullets.append(line)

        return bullets[:10]  # Limit to top 10

    def _extract_education(self, sections: dict) -> List[str]:
        """Extract education items."""
        education_text = sections.get("education", "")

        if not education_text:
            return []

        # Split into lines and extract degree info
        lines = [l.strip() for l in education_text.split("\n") if l.strip()]

        education_items = []
        for line in lines:
            # Look for degree keywords
            if any(
                keyword in line.lower()
                for keyword in ["bachelor", "master", "phd", "degree", "university", "college"]
            ):
                if len(line) > 10:
                    education_items.append(line)

        return education_items[:5]  # Limit to top 5


def parse_profile(file_path: str) -> CandidateProfile:
    """
    Convenience function to parse a profile file.

    Args:
        file_path: Path to profile file

    Returns:
        CandidateProfile object
    """
    parser = ProfileParser()
    return parser.parse_file(file_path)
