"""High-level semantic RAG service for the MCP server"""

import logging
import os
from typing import Any, Dict, List, Optional

from .indexer import load_or_create_db
from .retriever import create_retriever_with_reranker

logger = logging.getLogger(__name__)


class SemanticService:
    """Manages the semantic search capabilities of the MCP server"""

    def __init__(self, vault_path: str):
        self.vault_path = vault_path
        self.data_dir = os.path.join(vault_path, ".obsidianrag")
        self.db_path = os.path.join(self.data_dir, "db")
        self.metadata_file = os.path.join(self.data_dir, "metadata.json")
        self._db = None
        self._retriever = None

    def _ensure_db(self, force_rebuild: bool = False):
        """Ensure the vector database is loaded"""
        if self._db is None or force_rebuild:
            self._db = load_or_create_db(
                obsidian_path=self.vault_path,
                db_path=self.db_path,
                metadata_file=self.metadata_file,
                force_rebuild=force_rebuild,
            )
            self._retriever = None  # Reset retriever to use new DB

    def _ensure_retriever(self):
        """Ensure the retriever is configured"""
        self._ensure_db()
        if self._retriever is None and self._db is not None:
            self._retriever = create_retriever_with_reranker(self._db)

    def query(
        self,
        text: str,
        metadata_filter: Optional[Dict[str, Any]] = None,
        expand_links: bool = True,
    ) -> List[dict]:
        """
        Perform a semantic search query with optional metadata
        filtering and context expansion
        """
        self._ensure_retriever()
        if self._retriever is None:
            return []

        # If filter is provided, we bypass the ensemble for now as BM25
        # doesn't easily support metadata filtering without rebuild.
        if metadata_filter:
            logger.info(f"Performing filtered search: {metadata_filter}")
            docs = self._db.similarity_search(text, k=10, filter=metadata_filter)
        else:
            docs = self._retriever.invoke(text)

        results = []
        for doc in docs:
            links = (
                doc.metadata.get("links", "").split(",")
                if doc.metadata.get("links")
                else []
            )
            res = {
                "content": doc.page_content,
                "source": doc.metadata.get("source", "Unknown"),
                "relevance": doc.metadata.get("relevance_score", 0.0),
                "metadata": {
                    k: v
                    for k, v in doc.metadata.items()
                    if k not in ["source", "relevance_score", "links"]
                },
                "links": links,
                "linked_context": [],
            }

            if expand_links and links:
                for link in links[:3]:  # Limit to first 3 links
                    res["linked_context"].append(f"Nota relacionada: [[{link}]]")

            results.append(res)

        return results

    def index_vault(self, force: bool = False):
        """Force a manual indexing of the vault"""
        self._ensure_db(force_rebuild=force)
        return self._db is not None

    def suggest_connections(
        self, threshold: float = 0.85, limit: int = 10
    ) -> List[dict]:
        """
        Find notes with high semantic similarity that are NOT linked.
        This helps maintain the vault's knowledge graph.
        """
        self._ensure_db()
        if not self._db:
            return []

        logger.info("Analyzing vault for missing connections...")
        db_data = self._db.get()
        documents = db_data["documents"]
        metadatas = db_data["metadatas"]

        # This is a computationally expensive operation if done naively (O(N^2)).
        # For small-medium vaults, we can do it. For larger ones,
        # we'd use index-specific similarity search.
        # Here we'll do a sample-based or targeted approach if needed,
        # but let's try a direct approach for now.

        suggestions = []
        for i, doc_i_content in enumerate(documents):
            source_i = metadatas[i].get("source", "")
            links_i = metadatas[i].get("links", "").split(",")

            # Find similar docs to this one
            similar_docs = self._db.similarity_search_with_relevance_scores(
                doc_i_content, k=5
            )

            for doc_j, score in similar_docs:
                source_j = doc_j.metadata.get("source", "")
                if source_i == source_j:
                    continue

                if score < threshold:
                    continue

                # Check if they are already linked
                title_j = source_j.split("/")[-1].replace(".md", "")
                if title_j in links_i:
                    continue

                suggestions.append(
                    {
                        "note_a": source_i.split("/")[-1],
                        "note_b": source_j.split("/")[-1],
                        "similarity": float(score),
                        "reason": f"Alta similitud semántica ({score:.2f}) "
                        "sin enlace directo.",
                    }
                )

                if len(suggestions) >= limit:
                    return suggestions

        return suggestions
