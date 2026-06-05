# Deep Research Notes

## Relevant files

- `src/deep_research.py`
- `routes/research_routes.py`
- `static/js/research/*`
- `static/js/chat.js` research toggle handling
- `data/settings.json`
- `src/endpoint_resolver.py`

Settings currently include:

```json
{
  "research_endpoint_id": "",
  "research_model": "",
  "research_search_provider": "",
  "research_max_tokens": 16384,
  "research_extraction_timeout_seconds": 90,
  "research_extraction_concurrency": 3,
  "research_run_timeout_seconds": 1800
}
```

## Current understanding

Deep Research is an iterative background-ish workflow:

1. LLM plans/searches.
2. Search provider fetches sources.
3. LLM extracts/synthesizes findings.
4. LLM decides whether to continue.
5. Final report can be visualized.

`DeepResearcher` takes explicit:
- `llm_endpoint`
- `llm_model`
- headers
- max rounds/time/content/report token settings
- search provider

## User preference / local constraint

This workstation usually runs one model at a time. Deep Research should preferably use the current/default endpoint and current loaded model unless explicitly configured otherwise.

The current defaults are confusing because research settings exist even when the user did not intentionally configure a separate research model.

## Questions to resolve

- If `research_endpoint_id` / `research_model` are blank, does Deep Research fall back to the default chat endpoint/model or some hardcoded/provider default?
- Does the chat research toggle use the current selected model or the research-specific settings?
- Can the standalone Deep Research panel and in-chat research toggle diverge?
- How many concurrent requests can llama.cpp tolerate for research extraction/synthesis at the chosen context and `n_parallel`?

## llama.cpp concurrency notes

llama-server defaulted in logs to:

```text
n_parallel = 4
kv_unified = true
```

For one local 4090 and Gemma 31B GGUF:
- concurrency may work, but parallel slots multiply KV/cache pressure.
- Deep Research extraction concurrency is currently `3` by setting.
- If research gets unstable, reduce either:
  - llama-server `--parallel` / slots, or
  - `research_extraction_concurrency`.

## Desired behavior

- Blank research endpoint/model means “use current/default chat model”.
- UI should make it obvious when research is using a different endpoint/model than the visible chat.
- Research should not silently launch/use a second local model on single-GPU setups.
- For local llama.cpp, provide a conservative research profile:
  - lower extraction concurrency
  - bounded content chars
  - stable context/KV settings

## Next test plan

1. Inspect `routes/research_routes.py` endpoint/model resolution.
2. Run one small research job on the registered llama.cpp endpoint.
3. Watch llama-server logs for parallel slot usage and memory.
4. If needed, change fallback resolution so blank research settings use current/default endpoint/model.
