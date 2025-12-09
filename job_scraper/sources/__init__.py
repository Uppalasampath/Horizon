"""
ATS-specific scrapers for different job board platforms.
"""
from .greenhouse import GreenhouseScraper
from .lever import LeverScraper
from .workday import WorkdayScraper
from .generic import GenericScraper

# Optional scrapers (may not be present in all configurations)
try:
    from .ashby import AshbyScraper
except ImportError:
    AshbyScraper = None

try:
    from .smartrecruiters import SmartRecruitersScraper
except ImportError:
    SmartRecruitersScraper = None

try:
    from .workable import WorkableScraper
except ImportError:
    WorkableScraper = None

try:
    from .icims import ICIMSScraper
except ImportError:
    ICIMSScraper = None

__all__ = [
    "GreenhouseScraper",
    "LeverScraper",
    "WorkdayScraper",
    "GenericScraper",
]

# Add optional scrapers if available
if AshbyScraper:
    __all__.append("AshbyScraper")
if SmartRecruitersScraper:
    __all__.append("SmartRecruitersScraper")
if WorkableScraper:
    __all__.append("WorkableScraper")
if ICIMSScraper:
    __all__.append("ICIMSScraper")
