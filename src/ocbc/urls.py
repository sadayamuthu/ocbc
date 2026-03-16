"""Default OSCAL JSON download URLs from the official usnistgov/oscal-content repo.

If NIST changes these paths, update here or override via CLI flags.
Source repo: https://github.com/usnistgov/oscal-content
"""

_BASE = "https://raw.githubusercontent.com/usnistgov/oscal-content/main/nist.gov/SP800-53/rev5/json"

CATALOG_URL = f"{_BASE}/NIST_SP-800-53_rev5_catalog.json"

BASELINE_LOW_URL = f"{_BASE}/NIST_SP-800-53_rev5_LOW-baseline_profile.json"

BASELINE_MODERATE_URL = f"{_BASE}/NIST_SP-800-53_rev5_MODERATE-baseline_profile.json"

BASELINE_HIGH_URL = f"{_BASE}/NIST_SP-800-53_rev5_HIGH-baseline_profile.json"

BASELINE_PRIVACY_URL = f"{_BASE}/NIST_SP-800-53_rev5_PRIVACY-baseline_profile.json"

_FEDRAMP_BASE = "https://raw.githubusercontent.com/GSA/fedramp-automation/master/dist/content/rev5/baselines/json"

FEDRAMP_LI_SAAS_URL = f"{_FEDRAMP_BASE}/FedRAMP_rev5_LI-SaaS-baseline_profile.json"

FEDRAMP_LOW_URL = f"{_FEDRAMP_BASE}/FedRAMP_rev5_LOW-baseline_profile.json"

FEDRAMP_MODERATE_URL = f"{_FEDRAMP_BASE}/FedRAMP_rev5_MODERATE-baseline_profile.json"

FEDRAMP_HIGH_URL = f"{_FEDRAMP_BASE}/FedRAMP_rev5_HIGH-baseline_profile.json"
