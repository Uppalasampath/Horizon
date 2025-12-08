"""
Embedding Encoder - Load and use sentence-transformers models.
"""
import logging
from typing import List, Optional
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    raise ImportError(
        "sentence-transformers not installed. Install with: pip install sentence-transformers"
    )

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingEncoder:
    """Wrapper for sentence-transformers embedding models."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: Optional[str] = None,
    ):
        """
        Initialize embedding encoder.

        Args:
            model_name: HuggingFace model name (default: all-MiniLM-L6-v2)
            device: Device to use ('cpu', 'cuda', or None for auto)

        Popular models:
        - all-MiniLM-L6-v2: Fast, 384 dims (default)
        - all-mpnet-base-v2: Better quality, 768 dims, slower
        - all-MiniLM-L12-v2: Balance between speed and quality, 384 dims
        """
        logger.info(f"Loading embedding model: {model_name}")

        self.model_name = model_name
        self.model = SentenceTransformer(model_name, device=device)
        self.dimension = self.model.get_sentence_embedding_dimension()

        logger.info(f"Model loaded. Embedding dimension: {self.dimension}")

    def encode(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = False,
        normalize: bool = True,
    ) -> np.ndarray:
        """
        Encode texts to embeddings.

        Args:
            texts: List of text strings
            batch_size: Batch size for encoding
            show_progress: Show progress bar
            normalize: L2 normalize embeddings (for cosine similarity)

        Returns:
            Numpy array of shape (len(texts), dimension)
        """
        if not texts:
            return np.array([])

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
            normalize_embeddings=normalize,
        )

        return embeddings

    def encode_single(self, text: str, normalize: bool = True) -> np.ndarray:
        """
        Encode a single text to embedding.

        Args:
            text: Text string
            normalize: L2 normalize embedding

        Returns:
            Numpy array of shape (dimension,)
        """
        embeddings = self.encode([text], normalize=normalize)
        return embeddings[0]

    @property
    def embedding_dim(self) -> int:
        """Get embedding dimension."""
        return self.dimension


def create_encoder(model_name: str = "all-MiniLM-L6-v2") -> EmbeddingEncoder:
    """
    Factory function to create encoder.

    Args:
        model_name: Model name

    Returns:
        EmbeddingEncoder instance
    """
    return EmbeddingEncoder(model_name=model_name)


def compute_similarity(
    embedding1: np.ndarray,
    embedding2: np.ndarray
) -> float:
    """
    Compute cosine similarity between two embeddings.

    Args:
        embedding1: First embedding (normalized)
        embedding2: Second embedding (normalized)

    Returns:
        Similarity score in [0, 1]
    """
    # If embeddings are normalized, dot product = cosine similarity
    similarity = np.dot(embedding1, embedding2)

    # Clip to [0, 1] range (should already be there for normalized vectors)
    return float(np.clip(similarity, 0.0, 1.0))


def batch_compute_similarity(
    query_embedding: np.ndarray,
    embeddings: np.ndarray
) -> np.ndarray:
    """
    Compute cosine similarity between query and multiple embeddings.

    Args:
        query_embedding: Query embedding of shape (dimension,)
        embeddings: Array of embeddings of shape (n, dimension)

    Returns:
        Array of similarity scores of shape (n,)
    """
    # Matrix multiplication: (1, d) @ (d, n) = (1, n)
    similarities = np.dot(embeddings, query_embedding)

    # Clip to [0, 1]
    return np.clip(similarities, 0.0, 1.0)
