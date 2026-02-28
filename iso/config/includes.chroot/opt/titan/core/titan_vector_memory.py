"""
TITAN V7.6 SINGULARITY — Vector Memory Store (ChromaDB)
Persistent semantic memory for operational intelligence.

Provides:
1. Operation Memory    — Store/recall past operation outcomes by similarity
2. Target Intelligence — Semantic search over merchant intel corpus
3. BIN Knowledge Base  — Enriched BIN data with decline pattern embeddings
4. Profile Templates   — Find similar profile configs by fingerprint traits
5. Threat Intel        — Semantic search over antifraud detection signatures

Architecture:
    - ChromaDB persistent storage at /opt/titan/data/vector_db/
    - Sentence-transformer embeddings (all-MiniLM-L6-v2, 384-dim)
    - Falls back to TF-IDF hashing if sentence-transformers unavailable
    - Collections auto-created on first use
    - Thread-safe singleton access via get_vector_memory()
"""

import json
import time
import logging
import hashlib
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

__version__ = "8.0.0"
__author__ = "Dva.12"

logger = logging.getLogger("TITAN-VECTOR")

# ═══════════════════════════════════════════════════════════════════════════════
# CHROMADB INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

_VECTOR_DB_PATH = Path("/opt/titan/data/vector_db")
_CHROMA_AVAILABLE = False
_SENTENCE_TRANSFORMER_AVAILABLE = False

try:
    import chromadb
    from chromadb.config import Settings
    _CHROMA_AVAILABLE = True
except ImportError:
    chromadb = None
    logger.warning("ChromaDB not installed. Install with: pip install chromadb")

try:
    from chromadb.utils import embedding_functions
    _SENTENCE_TRANSFORMER_AVAILABLE = True
except ImportError:
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MemoryRecord:
    """A single memory record with metadata."""
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0  # similarity score (0-1, higher = more similar)
    timestamp: float = 0.0


@dataclass
class SearchResult:
    """Result from a vector similarity search."""
    records: List[MemoryRecord]
    query: str
    collection: str
    search_time_ms: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# COLLECTION NAMES
# ═══════════════════════════════════════════════════════════════════════════════

COLLECTION_OPERATIONS = "titan_operations"       # Past operation outcomes
COLLECTION_TARGETS = "titan_targets"             # Merchant intelligence
COLLECTION_BINS = "titan_bins"                   # BIN knowledge base
COLLECTION_PROFILES = "titan_profiles"           # Profile templates
COLLECTION_THREATS = "titan_threats"             # Threat intelligence
COLLECTION_DECLINES = "titan_declines"           # Decline patterns
COLLECTION_GENERAL = "titan_general"             # General knowledge


# ═══════════════════════════════════════════════════════════════════════════════
# VECTOR MEMORY STORE
# ═══════════════════════════════════════════════════════════════════════════════

