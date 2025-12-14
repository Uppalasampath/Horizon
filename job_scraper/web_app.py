"""
Web Application - Display jobs with apply buttons.
"""
from flask import Flask, render_template, jsonify, request, send_from_directory
from pathlib import Path
import json
import logging
from datetime import datetime
from typing import List, Dict
from .schema import JobPosting

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
JOBS_DIR = Path("data/jobs")
JOBS_FILE = JOBS_DIR / "jobs_latest.jsonl"


def load_jobs() -> List[Dict]:
    """Load jobs from JSONL file."""
    if not JOBS_FILE.exists():
        logger.warning(f"Jobs file not found: {JOBS_FILE}")
        return []

    jobs = []
    try:
        with open(JOBS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    job_data = json.loads(line)
                    jobs.append(job_data)

        logger.info(f"Loaded {len(jobs)} jobs from {JOBS_FILE}")
        return jobs

    except Exception as e:
        logger.error(f"Error loading jobs: {e}")
        return []


def get_stats(jobs: List[Dict]) -> Dict:
    """Calculate statistics from jobs."""
    if not jobs:
        return {
            "total": 0,
            "by_source": {},
            "by_level": {},
            "by_company": {},
        }

    stats = {
        "total": len(jobs),
        "by_source": {},
        "by_level": {},
        "by_company": {},
    }

    for job in jobs:
        # By source
        source = job.get("source", "unknown")
        stats["by_source"][source] = stats["by_source"].get(source, 0) + 1

        # By experience level
        level = job.get("experience_level", "unknown")
        stats["by_level"][level] = stats["by_level"].get(level, 0) + 1

        # By company
        company = job.get("company", "Unknown")
        stats["by_company"][company] = stats["by_company"].get(company, 0) + 1

    # Sort companies by count
    stats["by_company"] = dict(
        sorted(stats["by_company"].items(), key=lambda x: x[1], reverse=True)[:20]
    )

    return stats


@app.route("/")
def index():
    """Main page - display jobs."""
    return render_template("index.html")


@app.route("/api/jobs")
def get_jobs():
    """API endpoint to get jobs with filtering."""
    # Load jobs
    jobs = load_jobs()

    # Get filter parameters
    search = request.args.get("search", "").lower()
    source = request.args.get("source", "")
    level = request.args.get("level", "")
    company = request.args.get("company", "")
    limit = int(request.args.get("limit", 100))
    offset = int(request.args.get("offset", 0))

    # Apply filters
    filtered_jobs = jobs

    if search:
        filtered_jobs = [
            job for job in filtered_jobs
            if search in job.get("title", "").lower()
            or search in job.get("description", "").lower()
            or search in job.get("company", "").lower()
        ]

    if source:
        filtered_jobs = [
            job for job in filtered_jobs
            if job.get("source") == source
        ]

    if level:
        filtered_jobs = [
            job for job in filtered_jobs
            if job.get("experience_level") == level
        ]

    if company:
        filtered_jobs = [
            job for job in filtered_jobs
            if job.get("company", "").lower() == company.lower()
        ]

    # Pagination
    total = len(filtered_jobs)
    paginated_jobs = filtered_jobs[offset:offset + limit]

    return jsonify({
        "jobs": paginated_jobs,
        "total": total,
        "offset": offset,
        "limit": limit,
    })


@app.route("/api/stats")
def get_stats_api():
    """API endpoint to get statistics."""
    jobs = load_jobs()
    stats = get_stats(jobs)
    return jsonify(stats)


@app.route("/api/companies")
def get_companies():
    """API endpoint to get list of companies."""
    jobs = load_jobs()
    companies = sorted(set(job.get("company", "Unknown") for job in jobs))
    return jsonify({"companies": companies})


# Create templates directory if it doesn't exist
def create_templates():
    """Create HTML templates."""
    templates_dir = Path(__file__).parent / "templates"
    templates_dir.mkdir(exist_ok=True)

    # Create index.html
    index_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tech Jobs - Top Companies</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f5f5f5;
            color: #333;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        h1 {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }

        .subtitle {
            opacity: 0.9;
            font-size: 1.1rem;
        }

        .filters {
            background: white;
            padding: 1.5rem;
            margin: 2rem auto;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .filter-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }

        input, select {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 1rem;
        }

        input:focus, select:focus {
            outline: none;
            border-color: #667eea;
        }

        .stats {
            background: white;
            padding: 1.5rem;
            margin: 1rem auto;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }

        .stat-card {
            text-align: center;
            padding: 1rem;
            background: #f9f9f9;
            border-radius: 4px;
        }

        .stat-value {
            font-size: 2rem;
            font-weight: bold;
            color: #667eea;
        }

        .stat-label {
            color: #666;
            font-size: 0.9rem;
            margin-top: 0.5rem;
        }

        .jobs-container {
            margin: 2rem auto;
        }

        .job-card {
            background: white;
            padding: 1.5rem;
            margin-bottom: 1rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .job-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }

        .job-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 1rem;
        }

        .job-title {
            font-size: 1.3rem;
            font-weight: 600;
            color: #333;
            margin-bottom: 0.5rem;
        }

        .job-company {
            font-size: 1.1rem;
            color: #667eea;
            margin-bottom: 0.3rem;
        }

        .job-meta {
            display: flex;
            gap: 1rem;
            color: #666;
            font-size: 0.9rem;
            flex-wrap: wrap;
        }

        .job-meta span {
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
        }

        .badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.85rem;
            font-weight: 500;
        }

        .badge-entry {
            background: #d4edda;
            color: #155724;
        }

        .badge-mid {
            background: #fff3cd;
            color: #856404;
        }

        .badge-senior {
            background: #f8d7da;
            color: #721c24;
        }

        .badge-unknown {
            background: #e2e3e5;
            color: #383d41;
        }

        .job-skills {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin: 1rem 0;
        }

        .skill-tag {
            background: #f0f0f0;
            padding: 0.3rem 0.6rem;
            border-radius: 4px;
            font-size: 0.85rem;
            color: #555;
        }

        .job-description {
            color: #666;
            line-height: 1.6;
            margin: 1rem 0;
            max-height: 100px;
            overflow: hidden;
            position: relative;
        }

        .job-description.expanded {
            max-height: none;
        }

        .apply-btn {
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 0.75rem 2rem;
            border-radius: 4px;
            text-decoration: none;
            font-weight: 600;
            transition: transform 0.2s;
            margin-top: 1rem;
        }

        .apply-btn:hover {
            transform: scale(1.05);
        }

        .loading {
            text-align: center;
            padding: 2rem;
            color: #666;
        }

        .no-results {
            text-align: center;
            padding: 3rem;
            color: #999;
        }

        @media (max-width: 768px) {
            h1 {
                font-size: 1.8rem;
            }

            .filter-grid {
                grid-template-columns: 1fr;
            }

            .job-header {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <h1>🚀 Tech Jobs</h1>
            <p class="subtitle">Technical roles from top tech companies</p>
        </div>
    </div>

    <div class="container">
        <div class="stats">
            <h2>Statistics</h2>
            <div class="stats-grid" id="stats">
                <div class="stat-card">
                    <div class="stat-value" id="total-jobs">-</div>
                    <div class="stat-label">Total Jobs</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="entry-jobs">-</div>
                    <div class="stat-label">Entry Level</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="mid-jobs">-</div>
                    <div class="stat-label">Mid Level</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="companies">-</div>
                    <div class="stat-label">Companies</div>
                </div>
            </div>
        </div>

        <div class="filters">
            <h2>Filter Jobs</h2>
            <div class="filter-grid">
                <input type="text" id="search" placeholder="Search jobs...">
                <select id="level">
                    <option value="">All Levels</option>
                    <option value="entry">Entry Level</option>
                    <option value="mid">Mid Level</option>
                    <option value="senior">Senior Level</option>
                </select>
                <select id="company">
                    <option value="">All Companies</option>
                </select>
            </div>
        </div>

        <div class="jobs-container">
            <div id="jobs-list" class="loading">Loading jobs...</div>
        </div>
    </div>

    <script>
        let allJobs = [];
        let companies = [];

        // Load stats
        async function loadStats() {
            const response = await fetch('/api/stats');
            const stats = await response.json();

            document.getElementById('total-jobs').textContent = stats.total || 0;
            document.getElementById('entry-jobs').textContent = stats.by_level.entry || 0;
            document.getElementById('mid-jobs').textContent = stats.by_level.mid || 0;
            document.getElementById('companies').textContent = Object.keys(stats.by_company).length || 0;
        }

        // Load companies
        async function loadCompanies() {
            const response = await fetch('/api/companies');
            const data = await response.json();
            companies = data.companies;

            const select = document.getElementById('company');
            companies.forEach(company => {
                const option = document.createElement('option');
                option.value = company;
                option.textContent = company;
                select.appendChild(option);
            });
        }

        // Load jobs
        async function loadJobs() {
            const search = document.getElementById('search').value;
            const level = document.getElementById('level').value;
            const company = document.getElementById('company').value;

            const params = new URLSearchParams({
                search,
                level,
                company,
                limit: 100
            });

            const response = await fetch(`/api/jobs?${params}`);
            const data = await response.json();

            displayJobs(data.jobs);
        }

        // Display jobs
        function displayJobs(jobs) {
            const container = document.getElementById('jobs-list');

            if (jobs.length === 0) {
                container.innerHTML = '<div class="no-results">No jobs found matching your criteria.</div>';
                return;
            }

            container.innerHTML = jobs.map(job => `
                <div class="job-card">
                    <div class="job-header">
                        <div>
                            <div class="job-title">${escapeHtml(job.title)}</div>
                            <div class="job-company">${escapeHtml(job.company)}</div>
                            <div class="job-meta">
                                <span>📍 ${escapeHtml(job.location)}</span>
                                <span class="badge badge-${job.experience_level}">
                                    ${job.experience_level}
                                </span>
                                ${job.posted_date ? `<span>📅 ${formatDate(job.posted_date)}</span>` : ''}
                            </div>
                        </div>
                    </div>

                    ${job.skills && job.skills.length > 0 ? `
                        <div class="job-skills">
                            ${job.skills.slice(0, 8).map(skill =>
                                `<span class="skill-tag">${escapeHtml(skill)}</span>`
                            ).join('')}
                        </div>
                    ` : ''}

                    <div class="job-description">
                        ${escapeHtml(job.description.substring(0, 300))}...
                    </div>

                    <a href="${job.apply_url}" target="_blank" class="apply-btn">
                        Apply Now →
                    </a>
                </div>
            `).join('');
        }

        // Utility functions
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function formatDate(dateString) {
            try {
                const date = new Date(dateString);
                return date.toLocaleDateString();
            } catch {
                return dateString;
            }
        }

        // Event listeners
        document.getElementById('search').addEventListener('input', () => {
            setTimeout(loadJobs, 300);
        });

        document.getElementById('level').addEventListener('change', loadJobs);
        document.getElementById('company').addEventListener('change', loadJobs);

        // Initial load
        loadStats();
        loadCompanies();
        loadJobs();

        // Refresh every 5 minutes
        setInterval(() => {
            loadStats();
            loadJobs();
        }, 300000);
    </script>
</body>
</html>'''

    with open(templates_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(index_html)

    logger.info(f"Created templates in {templates_dir}")


# Create templates on import
create_templates()


def run_server(host="0.0.0.0", port=5000, debug=False):
    """Run the Flask web server."""
    logger.info(f"Starting web server on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Tech Jobs Web Application")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=5000, help="Port to bind to")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    args = parser.parse_args()

    run_server(host=args.host, port=args.port, debug=args.debug)
