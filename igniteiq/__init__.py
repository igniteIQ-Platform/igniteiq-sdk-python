"""
igniteiq — Python SDK for the IgniteIQ Vault API.

Quickstart
----------
::

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
        })
        print(result["data"])

    asyncio.run(main())

Sync usage::

    result = client.query_sync({"measures": ["fact_jobs.total_revenue"]})
"""

from .client import VaultClient
from .errors import VaultError

__all__ = ["VaultClient", "VaultError"]
__version__ = "0.2.0"