class TitanVectorMemory:
    """
    ChromaDB-backed semantic memory for Titan OS.

    Stores operational knowledge as vector embeddings for fast
    similarity search. Enables the cognitive core to recall
    relevant past experiences when making decisions.

    Usage:
        mem = get_vector_memory()

        # Store an operation outcome
        mem.store_operation({
            "bin": "411111", "target": "amazon.com", "amount": 299.99,
            "result": "declined", "reason": "3ds_challenge",
            "fraud_engine": "forter"
        })

        # Find similar past operations
        results = mem.recall_similar_operations(
            "BIN 411111 on amazon.com for $300"
        )

        # Store target intel
        mem.store_target_intel("amazon.com", {
            "fraud_engine": "forter", "3ds_rate": 0.85,
            "best_approach": "low-value exemption"
        })

        # Search target intel
        results = mem.search_targets("merchant with forter and high 3DS")
    """

    def __init__(self, db_path: str = None, in_memory: bool = False):
        self._lock = threading.Lock()
        self._db_path = Path(db_path) if db_path else _VECTOR_DB_PATH
        self._client = None
        self._collections: Dict[str, Any] = {}
        self._embedding_fn = None
        self._initialized = False
        self._in_memory = in_memory

        self._init_db()

    def _init_db(self):
        """Initialize ChromaDB client and collections."""
        if not _CHROMA_AVAILABLE:
            logger.warning("ChromaDB unavailable — vector memory disabled")
            return

        try:
            if self._in_memory:
                self._client = chromadb.Client()
            else:
                self._db_path.mkdir(parents=True, exist_ok=True)
                self._client = chromadb.PersistentClient(
                    path=str(self._db_path),
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True,
                    )
                )

            # Try sentence-transformer embeddings (best quality)
            if _SENTENCE_TRANSFORMER_AVAILABLE:
                try:
                    self._embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                        model_name="all-MiniLM-L6-v2"
                    )
                    logger.info("Using SentenceTransformer embeddings (all-MiniLM-L6-v2)")
                except Exception as e:
                    logger.warning(f"SentenceTransformer failed: {e}, using default embeddings")
                    self._embedding_fn = embedding_functions.DefaultEmbeddingFunction()
            else:
                self._embedding_fn = None  # ChromaDB will use its default

            self._initialized = True
            logger.info(f"Vector memory initialized at {self._db_path}")

        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self._initialized = False

    def _get_collection(self, name: str):
        """Get or create a collection."""
        if not self._initialized:
            return None

        if name not in self._collections:
            try:
                kwargs = {"name": name}
                if self._embedding_fn:
                    kwargs["embedding_function"] = self._embedding_fn
                self._collections[name] = self._client.get_or_create_collection(**kwargs)
            except Exception as e:
                logger.error(f"Failed to get collection '{name}': {e}")
                return None

        return self._collections[name]

    @property
    def is_available(self) -> bool:
        """Check if vector memory is operational."""
        return self._initialized and self._client is not None

    # ═══════════════════════════════════════════════════════════════════════
    # CORE CRUD OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════

    def store(self, collection_name: str, doc_id: str, content: str,
              metadata: Dict = None) -> bool:
        """
        Store a document in a collection.

        Args:
            collection_name: Target collection
            doc_id: Unique document ID
            content: Text content to embed and store
            metadata: Optional metadata dict (values must be str/int/float/bool)

        Returns:
            True if stored successfully
        """
        collection = self._get_collection(collection_name)
        if collection is None:
            return False

        try:
            # ChromaDB metadata values must be str, int, float, or bool
            clean_meta = self._clean_metadata(metadata or {})
            clean_meta["_stored_at"] = time.time()

            with self._lock:
                collection.upsert(
                    ids=[doc_id],
                    documents=[content],
                    metadatas=[clean_meta],
                )
            return True

        except Exception as e:
            logger.error(f"Store failed [{collection_name}]: {e}")
            return False

    def search(self, collection_name: str, query: str,
               n_results: int = 5, where: Dict = None,
               where_document: Dict = None) -> SearchResult:
        """
        Semantic similarity search.

        Args:
            collection_name: Collection to search
            query: Natural language query
            n_results: Max results to return
            where: Metadata filter (e.g., {"target": "amazon.com"})
            where_document: Document content filter

        Returns:
            SearchResult with ranked MemoryRecords
        """
        collection = self._get_collection(collection_name)
        if collection is None:
            return SearchResult(records=[], query=query,
                                collection=collection_name)

        t0 = time.time()
        try:
            kwargs = {
                "query_texts": [query],
                "n_results": min(n_results, collection.count() or 1),
            }
            if where:
                kwargs["where"] = where
            if where_document:
                kwargs["where_document"] = where_document

            with self._lock:
                results = collection.query(**kwargs)

            records = []
            if results and results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    distance = results["distances"][0][i] if results.get("distances") else 0
                    # Convert distance to similarity score (0-1)
                    similarity = max(0, 1 - distance / 2)

                    records.append(MemoryRecord(
                        id=doc_id,
                        content=results["documents"][0][i] if results.get("documents") else "",
                        metadata=results["metadatas"][0][i] if results.get("metadatas") else {},
                        score=round(similarity, 4),
                        timestamp=results["metadatas"][0][i].get("_stored_at", 0)
                        if results.get("metadatas") else 0,
                    ))

            elapsed = (time.time() - t0) * 1000
            return SearchResult(
                records=records, query=query,
                collection=collection_name,
                search_time_ms=round(elapsed, 2),
            )

        except Exception as e:
            logger.error(f"Search failed [{collection_name}]: {e}")
            return SearchResult(records=[], query=query,
                                collection=collection_name)

    def delete(self, collection_name: str, doc_id: str) -> bool:
        """Delete a document by ID."""
        collection = self._get_collection(collection_name)
        if collection is None:
            return False
        try:
            with self._lock:
                collection.delete(ids=[doc_id])
            return True
        except Exception as e:
            logger.error(f"Delete failed [{collection_name}]: {e}")
            return False

    def count(self, collection_name: str) -> int:
        """Get document count in a collection."""
        collection = self._get_collection(collection_name)
        if collection is None:
            return 0
        try:
            return collection.count()
        except Exception:
            return 0

    # ═══════════════════════════════════════════════════════════════════════
    # OPERATION MEMORY
    # ═══════════════════════════════════════════════════════════════════════

    def store_operation(self, op_data: Dict) -> bool:
        """
        Store an operation outcome for future recall.

        Args:
            op_data: Dict with keys like bin, target, amount, result,
                     reason, fraud_engine, profile_age, proxy_type, etc.
        """
        doc_id = hashlib.sha256(
            f"{op_data.get('bin', '')}_{op_data.get('target', '')}_{time.time()}"
            .encode()
        ).hexdigest()[:16]

        content = self._operation_to_text(op_data)
        metadata = {
            "bin": str(op_data.get("bin", ""))[:6],
            "target": str(op_data.get("target", "")),
            "amount": float(op_data.get("amount", 0)),
            "result": str(op_data.get("result", "unknown")),
            "reason": str(op_data.get("reason", "")),
            "fraud_engine": str(op_data.get("fraud_engine", "unknown")),
        }

        return self.store(COLLECTION_OPERATIONS, doc_id, content, metadata)

    def recall_similar_operations(self, query: str, n: int = 5,
                                   target: str = None) -> List[MemoryRecord]:
        """
        Recall past operations similar to the query.

        Args:
            query: Natural language description of current operation
            n: Number of results
            target: Optional filter by target domain
        """
        where = {"target": target} if target else None
        result = self.search(COLLECTION_OPERATIONS, query, n_results=n, where=where)
        return result.records

    def _operation_to_text(self, op: Dict) -> str:
        """Convert operation data to searchable text."""
        parts = []
        if op.get("bin"):
            parts.append(f"BIN {op['bin'][:6]}")
        if op.get("target"):
            parts.append(f"target {op['target']}")
        if op.get("amount"):
            parts.append(f"amount ${op['amount']:.2f}")
        if op.get("result"):
            parts.append(f"result: {op['result']}")
        if op.get("reason"):
            parts.append(f"reason: {op['reason']}")
        if op.get("fraud_engine"):
            parts.append(f"fraud engine: {op['fraud_engine']}")
        if op.get("card_type"):
            parts.append(f"card type: {op['card_type']}")
        if op.get("card_level"):
            parts.append(f"card level: {op['card_level']}")
        if op.get("proxy_type"):
            parts.append(f"proxy: {op['proxy_type']}")
        if op.get("notes"):
            parts.append(f"notes: {op['notes']}")
        return " | ".join(parts) if parts else json.dumps(op)

    # ═══════════════════════════════════════════════════════════════════════
    # TARGET INTELLIGENCE
    # ═══════════════════════════════════════════════════════════════════════

    def store_target_intel(self, domain: str, intel: Dict) -> bool:
        """Store merchant intelligence."""
        doc_id = f"target_{domain.replace('.', '_')}"
        content = (
            f"Merchant: {domain} | "
            f"Fraud engine: {intel.get('fraud_engine', 'unknown')} | "
            f"PSP: {intel.get('payment_processor', 'unknown')} | "
            f"3DS rate: {intel.get('three_ds_rate', 'unknown')} | "
            f"Friction: {intel.get('friction', 'unknown')} | "
            f"Best cards: {intel.get('best_cards', 'unknown')} | "
            f"Notes: {intel.get('notes', '')}"
        )
        metadata = {
            "domain": domain,
            "fraud_engine": str(intel.get("fraud_engine", "unknown")),
            "friction": str(intel.get("friction", "medium")),
            "three_ds_rate": float(intel.get("three_ds_rate", 0.3)),
        }
        return self.store(COLLECTION_TARGETS, doc_id, content, metadata)

    def search_targets(self, query: str, n: int = 5) -> List[MemoryRecord]:
        """Search target intelligence by semantic similarity."""
        result = self.search(COLLECTION_TARGETS, query, n_results=n)
        return result.records

    # ═══════════════════════════════════════════════════════════════════════
    # BIN KNOWLEDGE BASE
    # ═══════════════════════════════════════════════════════════════════════

    def store_bin_intel(self, bin6: str, intel: Dict) -> bool:
        """Store BIN intelligence."""
        doc_id = f"bin_{bin6}"
        content = (
            f"BIN {bin6} | Bank: {intel.get('bank', 'unknown')} | "
            f"Country: {intel.get('country', 'unknown')} | "
            f"Type: {intel.get('card_type', 'credit')} | "
            f"Level: {intel.get('card_level', 'classic')} | "
            f"Network: {intel.get('network', 'unknown')} | "
            f"Risk: {intel.get('risk_level', 'medium')} | "
            f"Success rate: {intel.get('success_rate', 'unknown')} | "
            f"Best targets: {intel.get('best_targets', [])} | "
            f"Notes: {intel.get('notes', '')}"
        )
        metadata = {
            "bin": bin6,
            "country": str(intel.get("country", "US")),
            "network": str(intel.get("network", "visa")),
            "card_type": str(intel.get("card_type", "credit")),
            "risk_level": str(intel.get("risk_level", "medium")),
        }
        return self.store(COLLECTION_BINS, doc_id, content, metadata)

    def search_bins(self, query: str, n: int = 5,
                    network: str = None) -> List[MemoryRecord]:
        """Search BIN knowledge base."""
        where = {"network": network} if network else None
        result = self.search(COLLECTION_BINS, query, n_results=n, where=where)
        return result.records

    # ═══════════════════════════════════════════════════════════════════════
    # DECLINE PATTERN MEMORY
    # ═══════════════════════════════════════════════════════════════════════

    def store_decline(self, decline_data: Dict) -> bool:
        """Store a decline event for pattern learning."""
        doc_id = hashlib.sha256(
            f"{decline_data.get('bin', '')}_{decline_data.get('target', '')}_{time.time()}"
            .encode()
        ).hexdigest()[:16]

        content = (
            f"Decline: BIN {decline_data.get('bin', '?')[:6]} on "
            f"{decline_data.get('target', '?')} for "
            f"${decline_data.get('amount', 0):.2f} | "
            f"Code: {decline_data.get('code', '?')} | "
            f"Category: {decline_data.get('category', '?')} | "
            f"Fraud engine: {decline_data.get('fraud_engine', '?')}"
        )
        metadata = {
            "bin": str(decline_data.get("bin", ""))[:6],
            "target": str(decline_data.get("target", "")),
            "code": str(decline_data.get("code", "")),
            "category": str(decline_data.get("category", "")),
            "amount": float(decline_data.get("amount", 0)),
        }
        return self.store(COLLECTION_DECLINES, doc_id, content, metadata)

    def find_similar_declines(self, query: str, n: int = 10) -> List[MemoryRecord]:
        """Find similar decline patterns."""
        result = self.search(COLLECTION_DECLINES, query, n_results=n)
        return result.records

    # ═══════════════════════════════════════════════════════════════════════
    # THREAT INTELLIGENCE
    # ═══════════════════════════════════════════════════════════════════════

    def store_threat_intel(self, threat_id: str, intel: Dict) -> bool:
        """Store antifraud/threat intelligence."""
        content = (
            f"Threat: {intel.get('vendor', 'unknown')} | "
            f"Type: {intel.get('type', 'unknown')} | "
            f"Severity: {intel.get('severity', 'medium')} | "
            f"Detection method: {intel.get('detection_method', '')} | "
            f"Countermeasure: {intel.get('countermeasure', '')} | "
            f"Notes: {intel.get('notes', '')}"
        )
        metadata = {
            "vendor": str(intel.get("vendor", "unknown")),
            "type": str(intel.get("type", "unknown")),
            "severity": str(intel.get("severity", "medium")),
        }
        return self.store(COLLECTION_THREATS, threat_id, content, metadata)

    def search_threats(self, query: str, n: int = 5) -> List[MemoryRecord]:
        """Search threat intelligence."""
        result = self.search(COLLECTION_THREATS, query, n_results=n)
        return result.records

    # ═══════════════════════════════════════════════════════════════════════
    # GENERAL KNOWLEDGE STORE
    # ═══════════════════════════════════════════════════════════════════════

    def store_knowledge(self, key: str, content: str,
                        metadata: Dict = None) -> bool:
        """Store general knowledge."""
        return self.store(COLLECTION_GENERAL, key, content, metadata)

    def search_knowledge(self, query: str, n: int = 5) -> List[MemoryRecord]:
        """Search general knowledge base."""
        result = self.search(COLLECTION_GENERAL, query, n_results=n)
        return result.records

    # ═══════════════════════════════════════════════════════════════════════
    # CONTEXT BUILDER — Generate context for LLM prompts
    # ═══════════════════════════════════════════════════════════════════════

    def build_operation_context(self, bin_number: str, target: str,
                                 amount: float) -> str:
        """
        Build enriched context from vector memory for an operation.
        This is injected into LLM prompts for better decision-making.

        Returns a formatted string with relevant past operations,
        target intel, BIN knowledge, and decline patterns.
        """
        context_parts = []
        query = f"BIN {bin_number[:6]} on {target} for ${amount:.2f}"

        # Past similar operations
        ops = self.recall_similar_operations(query, n=3, target=target)
        if ops:
            context_parts.append("SIMILAR PAST OPERATIONS:")
            for op in ops:
                context_parts.append(
                    f"  [{op.score:.0%} match] {op.content}"
                )

        # Target intelligence
        target_intel = self.search_targets(target, n=1)
        if target_intel:
            context_parts.append(f"\nTARGET INTEL: {target_intel[0].content}")

        # BIN knowledge
        bin_intel = self.search_bins(f"BIN {bin_number[:6]}", n=1)
        if bin_intel:
            context_parts.append(f"\nBIN INTEL: {bin_intel[0].content}")

        # Recent declines for this BIN
        declines = self.find_similar_declines(
            f"BIN {bin_number[:6]} decline", n=3
        )
        if declines:
            context_parts.append("\nRECENT DECLINE PATTERNS:")
            for d in declines:
                context_parts.append(f"  {d.content}")

        # Threat intel for target
        threats = self.search_threats(f"{target} antifraud", n=2)
        if threats:
            context_parts.append("\nTHREAT INTEL:")
            for t in threats:
                context_parts.append(f"  {t.content}")

        if not context_parts:
            return ""

        return "\n--- VECTOR MEMORY CONTEXT ---\n" + "\n".join(context_parts) + "\n--- END CONTEXT ---\n"

    # ═══════════════════════════════════════════════════════════════════════
    # UTILITIES
    # ═══════════════════════════════════════════════════════════════════════

    def _clean_metadata(self, metadata: Dict) -> Dict:
        """Clean metadata to only contain ChromaDB-compatible types."""
        clean = {}
        for k, v in metadata.items():
            if isinstance(v, (str, int, float, bool)):
                clean[k] = v
            elif isinstance(v, (list, tuple)):
                clean[k] = json.dumps(v)
            elif v is None:
                clean[k] = ""
            else:
                clean[k] = str(v)
        return clean

    def get_stats(self) -> Dict:
        """Get vector memory statistics."""
        if not self.is_available:
            return {"available": False, "reason": "ChromaDB not initialized"}

        stats = {
            "available": True,
            "db_path": str(self._db_path),
            "collections": {},
        }

        for name in [COLLECTION_OPERATIONS, COLLECTION_TARGETS,
                     COLLECTION_BINS, COLLECTION_PROFILES,
                     COLLECTION_THREATS, COLLECTION_DECLINES,
                     COLLECTION_GENERAL]:
            stats["collections"][name] = self.count(name)

        stats["total_documents"] = sum(stats["collections"].values())
        return stats

    def reset_collection(self, collection_name: str) -> bool:
        """Reset (delete all documents in) a collection."""
        if not self._initialized:
            return False
        try:
            self._client.delete_collection(collection_name)
            self._collections.pop(collection_name, None)
            logger.info(f"Reset collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Reset failed [{collection_name}]: {e}")
            return False

    def reset_all(self) -> bool:
        """Reset all collections."""
        if not self._initialized:
            return False
        try:
            self._client.reset()
            self._collections.clear()
            logger.info("All vector memory collections reset")
            return True
        except Exception as e:
            logger.error(f"Reset all failed: {e}")
            return False


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

_vector_memory: Optional[TitanVectorMemory] = None
_vector_lock = threading.Lock()


def get_vector_memory(db_path: str = None,
                      in_memory: bool = False) -> TitanVectorMemory:
    """
    Get singleton TitanVectorMemory instance.

    Args:
        db_path: Override default DB path
        in_memory: Use in-memory DB (for testing)
    """
    global _vector_memory
    with _vector_lock:
        if _vector_memory is None:
            _vector_memory = TitanVectorMemory(db_path=db_path,
                                                in_memory=in_memory)
    return _vector_memory


def is_vector_memory_available() -> bool:
    """Check if vector memory is operational."""
    try:
        mem = get_vector_memory()
        return mem.is_available
    except Exception:
        return False
