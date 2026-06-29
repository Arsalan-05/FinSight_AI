"""Suppress known harmless third-party warnings on macOS / LangGraph."""

import warnings

warnings.filterwarnings("ignore", module="urllib3")
warnings.filterwarnings("ignore", message="The default value of `allowed_objects`")
