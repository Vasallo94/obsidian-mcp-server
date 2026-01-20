"""QA Service with hybrid search and reranking"""

import logging

from langchain_classic.retrievers import (  # type: ignore[import-not-found]
    ContextualCompressionRetriever,
    EnsembleRetriever,
)
from langchain_classic.retrievers.document_compressors import (  # type: ignore[import-not-found]
    CrossEncoderReranker,
)
from langchain_community.cross_encoders import HuggingFaceCrossEncoder  # type: ignore
from langchain_community.retrievers import BM25Retriever  # type: ignore
from langchain_core.documents import Document  # type: ignore

logger = logging.getLogger(__name__)


def create_hybrid_retriever(
    db,
    bm25_k: int = 5,
    vector_k: int = 12,
    bm25_weight: float = 0.4,
    vector_weight: float = 0.6,
):
    """
    Create a hybrid retriever with BM25 + Vector search
    """
    logger.info("Configuring Hybrid Search (BM25 + Vector)")

    # Get documents from DB for BM25
    try:
        db_data = db.get()
        texts = db_data["documents"]
        metadatas = db_data["metadatas"]

        if not texts:
            logger.warning("No documents found in DB")
            return db.as_retriever(search_kwargs={"k": vector_k})

        # Create BM25 retriever
        docs = [
            Document(page_content=t, metadata=m)
            for t, m in zip(texts, metadatas, strict=False)
        ]
        bm25_retriever = BM25Retriever.from_documents(docs)
        bm25_retriever.k = bm25_k

        # Create vector retriever
        chroma_retriever = db.as_retriever(search_kwargs={"k": vector_k})

        # Combine with ensemble
        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, chroma_retriever],
            weights=[bm25_weight, vector_weight],
        )

        return ensemble_retriever

    except Exception as e:
        logger.error(f"Error creating hybrid retriever: {e}. Using only Vector Search")
        return db.as_retriever(search_kwargs={"k": vector_k})


def create_retriever_with_reranker(
    db,
    use_reranker: bool = True,
    reranker_model: str = "BAAI/bge-reranker-v2-m3",
    reranker_top_n: int = 6,
):
    """
    Create a retriever with optional reranking
    """
    ensemble_retriever = create_hybrid_retriever(db)

    if use_reranker:
        logger.info(f"Adding reranker: {reranker_model}")
        try:
            model = HuggingFaceCrossEncoder(model_name=reranker_model)
            compressor = CrossEncoderReranker(model=model, top_n=reranker_top_n)

            retriever = ContextualCompressionRetriever(
                base_compressor=compressor, base_retriever=ensemble_retriever
            )
            return retriever
        except Exception as e:
            logger.warning(f"Could not configure reranker: {e}")
            return ensemble_retriever

    return ensemble_retriever
