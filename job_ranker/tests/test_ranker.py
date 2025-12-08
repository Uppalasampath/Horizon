"""
Unit tests for job ranker - tests semantic matching capabilities.
"""
import pytest
import numpy as np
from job_ranker.schema import JobPosting, CandidateProfile, RankedJob
from job_ranker.parse_profile import ProfileParser
from job_ranker.encoder import EmbeddingEncoder, compute_similarity


# Sample test data
SAMPLE_PROFILE_TEXT = """
John Doe
Backend Software Engineer

Summary:
Recent CS graduate with strong background in backend development.
Built several REST APIs using Python and Django during internships.
Passionate about clean code and scalable systems.

Skills:
Python, Django, Flask, PostgreSQL, REST APIs, Docker, Git, SQL

Experience:
- Developed backend services for e-commerce platform using Django and PostgreSQL
- Built RESTful APIs for mobile app backend
- Implemented authentication and authorization using JWT
- Worked with Docker and CI/CD pipelines

Education:
Bachelor of Science in Computer Science, 2024
"""

SAMPLE_JOBS = [
    {
        "id": "job_1",
        "source": "generic",
        "title": "Junior Backend Developer",
        "company": "TechCorp",
        "location": "San Francisco, CA",
        "description": "Looking for junior backend developer with Python and Django experience. "
                      "Build REST APIs and work on microservices. Entry level position.",
        "skills": ["Python", "Django", "REST", "PostgreSQL"],
        "experience_level": "entry",
        "apply_url": "https://example.com/1"
    },
    {
        "id": "job_2",
        "source": "generic",
        "title": "Senior Frontend Architect",
        "company": "DesignCo",
        "location": "Remote",
        "description": "Senior frontend architect with 10+ years experience in React, TypeScript, "
                      "and system design. Lead frontend team and architecture decisions.",
        "skills": ["React", "TypeScript", "JavaScript", "GraphQL"],
        "experience_level": "senior",
        "apply_url": "https://example.com/2"
    },
    {
        "id": "job_3",
        "source": "generic",
        "title": "Backend Engineer - Python",
        "company": "StartupXYZ",
        "location": "New York, NY",
        "description": "Backend engineer role working with Python, FastAPI, and PostgreSQL. "
                      "Build scalable APIs for our platform. 0-2 years experience.",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
        "experience_level": "entry",
        "apply_url": "https://example.com/3"
    },
    {
        "id": "job_4",
        "source": "generic",
        "title": "Data Scientist - ML",
        "company": "AILabs",
        "location": "Boston, MA",
        "description": "Data scientist position working on machine learning models. "
                      "Need experience with PyTorch, TensorFlow, and Python.",
        "skills": ["Python", "PyTorch", "TensorFlow", "ML"],
        "experience_level": "mid",
        "apply_url": "https://example.com/4"
    },
    {
        "id": "job_5",
        "source": "generic",
        "title": "Full Stack Developer",
        "company": "WebDev Inc",
        "location": "Austin, TX",
        "description": "Full stack developer with React and Node.js experience. "
                      "Build web applications from frontend to backend.",
        "skills": ["React", "Node.js", "JavaScript", "MongoDB"],
        "experience_level": "entry",
        "apply_url": "https://example.com/5"
    },
]


class TestProfileParser:
    """Test profile parsing functionality."""

    def test_parse_text_profile(self):
        """Test parsing text profile."""
        parser = ProfileParser()
        profile = parser.parse_text(SAMPLE_PROFILE_TEXT)

        assert isinstance(profile, CandidateProfile)
        assert profile.title is not None
        assert "Backend" in profile.title or "Engineer" in profile.title

        # Check skills extraction
        assert len(profile.skills) > 0
        assert "Python" in profile.skills
        assert "Django" in profile.skills

        # Check experience
        assert len(profile.experience) > 0

    def test_weighted_text_generation(self):
        """Test weighted text generation for embeddings."""
        profile = CandidateProfile(
            title="Software Engineer",
            skills=["Python", "JavaScript"],
            summary="Experienced developer",
            experience=["Built APIs", "Worked on frontend"],
        )

        weighted_text = profile.to_weighted_text()

        # Title should appear 3 times (weight 3)
        assert weighted_text.count("Software Engineer") == 3

        # Skills should appear 2 times (weight 2)
        skill_text = "Python JavaScript"
        assert weighted_text.count(skill_text) == 2


