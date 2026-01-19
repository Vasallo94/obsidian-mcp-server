"""Database service for vector storage and document management"""

import logging
import os
import re
import shutil
from typing import Any, Dict, List, Optional, Set

import yaml
from langchain_chroma import Chroma  # type: ignore
from langchain_core.documents import Document  # type: ignore
from langchain_core.embeddings import Embeddings  # type: ignore
from langchain_huggingface import HuggingFaceEmbeddings  # type: ignore
from langchain_ollama import OllamaEmbeddings  # type: ignore
from langchain_text_splitters import RecursiveCharacterTextSplitter  # type: ignore

from .metadata_tracker import FileMetadataTracker

logger = logging.getLogger(__name__)


def extract_obsidian_links(content: str) -> List[str]:
    """Extract Obsidian wikilinks [[Note]] or [[Note|Alias]] from content"""
    links = re.findall(r"\[\[(.*?)\]\]", content)
    # Clean links (remove alias like [[Note|Alias]] -> Note)
    cleaned_links = [link.split("|")[0].strip() for link in links]
    # Remove duplicates while preserving order
    seen = set()
    unique_links = []
    for link in cleaned_links:
        if link and link not in seen:
            seen.add(link)
            unique_links.append(link)
    return unique_links


def parse_frontmatter(content: str) -> Dict[str, Any]:
    """Extract YAML frontmatter from content using PyYAML"""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return {}

    try:
        yaml_content = match.group(1)
        metadata = yaml.safe_load(yaml_content)
        if isinstance(metadata, dict):
            # Flatten or normalize some fields if needed
            processed = {}
            for k, v in metadata.items():
                if isinstance(v, list):
                    processed[k] = ",".join(str(i) for i in v)
                else:
                    processed[k] = str(v)
            return processed
    except Exception as e:
        logger.warning(f"Error parsing frontmatter: {e}")

    return {}


def get_embeddings(
    provider: str = "ollama",
    model: str = "embeddinggemma",
    ollama_base_url: str = "http://localhost:11434",
) -> Embeddings:
    """Get configured embeddings model based on provider setting."""
    if provider == "ollama":
        logger.info(f"Loading Ollama embeddings: {model}")
        return OllamaEmbeddings(model=model, base_url=ollama_base_url)

    # Fallback to HuggingFace
    logger.info(
        "Initializing HuggingFace embeddings: "
        "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    )
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    )


def get_text_splitter(
    chunk_size: int = 1500, chunk_overlap: int = 300
) -> RecursiveCharacterTextSplitter:
    """Get configured text splitter"""
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["#", "##", "###", "####", "\n\n", "\n", " ", ""],
    )


def load_documents_from_paths(filepaths: Set[str]) -> List[Document]:
    """Load documents from specific file paths with link extraction"""
    documents = []

    for filepath in filepaths:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract Obsidian links
            links = extract_obsidian_links(content)

            # Extract frontmatter metadata
            fm_metadata = parse_frontmatter(content)

            metadata = {
                "source": filepath,
                "links": ",".join(links) if links else "",
            }
            # Merge with frontmatter metadata
            metadata.update(fm_metadata)

            doc = Document(
                page_content=content,
                metadata=metadata,
            )
            documents.append(doc)

        except Exception as e:
            logger.warning(f"Could not load {filepath}: {e}")

    return documents


def load_all_obsidian_documents(obsidian_path: str) -> List[Document]:
    """Load all documents from Obsidian vault using recursive walk"""
    logger.info("Loading Obsidian documents (.md) recursively")

    # File patterns to exclude (binary, canvas, etc.)
    excluded_patterns = [
        ".excalidraw.md",
        ".canvas",
        "untitled",
    ]

    documents = []
    for root, _, files in os.walk(obsidian_path):
        for file in files:
            if file.endswith(".md"):
                filepath = os.path.join(root, file)

                # Skip excluded patterns
                if any(pattern in file.lower() for pattern in excluded_patterns):
                    continue

                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()

                        if content.strip():
                            links = extract_obsidian_links(content)
                            fm_metadata = parse_frontmatter(content)

                            doc_metadata = {
                                "source": filepath,
                                "links": ",".join(links) if links else "",
                            }
                            doc_metadata.update(fm_metadata)

                            doc = Document(
                                page_content=content,
                                metadata=doc_metadata,
                            )
                            documents.append(doc)

                except Exception as e:
                    logger.error(f"Error loading file {filepath}: {e}")

    return documents


def load_or_create_db(
    obsidian_path: str,
    db_path: str,
    **kwargs: Any,
) -> tuple[Optional[Chroma], Dict[str, Any]]:
    """Load or create vector database with incremental indexing support.

    Returns:
        Tuple of (db, stats_dict) where stats contains:
        - docs_processed: total documents in the operation
        - docs_new: new documents added
        - docs_modified: documents updated
        - docs_deleted: documents removed
        - is_incremental: whether update was incremental
    """
    stats: Dict[str, Any] = {
        "docs_processed": 0,
        "docs_new": 0,
        "docs_modified": 0,
        "docs_deleted": 0,
        "is_incremental": False,
    }

    metadata_file = kwargs.get("metadata_file", "")
    embeddings_provider = kwargs.get("embeddings_provider", "ollama")
    embeddings_model = kwargs.get("embeddings_model", "embeddinggemma")
    force_rebuild = kwargs.get("force_rebuild", False)
    logger.info("Starting vector database load or creation")

    embeddings = get_embeddings(provider=embeddings_provider, model=embeddings_model)
    tracker = FileMetadataTracker(metadata_file)

    # Check if we should do incremental update
    if os.path.exists(db_path) and not force_rebuild:
        if tracker.should_rebuild(obsidian_path):
            force_rebuild = True
        else:
            new_files, modified_files, deleted_files = tracker.detect_changes(
                obsidian_path
            )
            if not new_files and not modified_files and not deleted_files:
                db = Chroma(persist_directory=db_path, embedding_function=embeddings)
                return db, stats

            # Do incremental update
            stats["is_incremental"] = True
            stats["docs_new"] = len(new_files)
            stats["docs_modified"] = len(modified_files)
            stats["docs_deleted"] = len(deleted_files)
            stats["docs_processed"] = len(new_files) + len(modified_files)

            db = Chroma(persist_directory=db_path, embedding_function=embeddings)
            for f in deleted_files | modified_files:
                db.delete(where={"source": f})

            docs = load_documents_from_paths(new_files | modified_files)
            if docs:
                splitter = get_text_splitter()
                texts = splitter.split_documents(docs)
                db.add_documents(texts)

            tracker.update_metadata(obsidian_path)
            return db, stats

    # Full rebuild
    documents = load_all_obsidian_documents(obsidian_path)
    if not documents:
        return None, stats

    stats["docs_processed"] = len(documents)
    stats["is_incremental"] = False

    splitter = get_text_splitter()
    texts = splitter.split_documents(documents)

    if os.path.exists(db_path):
        shutil.rmtree(db_path)

    db = Chroma.from_documents(
        texts,
        embeddings,
        persist_directory=db_path,
        collection_metadata={"hnsw:space": "cosine"},
    )
    tracker.update_metadata(obsidian_path)
    return db, stats
