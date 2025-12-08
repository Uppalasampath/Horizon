# Job Ranker

Semantic job ranking engine that matches candidates to jobs using deep learning embeddings and cross-encoder re-ranking. Goes beyond keyword matching to understand semantic similarity between candidate profiles and job postings.

## Features

- **Semantic Understanding**: Uses sentence-transformers to understand meaning, not just keywords
- **Two-Stage Ranking**: Fast vector search + precise cross-encoder re-ranking
- **Profile Parsing**: Extracts structured data from plain text resumes
- **Weighted Scoring**: Intelligently weights title, skills, and experience
- **FAISS Indexing**: Efficient vector search for large job databases
- **Explainable Results**: Generates reasoning for each match
- **Local Models**: No API keys required, runs entirely offline
- **Model Flexibility**: Easy to swap embedding and re-ranking models

## How It Works

### Architecture

```
1. Profile Parsing
   Resume Text → Structured Profile → Weighted Text

2. Embedding
   Jobs → Sentence Embeddings (384d)
   Profile → Sentence Embedding (384d)

3. Vector Search (FAISS)
   Find top-K similar jobs by cosine similarity

4. Re-ranking (Cross-Encoder)
   Re-score top-K with fine-grained model

5. Results
   Ranked jobs with scores + explanations
```

### Why This Approach?

**Semantic Matching**: Traditional keyword-based matching fails when job descriptions use different terminology:
- Candidate: "Backend Developer" ↔ Job: "Server-Side Engineer" ✓
- Candidate: "REST APIs" ↔ Job: "RESTful Services" ✓
- Candidate: "Junior" ↔ Job: "Entry Level" ✓

**Two-Stage Ranking**: Combines efficiency with accuracy:
- Stage 1: Fast embedding search narrows to top 50-100 candidates
- Stage 2: Expensive cross-encoder re-ranks for final top-K

## Installation

```bash
pip install -r requirements.txt
```

**First Run**: Models will download automatically from HuggingFace (~160MB total):
- `all-MiniLM-L6-v2`: Sentence embedding model (~80MB)
- `cross-encoder/ms-marco-MiniLM-L-6-v2`: Re-ranking model (~80MB)

## Quick Start

### Basic Usage

```bash
# Rank jobs with a profile
python -m job_ranker.main \
  --profile sample_data/sample_profile.txt \
  --jobs ../job_scraper/fixtures/sample_jobs.jsonl \
  --topk 10
```

### With Explanations

```bash
python -m job_ranker.main \
  --profile sample_data/sample_profile.txt \
  --jobs ../job_scraper/fixtures/sample_jobs.jsonl \
  --topk 10 \
  --explain
```

### Different Models

```bash
# Use better (but slower) embedding model
python -m job_ranker.main \
  --profile sample_data/sample_profile.txt \
  --jobs jobs.jsonl \
  --model all-mpnet-base-v2 \
  --topk 20
```

### Save/Load Index

```bash
# Build and save index
python -m job_ranker.main \
  --profile profile.txt \
  --jobs jobs.jsonl \
  --save-index ./job_index

# Reuse saved index (faster)
python -m job_ranker.main \
  --profile profile.txt \
  --jobs jobs.jsonl \
  --load-index ./job_index \
  --topk 10
```

## CLI Options

- `--profile`: Path to candidate profile (text or JSON) [required]
- `--jobs`: Path to jobs JSONL file [required]
- `--topk`: Number of results to return (default: 20)
- `--model`: Embedding model name (default: `all-MiniLM-L6-v2`)
- `--reranker`: Cross-encoder model (default: `cross-encoder/ms-marco-MiniLM-L-6-v2`)
- `--no-rerank`: Disable re-ranking (use only embeddings)
- `--explain`: Generate match explanations
- `--save-index`: Save index to directory
- `--load-index`: Load pre-built index
- `--output`, `-o`: Output file path (default: stdout)
- `--verbose`, `-v`: Verbose logging

## Profile Format

### Plain Text (Recommended)

