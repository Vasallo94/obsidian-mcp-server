# Semantic Search (RAG)

The Obsidian MCP server includes **Retrieval-Augmented Generation (RAG)** capabilities, allowing the AI to query your vault using natural language and understanding context beyond simple keywords.

## How does it work?

The system uses a vector database to represent your notes as "vectors" in a multidimensional space. When you ask a question, the server searches for the notes whose vectors are closest to your query's vector.

### Technical Components
- **Embeddings**: Uses language models to convert text into numerical representations.
- **Vector Store**: `ChromaDB` is used to store and search these vectors efficiently.
- **Orchestration**: `LangChain` manages the data flow between the notes and the embeddings model.

## Dependency Installation

This functionality is optional and requires additional libraries that can increase the installation size:

```bash
pip install "obsidian-mcp-server[rag]"
```

## Semantic Tools

### 1. `preguntar_al_conocimiento`
This is the main tool for "human-like" queries.
- **Example**: "What have I written about artificial intelligence in the last few months?"
- **Filters**: You can restrict the search by metadata (e.g., only notes of type "poetry").

### 2. `indexar_vault_semantico`
New notes do not automatically appear in the semantic search. You must run this tool periodically to update the index.
- **Incremental**: Only processes new or modified notes.
- **Forced**: Rebuilds the entire index from scratch (useful if you change the embeddings model).

### 3. `encontrar_conexiones_sugeridas`
Analyzes the semantic similarity between all your notes.
- If two notes discuss very similar topics but do not have a `[[Note]]` link between them, the server will flag them as a suggested connection.
- It is ideal for maintaining and organically growing your Zettelkasten.

### 4. `sugerir_ubicacion` (Folder Recommendation)

This tool uses **semantic search** to suggest the most appropriate folder for a new note, based on similar notes already existing in your vault.

#### How does it work?

1. **Vector search**: Combines the title, tags, and content of the new note to create a query.
2. **RAG Retrieval**: Searches for the most similar notes in the vector index (ChromaDB).
3. **Voting system**: The folders of the similar notes "vote" for the suggested location.
4. **Ranking with confidence**: Returns multiple candidates sorted by number of votes and confidence percentage.

#### Usage Example

When you ask the AI to create a note about "SSH Configuration for NAS", the system:

```text
Suggested folders based on similar content:

1. `Technology/Infrastructure`
   Confidence: 80% (4 votes)
   Similar notes: NAS, Docker Setup, Local Networks

2. `Technology/Guides`
   Confidence: 20% (1 vote)
   Similar notes: VPN Guide

The option 1 has high confidence (80%). You can suggest it to the user.
```

#### Interpreting Results

| Confidence | Recommendation |
|-----------|---------------|
| >=60% | High confidence. The AI can suggest this folder directly. |
| 40-59% | Moderate confidence. Show options to the user to decide. |
| <40% | Low confidence. Ask the user where they prefer to place the note. |

#### Automatic Fallback

If the semantic index is unavailable or finds no matches, the tool automatically uses a **keyword-based rule system** as a backup, ensuring a useful suggestion is always provided.

## Data Storage
The vector index is saved locally in a folder inside your vault (usually `.obsidianrag/` or similar), ensuring that your knowledge never leaves your control.

### 5. Semantic Indexing for Images

The system has the ability to "read" the images in your vault through their descriptions.

#### The Problem
Text language models (like the one used by this RAG) cannot see the pixels of an `image.png`. If you search for "sales chart", the AI won't know that image contains a sales chart unless the file name is highly explicit.

#### The MCP Solution
The indexer scans all your notes looking for images with **captions**.
- Obsidian format: `![[image.png|This is a sales chart]]`
- Markdown format: `![This is a sales chart](image.png)`

When it finds one, it takes that description and **injects the text into the vector index** associated with the note, under a hidden section called "Image Context".

#### Result
You can ask: *"Do you have any charts about sales?"*
The system will find the note because it semantically "knows" it contains that image, even if the main text of the note never mentions the word "chart".

> [!TIP]
> For this to work, it is **MANDATORY** to add descriptions to relevant images. An image without a description is invisible to the semantic search engine.
