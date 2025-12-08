"""
Job Ranker - Main ranking pipeline combining embedding + re-ranking.
"""
import logging
from typing import List, Tuple, Optional
from pathlib import Path
import numpy as np
from .schema import JobPosting, CandidateProfile, RankedJob
from .encoder import EmbeddingEncoder
from .indexer import JobIndex, build_job_index
from .re_rerank import CrossEncoderReranker, FallbackReranker
from .parse_profile import ProfileParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JobRanker:
    """
    Semantic job ranker using embeddings and cross-encoder re-ranking.
    """

    def __init__(
        self,
        encoder_model: str = "all-MiniLM-L6-v2",
        reranker_model: Optional[str] = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        use_reranker: bool = True,
    ):
        """
        Initialize job ranker.

        Args:
            encoder_model: Sentence-transformers model for embeddings
            reranker_model: Cross-encoder model for re-ranking (None to disable)
            use_reranker: Whether to use re-ranker
        """
        # Initialize encoder
        self.encoder = EmbeddingEncoder(model_name=encoder_model)
        logger.info(f"Encoder initialized: {encoder_model}")

        # Initialize re-ranker
        self.use_reranker = use_reranker
        if use_reranker and reranker_model:
            try:
                self.reranker = CrossEncoderReranker(model_name=reranker_model)
            except Exception as e:
                logger.warning(f"Failed to load reranker: {e}. Using fallback.")
                self.reranker = FallbackReranker()
        else:
            self.reranker = None
            logger.info("Re-ranking disabled")

        # Job index (built later)
        self.index: Optional[JobIndex] = None
        self.jobs: List[JobPosting] = []

    def build_index(
        self,
        jobs: List[JobPosting],
        batch_size: int = 32,
    ):
        """
        Build vector index from job postings.

        Args:
            jobs: List of JobPosting objects
            batch_size: Batch size for encoding
        """
        logger.info(f"Building index for {len(jobs)} jobs...")

        self.jobs = jobs

        # Create job texts for embedding
        job_texts = []
        for job in jobs:
            # Combine title, skills, and description summary
            text = self._create_job_text(job)
            job_texts.append(text)

        # Encode
        logger.info("Encoding job texts...")
        embeddings = self.encoder.encode(
            job_texts,
            batch_size=batch_size,
            show_progress=True,
            normalize=True,
        )

        # Build index
        job_ids = [job.id for job in jobs]
        metadata = [
            {
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "apply_url": job.apply_url,
                "skills": job.skills,
                "experience_level": job.experience_level,
            }
            for job in jobs
        ]

        self.index = build_job_index(embeddings, job_ids, metadata)
        logger.info("Index built successfully")

    def rank_jobs(
        self,
        profile: CandidateProfile,
        topk: int = 20,
        rerank_topk: Optional[int] = None,
        explain: bool = False,
    ) -> List[RankedJob]:
        """
        Rank jobs for candidate profile.

        Args:
            profile: CandidateProfile object
            topk: Number of top results to return
            rerank_topk: Number of candidates to re-rank (default: topk * 2)
            explain: Generate explanations for rankings

        Returns:
            List of RankedJob objects
        """
        if self.index is None or self.index.num_jobs == 0:
            logger.warning("Index is empty. Build index first.")
            return []

        if rerank_topk is None:
            rerank_topk = min(topk * 2, self.index.num_jobs)

        logger.info(f"Ranking jobs for profile (topk={topk}, rerank_topk={rerank_topk})")

        # Step 1: Encode candidate profile
        profile_text = profile.to_weighted_text()
        profile_embedding = self.encoder.encode_single(profile_text, normalize=True)

        # Step 2: Vector search for top candidates
        scores, indices, metadata_list = self.index.search(
            profile_embedding,
            k=rerank_topk
        )

        logger.info(f"Retrieved {len(indices)} candidates from vector search")

        # Step 3: Re-rank with cross-encoder (optional)
        if self.use_reranker and self.reranker is not None:
            logger.info("Re-ranking candidates with cross-encoder...")

            # Get job texts for re-ranking
            candidate_jobs = [self.jobs[idx] for idx in indices if idx < len(self.jobs)]
            candidate_texts = [self._create_job_text(job) for job in candidate_jobs]

            # Re-rank
            reranked_scores, reranked_indices = self.reranker.rerank(
                query=profile_text,
                documents=candidate_texts,
                scores=scores.tolist(),
            )

            # Reorder results
            final_scores = reranked_scores[:topk]
            final_jobs = [candidate_jobs[i] for i in reranked_indices[:topk]]
            final_metadata = [metadata_list[i] for i in reranked_indices[:topk]]

        else:
            # Use vector search scores directly
            final_scores = scores[:topk]
            final_jobs = [self.jobs[idx] for idx in indices[:topk] if idx < len(self.jobs)]
            final_metadata = metadata_list[:topk]

        # Step 4: Create ranked results
        ranked_jobs = []
        for i, (job, score, meta) in enumerate(zip(final_jobs, final_scores, final_metadata)):
            reasoning = ""
            if explain:
                reasoning = self._generate_explanation(profile, job, score)

            ranked_job = RankedJob(
                job_id=job.id,
                score=float(score),
                title=job.title,
                company=job.company,
                location=job.location,
                apply_url=job.apply_url,
                reasoning=reasoning,
            )
            ranked_jobs.append(ranked_job)

        logger.info(f"Returned {len(ranked_jobs)} ranked jobs")

        return ranked_jobs

    def save_index(self, path: str):
        """
        Save index to disk.

        Args:
            path: Directory path
        """
        if self.index is None:
            raise ValueError("No index to save")

        self.index.save(path)
        logger.info(f"Index saved to {path}")

    def load_index(self, path: str):
        """
        Load index from disk.

        Args:
            path: Directory path
        """
        self.index = JobIndex.load(path)
        logger.info(f"Index loaded from {path}")

    def _create_job_text(self, job: JobPosting) -> str:
        """
        Create searchable text from job posting.

        Combines title, skills, and description summary.

        Args:
            job: JobPosting object

        Returns:
            Combined text string
        """
        parts = []

        # Title (weight 2x by repeating)
        parts.extend([job.title] * 2)

        # Skills (weight 2x)
        if job.skills:
            skills_text = " ".join(job.skills)
            parts.extend([skills_text] * 2)

        # Description summary (first 300 chars)
        if job.description:
            # Take first 2 paragraphs or 300 chars
            desc_parts = job.description.split("\n\n")
            desc_summary = " ".join(desc_parts[:2])[:300]
            parts.append(desc_summary)

        # Location and experience level
        parts.append(job.location)
        parts.append(f"experience level {job.experience_level}")

        return " ".join(parts)

    def _generate_explanation(
        self,
        profile: CandidateProfile,
        job: JobPosting,
        score: float,
    ) -> str:
        """
        Generate human-readable explanation for job ranking.

        Args:
            profile: Candidate profile
            job: Job posting
            score: Relevance score

        Returns:
            Explanation string
        """
        explanations = []

        # Skill match
        if profile.skills and job.skills:
            matched_skills = set(profile.skills) & set(job.skills)
            if matched_skills:
                skills_str = ", ".join(sorted(matched_skills)[:5])
                explanations.append(f"Matched skills: {skills_str}")

        # Title similarity
        if profile.title and job.title:
            profile_title_lower = profile.title.lower()
            job_title_lower = job.title.lower()

            # Check for role similarity
            profile_words = set(profile_title_lower.split())
            job_words = set(job_title_lower.split())
            common_words = profile_words & job_words

            if common_words:
                explanations.append(f"Similar role: {job.title}")

        # Experience level match
        if job.experience_level == "entry":
            explanations.append("Entry-level position")

        # Score interpretation
        if score > 0.8:
            explanations.append("Strong semantic match")
        elif score > 0.6:
            explanations.append("Good match")
        elif score > 0.4:
            explanations.append("Moderate match")

        # Combine
        if explanations:
            return ". ".join(explanations) + "."
        else:
            return f"Relevance score: {score:.2f}"