```text
John Doe
Software Engineer

SUMMARY
Experienced backend developer with Python and Django...

SKILLS
Python, Django, PostgreSQL, Docker, AWS...

EXPERIENCE
- Built REST APIs for e-commerce platform
- Implemented microservices architecture
...

EDUCATION
B.S. Computer Science, 2024
```

### JSON Format

```json
{
  "title": "Software Engineer",
  "summary": "Experienced backend developer...",
  "skills": ["Python", "Django", "PostgreSQL"],
  "experience": [
    "Built REST APIs...",
    "Implemented microservices..."
  ],
  "education": ["B.S. Computer Science, 2024"]
}
```

## Output Format

```json
[
  {
    "job_id": "greenhouse_12345",
    "score": 0.8234,
    "title": "Junior Backend Engineer",
    "company": "TechCorp",
    "location": "San Francisco, CA",
    "apply_url": "https://boards.greenhouse.io/...",
    "reasoning": "Matched skills: Python, Django, PostgreSQL. Similar role: Junior Backend Engineer. Entry-level position. Strong semantic match."
  },
  ...
]
```

## Python Module Usage

```python
from job_ranker import JobRanker, parse_profile
from job_ranker.schema import JobPosting

# Parse profile
profile = parse_profile("resume.txt")

# Load jobs
jobs = [JobPosting(**job_data) for job_data in job_list]

# Initialize ranker
ranker = JobRanker(
    encoder_model="all-MiniLM-L6-v2",
    reranker_model="cross-encoder/ms-marco-MiniLM-L-6-v2"
)

# Build index
ranker.build_index(jobs)

# Rank jobs
ranked_jobs = ranker.rank_jobs(
    profile=profile,
    topk=20,
    explain=True
)

# Use results
for job in ranked_jobs[:5]:
    print(f"{job.title} at {job.company} - Score: {job.score:.4f}")
```

## Model Selection

### Embedding Models

| Model | Dimension | Speed | Quality | Use Case |
|-------|-----------|-------|---------|----------|
| `all-MiniLM-L6-v2` | 384 | Fast | Good | **Default**, balanced |
| `all-MiniLM-L12-v2` | 384 | Medium | Better | More accuracy |
| `all-mpnet-base-v2` | 768 | Slow | Best | Highest quality |

### Re-ranking Models

| Model | Speed | Quality | Use Case |
|-------|-------|---------|----------|
| `cross-encoder/ms-marco-TinyBERT-L-2-v2` | Very Fast | Good | Large scale |
| `cross-encoder/ms-marco-MiniLM-L-6-v2` | Fast | Better | **Default** |
| `cross-encoder/ms-marco-MiniLM-L-12-v2` | Medium | Best | Highest quality |

## Performance

### Speed Benchmarks

On typical laptop (no GPU):
- Index building: ~100 jobs/second
- Vector search: <10ms for 1000 jobs
- Re-ranking: ~50ms for top-50 candidates

Total ranking time: **~100ms** for 1000 jobs

### Scaling

- **1K jobs**: <1 second
- **10K jobs**: ~2-3 seconds
- **100K jobs**: ~10-15 seconds

Use `--save-index` to avoid rebuilding for repeated queries.

## Semantic Matching Examples

The ranker demonstrates semantic understanding:

### Example 1: Synonym Understanding

**Candidate**: "Backend Developer, REST APIs"
**Job A**: "Server-Side Engineer, RESTful Services"
**Job B**: "Frontend Designer, UI/UX"

✓ **Result**: Job A ranks higher (semantic similarity despite different words)

### Example 2: Seniority Matching

**Candidate**: "Recent graduate, entry level, junior"
**Job A**: "Entry Level Software Engineer"
**Job B**: "Senior Architect, 10+ years"

✓ **Result**: Job A ranks higher (understands experience level match)

### Example 3: Tech Stack Understanding

**Candidate**: "Python, Django, PostgreSQL"
**Job A**: "Backend Engineer - Python & Django"
**Job B**: "Data Scientist - R & Statistics"

