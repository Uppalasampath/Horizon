"""
Top Tech Companies Database - Career page URLs for automated scraping.
"""
from typing import List, Dict

# Top tech companies with their career page URLs
TECH_COMPANIES = [
    # FAANG/Big Tech
    {
        "name": "Google",
        "url": "https://careers.google.com/jobs/results/",
        "ats": "generic",
    },
    {
        "name": "Meta (Facebook)",
        "url": "https://www.metacareers.com/jobs/",
        "ats": "generic",
    },
    {
        "name": "Amazon",
        "url": "https://www.amazon.jobs/en/search.json",
        "ats": "generic",
    },
    {
        "name": "Apple",
        "url": "https://jobs.apple.com/en-us/search",
        "ats": "generic",
    },
    {
        "name": "Netflix",
        "url": "https://jobs.netflix.com/search",
        "ats": "greenhouse",
    },

    # Major Tech Companies
    {
        "name": "Microsoft",
        "url": "https://careers.microsoft.com/us/en/search-results",
        "ats": "generic",
    },
    {
        "name": "Salesforce",
        "url": "https://salesforce.wd1.myworkdayjobs.com/External_Career_Site",
        "ats": "workday",
    },
    {
        "name": "Oracle",
        "url": "https://oracle.taleo.net/careersection/2/jobsearch.ftl",
        "ats": "generic",
    },
    {
        "name": "Adobe",
        "url": "https://careers.adobe.com/us/en/search-results",
        "ats": "generic",
    },
    {
        "name": "Nvidia",
        "url": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite",
        "ats": "workday",
    },

    # Unicorns & High-Growth
    {
        "name": "Stripe",
        "url": "https://stripe.com/jobs/search",
        "ats": "greenhouse",
    },
    {
        "name": "Databricks",
        "url": "https://www.databricks.com/company/careers",
        "ats": "greenhouse",
    },
    {
        "name": "Snowflake",
        "url": "https://careers.snowflake.com/us/en/search-results",
        "ats": "generic",
    },
    {
        "name": "Airbnb",
        "url": "https://careers.airbnb.com/positions/",
        "ats": "greenhouse",
    },
    {
        "name": "Uber",
        "url": "https://www.uber.com/careers/list/",
        "ats": "generic",
    },
    {
        "name": "Lyft",
        "url": "https://www.lyft.com/careers",
        "ats": "greenhouse",
    },
    {
        "name": "DoorDash",
        "url": "https://careers.doordash.com/jobs/",
        "ats": "greenhouse",
    },

    # AI & ML Companies
    {
        "name": "OpenAI",
        "url": "https://openai.com/careers/",
        "ats": "greenhouse",
    },
    {
        "name": "Anthropic",
        "url": "https://www.anthropic.com/careers",
        "ats": "ashby",
    },
    {
        "name": "DeepMind",
        "url": "https://www.deepmind.com/careers",
        "ats": "generic",
    },
    {
        "name": "Scale AI",
        "url": "https://scale.com/careers",
        "ats": "greenhouse",
    },

    # Cloud & Infrastructure
    {
        "name": "Cloudflare",
        "url": "https://www.cloudflare.com/careers/jobs/",
        "ats": "greenhouse",
    },
    {
        "name": "MongoDB",
        "url": "https://www.mongodb.com/careers",
        "ats": "greenhouse",
    },
    {
        "name": "HashiCorp",
        "url": "https://www.hashicorp.com/jobs",
        "ats": "greenhouse",
    },
    {
        "name": "Confluent",
        "url": "https://www.confluent.io/careers/",
        "ats": "greenhouse",
    },

    # FinTech
    {
        "name": "Coinbase",
        "url": "https://www.coinbase.com/careers/positions",
        "ats": "greenhouse",
    },
    {
        "name": "Plaid",
        "url": "https://plaid.com/careers/",
        "ats": "greenhouse",
    },
    {
        "name": "Square (Block)",
        "url": "https://careers.squareup.com/us/en/jobs",
        "ats": "generic",
    },
    {
        "name": "Robinhood",
        "url": "https://robinhood.com/us/en/careers/openings/",
        "ats": "greenhouse",
    },

    # Social & Communication
    {
        "name": "Snap",
        "url": "https://snap.com/en-US/jobs",
        "ats": "generic",
    },
    {
        "name": "Twitter (X)",
        "url": "https://careers.twitter.com/en/roles.html",
        "ats": "generic",
    },
    {
        "name": "Discord",
        "url": "https://discord.com/careers",
        "ats": "greenhouse",
    },
    {
        "name": "Reddit",
        "url": "https://www.redditinc.com/careers",
        "ats": "greenhouse",
    },
    {
        "name": "Slack",
        "url": "https://slack.com/careers",
        "ats": "generic",
    },

    # E-commerce & Marketplace
    {
        "name": "Shopify",
        "url": "https://www.shopify.com/careers/search",
        "ats": "greenhouse",
    },
    {
        "name": "Instacart",
        "url": "https://instacart.careers/",
        "ats": "greenhouse",
    },

    # Developer Tools
    {
        "name": "GitHub",
        "url": "https://github.com/about/careers",
        "ats": "generic",
    },
    {
        "name": "GitLab",
        "url": "https://about.gitlab.com/jobs/",
        "ats": "greenhouse",
    },
    {
        "name": "Atlassian",
        "url": "https://www.atlassian.com/company/careers/all-jobs",
        "ats": "generic",
    },
    {
        "name": "Vercel",
        "url": "https://vercel.com/careers",
        "ats": "ashby",
    },
]


