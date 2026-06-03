"""
IgniteIQ Vault SDK — LlamaIndex integration.

This module is an optional integration and does NOT require LlamaIndex to be
installed in order to import the rest of the SDK.  If LlamaIndex is not
installed, ``VaultDataSource`` will not be defined and attempting to use it
will raise an ``ImportError`` with a clear message.

Installation
------------
::

    pip install "igniteiq-vault[llamaindex]"

Example
-------
::

    from igniteiq import VaultClient
    from igniteiq.llamaindex import VaultDataSource

    client = VaultClient(api_key="iq_live_...", org_slug="tapps")
    source = VaultDataSource(client=client)

    # Load context as LlamaIndex Documents
    docs = source.load_data(period="last_30_days")
    print(docs[0].text[:200])

    # Use inside a VectorStoreIndex
    from llama_index.core import VectorStoreIndex
    index = VectorStoreIndex.from_documents(docs)
    query_engine = index.as_query_engine()
    response = query_engine.query("What was our revenue last month?")
    print(response)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .client import VaultClient

try:
    from llama_index.core import Document
    from llama_index.core.readers.base import BaseReader

    class VaultDataSource(BaseReader):
        """LlamaIndex reader that loads IgniteIQ Vault context snapshots as Documents.

        Each call to :meth:`load_data` returns a single :class:`~llama_index.core.Document`
        whose text is the ``systemPromptFragment`` from the Vault context
        snapshot.  The full structured data is stored in ``metadata``.

        Parameters
        ----------
        client : VaultClient
            An authenticated :class:`igniteiq.VaultClient` instance.

        Example
        -------
        ::

            from igniteiq import VaultClient
            from igniteiq.llamaindex import VaultDataSource

            client = VaultClient(api_key="iq_live_...", org_slug="tapps")
            source = VaultDataSource(client=client)
            docs = source.load_data(period="last_30_days")
        """

        def __init__(self, client: "VaultClient") -> None:
            self.client = client

        def load_data(
            self,
            period: str = "last_30_days",
            division_slug: str | None = None,
        ) -> list[Any]:
            """Load the context snapshot and return it as a list of Documents.

            Parameters
            ----------
            period : str, optional
                Time window for the snapshot.  Defaults to ``"last_30_days"``.
            division_slug : str | None, optional
                Scope to a specific division.

            Returns
            -------
            list[Document]
                A single-element list containing the context snapshot as a
                LlamaIndex ``Document``.
            """
            ctx = self.client.context_sync(period=period, division_slug=division_slug)
            text = ctx.get("systemPromptFragment", "")
            metadata = {
                "period": ctx.get("period", period),
                "generated_at": ctx.get("generatedAt", ""),
                "org_slug": self.client.org_slug,
                "source": "igniteiq-vault",
            }
            # Store structured summaries in metadata for downstream retrieval
            for key in ("revenue", "jobs", "ar", "technicians"):
                if key in ctx:
                    metadata[key] = str(ctx[key])
            return [Document(text=text, metadata=metadata)]

        async def aload_data(
            self,
            period: str = "last_30_days",
            division_slug: str | None = None,
        ) -> list[Any]:
            """Async version of :meth:`load_data`."""
            ctx = await self.client.context(period=period, division_slug=division_slug)
            text = ctx.get("systemPromptFragment", "")
            metadata = {
                "period": ctx.get("period", period),
                "generated_at": ctx.get("generatedAt", ""),
                "org_slug": self.client.org_slug,
                "source": "igniteiq-vault",
            }
            for key in ("revenue", "jobs", "ar", "technicians"):
                if key in ctx:
                    metadata[key] = str(ctx[key])
            return [Document(text=text, metadata=metadata)]

except ImportError:
    # LlamaIndex is not installed.  Provide a helpful error when VaultDataSource is accessed.
    class VaultDataSource:  # type: ignore[no-redef]
        """Placeholder that raises ImportError when llama-index-core is not installed."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise ImportError(
                "VaultDataSource requires llama-index-core.  "
                'Install it with: pip install "igniteiq-vault[llamaindex]"'
            )
