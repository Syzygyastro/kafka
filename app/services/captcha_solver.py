"""Captcha solving service using external providers."""

import asyncio
import base64
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional

from loguru import logger

from app.core.config import settings
from app.core.exceptions import CaptchaException


class CaptchaType(str, Enum):
    """Supported captcha types."""

    IMAGE = "image"
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    FUNCAPTCHA = "funcaptcha"
    TURNSTILE = "turnstile"  # Cloudflare


class BaseCaptchaSolver(ABC):
    """Abstract base class for captcha solvers."""

    @abstractmethod
    async def solve_image(self, image_base64: str) -> str:
        """Solve an image captcha."""
        pass

    @abstractmethod
    async def solve_recaptcha_v2(
        self, site_key: str, page_url: str, invisible: bool = False
    ) -> str:
        """Solve reCAPTCHA v2."""
        pass

    @abstractmethod
    async def solve_recaptcha_v3(
        self, site_key: str, page_url: str, action: str = "verify", min_score: float = 0.3
    ) -> str:
        """Solve reCAPTCHA v3."""
        pass

    @abstractmethod
    async def solve_hcaptcha(self, site_key: str, page_url: str) -> str:
        """Solve hCaptcha."""
        pass

    @abstractmethod
    async def solve_turnstile(self, site_key: str, page_url: str) -> str:
        """Solve Cloudflare Turnstile."""
        pass

    @abstractmethod
    async def get_balance(self) -> float:
        """Get account balance."""
        pass