# Technical role keywords for filtering
TECHNICAL_KEYWORDS = [
    # Software Engineering
    "software engineer",
    "backend engineer",
    "frontend engineer",
    "full stack",
    "fullstack",
    "web developer",
    "mobile developer",
    "ios developer",
    "android developer",
    "application developer",

    # Specialized Engineering
    "machine learning engineer",
    "ml engineer",
    "ai engineer",
    "data engineer",
    "data scientist",
    "research scientist",
    "applied scientist",
    "mlops",

    # Infrastructure & DevOps
    "devops engineer",
    "site reliability engineer",
    "sre",
    "cloud engineer",
    "infrastructure engineer",
    "platform engineer",
    "systems engineer",

    # Security
    "security engineer",
    "security analyst",
    "cybersecurity",
    "appsec",
    "infosec",

    # Leadership
    "engineering manager",
    "tech lead",
    "principal engineer",
    "staff engineer",
    "architect",
    "cto",

    # Data & Analytics
    "data analyst",
    "analytics engineer",
    "business intelligence",

    # QA & Testing
    "qa engineer",
    "test engineer",
    "sdet",
    "automation engineer",

    # Product & Design Tech
    "product manager",  # Technical PM
    "technical program manager",
    "tpm",
]


# Non-technical keywords to exclude
EXCLUDE_KEYWORDS = [
    "sales",
    "marketing",
    "recruiter",
    "recruiting",
    "hr",
    "human resources",
    "finance",
    "legal",
    "admin",
    "administrative",
    "office manager",
    "account manager",
    "customer success",
    "customer support",
    "operations coordinator",
    "facilities",
]


def get_all_companies() -> List[Dict]:
    """Get all tech companies."""
    return TECH_COMPANIES


def get_companies_by_ats(ats: str) -> List[Dict]:
    """Get companies using a specific ATS."""
    return [c for c in TECH_COMPANIES if c["ats"] == ats]


def is_technical_role(title: str, description: str = "") -> bool:
    """
    Determine if a role is technical based on title and description.

    Args:
        title: Job title
        description: Job description (optional)

    Returns:
        True if role is technical
    """
    combined = f"{title} {description}".lower()

    # First check exclusions
    if any(keyword in combined for keyword in EXCLUDE_KEYWORDS):
        return False

    # Then check technical keywords
    return any(keyword in combined for keyword in TECHNICAL_KEYWORDS)
