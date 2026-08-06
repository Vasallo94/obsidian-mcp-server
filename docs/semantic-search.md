# Semantic Search

Semantic search is supported through the `obsidianrag` tool set.

The recommended architecture is:

```mermaid
flowchart LR
    Agent["Agent / MCP client"] --> MCP["Obsidian MCP Server"]
    MCP --> Tools["rag.* tools"]
    Tools --> API["ObsidianRAG HTTP API"]
    API --> Index["Vector index"]
    API --> Vault["Obsidian vault"]
```

## Recommended path: ObsidianRAG

Enable the `obsidianrag` tool set and declare the local integration in
`.agents/vault.yaml`:

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

Available tools:

| Tool | Purpose |
|---|---|
| `rag.setup_status()` | Diagnose project path, uv, Ollama, backend, and API health |
| `rag.health()` | Check whether the ObsidianRAG API is reachable |
| `rag.ask(question, session_id)` | Ask a semantic question over the vault |
| `rag.rebuild_index()` | Trigger a rebuild through the ObsidianRAG backend |

Useful resources:

- `obsidian://integrations/obsidianrag/setup`
- `obsidian://integrations/obsidianrag/config`

Agents should show setup commands and ask for consent before:

- installing dependencies;
- pulling local models;
- starting services;
- rebuilding a large index.

## Why the RAG stack is external

The MCP server should remain small, fast, and easy to install. Keeping advanced
RAG in ObsidianRAG avoids bundling a second vector database, embedding stack,
retriever stack, and model runtime into every MCP installation.

This separation also makes the failure modes cleaner:

- MCP install problems stay in the MCP server.
- Indexing/model problems stay in ObsidianRAG.
- Agents can diagnose the boundary with `rag.setup_status()` and `rag.health()`.

## Removed: the legacy in-process tools

The `legacy_semantic` tool set — `semantic.index`, `semantic.search` and
`semantic.suggest_connections` — has been removed, along with the optional
`[rag]` dependency extra that powered it.

If a profile still lists `legacy_semantic` in `tool_sets`, nothing breaks: no
tool set by that name exists any more, so the entry registers nothing. As with
any unrecognised name, it does still appear under `tool_sets.enabled` in the
`obsidian://profile` resource while being absent from the available sets, so
removing it from the profile is worth doing for tidiness. To keep semantic
search, enable `obsidianrag` and point it at an ObsidianRAG instance as
described above.

One behaviour changed outside the tool set: `notes.suggest_location` used to
consult the local index first and fall back to a keyword heuristic when the
optional extra was absent. It now always uses the heuristic.
