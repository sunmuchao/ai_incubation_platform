"""
AI Hires Human - Python SDK

Python SDK for AI Hires Human platform.
Allows AI agents and employers to interact with the platform programmatically.
"""

__version__ = "1.0.0"
__author__ = "AI Hires Human Team"

from .client import Client, APIError
from .models import Task, Worker, Organization, Member

__all__ = [
    "Client",
    "APIError",
    "Task",
    "Worker",
    "Organization",
    "Member",
]
