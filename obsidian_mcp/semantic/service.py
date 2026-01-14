"""High-level semantic RAG service for the MCP server"""

import logging
import os
import re
import traceback
from typing import Any, Dict, List, Optional

from ..utils.timeout import TimeoutError as TimeLimitExceeded
from ..utils.timeout import time_limit
from .indexer import load_or_create_db
from .retriever import create_retriever_with_reranker

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore

try:
    from tqdm import tqdm
except ImportError:

    def tqdm(iterable, **kwargs):
        return iterable


logger = logging.getLogger(__name__)


# Constants for filtering
CARPETAS_EXCLUIDAS = [
    "00_Sistema",
    "ZZ_Plantillas",
    "04_Recursos/Obsidian",
]

PATRONES_EXCLUIDOS = [
    r".*MOC\.md",
    r".*Home\.md",
    r".*Inbox\.md",
    r".*Panel.*\.md",
    r".*\.agent\.md",
    r"copilot-instructions\.md",
]

CARPETAS_CONTENIDO = [
    "03_Notas",  # Notas permanentes
    "02_Proyectos",  # Proyectos activos
]


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

    def _should_exclude(
        self,
        filepath: str,
        carpetas_incluir: Optional[List[str]] = None,
        excluir_mocs: bool = True,
    ) -> bool:
        """Check if a file should be excluded based on filters"""
        rel_path = os.path.relpath(filepath, self.vault_path)
        filename = os.path.basename(filepath)

        # 1. Filter by specific include folders if provided
        if carpetas_incluir:
            if not any(rel_path.startswith(folder) for folder in carpetas_incluir):
                return True
        else:
            # Otherwise use default exclusions
            if any(rel_path.startswith(folder) for folder in CARPETAS_EXCLUIDAS):
                return True

        # 2. Filter by patterns (MOCs, System files)
        if excluir_mocs:
            for pattern in PATRONES_EXCLUIDOS:
                if re.match(pattern, filename):
                    return True

        return False

    def _extract_section_header(self, content: str) -> str:
        """Attempt to find the nearest header in the chunk"""
        # Look for headers in the content
        headers = re.findall(r"^(#{1,6})\s+(.+)$", content, re.MULTILINE)
        if headers:
            # Return the first header found in this chunk
            return f"{headers[0][0]} {headers[0][1]}"
        return "Contenido General"

    def suggest_connections(
        self,
        threshold: float = 0.85,
        limit: int = 10,
        carpetas_incluir: Optional[List[str]] = None,
        excluir_mocs: bool = True,
        min_palabras: int = 100,
        timeout_seconds: int = 180,
    ) -> List[dict]:
        """
        Find notes with high semantic similarity that are NOT linked.
        Uses vectorized operations for performance.
        """
        try:
            self._ensure_db()
            if self._db is None:
                return []

            if np is None:
                logger.error("numpy is required for fast connection suggestions")
                return []

            logger.info(
                f"Analyzing connections: threshold={threshold}, "
                f"mocs={excluir_mocs}, min_words={min_palabras}"
            )

            try:
                with time_limit(timeout_seconds):
                    # 1. Fetch all data in one go (including embeddings)
                    # ChromaDB .get() returns embeddings as a list of lists if requested
                    logger.info("DEBUG: Fetching data from ChromaDB")
                    db_data = self._db.get(
                        include=["metadatas", "documents", "embeddings"]
                    )

                    all_metadatas = db_data.get("metadatas", [])
                    all_documents = db_data.get("documents", [])
                    all_embeddings = db_data.get("embeddings", [])

                    if all_embeddings is None or len(all_embeddings) == 0:
                        logger.warning("No embeddings found in database")
                        return []

                    # 2. Pre-filter indices
                    valid_indices = []
                    for i, meta in enumerate(all_metadatas):
                        source = meta.get("source", "")
                        content = all_documents[i]

                        # Word count filter
                        if len(content.split()) < min_palabras:
                            continue

                        # Path/Pattern filter
                        if self._should_exclude(source, carpetas_incluir, excluir_mocs):
                            continue

                        if all_embeddings[i] is None:
                            continue

                        valid_indices.append(i)

                    n_docs = len(valid_indices)
                    logger.info(
                        f"DEBUG: Found {n_docs} valid notes out of {len(all_metadatas)}"
                    )
                    if n_docs < 2:
                        return []

                    logger.info(f"Computing similarity for {n_docs} valid notes...")

                    # 3. Create Matrix for valid docs
                    # shape: (n_docs, embedding_dim)
                    valid_embeddings = np.array(
                        [all_embeddings[i] for i in valid_indices]
                    )

                    # Normalize embeddings (L2 norm) for cosine similarity
                    norm = np.linalg.norm(valid_embeddings, axis=1, keepdims=True)
                    # Avoid division by zero using out and where
                    normalized_embeddings = np.divide(
                        valid_embeddings,
                        norm,
                        out=np.zeros_like(valid_embeddings),
                        where=norm != 0,
                    )

                    # 4. Compute Similarity Matrix (Vectorized)
                    # (n_docs, dim) @ (dim, n_docs) -> (n_docs, n_docs)
                    similarity_matrix = np.dot(
                        normalized_embeddings, normalized_embeddings.T
                    )

                    # 5. Extract Suggestions
                    suggestions = []

                    # Upper triangle only: avoids duplicates and self-matches
                    rows, cols = np.triu_indices(n_docs, k=1)

                    # Filter by threshold mask
                    mask = similarity_matrix[rows, cols] >= threshold
                    valid_rows = rows[mask]
                    valid_cols = cols[mask]
                    valid_scores = similarity_matrix[valid_rows, valid_cols]

                    # Process candidates
                    # Use tqdm for progress update if many candidates
                    iterator = zip(valid_rows, valid_cols, valid_scores, strict=False)
                    if len(valid_rows) > 1000:
                        iterator = tqdm(
                            iterator, total=len(valid_rows), desc="Filtering candidates"
                        )

                    for r, c, score in iterator:
                        # Map back to original indices
                        idx_i = valid_indices[r]
                        idx_j = valid_indices[c]

                        source_i = all_metadatas[idx_i].get("source", "")
                        source_j = all_metadatas[idx_j].get("source", "")

                        title_i = os.path.basename(source_i)
                        title_j = os.path.basename(source_j)

                        # Check links
                        links_i = all_metadatas[idx_i].get("links", "").split(",")
                        links_j = all_metadatas[idx_j].get("links", "").split(",")

                        clean_title_j = title_j.replace(".md", "")
                        clean_title_i = title_i.replace(".md", "")

                        if clean_title_j in links_i or clean_title_i in links_j:
                            continue

                        suggestions.append(
                            {
                                "note_a": title_i,
                                "note_b": title_j,
                                "similarity": float(score),
                                "folder_a": os.path.dirname(source_i),
                                "folder_b": os.path.dirname(source_j),
                                "words_a": len(all_documents[idx_i].split()),
                                "words_b": len(all_documents[idx_j].split()),
                                "section_a": self._extract_section_header(
                                    all_documents[idx_i]
                                ),
                                "section_b": self._extract_section_header(
                                    all_documents[idx_j]
                                ),
                                "reason": f"Similitud {score:.2f}",
                            }
                        )

                    # Sort and limit
                    suggestions.sort(key=lambda x: x["similarity"], reverse=True)
                    return suggestions[:limit]

            except TimeLimitExceeded:
                logger.warning("Suggestion search timed out")
                return [
                    {
                        "note_a": "Error",
                        "note_b": "Timeout",
                        "similarity": 0.0,
                        "folder_a": "",
                        "folder_b": "",
                        "words_a": 0,
                        "words_b": 0,
                        "section_a": "",
                        "section_b": "",
                        "reason": "Timeout. Reduce el umbral o filtra carpetas.",
                    }
                ]
        except Exception as e:
            logger.error(f"Error in suggest_connections: {e}")
            logger.error(traceback.format_exc())
            return []
