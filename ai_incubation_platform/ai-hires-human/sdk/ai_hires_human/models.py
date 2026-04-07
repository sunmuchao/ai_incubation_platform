"""
AI Hires Human SDK - Models module.

Data models used by the SDK.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class Task:
    """Task model."""
    id: str
    ai_employer_id: str
    title: str
    description: str
    status: str
    reward_amount: float
    reward_currency: str
    interaction_type: str
    capability_gap: str
    requirements: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    location_hint: Optional[str] = None
    required_skills: Dict[str, Any] = field(default_factory=dict)
    priority: str = "medium"
    deadline: Optional[str] = None
    worker_id: Optional[str] = None
    delivery_content: Optional[str] = None
    callback_url: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "Task":
        """Create Task from API response."""
        return cls(
            id=data.get("id", ""),
            ai_employer_id=data.get("ai_employer_id", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            status=data.get("status", "pending"),
            reward_amount=data.get("reward_amount", 0.0),
            reward_currency=data.get("reward_currency", "CNY"),
            interaction_type=data.get("interaction_type", "digital"),
            capability_gap=data.get("capability_gap", ""),
            requirements=data.get("requirements", []),
            acceptance_criteria=data.get("acceptance_criteria", []),
            location_hint=data.get("location_hint"),
            required_skills=data.get("required_skills", {}),
            priority=data.get("priority", "medium"),
            deadline=data.get("deadline"),
            worker_id=data.get("worker_id"),
            delivery_content=data.get("delivery_content"),
            callback_url=data.get("callback_url"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def __post_init__(self):
        # If initialized from dict directly
        if isinstance(self.id, dict):
            data = self.id
            for key, value in data.items():
                if hasattr(self, key):
                    setattr(self, key, value)

    def is_completed(self) -> bool:
        """Check if task is completed."""
        return self.status == "completed"

    def is_pending(self) -> bool:
        """Check if task is pending."""
        return self.status in ["pending", "published"]


@dataclass
class Worker:
    """Worker model."""
    worker_id: str
    name: Optional[str] = None
    avatar: Optional[str] = None
    location: Optional[str] = None
    skills: Dict[str, Any] = field(default_factory=dict)
    completed_tasks: int = 0
    success_rate: float = 1.0
    average_rating: float = 5.0
    total_earnings: float = 0.0
    level: int = 1
    tags: List[str] = field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "Worker":
        """Create Worker from API response."""
        return cls(
            worker_id=data.get("worker_id", data.get("id", "")),
            name=data.get("name"),
            avatar=data.get("avatar"),
            location=data.get("location"),
            skills=data.get("skills", {}),
            completed_tasks=data.get("completed_tasks", 0),
            success_rate=data.get("success_rate", 1.0),
            average_rating=data.get("average_rating", 5.0),
            total_earnings=data.get("total_earnings", 0.0),
            level=data.get("level", 1),
            tags=data.get("tags", []),
        )

    def __post_init__(self):
        # If initialized from dict directly
        if isinstance(self.worker_id, dict):
            data = self.worker_id
            for key, value in data.items():
                if hasattr(self, key):
                    setattr(self, key, value)

    @property
    def is_highly_rated(self) -> bool:
        """Check if worker has high rating."""
        return self.average_rating >= 4.5


@dataclass
class Organization:
    """Organization model."""
    org_id: str
    org_name: str
    org_type: str = "enterprise"
    description: Optional[str] = None
    contact_email: Optional[str] = None
    status: str = "active"
    is_verified: bool = False
    max_members: int = 10
    member_count: Optional[int] = None
    created_at: Optional[str] = None

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "Organization":
        """Create Organization from API response."""
        return cls(
            org_id=data.get("org_id", ""),
            org_name=data.get("org_name", ""),
            org_type=data.get("org_type", "enterprise"),
            description=data.get("description"),
            contact_email=data.get("contact_email"),
            status=data.get("status", "active"),
            is_verified=data.get("is_verified", False),
            max_members=data.get("max_members", 10),
            member_count=data.get("member_count"),
            created_at=data.get("created_at"),
        )

    def __post_init__(self):
        # If initialized from dict directly
        if isinstance(self.org_id, dict):
            data = self.org_id
            for key, value in data.items():
                if hasattr(self, key):
                    setattr(self, key, value)


@dataclass
class Member:
    """Team member model."""
    member_id: str
    user_id: str
    role_id: str
    role_name: str
    role_name_zh: str
    permissions: List[str] = field(default_factory=list)
    status: str = "active"
    joined_at: Optional[str] = None

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "Member":
        """Create Member from API response."""
        return cls(
            member_id=data.get("member_id", ""),
            user_id=data.get("user_id", ""),
            role_id=data.get("role_id", ""),
            role_name=data.get("role_name", ""),
            role_name_zh=data.get("role_name_zh", ""),
            permissions=data.get("permissions", []),
            status=data.get("status", "active"),
            joined_at=data.get("joined_at"),
        )

    def __post_init__(self):
        # If initialized from dict directly
        if isinstance(self.member_id, dict):
            data = self.member_id
            for key, value in data.items():
                if hasattr(self, key):
                    setattr(self, key, value)

    @property
    def is_admin(self) -> bool:
        """Check if member is admin."""
        return "org_admin" in self.role_name or "admin" in self.role_name


# Alias for backward compatibility
WorkerProfile = Worker
