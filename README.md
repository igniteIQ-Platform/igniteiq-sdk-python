# igniteiq-vault — Python SDK

Query home services business data from your LLM agents in three lines of Python.

```python
from igniteiq import VaultClient

client = VaultClient(api_key="iq_live_...", org_slug="tapps")
result = client.query_sync({"measures": ["fact_jobs.total_revenue"]})
```

## Installation

```bash
pip install igniteiq-vault
```

With optional LangChain integration:

```bash
pip install "igniteiq-vault[langchain]"
```

With optional LlamaIndex integration:

```bash
pip install "igniteiq-vault[llamaindex]"
```

## Getting an API key

1. Open **Studio** → your org → **Settings** → **API Keys**
2. Click **Generate key** and copy the value (starts with `iq_live_`)
3. Store it securely — it is shown only once

## Quick start

### Async (recommended)

```python
import asyncio
from igniteiq import VaultClient

client = VaultClient(api_key="iq_live_...", org_slug="tapps")

async def main():
    # Structured query
    result = await client.query({
        "measures": ["fact_jobs.total_revenue", "fact_jobs.job_count"],
        "timeDimensions": [{
            "dimension": "fact_jobs.job_created_at",
            "dateRange": "last 30 days",
        }],
        "limit": 100,
    })
    print(result["data"])

    # Context snapshot (injects business context into LLM system prompt)
    ctx = await client.context(period="last_30_days")
    print(ctx["systemPromptFragment"])

    # Natural language query
    ans = await client.ask("What was our revenue last month?")
    print(ans["answer"], "—", ans["confidence"])

    # LLM tool definitions
    tools = await client.schema.tools("openai")

asyncio.run(main())
```

### Sync (for scripts and non-async frameworks)

```python
from igniteiq import VaultClient

client = VaultClient(api_key="iq_live_...", org_slug="tapps")

result = client.query_sync({
    "measures": ["fact_jobs.total_revenue"],
    "timeDimensions": [{
        "dimension": "fact_jobs.job_created_at",
        "dateRange": "last 30 days",
    }],
})
print(result["data"])

ctx = client.context_sync(period="last_30_days")
print(ctx["systemPromptFragment"])

ans = client.ask_sync("How many jobs were completed last week?")
print(ans["answer"])
```

## Understanding queries

Vault uses a semantic layer (powered by [Cube.dev](https://cube.dev)).  Every
query is expressed in terms of **measures** and **dimensions**:

| Concept | Description | Example |
|---|---|---|
| Measure | An aggregated metric | `fact_jobs.total_revenue` |
| Dimension | A group-by attribute | `fact_jobs.business_unit_name` |
| Time dimension | A date/time filter | `fact_jobs.job_created_at` |
| Filter | A row-level filter | `{member: "...", operator: "equals", values: [...]}` |

Use `client.schema.tools("openai")` to get machine-readable definitions of
every available measure and dimension.

## LangChain integration

```python
from igniteiq import VaultClient
from igniteiq.langchain import VaultTool
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

client = VaultClient(api_key="iq_live_...", org_slug="tapps")
vault_tool = VaultTool(client=client)

llm = ChatOpenAI(model="gpt-4o")
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful business analyst for a home services company."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])
agent = create_tool_calling_agent(llm, [vault_tool], prompt)
executor = AgentExecutor(agent=agent, tools=[vault_tool])

result = executor.invoke({"input": "What was our revenue last month?"})
print(result["output"])
```

### Using raw tool definitions for function calling

```python
import openai

# Get OpenAI-format tool definitions from the Vault schema
tools_resp = await client.schema.tools("openai")
openai_tools = tools_resp["tools"]

response = openai.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "What was revenue last month?"}],
    tools=openai_tools,
)
```

## LlamaIndex integration

```python
from igniteiq import VaultClient
from igniteiq.llamaindex import VaultDataSource
from llama_index.core import VectorStoreIndex

client = VaultClient(api_key="iq_live_...", org_slug="tapps")
source = VaultDataSource(client=client)

# Load context snapshot as LlamaIndex Documents
docs = source.load_data(period="last_30_days")
print(docs[0].text[:300])

# Build a query engine over the context
index = VectorStoreIndex.from_documents(docs)
query_engine = index.as_query_engine()
response = query_engine.query("Summarise our financial performance.")
print(response)
```

## Error handling

```python
from igniteiq import VaultClient, VaultError

client = VaultClient(api_key="iq_live_...", org_slug="tapps")

try:
    result = await client.query({"measures": ["fact_jobs.total_revenue"]})
except VaultError as e:
    print(f"Error {e.code} (HTTP {e.status}): {e}")
    # e.code: UNAUTHORIZED | FORBIDDEN | NOT_FOUND | RATE_LIMITED | BAD_REQUEST | API_ERROR
```

## Division scoping

For multi-division organisations, scope requests to a specific division:

```python
result = await client.query(
    {"measures": ["fact_jobs.total_revenue"]},
)

ctx = await client.context(period="last_30_days", division_slug="north-division")
ans = await client.ask("Revenue trend?", division_slug="north-division")
```

## API reference

Full REST API reference: [https://igniteiq.com/docs/sdk/api-reference](https://igniteiq.com/docs/sdk/api-reference)

## License

MIT
