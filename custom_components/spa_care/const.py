"""Top-level constants. Most defaults live in domain/; this only adds
HA-glue identifiers and tunables that the coordinator/config flow need.
"""

from __future__ import annotations

DOMAIN = "spa_care"
PLATFORMS = ("sensor", "binary_sensor", "number", "button")

# HA Store keys
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}_state"

# Config-entry option keys
CONF_NAME = "name"
CONF_VOLUME_L = "volume_l"
CONF_TARGETS = "targets"
CONF_PRODUCTS = "products"          # list of selected product keys
CONF_QUIET_HOURS_START = "quiet_hours_start"
CONF_QUIET_HOURS_END = "quiet_hours_end"

# Default poll cadence for the rule-engine hourly tick
HOURLY_TICK_SECONDS = 3600
