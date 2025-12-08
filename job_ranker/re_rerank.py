"""
Cross-Encoder Re-Ranker - Re-score top-k results with fine-grained model.
"""
import logging
from typing import List, Tuple, Optional
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """
    Cross-encoder re-ranker for fine-grained relevance scoring.

    Uses sentence-transformers cross-encoder models.
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        device: Optional[str] = None,
    ):
        """
        Initialize cross-encoder re-ranker.

        Args:
            model_name: HuggingFace cross-encoder model name
            device: Device to use ('cpu', 'cuda', or None for auto)

        Popular models:
        - cross-encoder/ms-marco-MiniLM-L-6-v2: Fast, good for ranking
        - cross-encoder/ms-marco-TinyBERT-L-2-v2: Very fast, smaller
        """
        try:
            from sentence_transformers import CrossEncoder
        except ImportError:
            logger.warning(
                "sentence-transformers not installed. Re-ranking unavailable. "
                "Install with: pip install sentence-transformers"
            )
            self.model = None
            return

        logger.info(f"Loading cross-encoder model: {model_name}")

        try:
            self.model = CrossEncoder(model_name, device=device)
            logger.info("Cross-encoder loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load cross-encoder: {e}. Re-ranking disabled.")
            self.model = None

    def rerank(
        self,
        query: str,
        documents: List[str],
        scores: Optional[List[float]] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Re-rank documents using cross-encoder.

        Args:
            query: Query text
            documents: List of document texts
            scores: Optional initial scores (unused, for compatibility)

        Returns:
            Tuple of (reranked_scores, reranked_indices)
        """
        if self.model is None:
            # Fallback: return original order
            logger.warning("Re-ranking unavailable (model not loaded)")
            if scores:
                reranked_scores = np.array(scores)
                reranked_indices = np.argsort(-reranked_scores)
            else:
                reranked_scores = np.arange(len(documents), 0, -1, dtype=float)
                reranked_indices = np.arange(len(documents))

            return reranked_scores, reranked_indices

        if not documents:
            return np.array([]), np.array([])

        # Create query-document pairs
        pairs = [[query, doc] for doc in documents]

        # Score with cross-encoder
        try:
            ce_scores = self.model.predict(pairs, show_progress_bar=False)
            ce_scores = np.array(ce_scores)

            # Sort by descending score
            reranked_indices = np.argsort(-ce_scores)
            reranked_scores = ce_scores[reranked_indices]

            return reranked_scores, reranked_indices

        except Exception as e:
            logger.error(f"Re-ranking failed: {e}")
            # Fallback to original order
            reranked_scores = np.arange(len(documents), 0, -1, dtype=float)
            reranked_indices = np.arange(len(documents))
            return reranked_scores, reranked_indices


def create_reranker(
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
) -> CrossEncoderReranker:
    """
    Factory function to create re-ranker.

    Args:
        model_name: Cross-encoder model name

    Returns:
        CrossEncoderReranker instance
    """
    return CrossEncoderReranker(model_name=model_name)


class FallbackReranker:
    """
    Fallback re-ranker that uses simple heuristics.

    Used when cross-encoder is unavailable.
    """

    def __init__(self):
        """Initialize fallback re-ranker."""
        logger.info("Using fallback re-ranker (no ML model)")

    def rerank(
        self,
        query: str,
        documents: List[str],
        scores: Optional[List[float]] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Re-rank using keyword overlap heuristic.

        Args:
            query: Query text
            documents: List of document texts
            scores: Initial scores (if available)

        Returns:
            Tuple of (scores, indices)
        """
        if not documents:
            return np.array([]), np.array([])

        # Simple keyword overlap scoring
        query_tokens = set(query.lower().split())

        overlap_scores = []
        for doc in documents:
            doc_tokens = set(doc.lower().split())
            overlap = len(query_tokens & doc_tokens) / max(len(query_tokens), 1)
            overlap_scores.append(overlap)

        overlap_scores = np.array(overlap_scores)

        # Combine with initial scores if available
        if scores:
            scores_array = np.array(scores)
            combined = 0.7 * scores_array + 0.3 * overlap_scores
        else:
            combined = overlap_scores

        # Sort by descending score
        indices = np.argsort(-combined)
        reranked_scores = combined[indices]

        return reranked_scores, indices
