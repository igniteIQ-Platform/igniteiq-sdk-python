"""
IgniteIQ Vault SDK — LangChain integration.

This module is an optional integration and does NOT require LangChain to be
installed in order to import the rest of the SDK.  If LangChain is not
installed, ``VaultTool`` will not be defined and attempting to use it will
raise an ``ImportError`` with a clear message.

Installation
------------
::

    pip install "igniteiq-vault[langchain]"

Example
-------
::

    from igniteiq import VaultClient
    from igniteiq.langchain import VaultTool

    client = VaultClient(api_key="iq_live_...", org_slug="tapps")
    tool = VaultTool(client=client)

    # Use with an agent
    from langchain_openai import ChatOpenAI
    from langchain.agents import AgentExecutor, create_tool_calling_agent
    from langchain_core.prompts import ChatPromptTemplate

    llm = ChatOpenAI(model="gpt-4o")
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful business analyst for a home services company."),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    agent = create_tool_calling_agent(llm, [tool], prompt)
    executor = AgentExecutor(agent=agent, tools=[tool])
    result = executor.invoke({"input": "What was our revenue last month?"})
    print(result["output"])
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .client import VaultClient

try:
    from langchain_core.tools import BaseTool
    from pydantic import BaseModel, Field

    class VaultQueryInput(BaseModel):
        """Input schema for the VaultTool."""

        measures: list[str] = Field(
            description=(
                "Metric names to query, e.g. ['fact_jobs.total_revenue', "
                "'fact_jobs.job_count'].  Use dot notation: <cube>.<measure>."
            )
        )
        dimensions: list[str] = Field(
            default=[],
            description=(
                "Group-by dimensions, e.g. ['fact_jobs.business_unit_name', "
                "'fact_jobs.technician_name'].  Use dot notation: <cube>.<dimension>."
            ),
        )
        time_dimension: dict | None = Field(
            default=None,
            description=(
                "Time dimension filter.  Example: "
                '{"dimension": "fact_jobs.job_created_at", "dateRange": "last 30 days"}. '
                "Supported presets: last 7 days, last 30 days, last 90 days, this month, this year."
            ),
        )
        limit: int = Field(default=100, description="Maximum number of rows to return (1-10000).")

    class VaultTool(BaseTool):
        """LangChain tool that queries the IgniteIQ Vault semantic layer.

        Designed to be passed directly to a LangChain agent.  The tool
        converts natural-language-driven structured inputs into Vault API
        calls and returns the results as a formatted string.

        Parameters
        ----------
        client : VaultClient
            An authenticated :class:`igniteiq.VaultClient` instance.

        Example
        -------
        ::

            from igniteiq import VaultClient
            from igniteiq.langchain import VaultTool

            client = VaultClient(api_key="iq_live_...", org_slug="tapps")
            tool = VaultTool(client=client)
        """

        name: str = "query_home_services_data"
        description: str = (
            "Query structured operational metrics from a home services company. "
            "Returns business intelligence data — revenue, jobs, technicians, invoices, accounts receivable. "
            "Use this tool when asked about business performance, KPIs, trends, or operational details. "
            "Always specify at least one measure.  Add a time_dimension to limit results to a date range."
        )
        args_schema: type[BaseModel] = VaultQueryInput
        client: Any  # VaultClient — typed as Any to avoid circular import issues

        class Config:
            arbitrary_types_allowed = True

        def _run(
            self,
            measures: list[str],
            dimensions: list[str] = [],
            time_dimension: dict | None = None,
            limit: int = 100,
        ) -> str:
            """Execute the query synchronously and return a string representation."""
            query: dict[str, Any] = {
                "measures": measures,
                "dimensions": dimensions,
                "limit": limit,
            }
            if time_dimension:
                query["timeDimensions"] = [time_dimension]
            result = self.client.query_sync(query)
            rows = result.get("data", [])
            if not rows:
                return "No data found for the given query."
            return str(rows)

        async def _arun(
            self,
            measures: list[str],
            dimensions: list[str] = [],
            time_dimension: dict | None = None,
            limit: int = 100,
        ) -> str:
            """Execute the query asynchronously and return a string representation."""
            query: dict[str, Any] = {
                "measures": measures,
                "dimensions": dimensions,
                "limit": limit,
            }
            if time_dimension:
                query["timeDimensions"] = [time_dimension]
            result = await self.client.query(query)
            rows = result.get("data", [])
            if not rows:
                return "No data found for the given query."
            return str(rows)

except ImportError:
    # LangChain is not installed.  Provide a helpful error when VaultTool is accessed.
    class VaultTool:  # type: ignore[no-redef]
        """Placeholder that raises ImportError when langchain-core is not installed."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise ImportError(
                "VaultTool requires langchain-core.  "
                'Install it with: pip install "igniteiq-vault[langchain]"'
            )
