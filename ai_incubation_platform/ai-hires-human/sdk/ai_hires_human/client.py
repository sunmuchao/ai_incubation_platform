"""
AI Hires Human SDK - Client module.

Main client class for interacting with the AI Hires Human platform.
"""
import os
from typing import Any, Dict, List, Optional

import httpx


class APIError(Exception):
    """API 请求异常。"""
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API Error {status_code}: {detail}")


class Client:
    """
    AI Hires Human platform client.

    Usage:
        client = Client(api_key="your_api_key", base_url="http://localhost:8004")

        # Create a task
        task = client.tasks.create(
            title="Verify store status",
            description="Go to the store and take a photo",
            reward_amount=10.0
        )

        # Get task status
        status = client.tasks.get(task.id)

        # Get worker recommendations
        workers = client.recommendations.get_workers(task.id)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Initialize the client.

        Args:
            api_key: API key for authentication. Defaults to AI_HIRES_HUMAN_API_KEY env var.
            base_url: Base URL of the API. Defaults to AI_HIRES_HUMAN_BASE_URL env var or http://localhost:8004.
            timeout: Request timeout in seconds.
        """
        self.api_key = api_key or os.getenv("AI_HIRES_HUMAN_API_KEY")
        self.base_url = base_url or os.getenv("AI_HIRES_HUMAN_BASE_URL", "http://localhost:8004")
        self.timeout = timeout

        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={
                "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
                "Content-Type": "application/json",
            },
        )

        # Initialize sub-clients
        self.tasks = TasksClient(self._client)
        self.workers = WorkersClient(self._client)
        self.recommendations = RecommendationsClient(self._client)
        self.reputation = ReputationClient(self._client)
        self.team = TeamClient(self._client)
        self.dashboard = DashboardClient(self._client)

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Make an API request."""
        try:
            response = self._client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            detail = e.response.json().get("detail", str(e))
            raise APIError(e.response.status_code, detail)
        except httpx.RequestError as e:
            raise APIError(0, f"Request failed: {str(e)}")

    def close(self):
        """Close the client connection."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ==================== Sub-clients ====================

