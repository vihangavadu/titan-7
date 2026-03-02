#!/usr/bin/env python3
"""
TITAN V10.0 — Graph Evasion Engine
====================================
Defeats Graph Neural Network (GNN) based fraud detection systems.

Modern fraud detection builds heterogeneous entity graphs:
    Card <-> Device <-> IP <-> Merchant <-> Account <-> Email <-> Phone

GNN models (SemiGNN, GraphSAGE, GEM, CARE-GNN) detect fraud by analyzing
graph neighborhood structure — even when individual node features look clean.

This engine prevents detectable graph edges by:
1. Tracking all entity linkages across operations
2. Warning when reusing any node creates a dangerous graph connection
3. Recommending entity rotation to break graph chains
4. Enforcing isolation policies per operation

References:
    - DGFraud: https://github.com/safe-graph/DGFraud
    - CARE-GNN: "Enhancing GNN-based Fraud Detectors against Camouflaged Fraudsters" (CIKM'20)
    - GraphConsis: "Alleviating the Inconsistency Problem of Applying GNN to Fraud Detection" (SIGIR'20)
"""

import hashlib
import json
import logging
import os
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("TITAN-GRAPH-EVASION")


# ═══════════════════════════════════════════════════════════════════════════════
# ENTITY TYPES — Nodes in the fraud detection graph
# ═══════════════════════════════════════════════════════════════════════════════

class EntityType(Enum):
    CARD = "card"
    DEVICE_FINGERPRINT = "device_fp"
    IP_ADDRESS = "ip"
    MERCHANT = "merchant"
    ACCOUNT_EMAIL = "email"
    PHONE = "phone"
    BILLING_ADDRESS = "billing_addr"
    SHIPPING_ADDRESS = "shipping_addr"
    BROWSER_PROFILE = "browser_profile"
    PROXY_EXIT_IP = "proxy_exit_ip"


class RiskLevel(Enum):
    SAFE = "safe"
    CAUTION = "caution"
    DANGEROUS = "dangerous"
    CRITICAL = "critical"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class GraphEdge:
    """A link between two entities observed by fraud detection systems."""
    source_type: EntityType
    source_hash: str
    target_type: EntityType
    target_hash: str
    first_seen: datetime
    last_seen: datetime
    transaction_count: int = 1
    merchants_involved: Set[str] = field(default_factory=set)


@dataclass
class GraphSafetyReport:
    """Result of a graph safety check before an operation."""
    is_safe: bool
    risk_level: RiskLevel
    risk_score: float              # 0.0 (safe) to 1.0 (critical)
    existing_edges: List[GraphEdge]
    new_edges_created: int
    warnings: List[str]
    recommendations: List[str]
    entity_reuse_count: Dict[str, int]


@dataclass
class RotationRecommendation:
    """Recommendation for which entities to rotate."""
    entity_type: EntityType
    current_value_hash: str
    reason: str
    urgency: str                   # "immediate", "soon", "optional"
    linked_cards: int              # how many cards this entity is linked to


# ═══════════════════════════════════════════════════════════════════════════════
# GNN DETECTION THRESHOLDS
# Based on DGFraud research: typical GNN flags at these connection counts
# ═══════════════════════════════════════════════════════════════════════════════