class TwoCaptchaSolver(BaseCaptchaSolver):
    """2Captcha API implementation."""

    API_BASE = "https://2captcha.com"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None

    async def _get_client(self):
        """Get HTTP client."""
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(timeout=120)
        return self._client

    async def _submit_task(self, params: Dict[str, Any]) -> str:
        """Submit a captcha solving task."""
        client = await self._get_client()
        params["key"] = self.api_key
        params["json"] = 1

        response = await client.post(
            f"{self.API_BASE}/in.php",
            data=params,
        )
        result = response.json()

        if result.get("status") != 1:
            raise CaptchaException(
                f"Failed to submit captcha: {result.get('error_text', 'Unknown error')}"
            )

        return result["request"]

    async def _get_result(self, task_id: str, max_wait: int = 180) -> str:
        """Wait for and get captcha solution."""
        client = await self._get_client()

        for _ in range(max_wait // 5):
            await asyncio.sleep(5)

            response = await client.get(
                f"{self.API_BASE}/res.php",
                params={
                    "key": self.api_key,
                    "action": "get",
                    "id": task_id,
                    "json": 1,
                },
            )
            result = response.json()

            if result.get("status") == 1:
                return result["request"]
            elif result.get("request") == "CAPCHA_NOT_READY":
                continue
            else:
                raise CaptchaException(
                    f"Captcha solving failed: {result.get('error_text', 'Unknown error')}"
                )

        raise CaptchaException("Captcha solving timeout")

    async def solve_image(self, image_base64: str) -> str:
        """Solve an image captcha."""
        task_id = await self._submit_task({
            "method": "base64",
            "body": image_base64,
        })
        return await self._get_result(task_id)

    async def solve_recaptcha_v2(
        self, site_key: str, page_url: str, invisible: bool = False
    ) -> str:
        """Solve reCAPTCHA v2."""
        params = {
            "method": "userrecaptcha",
            "googlekey": site_key,
            "pageurl": page_url,
        }
        if invisible:
            params["invisible"] = 1

        task_id = await self._submit_task(params)
        return await self._get_result(task_id)

    async def solve_recaptcha_v3(
        self, site_key: str, page_url: str, action: str = "verify", min_score: float = 0.3
    ) -> str:
        """Solve reCAPTCHA v3."""
        task_id = await self._submit_task({
            "method": "userrecaptcha",
            "googlekey": site_key,
            "pageurl": page_url,
            "version": "v3",
            "action": action,
            "min_score": min_score,
        })
        return await self._get_result(task_id)

    async def solve_hcaptcha(self, site_key: str, page_url: str) -> str:
        """Solve hCaptcha."""
        task_id = await self._submit_task({
            "method": "hcaptcha",
            "sitekey": site_key,
            "pageurl": page_url,
        })
        return await self._get_result(task_id)

    async def solve_turnstile(self, site_key: str, page_url: str) -> str:
        """Solve Cloudflare Turnstile."""
        task_id = await self._submit_task({
            "method": "turnstile",
            "sitekey": site_key,
            "pageurl": page_url,
        })
        return await self._get_result(task_id)

    async def get_balance(self) -> float:
        """Get account balance."""
        client = await self._get_client()
        response = await client.get(
            f"{self.API_BASE}/res.php",
            params={
                "key": self.api_key,
                "action": "getbalance",
                "json": 1,
            },
        )
        result = response.json()
        return float(result.get("request", 0))

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


class AntiCaptchaSolver(BaseCaptchaSolver):
    """Anti-Captcha API implementation."""

    API_BASE = "https://api.anti-captcha.com"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None

    async def _get_client(self):
        """Get HTTP client."""
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(timeout=120)
        return self._client

    async def _create_task(self, task: Dict[str, Any]) -> int:
        """Create a captcha solving task."""
        client = await self._get_client()

        response = await client.post(
            f"{self.API_BASE}/createTask",
            json={
                "clientKey": self.api_key,
                "task": task,
            },
        )
        result = response.json()

        if result.get("errorId") != 0:
            raise CaptchaException(
                f"Failed to create task: {result.get('errorDescription', 'Unknown error')}"
            )

        return result["taskId"]

    async def _get_task_result(self, task_id: int, max_wait: int = 180) -> str:
        """Wait for and get task result."""
        client = await self._get_client()

        for _ in range(max_wait // 5):
            await asyncio.sleep(5)

            response = await client.post(
                f"{self.API_BASE}/getTaskResult",
                json={
                    "clientKey": self.api_key,
                    "taskId": task_id,
                },
            )
            result = response.json()

            if result.get("errorId") != 0:
                raise CaptchaException(
                    f"Task failed: {result.get('errorDescription', 'Unknown error')}"
                )

            if result.get("status") == "ready":
                solution = result.get("solution", {})
                return (
                    solution.get("gRecaptchaResponse")
                    or solution.get("token")
                    or solution.get("text")
                    or str(solution)
                )
            elif result.get("status") == "processing":
                continue

        raise CaptchaException("Captcha solving timeout")

    async def solve_image(self, image_base64: str) -> str:
        """Solve an image captcha."""
        task_id = await self._create_task({
            "type": "ImageToTextTask",
            "body": image_base64,
        })
        return await self._get_task_result(task_id)

    async def solve_recaptcha_v2(
        self, site_key: str, page_url: str, invisible: bool = False
    ) -> str:
        """Solve reCAPTCHA v2."""
        task_type = "RecaptchaV2TaskProxyless"
        if invisible:
            task_type = "RecaptchaV2EnterpriseTaskProxyless"

        task_id = await self._create_task({
            "type": task_type,
            "websiteURL": page_url,
            "websiteKey": site_key,
            "isInvisible": invisible,
        })
        return await self._get_task_result(task_id)

    async def solve_recaptcha_v3(
        self, site_key: str, page_url: str, action: str = "verify", min_score: float = 0.3
    ) -> str:
        """Solve reCAPTCHA v3."""
        task_id = await self._create_task({
            "type": "RecaptchaV3TaskProxyless",
            "websiteURL": page_url,
            "websiteKey": site_key,
            "minScore": min_score,
            "pageAction": action,
        })
        return await self._get_task_result(task_id)

    async def solve_hcaptcha(self, site_key: str, page_url: str) -> str:
        """Solve hCaptcha."""
        task_id = await self._create_task({
            "type": "HCaptchaTaskProxyless",
            "websiteURL": page_url,
            "websiteKey": site_key,
        })
        return await self._get_task_result(task_id)

    async def solve_turnstile(self, site_key: str, page_url: str) -> str:
        """Solve Cloudflare Turnstile."""
        task_id = await self._create_task({
            "type": "TurnstileTaskProxyless",
            "websiteURL": page_url,
            "websiteKey": site_key,
        })
        return await self._get_task_result(task_id)

    async def get_balance(self) -> float:
        """Get account balance."""
        client = await self._get_client()
        response = await client.post(
            f"{self.API_BASE}/getBalance",
            json={"clientKey": self.api_key},
        )
        result = response.json()
        return float(result.get("balance", 0))

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


class CaptchaSolver:
    """
    Unified captcha solving service.

    Supports multiple providers and automatic fallback.
    """

    def __init__(self):
        self._solver: Optional[BaseCaptchaSolver] = None
        self._stats = {
            "total_solved": 0,
            "total_failed": 0,
            "by_type": {},
        }

        # Initialize based on configuration
        if settings.captcha_solver_enabled:
            if settings.captcha_solver_provider == "2captcha" and settings.twocaptcha_api_key:
                self._solver = TwoCaptchaSolver(settings.twocaptcha_api_key)
                logger.info("Initialized 2captcha solver")
            elif settings.captcha_solver_provider == "anticaptcha" and settings.anticaptcha_api_key:
                self._solver = AntiCaptchaSolver(settings.anticaptcha_api_key)
                logger.info("Initialized Anti-Captcha solver")
            else:
                logger.warning("Captcha solving enabled but no valid API key configured")

    @property
    def is_available(self) -> bool:
        """Check if captcha solving is available."""
        return self._solver is not None

    async def solve(
        self,
        captcha_type: CaptchaType,
        **kwargs,
    ) -> str:
        """
        Solve a captcha.

        Args:
            captcha_type: Type of captcha to solve
            **kwargs: Captcha-specific parameters

        Returns:
            Solution token or text

        Raises:
            CaptchaException: If solving fails
        """
        if not self._solver:
            raise CaptchaException("No captcha solver configured")

        try:
            logger.info(f"Solving {captcha_type.value} captcha")

            if captcha_type == CaptchaType.IMAGE:
                result = await self._solver.solve_image(kwargs["image_base64"])
            elif captcha_type == CaptchaType.RECAPTCHA_V2:
                result = await self._solver.solve_recaptcha_v2(
                    kwargs["site_key"],
                    kwargs["page_url"],
                    kwargs.get("invisible", False),
                )
            elif captcha_type == CaptchaType.RECAPTCHA_V3:
                result = await self._solver.solve_recaptcha_v3(
                    kwargs["site_key"],
                    kwargs["page_url"],
                    kwargs.get("action", "verify"),
                    kwargs.get("min_score", 0.3),
                )
            elif captcha_type == CaptchaType.HCAPTCHA:
                result = await self._solver.solve_hcaptcha(
                    kwargs["site_key"],
                    kwargs["page_url"],
                )
            elif captcha_type == CaptchaType.TURNSTILE:
                result = await self._solver.solve_turnstile(
                    kwargs["site_key"],
                    kwargs["page_url"],
                )
            else:
                raise CaptchaException(f"Unsupported captcha type: {captcha_type}")

            # Update stats
            self._stats["total_solved"] += 1
            self._stats["by_type"][captcha_type.value] = (
                self._stats["by_type"].get(captcha_type.value, 0) + 1
            )

            logger.info(f"Successfully solved {captcha_type.value} captcha")
            return result

        except Exception as e:
            self._stats["total_failed"] += 1
            logger.error(f"Failed to solve {captcha_type.value} captcha: {e}")
            raise

    async def get_balance(self) -> Optional[float]:
        """Get captcha solver account balance."""
        if not self._solver:
            return None
        return await self._solver.get_balance()

    def get_stats(self) -> Dict[str, Any]:
        """Get solving statistics."""
        return self._stats.copy()

    async def close(self):
        """Close solver connections."""
        if self._solver and hasattr(self._solver, "close"):
            await self._solver.close()
