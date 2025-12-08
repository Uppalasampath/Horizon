"""
FAISS Indexer - Build and search vector index for job embeddings.
"""
import pickle
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import numpy as np

try:
    import faiss
except ImportError:
    raise ImportError(
        "faiss-cpu not installed. Install with: pip install faiss-cpu"
    )

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JobIndex:
    """FAISS-based vector index for job embeddings."""

    def __init__(self, dimension: int):
        """
        Initialize job index.

        Args:
            dimension: Embedding dimension
        """
        self.dimension = dimension

        # Use IndexFlatIP for inner product (cosine similarity with normalized vectors)
        self.index = faiss.IndexFlatIP(dimension)

        # Metadata storage (job ID and other info)
        self.metadata: List[Dict[str, Any]] = []

        # ID to index mapping
        self.id_to_idx: Dict[str, int] = {}

        logger.info(f"Initialized FAISS index (dimension={dimension})")

    def add_jobs(
        self,
        embeddings: np.ndarray,
        job_ids: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Add job embeddings to index.

        Args:
            embeddings: Numpy array of shape (n, dimension)
            job_ids: List of job IDs
            metadata: Optional list of metadata dicts
        """
        if embeddings.shape[0] != len(job_ids):
            raise ValueError("Number of embeddings must match number of job IDs")

        if embeddings.shape[1] != self.dimension:
            raise ValueError(
                f"Embedding dimension {embeddings.shape[1]} "
                f"doesn't match index dimension {self.dimension}"
            )

        # Ensure float32 for FAISS
        embeddings = embeddings.astype(np.float32)

        # Add to FAISS index
        start_idx = self.index.ntotal
        self.index.add(embeddings)

        # Store metadata
        for i, job_id in enumerate(job_ids):
            idx = start_idx + i
            self.id_to_idx[job_id] = idx

            meta = metadata[i] if metadata else {}
            meta["job_id"] = job_id
            self.metadata.append(meta)

        logger.info(f"Added {len(job_ids)} jobs to index. Total: {self.index.ntotal}")

    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 10
    ) -> Tuple[np.ndarray, np.ndarray, List[Dict[str, Any]]]:
        """
        Search for top-k similar jobs.

        Args:
            query_embedding: Query embedding of shape (dimension,)
            k: Number of results to return

        Returns:
            Tuple of (scores, indices, metadata_list)
        """
        if self.index.ntotal == 0:
            logger.warning("Index is empty")
            return np.array([]), np.array([]), []

        # Ensure correct shape and type
        query = query_embedding.reshape(1, -1).astype(np.float32)

        # Search
        k = min(k, self.index.ntotal)
        scores, indices = self.index.search(query, k)

        # Get metadata for results
        results_metadata = []
        for idx in indices[0]:
            if 0 <= idx < len(self.metadata):
                results_metadata.append(self.metadata[idx])

        return scores[0], indices[0], results_metadata

    def save(self, path: str):
        """
        Save index and metadata to disk.

        Args:
            path: Directory path to save to
        """
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        index_path = path / "index.faiss"
        faiss.write_index(self.index, str(index_path))

        # Save metadata
        metadata_path = path / "metadata.pkl"
        with open(metadata_path, "wb") as f:
            pickle.dump({
                "metadata": self.metadata,
                "id_to_idx": self.id_to_idx,
                "dimension": self.dimension,
            }, f)

        logger.info(f"Saved index to {path}")

    @classmethod
    def load(cls, path: str) -> "JobIndex":
        """
        Load index and metadata from disk.

        Args:
            path: Directory path to load from

        Returns:
            JobIndex instance
        """
        path = Path(path)

        # Load FAISS index
        index_path = path / "index.faiss"
        if not index_path.exists():
            raise FileNotFoundError(f"Index not found at {index_path}")

        faiss_index = faiss.read_index(str(index_path))

        # Load metadata
        metadata_path = path / "metadata.pkl"
        with open(metadata_path, "rb") as f:
            data = pickle.load(f)

        # Create instance
        dimension = data["dimension"]
        instance = cls(dimension)
        instance.index = faiss_index
        instance.metadata = data["metadata"]
        instance.id_to_idx = data["id_to_idx"]

        logger.info(f"Loaded index from {path} ({instance.index.ntotal} jobs)")

        return instance

    @property
    def num_jobs(self) -> int:
        """Get number of jobs in index."""
        return self.index.ntotal


def build_job_index(
    embeddings: np.ndarray,
    job_ids: List[str],
    metadata: Optional[List[Dict[str, Any]]] = None,
    dimension: Optional[int] = None,
) -> JobIndex:
    """
    Build a job index from embeddings.

    Args:
        embeddings: Job embeddings array of shape (n, dimension)
        job_ids: List of job IDs
        metadata: Optional metadata for each job
        dimension: Embedding dimension (inferred if None)

    Returns:
        JobIndex instance
    """
    if dimension is None:
        dimension = embeddings.shape[1]

    index = JobIndex(dimension)
    index.add_jobs(embeddings, job_ids, metadata)

    return index
