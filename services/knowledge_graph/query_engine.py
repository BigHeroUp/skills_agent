"""Query Layer deterministico sopra il Knowledge Graph JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.knowledge_graph.models import KnowledgeEdge, KnowledgeNode
from services.knowledge_graph.store import KnowledgeGraphStore


class KnowledgeGraphQueryEngine:
    """Motore di query locale e rule-based per il Knowledge Graph."""

    CODE_NODE_TYPES = {"python_file", "python_class", "python_function", "python_import"}
    ANALYSIS_NODE_TYPES = {
        "analysis_run",
        "dataset",
        "dataframe_column",
        "insight",
        "anomaly",
        "root_cause",
        "report",
    }
    NODE_TYPE_BY_INTENT = {
        "funzioni": "python_function",
        "funzione": "python_function",
        "classi": "python_class",
        "classe": "python_class",
        "file": "python_file",
        "import": "python_import",
        "analisi": "analysis_run",
        "anomalie": "anomaly",
        "anomalia": "anomaly",
        "root cause": "root_cause",
        "cause radice": "root_cause",
        "colonne": "dataframe_column",
        "colonna": "dataframe_column",
        "report": "report",
    }
    TERM_SYNONYMS = {
        "grafici": ["grafici", "grafico", "chart", "charts", "plot", "figure", "visualization"],
        "grafico": ["grafici", "grafico", "chart", "charts", "plot", "figure", "visualization"],
        "excel": ["excel", "xlsx", "xls"],
        "oracle": ["oracle", "sql"],
        "report": ["report", "final_report"],
        "anomalie": ["anomalie", "anomalia", "anomaly", "anomalies"],
        "root": ["root", "root_cause", "cause"],
        "cause": ["cause", "root_cause"],
        "response_time": ["response_time", "response time", "responsetime"],
    }
    STOPWORDS = {
        "quali",
        "quale",
        "che",
        "cosa",
        "hanno",
        "ha",
        "su",
        "per",
        "con",
        "dei",
        "del",
        "delle",
        "della",
        "gli",
        "le",
        "la",
        "il",
        "i",
        "generano",
        "genera",
        "usano",
        "usa",
    }

    def __init__(self, store: KnowledgeGraphStore | None = None, path: str | Path | None = None):
        self.store = store or KnowledgeGraphStore(path)
        self.graph_exists = self.store.path.exists()
        self.snapshot = self.store.load()
        self._nodes = {node.id: node for node in self.snapshot.nodes}

    def find_nodes(
        self,
        node_type: str | None = None,
        label_contains: str | None = None,
        property_filters: dict | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Trova nodi per tipo, label e filtri semplici sulle properties."""
        results = []
        label_query = (label_contains or "").lower()
        filters = property_filters if isinstance(property_filters, dict) else {}
        for node in self.snapshot.nodes:
            if node_type and node.type != node_type:
                continue
            if label_query and label_query not in node.label.lower():
                continue
            if filters and not self._properties_match(node.properties, filters):
                continue
            results.append(node.to_dict())
            if len(results) >= max(0, limit):
                break
        return results

    def find_edges(
        self,
        relationship: str | None = None,
        source: str | None = None,
        target: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Trova archi per relazione, source e target."""
        results = []
        for edge in self.snapshot.edges:
            if relationship and edge.relationship != relationship:
                continue
            if source and edge.source != source:
                continue
            if target and edge.target != target:
                continue
            results.append(edge.to_dict())
            if len(results) >= max(0, limit):
                break
        return results

    def get_neighbors(
        self,
        node_id: str,
        direction: str = "both",
        relationship: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Restituisce i vicini di un nodo con l'arco che li collega."""
        if direction not in {"both", "in", "out"}:
            raise ValueError("direction deve essere 'both', 'in' oppure 'out'")

        neighbors = []
        for edge in self.snapshot.edges:
            if relationship and edge.relationship != relationship:
                continue
            if direction in {"both", "out"} and edge.source == node_id:
                target = self._nodes.get(edge.target)
                if target:
                    neighbors.append(self._neighbor_payload(target, edge, "out"))
            if direction in {"both", "in"} and edge.target == node_id:
                source = self._nodes.get(edge.source)
                if source:
                    neighbors.append(self._neighbor_payload(source, edge, "in"))
            if len(neighbors) >= max(0, limit):
                break
        return neighbors

    def search_code(self, text: str, limit: int = 30) -> list[dict[str, Any]]:
        """Cerca testo nei nodi del codice Python."""
        return self._search_nodes(text, self.CODE_NODE_TYPES, limit)

    def search_analysis(self, text: str, limit: int = 30) -> list[dict[str, Any]]:
        """Cerca testo nei nodi prodotti dalle analisi."""
        return self._search_nodes(text, self.ANALYSIS_NODE_TYPES, limit)

    def get_latest_analysis_runs(self, limit: int = 5) -> list[dict[str, Any]]:
        """Restituisce le run analitiche piu recenti ordinate per created_at."""
        runs = [node.to_dict() for node in self.snapshot.nodes if node.type == "analysis_run"]
        runs.sort(
            key=lambda item: str((item.get("properties") or {}).get("created_at") or ""),
            reverse=True,
        )
        return runs[: max(0, limit)]

    def get_analysis_lineage(self, analysis_run_id: str) -> dict[str, Any]:
        """Restituisce gli elementi collegati a una run analitica."""
        run = self._nodes.get(analysis_run_id)
        lineage = {
            "analysis_run": run.to_dict() if run else None,
            "dataset": [],
            "columns": [],
            "insights": [],
            "anomalies": [],
            "root_causes": [],
            "reports": [],
            "domain_packs": [],
        }
        if not run:
            return lineage

        relation_map = {
            "ANALYZED_DATASET": "dataset",
            "USES_DATASET": "dataset",
            "HAS_COLUMN": "columns",
            "PRODUCED_INSIGHT": "insights",
            "GENERATED_INSIGHT": "insights",
            "DETECTED_ANOMALY": "anomalies",
            "IDENTIFIED_ROOT_CAUSE": "root_causes",
            "PROPOSED_ROOT_CAUSE": "root_causes",
            "GENERATED_REPORT": "reports",
            "USED_DOMAIN_PACK": "domain_packs",
        }
        seen: dict[str, set[str]] = {key: set() for key in lineage if key != "analysis_run"}
        for edge in self.snapshot.edges:
            if edge.source != analysis_run_id or edge.relationship not in relation_map:
                continue
            bucket = relation_map[edge.relationship]
            node = self._nodes.get(edge.target)
            if node and node.id not in seen[bucket]:
                lineage[bucket].append(node.to_dict())
                seen[bucket].add(node.id)
        return lineage

    def compare_latest_analysis_runs(self, limit: int = 2) -> dict[str, Any]:
        """Confronta le ultime due run analitiche disponibili."""
        from services.knowledge_graph.analysis_comparator import AnalysisComparator

        latest = self.get_latest_analysis_runs(limit=limit)
        if len(latest) < 2:
            return {
                "status": "insufficient_analysis_runs",
                "reason": "Servono almeno due analysis_run nel Knowledge Graph per eseguire il confronto.",
                "runs": latest,
            }
        return AnalysisComparator(self).compare_analysis_runs(latest[1]["id"], latest[0]["id"])

    def answer_question_deterministic(self, question: str) -> dict[str, Any]:
        """Risponde a domande semplici usando solo regole e grafo locale."""
        clean_question = (question or "").strip()
        if not self.graph_exists and not self.snapshot.nodes:
            return {
                "question": clean_question,
                "answer": (
                    f"Knowledge Graph non trovato in {self.store.path}. "
                    "Esegui prima lo script di indicizzazione."
                ),
                "matches": [],
                "confidence": 0.0,
                "execution_type": "deterministic_kg_query",
            }

        lowered = clean_question.lower()
        if self._looks_like_analysis_comparison_question(lowered):
            from services.knowledge_graph.analysis_comparator import summarize_comparison

            comparison = self.compare_latest_analysis_runs(limit=2)
            summary = summarize_comparison(comparison)
            return {
                "question": clean_question,
                "answer": summary,
                "matches": [
                    item for item in [
                        comparison.get("run_a"),
                        comparison.get("run_b"),
                    ]
                    if item and item.get("id")
                ],
                "comparison": comparison,
                "confidence": 0.88 if comparison.get("status") == "computed" else 0.25,
                "execution_type": "deterministic_kg_query",
            }

        if "ultima analisi" in lowered:
            matches = self.get_latest_analysis_runs(limit=1)
            return self._answer(clean_question, "ultima analisi", matches, 0.9 if matches else 0.25)

        if "analisi precedenti" in lowered:
            matches = self.get_latest_analysis_runs(limit=5)
            return self._answer(clean_question, "analisi precedenti", matches, 0.88 if matches else 0.25)

        if "metriche analizzate" in lowered:
            matches = self.find_nodes(
                node_type="dataframe_column",
                property_filters={"is_primary_metric": True},
                limit=30,
            )
            return self._answer(clean_question, "metriche analizzate", matches, 0.85 if matches else 0.25)

        if "colonne temporali" in lowered:
            matches = self.find_nodes(
                node_type="dataframe_column",
                property_filters={"is_time_axis": True},
                limit=30,
            )
            return self._answer(clean_question, "colonne temporali", matches, 0.85 if matches else 0.25)

        if "dataset analizzati" in lowered:
            matches = self.find_nodes(node_type="dataset", limit=30)
            return self._answer(clean_question, "dataset analizzati", matches, 0.85 if matches else 0.25)

        if "anomalie rilevate" in lowered:
            matches = self.find_nodes(node_type="anomaly", limit=30)
            return self._answer(clean_question, "anomalie rilevate", matches, 0.85 if matches else 0.25)

        if "root cause individuate" in lowered:
            matches = self.find_nodes(node_type="root_cause", limit=30)
            return self._answer(clean_question, "root cause individuate", matches, 0.85 if matches else 0.25)

        if "analisi" in lowered and any(term in lowered for term in ("anomalia", "anomalie", "anomaly")):
            matches = self._find_analysis_runs_with_matching_anomalies(clean_question)
            return self._answer(clean_question, "analisi con anomalie coerenti con la domanda", matches, 0.86)

        node_type = self._detect_node_type(lowered)
        if node_type:
            matches = self._search_nodes(clean_question, {node_type}, 30)
            if not matches:
                matches = self.find_nodes(node_type=node_type, limit=30)
            description = self._description_for_node_type(node_type)
            confidence = 0.82 if matches else 0.25
            return self._answer(clean_question, description, matches, confidence)

        if self._looks_like_code_question(lowered):
            matches = self.search_code(clean_question)
            return self._answer(clean_question, "elementi di codice", matches, 0.7 if matches else 0.2)

        matches = self.search_analysis(clean_question)
        return self._answer(clean_question, "elementi analitici", matches, 0.65 if matches else 0.2)

    def _find_analysis_runs_with_matching_anomalies(self, question: str) -> list[dict[str, Any]]:
        anomaly_matches = [
            item for item in self._search_nodes(question, {"anomaly"}, 50)
            if item.get("type") == "anomaly"
        ]
        analysis_by_id: dict[str, dict[str, Any]] = {}
        for anomaly in anomaly_matches:
            for neighbor in self.get_neighbors(
                anomaly["id"],
                direction="in",
                relationship="DETECTED_ANOMALY",
                limit=50,
            ):
                node = neighbor.get("node") or {}
                if node.get("type") == "analysis_run":
                    enriched = dict(node)
                    enriched["matched_anomaly"] = anomaly
                    analysis_by_id[enriched["id"]] = enriched
        return list(analysis_by_id.values())[:30]

    def _search_nodes(
        self,
        text: str,
        node_types: set[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        tokens = self._expand_tokens(text)
        scored = []
        for node in self.snapshot.nodes:
            if node.type not in node_types:
                continue
            haystack = self._node_haystack(node)
            score = sum(1 for token in tokens if token in haystack)
            if score <= 0 and text and text.lower() in haystack:
                score = 1
            if score > 0:
                scored.append((score, node.label.lower(), node.to_dict()))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [item[2] for item in scored[: max(0, limit)]]

    def _expand_tokens(self, text: str) -> list[str]:
        raw_tokens = [
            token.strip(" ?!.,;:()[]{}\"'").lower()
            for token in (text or "").replace("-", "_").split()
        ]
        tokens: list[str] = []
        for token in raw_tokens:
            if not token or token in self.STOPWORDS:
                continue
            tokens.append(token)
            tokens.extend(self.TERM_SYNONYMS.get(token, []))
        if "root" in raw_tokens and "cause" in raw_tokens:
            tokens.append("root_cause")
        return sorted(set(tokens))

    def _detect_node_type(self, lowered_question: str) -> str | None:
        for phrase, node_type in self.NODE_TYPE_BY_INTENT.items():
            if phrase in lowered_question:
                return node_type
        return None

    def _looks_like_code_question(self, lowered_question: str) -> bool:
        return any(term in lowered_question for term in ("codice", "funzione", "classe", "file", "import"))

    def _looks_like_analysis_comparison_question(self, lowered_question: str) -> bool:
        phrases = [
            "confronta ultime analisi",
            "differenze tra ultime analisi",
            "cosa è cambiato",
            "cosa e cambiato",
            "trend rispetto alla precedente",
            "rispetto all'ultima analisi",
            "rispetto all’ultima analisi",
        ]
        return any(phrase in lowered_question for phrase in phrases)

    def _answer(
        self,
        question: str,
        description: str,
        matches: list[dict[str, Any]],
        confidence: float,
    ) -> dict[str, Any]:
        if matches:
            labels = [str(match.get("label") or match.get("id")) for match in matches[:5]]
            answer = (
                f"Ho trovato {len(matches)} risultato/i per {description}. "
                f"Primi match: {', '.join(labels)}."
            )
            confidence_value = confidence
        else:
            answer = f"Non ho trovato risultati nel Knowledge Graph per {description}."
            confidence_value = min(confidence, 0.25)
        return {
            "question": question,
            "answer": answer,
            "matches": matches,
            "confidence": round(max(0.0, min(1.0, confidence_value)), 2),
            "execution_type": "deterministic_kg_query",
        }

    def _description_for_node_type(self, node_type: str) -> str:
        descriptions = {
            "python_function": "funzioni Python",
            "python_class": "classi Python",
            "python_file": "file Python",
            "python_import": "import Python",
            "analysis_run": "analisi",
            "anomaly": "anomalie",
            "root_cause": "root cause",
            "dataframe_column": "colonne dataframe",
            "report": "report",
        }
        return descriptions.get(node_type, node_type)

    def _properties_match(self, properties: dict[str, Any], filters: dict[str, Any]) -> bool:
        for key, expected in filters.items():
            if key not in properties:
                return False
            actual = properties.get(key)
            if isinstance(actual, str) and isinstance(expected, str):
                if actual.lower() != expected.lower():
                    return False
            elif actual != expected:
                return False
        return True

    def _node_haystack(self, node: KnowledgeNode) -> str:
        return " ".join([
            node.id,
            node.type,
            node.label,
            json.dumps(node.properties, ensure_ascii=False, sort_keys=True, default=str),
        ]).lower()

    def _neighbor_payload(
        self,
        node: KnowledgeNode,
        edge: KnowledgeEdge,
        direction: str,
    ) -> dict[str, Any]:
        return {
            "node": node.to_dict(),
            "edge": edge.to_dict(),
            "direction": direction,
        }
