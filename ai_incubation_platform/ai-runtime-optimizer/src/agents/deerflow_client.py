"""
DeerFlow Client - Unified Agent Framework Client

This module provides a client for interacting with the DeerFlow 2.0 framework,
with fallback support for local execution when DeerFlow is unavailable.
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DeerFlowClient:
    """
    DeerFlow 2.0 API Client with fallback support.

    This client handles communication with the DeerFlow framework,
    automatically falling back to local execution when the service is unavailable.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        fallback_enabled: bool = True,
        timeout: int = 30,
    ):
        """
        Initialize DeerFlow client.

        Args:
            api_key: DeerFlow API key (defaults to DEERFLOW_API_KEY env var)
            base_url: DeerFlow API base URL (defaults to DEERFLOW_BASE_URL env var)
            fallback_enabled: Whether to enable local fallback mode
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv("DEERFLOW_API_KEY")
        self.base_url = base_url or os.getenv("DEERFLOW_BASE_URL", "http://localhost:8000")
        self.fallback_enabled = fallback_enabled
        self.timeout = timeout
        self._available = None
        self._local_workflows: Dict[str, callable] = {}

    async def check_availability(self) -> bool:
        """Check if DeerFlow service is available."""
        if self._available is not None:
            return self._available

        try:
            import httpx
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/health",
                    headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
                )
                self._available = response.status_code == 200
        except Exception as e:
            logger.warning(f"DeerFlow service unavailable: {e}")
            self._available = False

        return self._available

    def is_available(self) -> bool:
        """Synchronous version of availability check."""
        if self._available is not None:
            return self._available
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.check_availability())
        except RuntimeError:
            # No event loop, create a new one
            return asyncio.run(self.check_availability())

    def register_local_workflow(self, name: str, handler: callable):
        """Register a local workflow for fallback mode."""
        self._local_workflows[name] = handler
        logger.info(f"Registered local workflow: {name}")

    async def run_workflow(
        self,
        name: str,
        **input_data: Any
    ) -> Dict[str, Any]:
        """
        Run a DeerFlow workflow with automatic fallback.

        Args:
            name: Workflow name
            **input_data: Workflow input parameters

        Returns:
            Workflow execution result
        """
        if await self.check_availability():
            return await self._run_remote_workflow(name, **input_data)
        elif self.fallback_enabled:
            logger.info(f"DeerFlow unavailable, using local fallback for workflow: {name}")
            return await self._run_local_workflow(name, **input_data)
        else:
            raise RuntimeError(
                f"DeerFlow service unavailable and fallback is disabled. "
                f"Attempted to run workflow: {name}"
            )

    async def _run_remote_workflow(
        self,
        name: str,
        **input_data: Any
    ) -> Dict[str, Any]:
        """Run workflow on remote DeerFlow service."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/workflows/{name}/run",
                    json=input_data,
                    headers={
                        "Authorization": f"Bearer {self.api_key}" if self.api_key else {},
                        "Content-Type": "application/json"
                    }
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Remote workflow execution failed: {e}")
            self._available = False  # Mark as unavailable for subsequent calls
            if self.fallback_enabled:
                return await self._run_local_workflow(name, **input_data)
            raise

    async def _run_local_workflow(
        self,
        name: str,
        **input_data: Any
    ) -> Dict[str, Any]:
        """Run workflow using local fallback implementation."""
        if name not in self._local_workflows:
            raise ValueError(f"Unknown workflow: {name}. No local handler registered.")

        handler = self._local_workflows[name]
        if asyncio.iscoroutinefunction(handler):
            return await handler(**input_data)
        return handler(**input_data)

    async def invoke_tool(
        self,
        tool_name: str,
        **parameters: Any
    ) -> Dict[str, Any]:
        """
        Invoke a DeerFlow tool.

        Args:
            tool_name: Tool name
            **parameters: Tool parameters

        Returns:
            Tool execution result
        """
        if await self.check_availability():
            return await self._invoke_remote_tool(tool_name, **parameters)
        else:
            raise RuntimeError("Tool invocation requires DeerFlow service")

    async def _invoke_remote_tool(
        self,
        tool_name: str,
        **parameters: Any
    ) -> Dict[str, Any]:
        """Invoke tool on remote DeerFlow service."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/tools/{tool_name}/invoke",
                    json=parameters,
                    headers={
                        "Authorization": f"Bearer {self.api_key}" if self.api_key else {},
                        "Content-Type": "application/json"
                    }
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Remote tool invocation failed: {e}")
            raise


# Global client instance
_deerflow_client: Optional[DeerFlowClient] = None


def get_deerflow_client(
    api_key: Optional[str] = None,
    fallback_enabled: bool = True,
) -> DeerFlowClient:
    """
    Get or create the global DeerFlow client instance.

    Args:
        api_key: Override API key
        fallback_enabled: Whether to enable local fallback

    Returns:
        DeerFlow client instance
    """
    global _deerflow_client
    if _deerflow_client is None:
        _deerflow_client = DeerFlowClient(
            api_key=api_key,
            fallback_enabled=fallback_enabled,
        )
    return _deerflow_client


def reset_deerflow_client():
    """Reset the global client instance (useful for testing)."""
    global _deerflow_client
    _deerflow_client = None