class TasksClient:
    """Tasks API client."""

    def __init__(self, http_client: httpx.Client):
        self._client = http_client

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        try:
            response = self._client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            detail = e.response.json().get("detail", str(e))
            raise APIError(e.response.status_code, detail)

    def create(
        self,
        title: str,
        description: str,
        reward_amount: float,
        requirements: Optional[List[str]] = None,
        acceptance_criteria: Optional[List[str]] = None,
        interaction_type: str = "digital",
        capability_gap: str = "",
        location_hint: Optional[str] = None,
        required_skills: Optional[Dict] = None,
        priority: str = "medium",
        callback_url: Optional[str] = None,
    ) -> "Task":
        """Create a new task."""
        data = {
            "title": title,
            "description": description,
            "requirements": requirements or [],
            "interaction_type": interaction_type,
            "capability_gap": capability_gap,
            "acceptance_criteria": acceptance_criteria or [],
            "location_hint": location_hint,
            "required_skills": required_skills or {},
            "priority": priority,
            "reward_amount": reward_amount,
            "callback_url": callback_url,
        }
        response = self._request("POST", "/api/tasks", json=data)
        return Task(response)

    def get(self, task_id: str) -> "Task":
        """Get a task by ID."""
        response = self._request("GET", f"/api/tasks/{task_id}")
        return Task(response)

    def list(
        self,
        status: Optional[str] = None,
        interaction_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List["Task"]:
        """List tasks with optional filters."""
        params = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        if interaction_type:
            params["interaction_type"] = interaction_type

        response = self._request("GET", "/api/tasks", params=params)
        return [Task(item) for item in response.get("tasks", [])]

    def search(self, query: str, limit: int = 20) -> List["Task"]:
        """Search tasks by keyword."""
        response = self._request("GET", "/api/tasks/search", params={"q": query, "limit": limit})
        return [Task(item) for item in response.get("tasks", [])]

    def update(self, task_id: str, **updates) -> "Task":
        """Update a task."""
        response = self._request("PUT", f"/api/tasks/{task_id}", json=updates)
        return Task(response)

    def cancel(self, task_id: str) -> Dict[str, Any]:
        """Cancel a task."""
        return self._request("POST", f"/api/tasks/{task_id}/cancel")

    def submit(
        self,
        task_id: str,
        delivery_content: str,
        delivery_attachments: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Submit task delivery."""
        data = {
            "delivery_content": delivery_content,
            "delivery_attachments": delivery_attachments or [],
        }
        return self._request("POST", f"/api/tasks/{task_id}/submit", json=data)

    def approve(self, task_id: str) -> Dict[str, Any]:
        """Approve task delivery."""
        return self._request("POST", f"/api/tasks/{task_id}/approve")

    def reject(self, task_id: str, reason: str) -> Dict[str, Any]:
        """Reject task delivery."""
        return self._request("POST", f"/api/tasks/{task_id}/reject", params={"reason": reason})


class WorkersClient:
    """Workers API client."""

    def __init__(self, http_client: httpx.Client):
        self._client = http_client

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        try:
            response = self._client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            detail = e.response.json().get("detail", str(e))
            raise APIError(e.response.status_code, detail)

    def get(self, worker_id: str) -> "Worker":
        """Get worker profile."""
        response = self._request("GET", f"/api/workers/{worker_id}")
        return Worker(response)

    def list(
        self,
        skill: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 100,
    ) -> List["Worker"]:
        """List workers with optional filters."""
        params = {"limit": limit}
        if skill:
            params["skill"] = skill
        if location:
            params["location"] = location

        response = self._request("GET", "/api/workers", params=params)
        return [Worker(item) for item in response.get("workers", [])]


class RecommendationsClient:
    """Recommendations API client."""

    def __init__(self, http_client: httpx.Client):
        self._client = http_client

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        try:
            response = self._client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            detail = e.response.json().get("detail", str(e))
            raise APIError(e.response.status_code, detail)

    def get_workers(self, task_id: str, limit: int = 10) -> List["Worker"]:
        """Get recommended workers for a task."""
        response = self._request("GET", "/api/recommendations/workers", params={"task_id": task_id, "limit": limit})
        return [Worker(item) for item in response.get("recommendations", [])]


class ReputationClient:
    """Reputation API client."""

    def __init__(self, http_client: httpx.Client):
        self._client = http_client

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        try:
            response = self._client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            detail = e.response.json().get("detail", str(e))
            raise APIError(e.response.status_code, detail)

    def get(self, user_id: str) -> Dict[str, Any]:
        """Get user reputation."""
        return self._request("GET", "/api/reputation", params={"user_id": user_id})

    def update(self, user_id: str, rating: float, review: Optional[str] = None) -> Dict[str, Any]:
        """Update user reputation."""
        return self._request("POST", "/api/reputation", json={"user_id": user_id, "rating": rating, "review": review})


class TeamClient:
    """Team API client."""

    def __init__(self, http_client: httpx.Client):
        self._client = http_client

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        try:
            response = self._client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            detail = e.response.json().get("detail", str(e))
            raise APIError(e.response.status_code, detail)

    def create_organization(
        self,
        org_name: str,
        org_type: str = "enterprise",
        description: Optional[str] = None,
        contact_email: Optional[str] = None,
        current_user_id: str = "system",
    ) -> "Organization":
        """Create a new organization."""
        data = {
            "org_name": org_name,
            "org_type": org_type,
            "description": description,
            "contact_email": contact_email,
        }
        response = self._request(
            "POST",
            "/api/team/organizations",
            json=data,
            params={"current_user_id": current_user_id},
        )
        return Organization(response)

    def list_organizations(self, current_user_id: str = "system") -> List["Organization"]:
        """List organizations for a user."""
        response = self._request(
            "GET",
            "/api/team/organizations",
            params={"current_user_id": current_user_id},
        )
        return [Organization(item) for item in response]

    def get_organization(self, org_id: str, current_user_id: str = "system") -> "Organization":
        """Get organization details."""
        response = self._request(
            "GET",
            f"/api/team/organizations/{org_id}",
            params={"current_user_id": current_user_id},
        )
        return Organization(response)

    def list_members(self, org_id: str, current_user_id: str = "system") -> List["Member"]:
        """List organization members."""
        response = self._request(
            "GET",
            f"/api/team/organizations/{org_id}/members",
            params={"current_user_id": current_user_id},
        )
        return [Member(item) for item in response]

    def invite_member(
        self,
        org_id: str,
        invitee_email: str,
        role_id: str,
        current_user_id: str = "system",
    ) -> Dict[str, Any]:
        """Invite a new member to the organization."""
        data = {"invitee_email": invitee_email, "role_id": role_id}
        return self._request(
            "POST",
            f"/api/team/organizations/{org_id}/invitations",
            json=data,
            params={"current_user_id": current_user_id},
        )

    def get_my_permissions(self, org_id: str, current_user_id: str = "system") -> Dict[str, Any]:
        """Get current user's permissions in an organization."""
        return self._request(
            "GET",
            f"/api/team/organizations/{org_id}/my-permissions",
            params={"current_user_id": current_user_id},
        )


class DashboardClient:
    """Dashboard API client."""

    def __init__(self, http_client: httpx.Client):
        self._client = http_client

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        try:
            response = self._client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            detail = e.response.json().get("detail", str(e))
            raise APIError(e.response.status_code, detail)

    def get_overview(self, time_range: str = "realtime") -> Dict[str, Any]:
        """Get dashboard overview metrics."""
        return self._request("GET", "/api/dashboard/overview", params={"time_range": time_range})

    def get_tasks_analysis(self) -> Dict[str, Any]:
        """Get task analysis data."""
        return self._request("GET", "/api/dashboard/tasks")

    def get_workers_analysis(self) -> Dict[str, Any]:
        """Get worker analysis data."""
        return self._request("GET", "/api/dashboard/workers")

    def get_quality_analysis(self) -> Dict[str, Any]:
        """Get quality analysis data."""
        return self._request("GET", "/api/dashboard/quality")

    def get_financial_analysis(self) -> Dict[str, Any]:
        """Get financial analysis data."""
        return self._request("GET", "/api/dashboard/financial")

    def get_task_trend(self, days: int = 7) -> Dict[str, Any]:
        """Get task trend data."""
        return self._request("GET", "/api/dashboard/trend/tasks", params={"days": days})

    def get_financial_trend(self, days: int = 7) -> Dict[str, Any]:
        """Get financial trend data."""
        return self._request("GET", "/api/dashboard/trend/financial", params={"days": days})