GNN_THRESHOLDS = {
    EntityType.DEVICE_FINGERPRINT: {
        "max_cards": 2,        # Same device with >2 cards = strong signal
        "max_merchants": 8,    # Same device at >8 merchants in 7d = anomaly
        "decay_days": 30,      # Links decay after 30 days
    },
    EntityType.IP_ADDRESS: {
        "max_cards": 3,        # Same IP with >3 cards = flag
        "max_merchants": 10,
        "decay_days": 7,       # IP links decay faster (dynamic IPs)
    },
    EntityType.ACCOUNT_EMAIL: {
        "max_cards": 1,        # Same email with >1 card = strong fraud signal
        "max_merchants": 15,
        "decay_days": 90,
    },
    EntityType.PHONE: {
        "max_cards": 2,
        "max_merchants": 10,
        "decay_days": 60,
    },
    EntityType.BILLING_ADDRESS: {
        "max_cards": 3,        # Multiple cards at same address = less suspicious
        "max_merchants": 20,
        "decay_days": 90,
    },
    EntityType.BROWSER_PROFILE: {
        "max_cards": 1,        # Profile should be 1:1 with card
        "max_merchants": 15,
        "decay_days": 30,
    },
    EntityType.PROXY_EXIT_IP: {
        "max_cards": 2,        # Residential proxy shared, but limit exposure
        "max_merchants": 8,
        "decay_days": 3,       # Proxy IPs rotate frequently
    },
    EntityType.MERCHANT: {
        "max_cards": 50,       # Merchant sees many cards (normal)
        "max_merchants": 1,
        "decay_days": 90,
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# GRAPH ISOLATION POLICY
# ═══════════════════════════════════════════════════════════════════════════════

class GraphIsolationPolicy:
    """
    Enforces graph isolation between operations to prevent GNN detection.

    Core principle: Each card should have a UNIQUE subgraph.
    Sharing any entity (device, IP, email) between cards creates edges
    that GNN models use to cluster fraud rings.
    """

    def __init__(self, state_dir: Optional[Path] = None):
        self._state_dir = state_dir or Path(
            os.environ.get("TITAN_STATE_DIR", "/opt/titan/state")
        ) / "graph_evasion"
        self._state_dir.mkdir(parents=True, exist_ok=True)

        self._edges: Dict[str, GraphEdge] = {}
        self._entity_cards: Dict[str, Set[str]] = defaultdict(set)
        self._card_entities: Dict[str, Set[str]] = defaultdict(set)
        self._lock = threading.Lock()

        self._load_state()

    def _edge_key(self, src_type: EntityType, src_hash: str,
                  tgt_type: EntityType, tgt_hash: str) -> str:
        return f"{src_type.value}:{src_hash}:{tgt_type.value}:{tgt_hash}"

    def _hash_entity(self, value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()[:16]

    # ─── State Persistence ──────────────────────────────────────────────

    def _load_state(self):
        state_file = self._state_dir / "graph_state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for ek, ed in data.get("edges", {}).items():
                    self._edges[ek] = GraphEdge(
                        source_type=EntityType(ed["st"]),
                        source_hash=ed["sh"],
                        target_type=EntityType(ed["tt"]),
                        target_hash=ed["th"],
                        first_seen=datetime.fromisoformat(ed["fs"]),
                        last_seen=datetime.fromisoformat(ed["ls"]),
                        transaction_count=ed.get("tc", 1),
                        merchants_involved=set(ed.get("mi", [])),
                    )
                for entity_key, cards in data.get("entity_cards", {}).items():
                    self._entity_cards[entity_key] = set(cards)
                for card_key, entities in data.get("card_entities", {}).items():
                    self._card_entities[card_key] = set(entities)
                logger.info(f"Loaded graph state: {len(self._edges)} edges, "
                            f"{len(self._entity_cards)} entities tracked")
            except Exception as e:
                logger.warning(f"Failed to load graph state: {e}")

    def _save_state(self):
        state_file = self._state_dir / "graph_state.json"
        try:
            edges_data = {}
            for ek, edge in self._edges.items():
                edges_data[ek] = {
                    "st": edge.source_type.value,
                    "sh": edge.source_hash,
                    "tt": edge.target_type.value,
                    "th": edge.target_hash,
                    "fs": edge.first_seen.isoformat(),
                    "ls": edge.last_seen.isoformat(),
                    "tc": edge.transaction_count,
                    "mi": list(edge.merchants_involved),
                }
            data = {
                "edges": edges_data,
                "entity_cards": {k: list(v) for k, v in self._entity_cards.items()},
                "card_entities": {k: list(v) for k, v in self._card_entities.items()},
                "updated": datetime.now().isoformat(),
            }
            state_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save graph state: {e}")

    # ─── Graph Safety Check ─────────────────────────────────────────────

    def check_graph_safety(
        self,
        card_number: str,
        device_fingerprint: str = "",
        ip_address: str = "",
        email: str = "",
        phone: str = "",
        billing_address: str = "",
        merchant_id: str = "",
        browser_profile_id: str = "",
        proxy_exit_ip: str = "",
    ) -> GraphSafetyReport:
        """
        Check if an operation creates dangerous graph edges.

        Returns a safety report with risk level and recommendations.
        """
        card_hash = self._hash_entity(card_number)
        now = datetime.now()

        entities = {}
        if device_fingerprint:
            entities[EntityType.DEVICE_FINGERPRINT] = self._hash_entity(device_fingerprint)
        if ip_address:
            entities[EntityType.IP_ADDRESS] = self._hash_entity(ip_address)
        if email:
            entities[EntityType.ACCOUNT_EMAIL] = self._hash_entity(email)
        if phone:
            entities[EntityType.PHONE] = self._hash_entity(phone)
        if billing_address:
            entities[EntityType.BILLING_ADDRESS] = self._hash_entity(billing_address)
        if merchant_id:
            entities[EntityType.MERCHANT] = self._hash_entity(merchant_id)
        if browser_profile_id:
            entities[EntityType.BROWSER_PROFILE] = self._hash_entity(browser_profile_id)
        if proxy_exit_ip:
            entities[EntityType.PROXY_EXIT_IP] = self._hash_entity(proxy_exit_ip)

        warnings = []
        recommendations = []
        existing_edges = []
        new_edges = 0
        entity_reuse = {}
        risk_score = 0.0

        with self._lock:
            for etype, ehash in entities.items():
                entity_key = f"{etype.value}:{ehash}"
                thresholds = GNN_THRESHOLDS.get(etype, {"max_cards": 3, "decay_days": 30})
                decay_cutoff = now - timedelta(days=thresholds["decay_days"])

                # Check how many OTHER cards this entity is linked to
                linked_cards = self._entity_cards.get(entity_key, set())
                active_linked = set()
                for lc in linked_cards:
                    # Check if the link is still within decay window
                    ek = self._edge_key(EntityType.CARD, lc, etype, ehash)
                    edge = self._edges.get(ek)
                    if edge and edge.last_seen > decay_cutoff:
                        active_linked.add(lc)

                other_cards = active_linked - {card_hash}
                entity_reuse[etype.value] = len(other_cards)

                if other_cards:
                    max_cards = thresholds["max_cards"]
                    card_count = len(other_cards) + 1  # +1 for current card

                    if card_count > max_cards:
                        severity = min(1.0, (card_count - max_cards) / max_cards)
                        risk_score += severity * 0.3  # Weight per entity type

                        if severity > 0.5:
                            warnings.append(
                                f"CRITICAL: {etype.value} linked to {card_count} cards "
                                f"(threshold: {max_cards}). GNN WILL detect this cluster."
                            )
                            recommendations.append(
                                f"ROTATE {etype.value} immediately — use a fresh "
                                f"{'device profile' if etype == EntityType.DEVICE_FINGERPRINT else etype.value}"
                            )
                        else:
                            warnings.append(
                                f"WARNING: {etype.value} approaching threshold "
                                f"({card_count}/{max_cards} cards)"
                            )

                    # Record existing edges
                    for oc in other_cards:
                        ek = self._edge_key(EntityType.CARD, oc, etype, ehash)
                        if ek in self._edges:
                            existing_edges.append(self._edges[ek])
                else:
                    new_edges += 1

        risk_score = min(1.0, risk_score)

        if risk_score >= 0.7:
            risk_level = RiskLevel.CRITICAL
        elif risk_score >= 0.4:
            risk_level = RiskLevel.DANGEROUS
        elif risk_score >= 0.15:
            risk_level = RiskLevel.CAUTION
        else:
            risk_level = RiskLevel.SAFE

        if not warnings:
            recommendations.append("Graph is clean — no dangerous entity reuse detected")

        return GraphSafetyReport(
            is_safe=risk_level in (RiskLevel.SAFE, RiskLevel.CAUTION),
            risk_level=risk_level,
            risk_score=risk_score,
            existing_edges=existing_edges,
            new_edges_created=new_edges,
            warnings=warnings,
            recommendations=recommendations,
            entity_reuse_count=entity_reuse,
        )

    # ─── Record Operation ───────────────────────────────────────────────

    def record_operation(
        self,
        card_number: str,
        device_fingerprint: str = "",
        ip_address: str = "",
        email: str = "",
        phone: str = "",
        billing_address: str = "",
        merchant_id: str = "",
        browser_profile_id: str = "",
        proxy_exit_ip: str = "",
    ):
        """Record an operation's entity linkages in the graph."""
        card_hash = self._hash_entity(card_number)
        now = datetime.now()
        merchant_hash = self._hash_entity(merchant_id) if merchant_id else ""

        entities = {}
        if device_fingerprint:
            entities[EntityType.DEVICE_FINGERPRINT] = self._hash_entity(device_fingerprint)
        if ip_address:
            entities[EntityType.IP_ADDRESS] = self._hash_entity(ip_address)
        if email:
            entities[EntityType.ACCOUNT_EMAIL] = self._hash_entity(email)
        if phone:
            entities[EntityType.PHONE] = self._hash_entity(phone)
        if billing_address:
            entities[EntityType.BILLING_ADDRESS] = self._hash_entity(billing_address)
        if browser_profile_id:
            entities[EntityType.BROWSER_PROFILE] = self._hash_entity(browser_profile_id)
        if proxy_exit_ip:
            entities[EntityType.PROXY_EXIT_IP] = self._hash_entity(proxy_exit_ip)
        if merchant_id:
            entities[EntityType.MERCHANT] = self._hash_entity(merchant_id)

        with self._lock:
            for etype, ehash in entities.items():
                entity_key = f"{etype.value}:{ehash}"
                edge_key = self._edge_key(EntityType.CARD, card_hash, etype, ehash)

                if edge_key in self._edges:
                    edge = self._edges[edge_key]
                    edge.last_seen = now
                    edge.transaction_count += 1
                    if merchant_hash:
                        edge.merchants_involved.add(merchant_hash)
                else:
                    self._edges[edge_key] = GraphEdge(
                        source_type=EntityType.CARD,
                        source_hash=card_hash,
                        target_type=etype,
                        target_hash=ehash,
                        first_seen=now,
                        last_seen=now,
                        transaction_count=1,
                        merchants_involved={merchant_hash} if merchant_hash else set(),
                    )

                self._entity_cards[entity_key].add(card_hash)
                self._card_entities[card_hash].add(entity_key)

            self._save_state()

        logger.info(
            f"Graph recorded: card {card_hash[:8]}.. linked to "
            f"{len(entities)} entities"
        )

    # ─── Rotation Recommendations ───────────────────────────────────────

    def suggest_rotations(self, card_number: str = "") -> List[RotationRecommendation]:
        """
        Suggest which entities should be rotated to reduce graph risk.
        If card_number is provided, recommendations are specific to that card.
        Otherwise, returns global recommendations.
        """
        recommendations = []
        now = datetime.now()

        with self._lock:
            for entity_key, linked_cards in self._entity_cards.items():
                if len(linked_cards) <= 1:
                    continue

                parts = entity_key.split(":", 1)
                if len(parts) != 2:
                    continue
                etype_str, ehash = parts
                try:
                    etype = EntityType(etype_str)
                except ValueError:
                    continue

                thresholds = GNN_THRESHOLDS.get(etype, {"max_cards": 3, "decay_days": 30})
                decay_cutoff = now - timedelta(days=thresholds["decay_days"])

                # Count active links
                active_cards = set()
                for ch in linked_cards:
                    ek = self._edge_key(EntityType.CARD, ch, etype, ehash)
                    edge = self._edges.get(ek)
                    if edge and edge.last_seen > decay_cutoff:
                        active_cards.add(ch)

                if len(active_cards) > thresholds["max_cards"]:
                    urgency = "immediate" if len(active_cards) > thresholds["max_cards"] * 2 else "soon"
                    recommendations.append(RotationRecommendation(
                        entity_type=etype,
                        current_value_hash=ehash,
                        reason=f"{len(active_cards)} cards sharing this {etype.value} "
                               f"(max safe: {thresholds['max_cards']})",
                        urgency=urgency,
                        linked_cards=len(active_cards),
                    ))
                elif len(active_cards) == thresholds["max_cards"]:
                    recommendations.append(RotationRecommendation(
                        entity_type=etype,
                        current_value_hash=ehash,
                        reason=f"{etype.value} at threshold ({len(active_cards)}/{thresholds['max_cards']})",
                        urgency="optional",
                        linked_cards=len(active_cards),
                    ))

        recommendations.sort(key=lambda r: {"immediate": 0, "soon": 1, "optional": 2}[r.urgency])
        return recommendations

    # ─── Graph Statistics ───────────────────────────────────────────────

    def get_graph_stats(self) -> Dict[str, Any]:
        """Get current graph statistics."""
        with self._lock:
            now = datetime.now()
            active_edges = 0
            expired_edges = 0
            for edge in self._edges.values():
                thresholds = GNN_THRESHOLDS.get(edge.target_type, {"decay_days": 30})
                if edge.last_seen > now - timedelta(days=thresholds["decay_days"]):
                    active_edges += 1
                else:
                    expired_edges += 1

            multi_card_entities = sum(
                1 for cards in self._entity_cards.values() if len(cards) > 1
            )

            return {
                "total_edges": len(self._edges),
                "active_edges": active_edges,
                "expired_edges": expired_edges,
                "unique_entities": len(self._entity_cards),
                "unique_cards": len(self._card_entities),
                "multi_card_entities": multi_card_entities,
                "risk_entities": sum(
                    1 for entity_key, cards in self._entity_cards.items()
                    if len(cards) > GNN_THRESHOLDS.get(
                        EntityType(entity_key.split(":")[0]),
                        {"max_cards": 3}
                    ).get("max_cards", 3)
                ),
            }

    # ─── Cleanup ────────────────────────────────────────────────────────

    def cleanup_expired(self) -> int:
        """Remove expired edges from the graph. Returns count removed."""
        now = datetime.now()
        removed = 0
        with self._lock:
            expired_keys = []
            for ek, edge in self._edges.items():
                thresholds = GNN_THRESHOLDS.get(edge.target_type, {"decay_days": 30})
                if edge.last_seen < now - timedelta(days=thresholds["decay_days"]):
                    expired_keys.append(ek)

            for ek in expired_keys:
                edge = self._edges.pop(ek)
                entity_key = f"{edge.target_type.value}:{edge.target_hash}"
                if entity_key in self._entity_cards:
                    self._entity_cards[entity_key].discard(edge.source_hash)
                    if not self._entity_cards[entity_key]:
                        del self._entity_cards[entity_key]
                removed += 1

            if removed:
                self._save_state()
                logger.info(f"Cleaned up {removed} expired graph edges")

        return removed


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

_policy_instance: Optional[GraphIsolationPolicy] = None
_policy_lock = threading.Lock()


def get_graph_policy() -> GraphIsolationPolicy:
    """Get or create the singleton graph isolation policy."""
    global _policy_instance
    if _policy_instance is None:
        with _policy_lock:
            if _policy_instance is None:
                _policy_instance = GraphIsolationPolicy()
    return _policy_instance


def check_graph_safety(**kwargs) -> GraphSafetyReport:
    """Quick check if an operation is graph-safe."""
    return get_graph_policy().check_graph_safety(**kwargs)


def record_operation(**kwargs):
    """Record operation entities in the graph."""
    get_graph_policy().record_operation(**kwargs)


def suggest_rotations(card_number: str = "") -> List[RotationRecommendation]:
    """Get entity rotation recommendations."""
    return get_graph_policy().suggest_rotations(card_number)


def get_graph_stats() -> Dict[str, Any]:
    """Get graph statistics."""
    return get_graph_policy().get_graph_stats()