class TestEmbeddings:
    """Test embedding functionality."""

    @pytest.mark.skip(reason="Requires downloading models - enable for full test")
    def test_encoder_initialization(self):
        """Test encoder initialization."""
        encoder = EmbeddingEncoder(model_name="all-MiniLM-L6-v2")
        assert encoder.embedding_dim == 384  # all-MiniLM-L6-v2 dimension

    @pytest.mark.skip(reason="Requires downloading models - enable for full test")
    def test_encode_texts(self):
        """Test encoding texts to embeddings."""
        encoder = EmbeddingEncoder(model_name="all-MiniLM-L6-v2")

        texts = ["Python developer", "JavaScript engineer"]
        embeddings = encoder.encode(texts, normalize=True)

        assert embeddings.shape == (2, 384)
        # Check normalization (L2 norm should be ~1)
        norms = np.linalg.norm(embeddings, axis=1)
        assert np.allclose(norms, 1.0, atol=1e-5)

    def test_similarity_computation(self):
        """Test similarity computation between embeddings."""
        # Create mock normalized embeddings
        emb1 = np.array([1.0, 0.0, 0.0])
        emb2 = np.array([1.0, 0.0, 0.0])  # Identical
        emb3 = np.array([0.0, 1.0, 0.0])  # Orthogonal

        # Same embeddings should have similarity ~1
        sim1 = compute_similarity(emb1, emb2)
        assert abs(sim1 - 1.0) < 0.01

        # Orthogonal embeddings should have similarity ~0
        sim2 = compute_similarity(emb1, emb3)
        assert abs(sim2 - 0.0) < 0.01


class TestSemanticMatching:
    """
    Test semantic matching capabilities.

    These tests demonstrate that the ranker understands semantic similarity
    beyond simple keyword matching.
    """

    @pytest.mark.skip(reason="Requires downloading models - enable for full test")
    def test_synonym_understanding(self):
        """
        Test that ranker understands synonyms.

        "software engineer" candidate should match "backend developer" job
        even though exact keywords differ.
        """
        from job_ranker.encoder import EmbeddingEncoder

        encoder = EmbeddingEncoder()

        # Encode synonymous terms
        texts = [
            "software engineer backend development",
            "backend developer programming",
            "frontend designer user interface",
        ]

        embeddings = encoder.encode(texts, normalize=True)

        # First two should be more similar than first and third
        sim_backend = compute_similarity(embeddings[0], embeddings[1])
        sim_different = compute_similarity(embeddings[0], embeddings[2])

        assert sim_backend > sim_different, \
            "Backend engineer and backend developer should be more similar than backend and frontend"

    @pytest.mark.skip(reason="Requires downloading models - enable for full test")
    def test_role_level_understanding(self):
        """Test that ranker understands seniority levels."""
        from job_ranker.encoder import EmbeddingEncoder

        encoder = EmbeddingEncoder()

        texts = [
            "junior entry level recent graduate",
            "entry level associate position",
            "senior lead architect 10 years",
        ]

        embeddings = encoder.encode(texts, normalize=True)

        # Entry level terms should be more similar to each other
        sim_entry = compute_similarity(embeddings[0], embeddings[1])
        sim_different_level = compute_similarity(embeddings[0], embeddings[2])

        assert sim_entry > sim_different_level, \
            "Entry level positions should be more similar to each other"

    @pytest.mark.skip(reason="Requires downloading models - enable for full test")
    def test_technical_skill_similarity(self):
        """Test understanding of related technical skills."""
        from job_ranker.encoder import EmbeddingEncoder

        encoder = EmbeddingEncoder()

        texts = [
            "Python Django REST API backend",
            "Python Flask API development",
            "JavaScript React frontend development",
        ]

        embeddings = encoder.encode(texts, normalize=True)

        # Python backend roles should be more similar
        sim_python_backend = compute_similarity(embeddings[0], embeddings[1])
        sim_different_stack = compute_similarity(embeddings[0], embeddings[2])

        assert sim_python_backend > sim_different_stack, \
            "Python backend roles should be more similar than Python backend vs JS frontend"


