"""
Data Processor Agent
Elabora e trasforma i dati validati
"""

from agents.base_agent import BaseAgent
from services.advanced_statistical_engine import AdvancedStatisticalEngine
from services.anomaly_detection_engine import AnomalyDetectionEngine
from services.analysis_engine import AnalysisEngine
from services.analytical_reasoning_layer import AnalyticalReasoningLayer
from services.analytical_intent_planner import AnalyticalIntentPlanner
from services.autonomous_analyst import AutonomousAnalyst
from services.domain_pack_loader import DomainPackLoader
from services.learning_engine import LearningEngine
from services.pattern_knowledge_engine import PatternKnowledgeEngine
from services.root_cause_analysis_engine import RootCauseAnalysisEngine
from services.semantic_column_classifier import SemanticColumnClassifier
from services.semantic_feature_engineering import SemanticFeatureEngineeringEngine
from utils.context import AgentContext
from utils.analysis_history_manager import AnalysisHistoryManager
from utils.data_analysis import summarize_dataframe


class DataProcessorAgent(BaseAgent):
    """Agent che elabora i dati"""
    
    def __init__(self):
        super().__init__(name="DataProcessor", skill_name="data_processing")
    
    def process(self, context: AgentContext) -> AgentContext:
        """Elabora i dati validati"""
        self.log("Elaborazione dati in corso...")
        
        try:
            if not context.is_valid:
                context.add_error("Dati non validi, impossibile elaborare", agent=self.name)
                return context
            
            df = context.raw_data.get("dataframe")
            initial_summary = summarize_dataframe(df)
            analysis_engine = AnalysisEngine(history_manager=AnalysisHistoryManager())
            autonomous_analyst = AutonomousAnalyst()
            domain_pack_loader = DomainPackLoader()
            semantic_classifier = SemanticColumnClassifier()
            context.semantic_columns = semantic_classifier.classify_dataframe(df)
            context.domain_pack_context = self._build_domain_pack_context(
                domain_pack_loader,
                context.user_input,
                initial_summary,
            )
            feature_engine = SemanticFeatureEngineeringEngine()
            context.semantic_feature_plan = feature_engine.build_feature_plan(
                context.user_input,
                df,
                context.semantic_columns,
                context.domain_pack_context,
            )
            df_enriched, context.semantic_feature_results = feature_engine.apply_feature_plan(
                df,
                context.semantic_feature_plan,
            )
            for feature_result in context.semantic_feature_results.get("features", []):
                self.log(
                    "Feature engineering: "
                    f"{feature_result.get('feature_name')} "
                    f"status={feature_result.get('status')} "
                    f"sources={feature_result.get('source_columns')} "
                    f"valid={feature_result.get('valid_count')} "
                    f"missing={feature_result.get('missing_count')} "
                    f"negative={feature_result.get('negative_duration_count')}"
                )
            context.engineered_features = context.semantic_feature_results.get(
                "engineered_features",
                [],
            )
            context.dataframe_enriched_metadata = summarize_dataframe(df_enriched)
            context.raw_data["dataframe"] = df_enriched
            df = df_enriched
            context.semantic_columns = semantic_classifier.classify_dataframe(
                df,
                context.domain_pack_context,
            )
            intent_planner = AnalyticalIntentPlanner()
            context.analytical_intent_plan = intent_planner.build_plan(
                context.user_input,
                df,
                context.semantic_feature_results,
                context.semantic_columns,
                context.domain_pack_context,
            )
            context.primary_metric = context.analytical_intent_plan.get("primary_metric")
            context.time_axis = context.analytical_intent_plan.get("time_axis")
            context.segmentations = context.analytical_intent_plan.get("segmentations", [])
            context.forbidden_columns = context.analytical_intent_plan.get("forbidden_columns", [])
            deterministic_summary = context.dataframe_enriched_metadata
            context.autonomous_mode = autonomous_analyst.should_run_autonomous(context.user_input)

            if context.autonomous_mode:
                autonomous_payload = autonomous_analyst.run(context.user_input, df)
                context.autonomous_analysis_plan = autonomous_payload["autonomous_analysis_plan"]
                context.autonomous_analysis_results = autonomous_payload["autonomous_analysis_results"]
                context.autonomous_executive_summary = autonomous_payload["autonomous_executive_summary"]
                context.autonomous_recommendations = autonomous_payload["autonomous_recommendations"]
                first_completed = next(
                    (
                        item for item in context.autonomous_analysis_results
                        if item.get("status") == "completed"
                    ),
                    {},
                )
                first_result = first_completed.get("result", {})
                analysis_payload = {
                    "analysis_plan": first_result.get("plan", {}),
                    "deterministic_results": first_result,
                    "execution_summary": {
                        "status": "completed",
                        "source": "autonomous_analyst",
                        "step_count": len(context.autonomous_analysis_results),
                    },
                    "analysis_pattern_id": None,
                    "plan_source": "autonomous",
                    "confidence_score": 0.0,
                    "similarity_score": None,
                    "similarity_method": None,
                }
            else:
                requested_plan = intent_planner.build_analysis_plan(context.analytical_intent_plan)
                analysis_payload = analysis_engine.run(
                    user_request=context.user_input,
                    df=df,
                    source_type=context.metadata.get("source_type", "unknown"),
                    plan=requested_plan or None,
                )
            context.analysis_plan = analysis_payload["analysis_plan"]
            context.deterministic_results = analysis_payload["deterministic_results"]
            context.execution_summary = analysis_payload["execution_summary"]
            context.analysis_pattern_id = analysis_payload.get("analysis_pattern_id")
            context.plan_source = analysis_payload.get("plan_source", "new")
            context.confidence_score = analysis_payload.get("confidence_score", 0.0)
            context.similarity_score = analysis_payload.get("similarity_score")
            context.similarity_method = analysis_payload.get("similarity_method")
            knowledge_engine = PatternKnowledgeEngine()
            enriched_plan = knowledge_engine.enrich_analysis_plan(
                context.analysis_plan,
                context.user_input,
                deterministic_summary,
                context.domain_pack_context,
            )
            enrichment = enriched_plan.get("knowledge_enrichment", {})
            context.analysis_plan = enriched_plan
            context.detected_patterns = enrichment.get("patterns", [])
            context.knowledge_analysis_steps = enrichment.get(
                "suggested_analysis_steps",
                [],
            )
            learning_engine = LearningEngine()
            context.learning_events = []
            for pattern in context.detected_patterns:
                pattern_id = pattern.get("pattern_id")
                if not pattern_id:
                    continue
                learning_result = learning_engine.record_usage(
                    pattern_id,
                    {
                        "source": "data_processor",
                        "user_request": context.user_input,
                        "plan_source": context.plan_source,
                    },
                )
                context.learning_events.append(learning_result["event"])
            context.learning_state = learning_engine.export_learning_state()
            reasoning_layer = AnalyticalReasoningLayer()
            context.analytical_strategy = reasoning_layer.build_strategy(
                user_request=context.user_input,
                dataframe_metadata=deterministic_summary,
                detected_patterns=context.detected_patterns,
                learning_state=context.learning_state,
                domain_pack_context=context.domain_pack_context,
                analytical_intent_plan=context.analytical_intent_plan,
            )
            context.analytical_reasoning_trace = reasoning_layer.export_reasoning_trace(
                context.analytical_strategy
            )
            statistical_engine = AdvancedStatisticalEngine()
            if self._should_run_advanced_statistics(context, deterministic_summary):
                context.advanced_statistical_results = statistical_engine.analyze_dataframe(
                    df,
                    config={
                        "correlation_methods": ["pearson", "spearman", "kendall"],
                        "outlier_methods": ["iqr", "zscore", "modified_zscore"],
                        "forbidden_columns": context.forbidden_columns,
                        "primary_metric": context.primary_metric,
                    },
                )
            else:
                context.advanced_statistical_results = {
                    "status": "skipped",
                    "reason": "Strategia analitica e metadata non richiedono analisi statistiche avanzate.",
                }
            anomaly_engine = AnomalyDetectionEngine(statistical_engine)
            if self._should_run_anomaly_detection(context):
                anomaly_config = self._build_anomaly_config(
                    context,
                    deterministic_summary,
                )
                context.anomaly_detection_results = anomaly_engine.detect_anomalies(
                    df,
                    config=anomaly_config,
                )
            else:
                context.anomaly_detection_results = {
                    "status": "skipped",
                    "reason": "Strategia analitica e pattern non richiedono anomaly detection.",
                    "anomaly_count": 0,
                    "anomalies": [],
                }
            root_cause_engine = RootCauseAnalysisEngine()
            if self._should_run_root_cause_analysis(context):
                context.root_cause_results = root_cause_engine.analyze({
                    "user_request": context.user_input,
                    "deterministic_summary": deterministic_summary,
                    "analysis_plan": context.analysis_plan,
                    "deterministic_results": context.deterministic_results,
                    "detected_patterns": context.detected_patterns,
                    "knowledge_analysis_steps": context.knowledge_analysis_steps,
                    "learning_state": context.learning_state,
                    "analytical_strategy": context.analytical_strategy,
                    "advanced_statistical_results": context.advanced_statistical_results,
                    "anomaly_detection_results": context.anomaly_detection_results,
                    "domain_pack_context": context.domain_pack_context,
                    "analytical_intent_plan": context.analytical_intent_plan,
                })
            else:
                context.root_cause_results = {
                    "status": "skipped",
                    "reason": "Nessuna anomalia o richiesta di causa radice rilevata.",
                    "root_cause_count": 0,
                    "possible_causes": [],
                }

            if (
                context.analytical_intent_plan.get("temporal_concentration")
                and context.primary_metric
                and context.time_axis
            ):
                context.temporal_concentration_results = intent_planner.temporal_concentration(
                    df,
                    context.primary_metric,
                    context.time_axis,
                )
            else:
                context.temporal_concentration_results = {
                    "status": "skipped",
                    "reason": "not_requested_or_missing_axes",
                    "metric": context.primary_metric,
                    "time_axis": context.time_axis,
                }

            response = {
                "trasformazioni_applicate": [
                    "profilazione dataframe",
                    "feature engineering semantico",
                    "pianificazione analitica deterministica",
                    "calcolo KPI e controlli statistici locali",
                ],
                "statistiche_riepilogative": {
                    "row_count": deterministic_summary.get("row_count", 0),
                    "column_count": deterministic_summary.get("column_count", 0),
                    "plan_source": context.plan_source,
                    "patterns": [item.get("pattern_id") for item in context.detected_patterns],
                },
                "forma_dati": f"{deterministic_summary.get('row_count', 0)} righe, {deterministic_summary.get('column_count', 0)} colonne",
                "note_elaborazione": (
                    "Report di processing generato localmente. OpenAI non viene usato per calcoli, "
                    "trasformazioni o controlli deterministici."
                ),
                "mode": "local",
            }
            
            context.processed_data = {
                "processing_report": response,
                "deterministic_summary": deterministic_summary,
                "analysis_plan": context.analysis_plan,
                "deterministic_results": context.deterministic_results,
                "execution_summary": context.execution_summary,
                "analysis_pattern_id": context.analysis_pattern_id,
                "plan_source": context.plan_source,
                "confidence_score": context.confidence_score,
                "similarity_score": context.similarity_score,
                "similarity_method": context.similarity_method,
                "detected_patterns": context.detected_patterns,
                "knowledge_analysis_steps": context.knowledge_analysis_steps,
                "learning_state": context.learning_state,
                "learning_events": context.learning_events,
                "semantic_columns": context.semantic_columns,
                "semantic_feature_plan": context.semantic_feature_plan,
                "semantic_feature_results": context.semantic_feature_results,
                "engineered_features": context.engineered_features,
                "dataframe_enriched_metadata": context.dataframe_enriched_metadata,
                "analytical_intent_plan": context.analytical_intent_plan,
                "primary_metric": context.primary_metric,
                "time_axis": context.time_axis,
                "segmentations": context.segmentations,
                "forbidden_columns": context.forbidden_columns,
                "temporal_concentration_results": context.temporal_concentration_results,
                "analytical_strategy": context.analytical_strategy,
                "analytical_reasoning_trace": context.analytical_reasoning_trace,
                "advanced_statistical_results": context.advanced_statistical_results,
                "anomaly_detection_results": context.anomaly_detection_results,
                "root_cause_results": context.root_cause_results,
                "domain_pack_context": context.domain_pack_context,
                "autonomous_analysis_plan": context.autonomous_analysis_plan,
                "autonomous_analysis_results": context.autonomous_analysis_results,
                "autonomous_executive_summary": context.autonomous_executive_summary,
                "autonomous_recommendations": context.autonomous_recommendations,
                "autonomous_mode": context.autonomous_mode,
                "shape": f"{deterministic_summary.get('row_count', 0)} righe, {deterministic_summary.get('column_count', 0)} colonne",
                "status": "elaborato"
            }
            
            self.log("✅ Elaborazione completata")
            
        except Exception as e:
            context.add_error(str(e), agent=self.name)
            self.log(f"❌ Errore: {e}")
        
        return context

    def _build_domain_pack_context(
        self,
        loader: DomainPackLoader,
        user_request: str,
        dataframe_metadata: dict,
    ) -> dict:
        """Rileva un domain pack senza bloccare la pipeline in caso di errori."""
        try:
            suggestion = loader.suggest_pack(user_request, dataframe_metadata)
            if not suggestion:
                return {
                    "status": "not_detected",
                    "available_packs": loader.list_available_packs(),
                }
            knowledge = loader.export_pack_knowledge(suggestion["pack_id"])
            return {
                "status": "detected",
                "pack_id": suggestion["pack_id"],
                "suggestion": suggestion,
                "knowledge": knowledge,
            }
        except Exception as exc:
            return {
                "status": "error",
                "error": str(exc),
            }

    def _should_run_advanced_statistics(
        self,
        context: AgentContext,
        dataframe_metadata: dict,
    ) -> bool:
        """Esegue statistiche avanzate solo quando i dati o la strategy lo giustificano."""
        numeric_columns = dataframe_metadata.get("numeric_columns") or []
        categorical_columns = dataframe_metadata.get("categorical_columns") or []
        datetime_columns = dataframe_metadata.get("datetime_columns") or []
        if not any([numeric_columns, categorical_columns, datetime_columns]):
            return False
        pattern_ids = {
            pattern.get("pattern_id")
            for pattern in context.detected_patterns
            if isinstance(pattern, dict)
        }
        if pattern_ids.intersection({
            "time_performance_analysis",
            "operational_kpi_analysis",
            "data_quality_audit",
            "categorical_segmentation",
        }):
            return True
        statistical_steps = {
            "advanced_statistical_summary",
            "percentile_analysis",
            "numeric_distribution",
            "advanced_dispersion_analysis",
            "outlier_analysis",
            "threshold_comparison",
            "time_trend",
            "correlation_matrix",
            "categorical_segmentation",
            "top_values",
            "data_quality_audit",
        }
        return any(
            step.get("analysis_type") in statistical_steps
            for step in context.analytical_strategy.get("recommended_sequence", [])
            if isinstance(step, dict)
        )

    def _should_run_anomaly_detection(self, context: AgentContext) -> bool:
        request = str(context.user_input or "").lower()
        anomaly_terms = {
            "anomalia",
            "anomalie",
            "anomalo",
            "outlier",
            "spike",
            "picco",
            "degrado",
            "drift",
            "sla",
            "soglia",
            "violazione",
            "violazioni",
        }
        if any(term in request for term in anomaly_terms):
            return True
        pattern_ids = {
            pattern.get("pattern_id")
            for pattern in context.detected_patterns
            if isinstance(pattern, dict)
        }
        if "time_performance_analysis" in pattern_ids or "data_quality_audit" in pattern_ids:
            return True
        anomaly_steps = {
            "outlier_analysis",
            "anomaly_detection",
            "time_series_anomaly_detection",
            "degradation_detection",
            "threshold_comparison",
            "segment_anomaly_analysis",
        }
        return any(
            step.get("analysis_type") in anomaly_steps
            for step in context.analytical_strategy.get("recommended_sequence", [])
            if isinstance(step, dict)
        )

    def _should_run_root_cause_analysis(self, context: AgentContext) -> bool:
        request = str(context.user_input or "").lower()
        root_cause_terms = {
            "root cause",
            "causa",
            "cause",
            "perché",
            "perche",
            "motivo",
            "degradation",
            "degrado",
            "anomaly",
            "anomalia",
            "anomalie",
            "explain",
            "spiega",
            "spiegazione",
        }
        if any(term in request for term in root_cause_terms):
            return True
        anomaly_results = context.anomaly_detection_results or {}
        try:
            anomaly_count = int(anomaly_results.get("anomaly_count", 0) or 0)
        except (TypeError, ValueError):
            anomaly_count = 0
        if anomaly_count > 0:
            return True
        return any(
            step.get("analysis_type") == "root_cause_analysis"
            for step in context.analytical_strategy.get("recommended_sequence", [])
            if isinstance(step, dict)
        )

    def _build_anomaly_config(
        self,
        context: AgentContext,
        dataframe_metadata: dict,
    ) -> dict:
        numeric_columns = dataframe_metadata.get("numeric_columns") or []
        datetime_columns = dataframe_metadata.get("datetime_columns") or []
        forbidden_columns = set(context.forbidden_columns or [])
        numeric_columns = [column for column in numeric_columns if column not in forbidden_columns]
        datetime_columns = [column for column in datetime_columns if column not in forbidden_columns]
        metric = None
        if context.primary_metric in numeric_columns:
            metric = context.primary_metric
        elif "TEMPO_ATTIVAZIONE_GIORNI" in numeric_columns:
            metric = "TEMPO_ATTIVAZIONE_GIORNI"
        for column in numeric_columns:
            if metric:
                break
            normalized = str(column).lower()
            if any(term in normalized for term in ("duration", "durata", "tempo", "latency", "sla", "hours")):
                metric = column
                break
        if metric is None and numeric_columns:
            metric = numeric_columns[0]
        config = {
            "numeric_columns": numeric_columns,
            "time_column": datetime_columns[0] if datetime_columns else None,
            "value_column": metric,
            "frequency": "MS",
            "rolling_window": 3,
            "growth_threshold_percent": 50.0,
            "degradation_threshold_percent": 20.0,
        }
        if metric == "TEMPO_ATTIVAZIONE_GIORNI":
            config["numeric_columns"] = [metric]
            config["growth_threshold_percent"] = 35.0
        return {key: value for key, value in config.items() if value is not None}
