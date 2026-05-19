# Semantic Search

The recommended semantic-search path is the `obsidianrag` tool set. It keeps
this MCP server lightweight and delegates advanced RAG behavior to the external
ObsidianRAG service over HTTP.

## Recommended Architecture

Use this MCP server for vault access, orchestration, setup diagnostics, and MCP
tool exposure. Use ObsidianRAG for embeddings, indexing, hybrid retrieval,
reranking, and natural-language answers over the vault.

```text
MCP client -> obsidian-mcp-server -> ObsidianRAG HTTP API -> local vault index
```

Enable it from `.agents/vault.yaml`:

```yaml
profile:
  tool_sets:
    - "obsidianrag"
  integrations:
    obsidianrag:
      project_path: "/path/to/ObsidianRAG"
      api_url: "http://127.0.0.1:8000"
      env:
        OBSIDIANRAG_LLM_MODEL: "gemma3"
        OBSIDIANRAG_OLLAMA_EMBEDDING_MODEL: "embeddinggemma"
```

Useful tools and resources:

- `rag.setup_status()`: inspect local prerequisites and backend reachability.
- `rag.health()`: check whether the ObsidianRAG API is healthy.
- `rag.ask(question, session_id)`: ask semantic questions against the vault.
- `rag.rebuild_index()`: trigger a backend index rebuild.
- `obsidian://integrations/obsidianrag/setup`: guided setup playbook.
- `obsidian://integrations/obsidianrag/config`: safe integration summary.

## Legacy In-Process RAG

The `legacy_semantic` tool set is deprecated. It remains available only for
backwards compatibility with old local deployments that embedded a RAG stack
inside this MCP server.

Legacy tools:

- `semantic.search`
- `semantic.index`
- `semantic.suggest_connections`

They require the deprecated optional dependency extra:

```bash
pip install "obsidian-mcp-server[rag]"
```

This path includes heavier dependencies such as ChromaDB, LangChain packages,
sentence-transformers, and PyTorch. New installations should not use it. Prefer
ObsidianRAG so the MCP server does not duplicate indexing and retrieval logic.

## Migration Notes

For a vault currently using `legacy_semantic`:

1. Install and start ObsidianRAG.
2. Enable the `obsidianrag` tool set in `.agents/vault.yaml`.
3. Configure the ObsidianRAG project path and local API URL.
4. Run `rag.setup_status()` and follow the setup resource.
5. Rebuild the ObsidianRAG index once.
6. Replace legacy calls:
   - `semantic.search` -> `rag.ask`
   - `semantic.index` -> `rag.rebuild_index`
   - `semantic.suggest_connections` -> use ObsidianRAG retrieval plus explicit
     link-analysis tools until a dedicated external suggestion workflow exists.

Once no active client depends on `legacy_semantic`, the legacy package extra and
in-process RAG modules can be removed from the MCP server.