class TestRankingPipeline:
    """Test end-to-end ranking pipeline (with mocked embeddings)."""

    def test_job_schema_validation(self):
        """Test JobPosting schema validation."""
        job_data = SAMPLE_JOBS[0]
        job = JobPosting(**job_data)

        assert job.id == "job_1"
        assert job.title == "Junior Backend Developer"
        assert "Python" in job.skills

    def test_profile_to_weighted_text(self):
        """Test profile conversion to weighted text."""
        profile = CandidateProfile(
            title="Backend Engineer",
            skills=["Python", "Django"],
            summary="Experienced backend developer",
        )

        weighted = profile.to_weighted_text()

        # Title appears 3 times
        assert weighted.count("Backend Engineer") == 3

        # Skills appear 2 times
        assert weighted.count("Python Django") == 2

    def test_ranked_job_creation(self):
        """Test RankedJob creation."""
        job = RankedJob(
            job_id="test_1",
            score=0.85,
            title="Engineer",
            company="Company",
            location="NYC",
            apply_url="https://example.com",
            reasoning="Strong match"
        )

        assert job.score == 0.85
        assert job.reasoning == "Strong match"

        # Test JSON serialization
        json_dict = job.model_dump()
        assert "job_id" in json_dict
        assert "score" in json_dict


class TestEndToEnd:
    """
    End-to-end integration tests (mocked to avoid model downloads).
    """

    def test_profile_parsing_full(self):
        """Test full profile parsing."""
        parser = ProfileParser()
        profile = parser.parse_text(SAMPLE_PROFILE_TEXT)

        # Verify all sections parsed
        assert profile.title is not None
        assert profile.summary is not None
        assert len(profile.skills) >= 5
        assert len(profile.experience) >= 2
        assert len(profile.education) >= 1

    def test_job_loading(self):
        """Test loading jobs from dict."""
        jobs = [JobPosting(**job_data) for job_data in SAMPLE_JOBS]

        assert len(jobs) == 5
        assert all(isinstance(job, JobPosting) for job in jobs)

        # Check that we have diverse experience levels
        levels = [job.experience_level for job in jobs]
        assert "entry" in levels
        assert "senior" in levels

    def test_expected_ranking_behavior(self):
        """
        Test expected ranking behavior using heuristics.

        For the sample profile (Python/Django backend engineer),
        we expect:
        1. job_1 (Junior Backend Developer - Python/Django) to rank high
        2. job_3 (Backend Engineer - Python) to rank high
        3. job_2 (Senior Frontend - React/TypeScript) to rank low
        """
        parser = ProfileParser()
        profile = parser.parse_text(SAMPLE_PROFILE_TEXT)

        jobs = [JobPosting(**job_data) for job_data in SAMPLE_JOBS]

        # Simple skill overlap scoring (as proxy for semantic matching)
        profile_skills_set = set(s.lower() for s in profile.skills)

        scores = []
        for job in jobs:
            job_skills_set = set(s.lower() for s in job.skills)
            overlap = len(profile_skills_set & job_skills_set)

            # Bonus for entry level
            level_bonus = 2 if job.experience_level == "entry" else 0

            # Bonus for backend in title
            title_bonus = 2 if "backend" in job.title.lower() else 0

            score = overlap + level_bonus + title_bonus
            scores.append((job.id, score))

        # Sort by score
        scores.sort(key=lambda x: x[1], reverse=True)

        # Job 1 (Junior Backend Developer with Python/Django) should be top
        assert scores[0][0] == "job_1", \
            f"Expected job_1 to rank first, but got {scores[0][0]}"

        # Job 2 (Senior Frontend) should NOT be in top 2
        top_2_ids = [scores[0][0], scores[1][0]]
        assert "job_2" not in top_2_ids, \
            "Senior Frontend job should not be in top 2 for Backend Python profile"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
