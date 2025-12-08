"""
Job Ranker - Semantic job ranking with embeddings and cross-encoder re-ranking.
"""
from .schema import JobPosting, CandidateProfile, RankedJob
from .ranker import JobRanker
from .parse_profile import parse_profile

__version__ = "1.0.0"
__all__ = [
    "JobPosting",
    "CandidateProfile",
    "RankedJob",
    "JobRanker",
    "parse_profile",
]
