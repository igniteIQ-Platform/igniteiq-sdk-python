"""
IgniteIQ Vault SDK — VaultClient.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any

import httpx

from .errors import VaultError

DEFAULT_BASE_URL = "https://api.igniteiq.com"


class VaultClient:
    """Async-first client for the IgniteIQ Vault API.

    Parameters
    ----------
    api_key : str
        Your IgniteIQ API key (starts with ``iq_live_`` or ``iq_test_``).
        Obtain one from Studio → Settings → API Keys.
    org_slug : str
        Your organisation slug, e.g. ``tapps`` or ``airworks``.
    base_url : str, optional
        Override the API base URL.  Defaults to ``https://api.igniteiq.com``.

    Example
    -------
    Async usage::

        import asyncio
        from igniteiq import VaultClient

        client = VaultClient(api_key="iq_live_...", org_slug="tapps")

        async def main():
            result = await client.query({
                "measures": ["fact_jobs.total_revenue"],
                "timeDimensions": [{
                    "dimension": "fact_jobs.job_created_at",
                    "dateRange": "last 30 days",
                }],
                "limit": 100,
            })
            print(result["data"])

        asyncio.run(main())

    Sync usage::

        client = VaultClient(api_key="iq_live_...", org_slug="tapps")
        result = client.query_sync({"measures": ["fact_jobs.total_revenue"]})
        print(result["data"])
    """

    def __init__(
        self,
        api_key: str,
        org_slug: str,
        base_url: str = DEFAULT_BASE_URL,
    ) -> None:
        self.api_key = api_key
        self.org_slug = org_slug
        self.base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict:
        """Execute an authenticated HTTP request and return the parsed JSON body.

        Raises :class:`VaultError` on any non-2xx response.
        """
        async with httpx.AsyncClient() as http:
            res = await http.request(
                method,
                f"{self.base_url}{path}",
                headers=self._headers,
                timeout=30.0,
                **kwargs,
            )
            try:
                data = res.json()
            except Exception:
                data = {}

            if not res.is_success:
                err = data.get("error", {}) if isinstance(data, dict) else {}
                raise VaultError(
                    err.get("code", "API_ERROR"),
                    err.get("message", f"HTTP {res.status_code}"),
                    res.status_code,
                )
            return data

    def _sync(self, coro: Any) -> Any:
        """Run an async coroutine from synchronous code.

        Works whether or not an event loop is already running (e.g. inside a
        Jupyter notebook or a threaded web framework).
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Already inside a running loop (Jupyter, FastAPI, etc.) —
                # execute in a fresh thread with its own loop.
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(asyncio.run, coro)
                    return future.result()
            return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)

    # ------------------------------------------------------------------
    # Async API methods
    # ------------------------------------------------------------------

    async def query(self, query: dict) -> dict:
        """Execute a structured Vault query and return matching rows.

        Parameters
        ----------
        query : dict
            A Vault/Cube.dev-style query object with keys:
            ``measures``, ``dimensions``, ``timeDimensions``, ``filters``,
            ``limit``, ``offset``, ``order``.

        Returns
        -------
        dict
            ``{"data": list[dict], "query": dict, "lastRefreshTime": str}``

        Example
        -------
        >>> result = await client.query({
        ...     "measures": ["fact_jobs.total_revenue"],
        ...     "timeDimensions": [{
        ...         "dimension": "fact_jobs.job_created_at",
        ...         "dateRange": "last 30 days",
        ...     }],
        ...     "limit": 50,
        ... })
        >>> rows = result["data"]
        """
        return await self._request("POST", "/api/vault/query", json={"query": query})

    async def context(
        self,
        *,
        period: str = "last_30_days",
        division_slug: str | None = None,
    ) -> dict:
        """Fetch a structured context snapshot for an org or division.

        The snapshot includes a ``systemPromptFragment`` string that can be
        injected directly into an LLM system prompt to give the model
        up-to-date business context.

        Parameters
        ----------
        period : str, optional
            Time window.  Defaults to ``"last_30_days"``.
            Other values: ``"last_7_days"``, ``"last_90_days"``, ``"mtd"``,
            ``"ytd"``.
        division_slug : str | None, optional
            If provided, scopes the snapshot to a single ServiceTitan
            division (tenant).

        Returns
        -------
        dict
            Keys: ``systemPromptFragment``, ``period``, ``generatedAt``,
            ``revenue``, ``jobs``, ``ar``, ``technicians``.

        Example
        -------
        >>> ctx = await client.context(period="last_30_days")
        >>> system_prompt = ctx["systemPromptFragment"]
        """
        params: dict[str, str] = {"period": period}
        if division_slug:
            params["divisionSlug"] = division_slug
        return await self._request(
            "GET",
            f"/api/context/{self.org_slug}",
            params=params,
        )

    async def ask(
        self,
        question: str,
        *,
        division_slug: str | None = None,
    ) -> dict:
        """Ask a natural-language question about your business data.

        The platform translates the question into a structured Vault query,
        executes it, and returns a human-readable answer with confidence.

        Parameters
        ----------
        question : str
            Plain-English question, e.g. ``"What was our revenue last month?"``
        division_slug : str | None, optional
            Scope the query to a specific division.

        Returns
        -------
        dict
            Keys: ``answer`` (str), ``confidence`` (``"high"``/``"medium"``/
            ``"low"``), ``data`` (list), ``query`` (dict|None),
            ``caveats`` (list|None).

        Example
        -------
        >>> ans = await client.ask("What was our revenue last month?")
        >>> print(ans["answer"])
        """
        return await self._request(
            "POST",
            "/api/ask",
            json={"question": question, "orgSlug": self.org_slug, "divisionSlug": division_slug},
        )

    # ------------------------------------------------------------------
    # Schema sub-resource
    # ------------------------------------------------------------------

    class _Schema:
        """Access Vault schema and tool-definition endpoints."""

        def __init__(self, client: "VaultClient") -> None:
            self._client = client

        async def tools(self, fmt: str = "openai") -> dict:
            """Fetch LLM tool/function definitions for the Vault query endpoint.

            Parameters
            ----------
            fmt : str, optional
                Output format.  One of ``"openai"`` (default), ``"anthropic"``,
                ``"json-schema"``.

            Returns
            -------
            dict
                Tool definitions ready to pass to your LLM SDK's ``tools``
                parameter.

            Example
            -------
            >>> tools = await client.schema.tools("openai")
            >>> # Pass tools["tools"] to openai.chat.completions.create(tools=...)
            """
            return await self._client._request("GET", f"/api/schema/tools/{fmt}")

        async def openapi(self) -> dict:
            """Fetch the full OpenAPI 3.1 specification for the Vault API.

            Returns
            -------
            dict
                OpenAPI document as a Python dict.
            """
            return await self._client._request("GET", "/api/schema/openapi")

    @property
    def schema(self) -> "_Schema":
        """Access schema and tool-definition endpoints.

        Example
        -------
        >>> tools = await client.schema.tools("openai")
        >>> spec = await client.schema.openapi()
        """
        return self._Schema(self)

    # ------------------------------------------------------------------
    # Webhooks sub-resource
    # ------------------------------------------------------------------

    class _Webhooks:
        """Manage webhooks — create, list, delete.

        Requires an API key with the ``webhooks`` scope (create one in
        Studio → Settings → API Keys). Each method has an async form and a
        ``*_sync`` wrapper.
        """

        VALID_EVENTS = (
            "forge.run.completed",
            "forge.run.failed",
            "depot.sync.completed",
            "depot.sync.failed",
            "vault.schema.updated",
        )

        def __init__(self, client: "VaultClient") -> None:
            self._client = client

        async def create(
            self,
            url: str,
            events: list[str],
            *,
            secret: str | None = None,
        ) -> dict:
            """Register a webhook.

            If ``secret`` is omitted, IgniteIQ generates one and returns it
            **once** on the created webhook (``secret`` key) — store it to verify
            the ``X-IgniteIQ-Signature`` header on deliveries.

            Parameters
            ----------
            url : str
                HTTPS endpoint that will receive event POSTs.
            events : list[str]
                Subscribed events. See :attr:`VALID_EVENTS`.
            secret : str | None, optional
                Your signing secret. Omit to have IgniteIQ generate one.

            Returns
            -------
            dict
                Keys: ``id``, ``url``, ``events``, ``isActive``, ``createdAt``,
                and ``secret`` (only when generated).

            Example
            -------
            >>> wh = await client.webhooks.create(
            ...     "https://example.com/iq-hook",
            ...     ["forge.run.completed"],
            ... )
            >>> wh["secret"]  # 'whsec_...' (shown only here)
            """
            body: dict[str, Any] = {"url": url, "events": events}
            if secret is not None:
                body["secret"] = secret
            return await self._client._request("POST", "/api/webhooks", json=body)

        async def list(self) -> list[dict]:
            """List active webhooks for the organisation. Secrets are never returned."""
            res = await self._client._request("GET", "/api/webhooks")
            return res.get("webhooks", []) if isinstance(res, dict) else []

        async def delete(self, webhook_id: str) -> None:
            """Deactivate (delete) a webhook by id."""
            await self._client._request("DELETE", f"/api/webhooks/{webhook_id}")

        def create_sync(
            self,
            url: str,
            events: list[str],
            *,
            secret: str | None = None,
        ) -> dict:
            """Synchronous wrapper for :meth:`create`."""
            return self._client._sync(self.create(url, events, secret=secret))

        def list_sync(self) -> list[dict]:
            """Synchronous wrapper for :meth:`list`."""
            return self._client._sync(self.list())

        def delete_sync(self, webhook_id: str) -> None:
            """Synchronous wrapper for :meth:`delete`."""
            return self._client._sync(self.delete(webhook_id))

    @property
    def webhooks(self) -> "_Webhooks":
        """Manage webhooks — create, list, delete (requires ``webhooks`` scope).

        Example
        -------
        >>> wh = await client.webhooks.create("https://…", ["forge.run.completed"])
        >>> hooks = await client.webhooks.list()
        >>> await client.webhooks.delete(wh["id"])
        """
        return self._Webhooks(self)

    # ------------------------------------------------------------------
    # Sync wrappers
    # ------------------------------------------------------------------

    def query_sync(self, query: dict) -> dict:
        """Synchronous wrapper for :meth:`query`.

        Suitable for scripts, Django views, or any non-async context.

        Example
        -------
        >>> result = client.query_sync({"measures": ["fact_jobs.total_revenue"]})
        """
        return self._sync(self.query(query))

    def context_sync(
        self,
        *,
        period: str = "last_30_days",
        division_slug: str | None = None,
    ) -> dict:
        """Synchronous wrapper for :meth:`context`.

        Example
        -------
        >>> ctx = client.context_sync(period="last_30_days")
        """
        return self._sync(self.context(period=period, division_slug=division_slug))

    def ask_sync(self, question: str, *, division_slug: str | None = None) -> dict:
        """Synchronous wrapper for :meth:`ask`.

        Example
        -------
        >>> ans = client.ask_sync("What was our revenue last month?")
        """
        return self._sync(self.ask(question, division_slug=division_slug))
