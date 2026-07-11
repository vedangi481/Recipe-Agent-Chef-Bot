"""
RAG Pipeline Module — Recipe Preparation Agent
Handles document ingestion, embedding, and semantic retrieval using ChromaDB.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# ChromaDB for vector store (1.x API — no C compiler required)
import chromadb
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

logger = logging.getLogger(__name__)

# ChromaDB 1.x moved Settings into chromadb.config
try:
    from chromadb.config import Settings as ChromaSettings
    _HAS_SETTINGS = True
except ImportError:
    _HAS_SETTINGS = False


class RecipeRAGPipeline:
    """
    Retrieval-Augmented Generation pipeline for the recipe knowledge base.
    Loads text documents from the knowledge_base/ folder into ChromaDB,
    then performs semantic search to retrieve relevant context.
    """

    # ------------------------------------------------------------------ #
    # Collection names — each maps to one knowledge-base subfolder        #
    # ------------------------------------------------------------------ #
    COLLECTIONS = {
        "recipes":       "knowledge_base/recipes",
        "techniques":    "knowledge_base/techniques",
        "substitutions": "knowledge_base/substitutions",
        "nutrition":     "knowledge_base/nutrition",
        "dietary":       "knowledge_base/dietary",
    }

    def __init__(self, persist_dir: str = ".chroma_db"):
        """
        Initialize the RAG pipeline.

        Args:
            persist_dir: Directory where ChromaDB stores its data on disk.
        """
        self.persist_dir = persist_dir
        # ONNX-based all-MiniLM-L6-v2 — ships pre-compiled with ChromaDB,
        # no PyTorch and no C compiler required.
        self.ef = ONNXMiniLM_L6_V2()

        # Persistent client — ChromaDB 1.x uses chromadb.PersistentClient
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collections: Dict[str, Any] = {}
        self._initialized = False

    # ------------------------------------------------------------------ #
    # Initialization                                                       #
    # ------------------------------------------------------------------ #

    def initialize(self, force_reload: bool = False) -> None:
        """
        Load all knowledge-base documents into ChromaDB.
        Skips reloading if collections already exist (unless force_reload=True).
        """
        logger.info("Initializing RAG pipeline …")
        for name, folder_path in self.COLLECTIONS.items():
            collection = self.client.get_or_create_collection(
                name=name,
                embedding_function=self.ef,
                # ChromaDB 1.x: cosine distance config key
                metadata={"hnsw:space": "cosine"},
            )
            self.collections[name] = collection

            # Only ingest if collection is empty or force_reload requested
            existing = collection.count()
            if existing > 0 and not force_reload:
                logger.info("  Collection '%s' already has %d documents — skipping ingest.", name, existing)
                continue

            if force_reload and existing > 0:
                # Delete and recreate
                self.client.delete_collection(name)
                collection = self.client.get_or_create_collection(
                    name=name,
                    embedding_function=self.ef,
                    metadata={"hnsw:space": "cosine"},
                )
                self.collections[name] = collection

            # Ingest documents
            docs, ids, metas = self._load_documents(folder_path)
            if docs:
                # ChromaDB has a batch limit; chunk into batches of 100
                for batch_start in range(0, len(docs), 100):
                    batch_end = batch_start + 100
                    collection.add(
                        documents=docs[batch_start:batch_end],
                        ids=ids[batch_start:batch_end],
                        metadatas=metas[batch_start:batch_end],
                    )
                logger.info("  Ingested %d chunks into collection '%s'.", len(docs), name)
            else:
                logger.warning("  No documents found in '%s'.", folder_path)

        self._initialized = True
        logger.info("RAG pipeline ready.")

    def _load_documents(
        self, folder_path: str
    ) -> tuple[List[str], List[str], List[Dict]]:
        """
        Load and chunk all .txt / .json files in a folder.

        Returns:
            Tuple of (documents, ids, metadatas)
        """
        docs, ids, metas = [], [], []
        path = Path(folder_path)
        if not path.exists():
            logger.warning("Folder not found: %s", folder_path)
            return docs, ids, metas

        for file_path in sorted(path.glob("*.*")):
            if file_path.suffix == ".txt":
                text = file_path.read_text(encoding="utf-8")
                chunks = self._chunk_text(text, chunk_size=600, overlap=80)
                for i, chunk in enumerate(chunks):
                    doc_id = f"{file_path.stem}_{i}"
                    docs.append(chunk)
                    ids.append(doc_id)
                    metas.append({"source": str(file_path), "chunk": i})

            elif file_path.suffix == ".json":
                try:
                    data = json.loads(file_path.read_text(encoding="utf-8"))
                    if isinstance(data, list):
                        for j, item in enumerate(data):
                            text = json.dumps(item, ensure_ascii=False)
                            doc_id = f"{file_path.stem}_item_{j}"
                            docs.append(text)
                            ids.append(doc_id)
                            metas.append({"source": str(file_path), "chunk": j})
                except json.JSONDecodeError as exc:
                    logger.error("JSON parse error in %s: %s", file_path, exc)

        return docs, ids, metas

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 600, overlap: int = 80) -> List[str]:
        """
        Split text into overlapping chunks of approximately `chunk_size` characters.
        Tries to split at paragraph boundaries first.
        """
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks: List[str] = []
        current = ""

        for para in paragraphs:
            if len(current) + len(para) < chunk_size:
                current = current + "\n\n" + para if current else para
            else:
                if current:
                    chunks.append(current.strip())
                # If the paragraph itself is too long, break it by sentences
                if len(para) > chunk_size:
                    sentences = para.replace(". ", ".|").split("|")
                    sub = ""
                    for sent in sentences:
                        if len(sub) + len(sent) < chunk_size:
                            sub += sent + " "
                        else:
                            if sub:
                                chunks.append(sub.strip())
                            sub = sent + " "
                    if sub:
                        current = sub.strip()
                    else:
                        current = ""
                else:
                    current = para

        if current:
            chunks.append(current.strip())

        return chunks

    # ------------------------------------------------------------------ #
    # Retrieval                                                            #
    # ------------------------------------------------------------------ #

    def retrieve(
        self,
        query: str,
        n_results: int = 5,
        collections: Optional[List[str]] = None,
    ) -> str:
        """
        Retrieve the most relevant document chunks for a query.

        Args:
            query:       The user's question / ingredient list.
            n_results:   How many chunks to return per collection.
            collections: Which collections to search (default: all).

        Returns:
            A single string of concatenated relevant context.
        """
        if not self._initialized:
            self.initialize()

        target_collections = collections or list(self.collections.keys())
        all_chunks: List[str] = []

        for col_name in target_collections:
            collection = self.collections.get(col_name)
            if collection is None or collection.count() == 0:
                continue
            try:
                results = collection.query(
                    query_texts=[query],
                    n_results=min(n_results, collection.count()),
                )
                if results and results.get("documents"):
                    all_chunks.extend(results["documents"][0])
            except Exception as exc:
                logger.error("Retrieval error in collection '%s': %s", col_name, exc)

        # Deduplicate while preserving order
        seen: set = set()
        unique_chunks: List[str] = []
        for chunk in all_chunks:
            key = chunk[:120]
            if key not in seen:
                seen.add(key)
                unique_chunks.append(chunk)

        context = "\n\n---\n\n".join(unique_chunks)
        logger.debug("Retrieved %d chunks (%d chars) for query: %s", len(unique_chunks), len(context), query[:80])
        return context

    def retrieve_by_ingredients(self, ingredients: List[str], n_results: int = 5) -> str:
        """
        Targeted retrieval using ingredient list query to find matching recipes.
        """
        ingredient_query = f"recipes with ingredients: {', '.join(ingredients)}"
        return self.retrieve(
            query=ingredient_query,
            n_results=n_results,
            collections=["recipes"],
        )

    def retrieve_substitutions(self, ingredient: str) -> str:
        """Retrieve substitution options for a specific ingredient."""
        return self.retrieve(
            query=f"substitution alternatives for {ingredient}",
            n_results=3,
            collections=["substitutions"],
        )

    def retrieve_dietary(self, diet_type: str) -> str:
        """Retrieve dietary guidance for a specific diet."""
        return self.retrieve(
            query=f"{diet_type} diet guidelines recipes",
            n_results=3,
            collections=["dietary", "recipes"],
        )

    def get_status(self) -> Dict[str, Any]:
        """Return current collection sizes for health-check endpoint."""
        status = {"initialized": self._initialized, "collections": {}}
        for name, col in self.collections.items():
            try:
                status["collections"][name] = col.count()
            except Exception:
                status["collections"][name] = 0
        return status
