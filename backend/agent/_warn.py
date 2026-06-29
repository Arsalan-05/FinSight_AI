"""Suppress known harmless third-party warnings on macOS / LangGraph."""

import warnings

warnings.filterwarnings("ignore", module="urllib3")

from langchain_core._api.deprecation import LangChainPendingDeprecationWarning

warnings.filterwarnings("ignore", category=LangChainPendingDeprecationWarning)