✓ **Result**: Job A ranks higher (understands related technologies)

## Testing

Run unit tests:

```bash
pytest job_ranker/tests/test_ranker.py -v
```

**Note**: Some tests are skipped by default to avoid downloading models during testing. Enable with:

```bash
pytest job_ranker/tests/test_ranker.py -v --runall
```

Tests demonstrate:
- Profile parsing accuracy
- Semantic similarity detection
- Synonym understanding
- Seniority level matching
- Expected ranking behavior

## Architecture

```
job_ranker/
├── main.py              # CLI entrypoint
├── ranker.py            # Main ranking pipeline
├── encoder.py           # Sentence-transformers wrapper
├── indexer.py           # FAISS index management
├── re_rerank.py         # Cross-encoder re-ranker
├── parse_profile.py     # Profile parser
├── schema.py            # Pydantic models
├── tests/               # Unit tests
└── sample_data/         # Sample profiles and jobs
```

## Advanced Features

### Weighted Profile Text

Profiles are converted to weighted text for better matching:

- **Title**: Weight 3x (most important signal)
- **Skills**: Weight 2x (critical for technical match)
- **Summary**: Weight 2x (shows expertise)
- **Experience**: Weight 1x (context)
- **Education**: Weight 1x (background)

### Job Text Creation

Jobs are represented by:
- Title (repeated 2x)
- Skills (repeated 2x)
- Description summary (first 300 chars)
- Location and experience level

### Explanation Generation

Explanations consider:
- Skill overlap
- Title similarity
- Experience level match
- Overall semantic score

## Common Use Cases

### 1. Job Board Recommendations

```python
# Recommend jobs for each user
for user in users:
    profile = parse_profile(user.resume)
    ranked = ranker.rank_jobs(profile, topk=10)
    send_recommendations(user, ranked)
```

### 2. Application Filtering

```python
# Filter applicants for a job
job_as_profile = CandidateProfile(
    title=job.title,
    skills=job.skills,
    summary=job.description[:500]
)

ranked_candidates = ranker.rank_jobs(
    profile=job_as_profile,
    topk=50
)
```

### 3. Batch Processing

```python
# Process multiple profiles
for profile_file in profile_files:
    profile = parse_profile(profile_file)
    results = ranker.rank_jobs(profile, topk=20)
    save_results(profile_file, results)
```

## Troubleshooting

**Models not downloading?**
- Ensure internet connection on first run
- Models are cached in `~/.cache/huggingface/`

**Out of memory?**
- Use smaller embedding model (`all-MiniLM-L6-v2`)
- Reduce batch size: `encoder.encode(texts, batch_size=16)`
- Disable re-ranking: `--no-rerank`

**Slow performance?**
- Save and reuse index: `--save-index`
- Use faster embedding model
- Reduce `topk` value

**Poor ranking quality?**
- Try better model: `--model all-mpnet-base-v2`
- Enable explanations to debug: `--explain`
- Check profile parsing quality

## Extending

### Custom Embedding Model

```python
ranker = JobRanker(
    encoder_model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
```

### Custom Profile Parser

```python
class CustomParser(ProfileParser):
    def _extract_skills(self, text):
        # Custom skill extraction logic
        return custom_skills
```

### Custom Scoring

Modify `ranker.py` to implement custom relevance scoring logic.

## Example Workflow

```bash
# 1. Scrape jobs
cd job_scraper
python -m job_scraper.main --use-fixtures --out jobs.jsonl

# 2. Rank jobs
cd ../job_ranker
python -m job_ranker.main \
  --profile sample_data/sample_profile.txt \
  --jobs ../job_scraper/jobs.jsonl \
  --topk 10 \
  --explain

# 3. Review results
# Top matches are printed with scores and explanations
```

## Citation

Uses models from:
- [sentence-transformers](https://www.sbert.net/) by UKP Lab
- [HuggingFace Transformers](https://huggingface.co/transformers/)
- [FAISS](https://github.com/facebookresearch/faiss) by Facebook Research

## License

MIT License - See LICENSE file for details.
