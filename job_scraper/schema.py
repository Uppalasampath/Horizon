"""
Job Posting Schema - Pydantic models for normalized job data.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, validator


class JobPosting(BaseModel):
    """Normalized job posting data structure."""

    id: str = Field(..., description="Unique identifier: source + job id")
    source: Literal["greenhouse", "lever", "workday", "generic"] = Field(
        ..., description="ATS source provider"
    )
    title: str = Field(..., description="Job title")
    company: str = Field(..., description="Company name")
    location: str = Field(..., description="Job location")
    posted_date: Optional[str] = Field(
        None, description="ISO 8601 date string or null"
    )
    description: str = Field(..., description="Full job description text")
    skills: List[str] = Field(
        default_factory=list, description="Extracted skills/technologies"
    )
    experience_level: Literal["entry", "mid", "senior", "unknown"] = Field(
        default="unknown", description="Detected experience level"
    )
    apply_url: str = Field(..., description="Application URL")
    raw: Dict[str, Any] = Field(
        default_factory=dict, description="Raw metadata from source"
    )

    @validator("posted_date")
    def validate_date_format(cls, v):
        """Validate ISO 8601 date format if provided."""
        if v is not None:
            try:
                datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                # Try to parse and convert to ISO format
                pass
        return v

    class Config:
        """Pydantic config."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


def normalize_experience_level(text: str) -> str:
    """
    Detect experience level from job title or description.

    Args:
        text: Combined title and description text

    Returns:
        Experience level: "entry", "mid", "senior", or "unknown"
    """
    text_lower = text.lower()

    # Entry level indicators
    entry_keywords = [
        "entry level", "junior", "associate", "graduate", "new grad",
        "early career", "recent graduate", "0-2 years", "0-1 year",
        "intern", "trainee", "apprentice"
    ]

    # Senior level indicators
    senior_keywords = [
        "senior", "lead", "principal", "staff", "architect",
        "director", "head of", "vp", "chief", "5+ years", "7+ years"
    ]

    # Mid level indicators
    mid_keywords = [
        "mid level", "intermediate", "3-5 years", "2-4 years",
        "experienced", "professional"
    ]

    # Check in priority order
    if any(keyword in text_lower for keyword in entry_keywords):
        return "entry"
    if any(keyword in text_lower for keyword in senior_keywords):
        return "senior"
    if any(keyword in text_lower for keyword in mid_keywords):
        return "mid"

    return "unknown"
