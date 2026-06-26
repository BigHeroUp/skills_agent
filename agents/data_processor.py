"""
Data Processor Agent
Elabora e trasforma i dati validati
"""

from agents.base_agent import BaseAgent
from services.advanced_statistical_engine import AdvancedStatisticalEngine
from services.anomaly_detection_engine import AnomalyDetectionEngine
from services.analysis_engine import AnalysisEngine
from services.analytical_reasoning_layer import AnalyticalReasoningLayer
from services.autonomous_analyst import AutonomousAnalyst
from services.learning_engine import LearningEngine
from services.pattern_knowledge_engine import PatternKnowledgeEngine
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
            deterministic_summary = summarize_dataframe(df)
            analysis_engine = AnalysisEngine(history_manager=AnalysisHistoryManager())
            autonomous_analyst = AutonomousAnalyst()
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
                analysis_payload = analysis_engine.run(
                    user_request=context.user_input,
                    df=df,
                    source_type=context.metadata.get("source_type", "unknown"),
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

            # Prepara il prompt per OpenAI
            task_prompt = f"""
            Elabora questi dati validati (rispondi SEMPRE in italiano):
            Riepilogo calcolato dal dataframe reale:
            {str(deterministic_summary)[:2000]}

            Piano analitico deterministico eseguito dal motore Python/Pandas:
            {str(context.analysis_plan)[:1200]}

            Risultati deterministici calcolati dal dataframe:
            {str(context.deterministic_results)[:2000]}

            Knowledge Base analitica:
            - Pattern rilevati: {str([item.get("pattern_id") for item in context.detected_patterns])}
            - Step consigliati: {str(context.knowledge_analysis_steps)[:1600]}

            Memoria operativa:
            - Fonte piano: {"memoria storica" if context.plan_source == "history" else "nuovo piano"}
            - Confidence score: {context.confidence_score}
            - Similarity score: {context.similarity_score}
            - Similarity method: {context.similarity_method}

            Strategia analitica locale:
            {str(context.analytical_strategy)[:2000]}

            Statistiche avanzate locali:
            {str(context.advanced_statistical_results)[:2000]}

            Anomaly detection locale:
            {str(context.anomaly_detection_results)[:2000]}

            Analisi autonoma:
            - Modalita autonoma: {context.autonomous_mode}
            - Executive summary autonoma: {context.autonomous_executive_summary[:1200]}
            - Raccomandazioni autonome: {str(context.autonomous_recommendations)[:1200]}
            
            Applica in italiano:
            1. Aggregazioni necessarie
            2. Calcoli (somme, medie, percentuali)
            3. Trasformazioni (normalizzazione, pulizia)
            4. Grouping e sorting intelligente
            
            Ritorna in italiano:
            {{
                "trasformazioni_applicate": [...],
                "statistiche_riepilogative": {{...}},
                "forma_dati": "X righe, Y colonne",
                "note_elaborazione": "..."
            }}
            """
            prompt = self.build_prompt_with_skill(task_prompt)
            
            messages = [{"role": "user", "content": prompt}]
            response = self.call_openai(messages)
            
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
                "analytical_strategy": context.analytical_strategy,
                "analytical_reasoning_trace": context.analytical_reasoning_trace,
                "advanced_statistical_results": context.advanced_statistical_results,
                "anomaly_detection_results": context.anomaly_detection_results,
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

    def _build_anomaly_config(
        self,
        context: AgentContext,
        dataframe_metadata: dict,
    ) -> dict:
        numeric_columns = dataframe_metadata.get("numeric_columns") or []
        datetime_columns = dataframe_metadata.get("datetime_columns") or []
        metric = None
        for column in numeric_columns:
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
        return {key: value for key, value in config.items() if value is not None}
