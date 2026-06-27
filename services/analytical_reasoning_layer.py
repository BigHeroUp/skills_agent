"""Layer locale per scegliere e motivare una strategia analitica."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from typing import Any


class AnalyticalReasoningLayer:
    """Costruisce piani analitici ordinati senza chiamate OpenAI."""

    SCHEMA_VERSION = 1

    PERFORMANCE_TERMS = {
        "tempo",
        "tempi",
        "durata",
        "latenza",
        "latency",
        "performance",
        "prestazioni",
        "sla",
        "risoluzione",
        "risposta",
        "degrado",
        "p90",
        "p95",
        "p99",
        "percentile",
        "percentili",
    }
    CATEGORICAL_TERMS = {
        "categoria",
        "categorie",
        "distribuzione",
        "segmenta",
        "segmentazione",
        "raggruppa",
        "gruppo",
        "stato",
        "cliente",
        "regione",
        "canale",
        "top",
    }
    AMBIGUOUS_TERMS = {
        "analizza",
        "analisi",
        "fammi vedere",
        "cosa vedi",
        "panoramica",
        "overview",
        "insight",
    }
    ANOMALY_TERMS = {
        "anomalia",
        "anomalie",
        "anomalo",
        "outlier",
        "spike",
        "picco",
        "degrado",
        "drift",
        "violazione",
        "violazioni",
    }
    ROOT_CAUSE_TERMS = {
        "root cause",
        "causa",
        "cause",
        "perche",
        "perché",
        "motivo",
        "motivazione",
        "spiega",
        "spiegazione",
        "explain",
        "why",
        "ragione",
        "ragioni",
    }

    def build_strategy(
        self,
        user_request: str,
        dataframe_metadata: dict,
        detected_patterns: list[dict] | None = None,
        learning_state: dict | None = None,
        domain_pack_context: dict | None = None,
        analytical_intent_plan: dict | None = None,
    ) -> dict:
        """Produce una strategia ordinata e JSON-serializzabile."""
        request = str(user_request or "").strip()
        metadata = dataframe_metadata if isinstance(dataframe_metadata, dict) else {}
        patterns = [
            copy.deepcopy(item)
            for item in detected_patterns or []
            if isinstance(item, dict)
        ]
        context = {
            "user_request": request,
            "metadata": self._metadata_profile(metadata),
            "detected_patterns": patterns,
            "learning_state": learning_state if isinstance(learning_state, dict) else {},
            "intent": self._classify_intent(request),
            "domain_pack_context": (
                domain_pack_context if isinstance(domain_pack_context, dict) else {}
            ),
            "analytical_intent_plan": (
                analytical_intent_plan if isinstance(analytical_intent_plan, dict) else {}
            ),
        }

        candidates, excluded = self._build_candidates(context)
        ranked = self.rank_candidate_analyses(candidates, context)
        questions = self.identify_missing_context(
            request,
            metadata,
            context["domain_pack_context"],
        )
        recommended = [
            self._strategy_step(index, candidate)
            for index, candidate in enumerate(ranked, start=1)
        ]
        trace = {
            "schema_version": self.SCHEMA_VERSION,
            "intent": context["intent"],
            "metadata_profile": context["metadata"],
            "detected_pattern_ids": [
                pattern.get("pattern_id") for pattern in patterns if pattern.get("pattern_id")
            ],
            "domain_pack_id": (
                context["domain_pack_context"].get("pack_id")
                or (context["domain_pack_context"].get("suggestion") or {}).get("pack_id")
            ),
            "candidate_count": len(candidates),
            "excluded_count": len(excluded),
            "ranking_factors": [
                "intent_match",
                "pattern_confidence",
                "learning_confidence",
                "data_compatibility",
                "priority",
            ],
            "ranked_candidate_scores": [
                {
                    "analysis_type": item["analysis_type"],
                    "priority": item["priority"],
                    "confidence_score": item["confidence_score"],
                    "score_components": item.get("score_components", {}),
                }
                for item in ranked
            ],
        }
        strategy = {
            "schema_version": self.SCHEMA_VERSION,
            "strategy_id": self._strategy_id(request, metadata, patterns),
            "user_request": request,
            "recommended_sequence": recommended,
            "excluded_analyses": self._json_safe(excluded),
            "clarification_questions": questions,
            "reasoning_trace": trace,
            "confidence_score": self._strategy_confidence(recommended, questions),
            "data_requirements": self._data_requirements(recommended),
            "stopping_conditions": self._stopping_conditions(questions),
            "domain_strategy_rules": self._domain_strategy_rules(
                context["domain_pack_context"]
            ),
            "analytical_intent_plan": context["analytical_intent_plan"],
        }
        return self._json_safe(strategy)

    def rank_candidate_analyses(
        self,
        candidates: list[dict],
        context: dict,
    ) -> list[dict]:
        """Ordina analisi candidate usando contesto, pattern e learning state."""
        ranked = []
        pattern_confidence = self._pattern_confidence_map(
            context.get("detected_patterns", []),
            context.get("learning_state", {}),
        )
        for candidate in candidates or []:
            if not isinstance(candidate, dict):
                continue
            pattern_id = candidate.get("pattern_id")
            learned = pattern_confidence.get(pattern_id, candidate.get("confidence_score", 0.45))
            intent_bonus = self._intent_bonus(candidate, context.get("intent", {}))
            data_bonus = 0.12 if candidate.get("required_columns") else 0.04
            priority_penalty = min(0.25, max(0, int(candidate.get("base_priority", 50)) - 10) / 200)
            score = max(
                0.0,
                min(
                    1.0,
                    float(candidate.get("confidence_score", 0.45)) * 0.35
                    + float(learned) * 0.35
                    + intent_bonus
                    + data_bonus
                    - priority_penalty,
                ),
            )
            item = copy.deepcopy(candidate)
            item["confidence_score"] = round(score, 4)
            item["priority"] = 0
            item["score_components"] = {
                "base_confidence": candidate.get("confidence_score", 0.45),
                "learning_confidence": round(float(learned), 4),
                "intent_bonus": round(intent_bonus, 4),
                "data_bonus": round(data_bonus, 4),
                "priority_penalty": round(priority_penalty, 4),
            }
            ranked.append(item)

        ranked.sort(
            key=lambda item: (
                -item["confidence_score"],
                int(item.get("base_priority", 50)),
                item.get("analysis_type", ""),
            )
        )
        for index, item in enumerate(ranked, start=1):
            item["priority"] = index
        return self._json_safe(ranked)

    def identify_missing_context(
        self,
        user_request: str,
        dataframe_metadata: dict,
        domain_pack_context: dict | None = None,
    ) -> list[dict]:
        """Identifica chiarimenti necessari prima di conclusioni forti."""
        request = self._normalize(user_request)
        metadata = self._metadata_profile(dataframe_metadata)
        questions: list[dict[str, Any]] = []
        intent = self._classify_intent(user_request)

        if not request:
            questions.append(self._question(
                "objective",
                "Qual e l'obiettivo business dell'analisi?",
                "Definire il risultato atteso prima di scegliere metriche e tagli.",
            ))
        if not metadata["columns"]:
            questions.append(self._question(
                "dataframe_schema",
                "Quali colonne sono disponibili nel dataset?",
                "La strategia non puo proporre analisi verificabili senza schema.",
            ))
        if intent["ambiguous"] and not intent["performance"] and not intent["categorical"]:
            questions.append(self._question(
                "analysis_goal",
                "Vuoi dare priorita a KPI, qualita dati, trend, segmentazioni o anomalie?",
                "La richiesta e ampia e non indica una priorita analitica esplicita.",
            ))
        if intent["performance"] and len(metadata["numeric_columns"]) > 1:
            questions.append(self._question(
                "performance_metric",
                "Quale metrica numerica rappresenta tempi, durata o SLA?",
                "Sono presenti piu colonne numeriche e non e sicuro scegliere una metrica al posto dell'utente.",
            ))
        if intent["performance"] and "sla" in request and not re.search(r"\b\d+(?:[,.]\d+)?\b", request):
            questions.append(self._question(
                "sla_threshold",
                "Quale soglia SLA devo usare per il confronto?",
                "La richiesta cita SLA ma non specifica un valore soglia.",
            ))
        if intent["categorical"] and len(metadata["categorical_columns"]) > 1:
            questions.append(self._question(
                "segmentation_dimension",
                "Quale dimensione categoriale devo usare come segmento principale?",
                "Sono disponibili piu colonne categoriali compatibili.",
            ))

        questions.extend(self._domain_questions(domain_pack_context))
        return self._deduplicate_questions(questions)

    def explain_strategy(self, strategy: dict) -> str:
        """Restituisce una spiegazione testuale sintetica della strategia."""
        data = strategy if isinstance(strategy, dict) else {}
        sequence = data.get("recommended_sequence") or []
        excluded = data.get("excluded_analyses") or []
        questions = data.get("clarification_questions") or []
        lines = [
            f"Strategia {data.get('strategy_id', 'n/a')} con confidence {data.get('confidence_score', 0)}."
        ]
        if sequence:
            lines.append("Analisi consigliate:")
            for step in sequence:
                lines.append(
                    f"- {step.get('priority')}. {step.get('analysis_type')}: {step.get('rationale')}"
                )
        else:
            lines.append("Nessuna analisi consigliata con i dati disponibili.")
        if excluded:
            lines.append("Analisi escluse:")
            for item in excluded:
                lines.append(f"- {item.get('analysis_type')}: {item.get('reason')}")
        if questions:
            lines.append("Chiarimenti richiesti:")
            for item in questions:
                lines.append(f"- {item.get('question')}")
        return "\n".join(lines)

    def export_reasoning_trace(self, strategy: dict) -> dict:
        """Esporta solo audit trail e decisioni in forma JSON-safe."""
        data = strategy if isinstance(strategy, dict) else {}
        return self._json_safe({
            "strategy_id": data.get("strategy_id"),
            "reasoning_trace": data.get("reasoning_trace") or {},
            "recommended_step_ids": [
                step.get("step_id") for step in data.get("recommended_sequence") or []
            ],
            "excluded_analyses": data.get("excluded_analyses") or [],
            "clarification_questions": data.get("clarification_questions") or [],
            "confidence_score": data.get("confidence_score", 0.0),
        })

    def _build_candidates(self, context: dict) -> tuple[list[dict], list[dict]]:
        metadata = context["metadata"]
        intent = context["intent"]
        intent_plan = context.get("analytical_intent_plan") or {}
        patterns = context.get("detected_patterns", [])
        pattern_ids = {pattern.get("pattern_id") for pattern in patterns}
        candidates: list[dict[str, Any]] = []
        excluded: list[dict[str, Any]] = []
        forbidden = set(intent_plan.get("forbidden_columns") or [])
        numeric = [column for column in metadata["numeric_columns"] if column not in forbidden]
        categorical = [column for column in metadata["categorical_columns"] if column not in forbidden]
        datetime_cols = [column for column in metadata["datetime_columns"] if column not in forbidden]
        primary_metric = intent_plan.get("primary_metric")
        time_axis = intent_plan.get("time_axis")
        segmentations = [
            column for column in intent_plan.get("segmentations", [])
            if column in metadata["columns"] and column not in forbidden
        ]

        def add(
            analysis_type: str,
            rationale: str,
            required_columns: list[str],
            expected_output: str,
            pattern_id: str | None,
            base_priority: int,
            confidence: float,
            depends_on: list[str] | None = None,
        ) -> None:
            candidates.append({
                "analysis_type": analysis_type,
                "rationale": rationale,
                "required_columns": required_columns,
                "expected_output": expected_output,
                "pattern_id": pattern_id,
                "base_priority": base_priority,
                "confidence_score": confidence,
                "depends_on": depends_on or [],
            })

        if numeric:
            metric = primary_metric if primary_metric in numeric else self._preferred_numeric_column(numeric, metadata["columns"])
            add(
                "percentile_analysis",
                "La richiesta riguarda tempi/prestazioni/SLA: percentili e mediana descrivono meglio la coda della sola media.",
                [metric],
                "mediana, P75, P90, P95, P99 e confronto del comportamento di coda",
                "time_performance_analysis" if intent["performance"] else "operational_kpi_analysis",
                10 if intent["performance"] else 35,
                0.62,
            )
            add(
                "numeric_distribution",
                "Le colonne numeriche disponibili consentono statistiche descrittive verificabili.",
                [metric],
                "conteggio, media, mediana, minimo, massimo e dispersione",
                "operational_kpi_analysis",
                25,
                0.55,
            )
            add(
                "advanced_dispersion_analysis",
                "Range, IQR, varianza, deviazione standard, coefficiente di variazione e MAD rendono la variabilita piu leggibile.",
                [metric],
                "range, IQR, varianza, deviazione standard, coefficiente di variazione e MAD",
                "time_performance_analysis" if intent["performance"] else "operational_kpi_analysis",
                35 if intent["performance"] else 42,
                0.52,
                depends_on=["numeric_distribution"],
            )
            add(
                "outlier_analysis",
                "La distribuzione numerica puo contenere valori estremi da isolare prima delle conclusioni operative.",
                [metric],
                "valori estremi potenziali e indicatori di severita",
                "time_performance_analysis" if intent["performance"] else "operational_kpi_analysis",
                20 if intent["performance"] else 45,
                0.58,
            )
            if intent["anomaly"] or "time_performance_analysis" in pattern_ids:
                add(
                    "anomaly_detection",
                    "La richiesta o i pattern indicano anomalie, outlier, spike, degrado o drift: serve un controllo dedicato con severity e confidence.",
                    [metric],
                    "anomalie numeriche, spike, degrado, drift e possibili violazioni soglia",
                    "time_performance_analysis" if intent["performance"] else "operational_kpi_analysis",
                    38 if intent["performance"] else 48,
                    0.5,
                    depends_on=["outlier_analysis", "threshold_comparison"],
                )
            if intent["root_cause"] or intent["anomaly"]:
                add(
                    "root_cause_analysis",
                    "La richiesta chiede cause, motivi o spiegazioni di anomalie: serve raggruppare evidenze prima di proporre ipotesi.",
                    [metric],
                    "ipotesi di cause radice con evidenze, alternative e azioni raccomandate",
                    "time_performance_analysis" if intent["performance"] else "operational_kpi_analysis",
                    18 if intent["root_cause"] else 52,
                    0.54,
                    depends_on=["anomaly_detection", "advanced_dispersion_analysis"],
                )
            if intent["performance"]:
                add(
                    "threshold_comparison",
                    "La richiesta cita tempi/prestazioni/SLA: il confronto con soglia e utile se la soglia viene fornita.",
                    [metric],
                    "tasso di superamento soglia e record critici",
                    "time_performance_analysis",
                    30,
                    0.56,
                    depends_on=["percentile_analysis"],
                )
            if len(numeric) >= 2:
                add(
                    "correlation_matrix",
                    "Piu colonne numeriche consentono una matrice di correlazione per individuare relazioni lineari e monotone.",
                    [column for column in numeric if column not in forbidden],
                    "matrici Pearson, Spearman e Kendall con coppie piu correlate",
                    "operational_kpi_analysis",
                    65,
                    0.46,
                )
        else:
            excluded.extend([
                self._excluded("percentile_analysis", "Mancano colonne numeriche nei metadata."),
                self._excluded("numeric_distribution", "Mancano colonne numeriche nei metadata."),
                self._excluded("advanced_dispersion_analysis", "Mancano colonne numeriche nei metadata."),
                self._excluded("outlier_analysis", "Mancano colonne numeriche nei metadata."),
                self._excluded("anomaly_detection", "Mancano colonne numeriche per rilevare outlier, degrado o soglie."),
                self._excluded("threshold_comparison", "Mancano colonne numeriche per confrontare soglie o SLA."),
                self._excluded("correlation_matrix", "Mancano almeno due colonne numeriche nei metadata."),
            ])
        if len(numeric) == 1:
            excluded.append(self._excluded(
                "correlation_matrix",
                "Serve almeno una seconda colonna numerica per calcolare correlazioni.",
            ))

        if datetime_cols:
            selected_time = time_axis if time_axis in datetime_cols else datetime_cols[0]
            required = [selected_time]
            if numeric:
                metric = primary_metric if primary_metric in numeric else self._preferred_numeric_column(numeric, metadata["columns"])
                required.append(metric)
            add(
                "time_trend",
                "Esiste una colonna data: il trend puo mostrare variazioni nel tempo senza inventare assi temporali.",
                required,
                "serie temporale per periodo e variazione tra primo e ultimo punto",
                "time_performance_analysis" if intent["performance"] else "operational_kpi_analysis",
                15 if intent["performance"] else 40,
                0.57,
                depends_on=["numeric_distribution"] if numeric else [],
            )
        else:
            excluded.append(self._excluded(
                "time_trend",
                "Mancano colonne data/ora nei metadata; non viene suggerito alcun trend temporale.",
            ))

        if categorical:
            segment = segmentations[0] if segmentations else self._preferred_categorical_column(categorical, context["user_request"])
            add(
                "categorical_segmentation",
                "La richiesta parla di distribuzione/categorie o i dati contengono dimensioni categoriali segmentabili.",
                [segment],
                "conteggi e quota percentuale per segmento",
                "categorical_segmentation",
                10 if intent["categorical"] else 50,
                0.6,
            )
            add(
                "top_values",
                "I top valori evidenziano concentrazione e categorie dominanti.",
                [segment],
                "classifica dei valori piu frequenti",
                "categorical_segmentation",
                20 if intent["categorical"] else 55,
                0.56,
                depends_on=["categorical_segmentation"],
            )
        else:
            excluded.extend([
                self._excluded("categorical_segmentation", "Mancano colonne categoriali nei metadata."),
                self._excluded("top_values", "Mancano colonne categoriali nei metadata."),
            ])

        for column in sorted(forbidden):
            excluded.extend([
                self._excluded("top_values", f"{column} esclusa: identificativo o codice tecnico."),
                self._excluded("correlation_matrix", f"{column} esclusa: identificativo o codice tecnico."),
                self._excluded("categorical_segmentation", f"{column} esclusa: identificativo o codice tecnico."),
            ])

        if pattern_ids and "data_quality_audit" in pattern_ids:
            add(
                "data_quality_audit",
                "Un pattern di qualita dati e stato rilevato: completezza e duplicati possono bloccare KPI e segmentazioni.",
                metadata["columns"][:5],
                "valori mancanti, duplicati e note di qualita",
                "data_quality_audit",
                12,
                0.58,
            )
        elif context["intent"]["ambiguous"]:
            add(
                "data_quality_audit",
                "Per richieste ampie, controllare qualita dati riduce il rischio di conclusioni premature.",
                metadata["columns"][:5],
                "valori mancanti, duplicati e limiti del profilo dati",
                "data_quality_audit",
                60,
                0.48,
            )

        domain_rules = self._domain_strategy_rules(context.get("domain_pack_context"))
        existing_types = {candidate["analysis_type"] for candidate in candidates}
        for rule in domain_rules:
            for analysis_type in rule.get("analysis_types", []) or []:
                if analysis_type in existing_types:
                    continue
                required_columns = []
                if analysis_type in {"categorical_segmentation", "segment_anomaly_analysis"} and categorical:
                    required_columns = [self._preferred_categorical_column(categorical, context["user_request"])]
                elif analysis_type in {
                    "percentile_analysis",
                    "advanced_dispersion_analysis",
                    "threshold_comparison",
                    "anomaly_detection",
                    "degradation_detection",
                } and numeric:
                    required_columns = [self._preferred_numeric_column(numeric, metadata["columns"])]
                elif analysis_type == "time_trend" and datetime_cols:
                    required_columns = [datetime_cols[0]]
                if not required_columns and analysis_type not in {"anomaly_detection"}:
                    continue
                add(
                    analysis_type,
                    rule.get("description", "Regola derivata dal domain pack."),
                    required_columns,
                    "output guidato dal domain pack",
                    "domain_pack",
                    int(rule.get("priority", 50)),
                    0.5,
                )
                existing_types.add(analysis_type)

        return candidates, self._deduplicate_exclusions(excluded)

    def _strategy_step(self, index: int, candidate: dict) -> dict:
        return {
            "step_id": f"strategy-step-{index:02d}",
            "analysis_type": candidate.get("analysis_type"),
            "priority": candidate.get("priority", index),
            "rationale": candidate.get("rationale", ""),
            "required_columns": candidate.get("required_columns", []),
            "expected_output": candidate.get("expected_output", ""),
            "depends_on": candidate.get("depends_on", []),
            "confidence_score": candidate.get("confidence_score", 0.0),
        }

    def _metadata_profile(self, metadata: dict) -> dict:
        data = metadata if isinstance(metadata, dict) else {}
        columns = self._string_list(data.get("columns", []))
        numeric = self._existing_columns(data.get("numeric_columns", []), columns)
        categorical = self._existing_columns(data.get("categorical_columns", []), columns)
        datetime_cols = self._existing_columns(data.get("datetime_columns", []), columns)
        return {
            "columns": columns,
            "numeric_columns": numeric,
            "categorical_columns": categorical,
            "datetime_columns": datetime_cols,
            "row_count": data.get("row_count", data.get("rows")),
            "column_count": data.get("column_count", len(columns) if columns else data.get("columns_count")),
        }

    def _classify_intent(self, user_request: str) -> dict:
        request = self._normalize(user_request)
        performance = self._contains_any(request, self.PERFORMANCE_TERMS)
        categorical = self._contains_any(request, self.CATEGORICAL_TERMS)
        ambiguous = self._contains_any(request, self.AMBIGUOUS_TERMS) and not performance and not categorical
        return {
            "performance": performance,
            "categorical": categorical,
            "ambiguous": ambiguous,
            "anomaly": self._contains_any(request, self.ANOMALY_TERMS),
            "root_cause": self._contains_any(request, self.ROOT_CAUSE_TERMS),
            "quality": self._contains_any(request, {"qualita", "quality", "missing", "null", "duplicati"}),
        }

    def _pattern_confidence_map(self, patterns: list[dict], learning_state: dict) -> dict[str, float]:
        output: dict[str, float] = {}
        for pattern in patterns or []:
            if isinstance(pattern, dict) and pattern.get("pattern_id"):
                output[str(pattern["pattern_id"])] = self._safe_float(
                    pattern.get("confidence_score"),
                    0.45,
                )
        if isinstance(learning_state, dict):
            for pattern in learning_state.get("patterns", []) or []:
                if isinstance(pattern, dict) and pattern.get("pattern_id"):
                    output[str(pattern["pattern_id"])] = self._safe_float(
                        pattern.get("confidence_score"),
                        output.get(str(pattern["pattern_id"]), 0.45),
                    )
        return output

    def _intent_bonus(self, candidate: dict, intent: dict) -> float:
        analysis_type = candidate.get("analysis_type")
        pattern_id = candidate.get("pattern_id")
        if intent.get("performance") and (
            pattern_id == "time_performance_analysis"
            or analysis_type in {
                "percentile_analysis",
                "advanced_dispersion_analysis",
                "time_trend",
                "outlier_analysis",
                "anomaly_detection",
                "threshold_comparison",
            }
        ):
            return 0.22
        if intent.get("categorical") and (
            pattern_id == "categorical_segmentation"
            or analysis_type in {"categorical_segmentation", "top_values"}
        ):
            return 0.22
        if intent.get("root_cause") and analysis_type == "root_cause_analysis":
            return 0.24
        if intent.get("quality") and analysis_type == "data_quality_audit":
            return 0.18
        return 0.04

    def _preferred_numeric_column(self, numeric_columns: list[str], columns: list[str]) -> str:
        terms = ("duration", "durata", "tempo", "time", "latency", "latenza", "sla", "hours", "minuti")
        for column in numeric_columns:
            normalized = self._normalize(column)
            if any(term in normalized for term in terms):
                return column
        for column in numeric_columns:
            if column in columns:
                return column
        return numeric_columns[0]

    def _preferred_categorical_column(self, categorical_columns: list[str], user_request: str) -> str:
        request = self._normalize(user_request)
        for column in categorical_columns:
            if self._normalize(column) in request:
                return column
        return categorical_columns[0]

    def _data_requirements(self, recommended: list[dict]) -> dict:
        required = []
        for step in recommended:
            for column in step.get("required_columns") or []:
                if column not in required:
                    required.append(column)
        return {
            "required_columns": required,
            "requires_numeric_columns": any(
                step.get("analysis_type") in {
                    "percentile_analysis",
                    "numeric_distribution",
                    "advanced_dispersion_analysis",
                    "outlier_analysis",
                    "anomaly_detection",
                    "threshold_comparison",
                    "correlation_matrix",
                }
                for step in recommended
            ),
            "requires_datetime_columns": any(
                step.get("analysis_type") == "time_trend" for step in recommended
            ),
            "requires_categorical_columns": any(
                step.get("analysis_type") in {"categorical_segmentation", "top_values"}
                for step in recommended
            ),
        }

    def _stopping_conditions(self, questions: list[dict]) -> list[str]:
        conditions = [
            "Interrompere o degradare l'analisi se le colonne richieste non sono presenti nel dataframe.",
            "Non produrre trend temporali senza colonne data/ora valide.",
            "Non produrre statistiche numeriche senza colonne numeriche valide.",
        ]
        if questions:
            conditions.append(
                "Richiedere chiarimenti prima di trasformare la strategia in conclusioni operative vincolanti."
            )
        return conditions

    def _domain_strategy_rules(self, domain_pack_context: dict | None) -> list[dict]:
        context = domain_pack_context if isinstance(domain_pack_context, dict) else {}
        knowledge = context.get("knowledge") if isinstance(context.get("knowledge"), dict) else {}
        rules = knowledge.get("strategy_rules") if isinstance(knowledge, dict) else []
        return [
            copy.deepcopy(rule)
            for rule in rules or []
            if isinstance(rule, dict)
        ]

    def _domain_questions(self, domain_pack_context: dict | None) -> list[dict]:
        context = domain_pack_context if isinstance(domain_pack_context, dict) else {}
        knowledge = context.get("knowledge") if isinstance(context.get("knowledge"), dict) else {}
        questions = []
        for item in knowledge.get("questions") or []:
            if not isinstance(item, dict) or not item.get("question"):
                continue
            questions.append(self._question(
                str(item.get("question_id") or "domain_context"),
                str(item["question"]),
                str(item.get("reason") or "Chiarimento richiesto dal domain pack."),
            ))
        return questions

    def _strategy_confidence(self, recommended: list[dict], questions: list[dict]) -> float:
        if not recommended:
            return 0.0
        average = sum(float(step.get("confidence_score", 0.0)) for step in recommended) / len(recommended)
        penalty = min(0.35, len(questions) * 0.07)
        return round(max(0.0, average - penalty), 4)

    def _strategy_id(self, request: str, metadata: dict, patterns: list[dict]) -> str:
        source = json.dumps(
            {
                "request": request,
                "columns": metadata.get("columns", []),
                "patterns": [pattern.get("pattern_id") for pattern in patterns],
            },
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
        return "strategy-" + hashlib.sha1(source.encode("utf-8")).hexdigest()[:12]

    def _question(self, question_id: str, question: str, rationale: str) -> dict:
        return {
            "question_id": question_id,
            "question": question,
            "rationale": rationale,
            "required": True,
        }

    def _excluded(self, analysis_type: str, reason: str) -> dict:
        return {"analysis_type": analysis_type, "reason": reason}

    def _deduplicate_questions(self, questions: list[dict]) -> list[dict]:
        output = []
        seen = set()
        for item in questions:
            question_id = item.get("question_id")
            if question_id in seen:
                continue
            seen.add(question_id)
            output.append(item)
        return output

    def _deduplicate_exclusions(self, exclusions: list[dict]) -> list[dict]:
        output = []
        seen = set()
        for item in exclusions:
            key = item.get("analysis_type")
            if key in seen:
                continue
            seen.add(key)
            output.append(item)
        return output

    def _existing_columns(self, values: Any, columns: list[str]) -> list[str]:
        output = self._string_list(values)
        if not columns:
            return output
        allowed = set(columns)
        return [value for value in output if value in allowed]

    def _string_list(self, values: Any) -> list[str]:
        if not isinstance(values, list):
            return []
        return [str(value) for value in values if str(value)]

    def _contains_any(self, value: str, terms: set[str]) -> bool:
        return any(re.search(rf"\b{re.escape(term)}\w*\b", value) for term in terms)

    def _normalize(self, value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "").lower()).strip()

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            result = float(value)
        except (TypeError, ValueError):
            return default
        return result if math.isfinite(result) else default

    def _json_safe(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._json_safe(item) for item in value]
        if isinstance(value, float) and not math.isfinite(value):
            return None
        if hasattr(value, "item"):
            return self._json_safe(value.item())
        json.dumps(value, ensure_ascii=False, default=str)
        return value
