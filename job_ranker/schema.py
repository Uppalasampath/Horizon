"""
Job Ranking Schema - Models for jobs, profiles, and ranking results.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class JobPosting(BaseModel):
    """Job posting schema (matches scraper output)."""

    id: str
    source: str
    title: str
    company: str
    location: str
    posted_date: Optional[str] = None
    description: str
    skills: List[str] = Field(default_factory=list)
    experience_level: str = "unknown"
    apply_url: str
    raw: Dict[str, Any] = Field(default_factory=dict)


class CandidateProfile(BaseModel):
    """Parsed candidate profile."""

    title: Optional[str] = None
    summary: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    experience: List[str] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)
    raw_text: str = ""

    def to_weighted_text(self) -> str:
        """
        Convert profile to weighted text for embedding.

        Weights:
        - Title: 3x
        - Skills: 2x
        - Summary: 2x
        - Experience: 1x
        - Education: 1x

        Returns:
            Weighted text string
        """
        parts = []

        # Title (weight 3)
        if self.title:
            parts.extend([self.title] * 3)

        # Skills (weight 2)
        if self.skills:
            skills_text = " ".join(self.skills)
            parts.extend([skills_text] * 2)

        # Summary (weight 2)
        if self.summary:
            parts.extend([self.summary] * 2)

        # Experience (weight 1)
        for exp in self.experience:
            parts.append(exp)

        # Education (weight 1)
        for edu in self.education:
            parts.append(edu)

        return " ".join(parts)


class RankedJob(BaseModel):
    """Ranked job result with score and explanation."""

    job_id: str
    score: float
    title: str
    company: str
    location: str
    apply_url: str
    reasoning: str = ""

    class Config:
        """Pydantic config."""
        json_encoders = {
            float: lambda v: round(v, 4)
        }
