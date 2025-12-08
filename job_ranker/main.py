"""
Job Ranker CLI - Main entrypoint for ranking jobs.
"""
import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List
from .schema import JobPosting
from .ranker import JobRanker
from .parse_profile import parse_profile

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Semantic job ranking using embeddings and cross-encoder re-ranking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Rank jobs with profile
  python -m job_ranker.main \\
    --profile sample_data/sample_profile.txt \\
    --jobs ../job_scraper/fixtures/sample_jobs.jsonl \\
    --topk 10

  # With explanation
  python -m job_ranker.main \\
    --profile sample_data/sample_profile.txt \\
    --jobs ../job_scraper/fixtures/sample_jobs.jsonl \\
    --topk 10 \\
    --explain

  # Use different model
  python -m job_ranker.main \\
    --profile sample_data/sample_profile.txt \\
    --jobs jobs.jsonl \\
    --model all-mpnet-base-v2 \\
    --topk 20
        """
    )

    parser.add_argument(
        "--profile",
        type=str,
        required=True,
        help="Path to candidate profile (text or JSON)"
    )

    parser.add_argument(
        "--jobs",
        type=str,
        required=True,
        help="Path to jobs JSONL file"
    )

    parser.add_argument(
        "--topk",
        type=int,
        default=20,
        help="Number of top results to return (default: 20)"
    )

    parser.add_argument(
        "--model",
        type=str,
        default="all-MiniLM-L6-v2",
        help="Sentence-transformers model name (default: all-MiniLM-L6-v2)"
    )

    parser.add_argument(
        "--reranker",
        type=str,
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        help="Cross-encoder model for re-ranking (default: cross-encoder/ms-marco-MiniLM-L-6-v2)"
    )

    parser.add_argument(
        "--no-rerank",
        action="store_true",
        help="Disable re-ranking (use only embedding similarity)"
    )

    parser.add_argument(
        "--explain",
        action="store_true",
        help="Generate explanations for rankings"
    )

    parser.add_argument(
        "--save-index",
        type=str,
        help="Save index to directory for reuse"
    )

    parser.add_argument(
        "--load-index",
        type=str,
        help="Load index from directory"
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file path (default: stdout)"
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )

    return parser.parse_args()


def load_jobs(jobs_path: str) -> List[JobPosting]:
    """
    Load jobs from JSONL file.

    Args:
        jobs_path: Path to JSONL file

    Returns:
        List of JobPosting objects
    """
    path = Path(jobs_path)

    if not path.exists():
        raise FileNotFoundError(f"Jobs file not found: {jobs_path}")

    jobs = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
                job = JobPosting(**data)
                jobs.append(job)
            except Exception as e:
                logger.warning(f"Failed to parse job on line {line_num}: {e}")
                continue

    logger.info(f"Loaded {len(jobs)} jobs from {jobs_path}")
    return jobs


def main():
    """Main CLI entrypoint."""
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Parse profile
        logger.info(f"Parsing profile: {args.profile}")
        profile = parse_profile(args.profile)

        logger.info(
            f"Profile parsed: {len(profile.skills)} skills, "
            f"{len(profile.experience)} experience items"
        )

        # Initialize ranker
        logger.info(f"Initializing ranker with model: {args.model}")
        ranker = JobRanker(
            encoder_model=args.model,
            reranker_model=args.reranker if not args.no_rerank else None,
            use_reranker=not args.no_rerank,
        )

        # Load or build index
        if args.load_index:
            logger.info(f"Loading index from {args.load_index}")
            ranker.load_index(args.load_index)

            # Still need to load jobs for result generation
            jobs = load_jobs(args.jobs)
            ranker.jobs = jobs

        else:
            # Load jobs
            jobs = load_jobs(args.jobs)

            if not jobs:
                logger.error("No jobs loaded. Exiting.")
                sys.exit(1)

            # Build index
            ranker.build_index(jobs)

            # Save index if requested
            if args.save_index:
                ranker.save_index(args.save_index)

        # Rank jobs
        logger.info(f"Ranking jobs (topk={args.topk})...")
        ranked_jobs = ranker.rank_jobs(
            profile=profile,
            topk=args.topk,
            explain=args.explain,
        )

        # Format output
        results = [job.model_dump() for job in ranked_jobs]
        output_json = json.dumps(results, indent=2)

        # Write output
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(output_json)
            logger.info(f"Results written to {args.output}")
        else:
            print("\n" + "="*80)
            print("RANKED JOBS")
            print("="*80 + "\n")
            print(output_json)

        # Print summary
        print(f"\n{'='*80}")
        print(f"✓ Ranked {len(ranked_jobs)} jobs")

        if ranked_jobs:
            print(f"\nTop 3 matches:")
            for i, job in enumerate(ranked_jobs[:3], 1):
                print(f"\n{i}. {job.title} at {job.company}")
                print(f"   Score: {job.score:.4f}")
                print(f"   Location: {job.location}")
                if job.reasoning:
                    print(f"   Reason: {job.reasoning}")
                print(f"   Apply: {job.apply_url}")

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=args.verbose)
        sys.exit(1)


if __name__ == "__main__":
    main()
