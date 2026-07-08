from services.experience import AnalyticalExperience, ExperienceStore


def test_store_saves_and_loads_experiences(tmp_path):
    store = ExperienceStore(tmp_path / "experience_store.json")
    experience = AnalyticalExperience(
        id="experience.metric.response_time",
        title="Esperienza response_time",
        description="Esperienza riusabile",
        source_analysis_run_ids=["analysis_run:1", "analysis_run:2"],
        metrics=["response_time"],
        columns=["response_time", "status"],
        anomalies=["sla_violation"],
        root_causes=["Performance degradation"],
        recommended_steps=["Analizzare il trend temporale di response_time su created_at"],
        confidence=0.8,
        evidence_count=2,
        created_at="2026-01-01T10:00:00",
        updated_at="2026-01-01T10:00:00",
        tags=["metric", "response_time"],
    )

    store.upsert_experience(experience)
    store.save()

    reloaded = ExperienceStore(tmp_path / "experience_store.json")
    loaded = reloaded.load()

    assert len(loaded) == 1
    assert loaded[0].id == "experience.metric.response_time"
    assert reloaded.find_by_metric("response_time")[0].id == experience.id
    assert reloaded.find_by_anomaly("sla_violation")[0].id == experience.id
    assert reloaded.find_by_root_cause("Performance degradation")[0].id == experience.id
    assert reloaded.find_by_tag("metric")[0].id == experience.id


def test_store_does_not_persist_raw_dataframe_rows(tmp_path):
    store = ExperienceStore(tmp_path / "experience_store.json")
    experience = AnalyticalExperience(
        id="experience.metric.response_time",
        title="Esperienza response_time",
        description="Esperienza sintetica senza raw rows",
        source_analysis_run_ids=["analysis_run:1"],
        metrics=["response_time"],
        columns=["response_time"],
        anomalies=[],
        root_causes=[],
        recommended_steps=["Calcolare percentili e distribuzione di response_time"],
        confidence=0.6,
        evidence_count=1,
        created_at="2026-01-01T10:00:00",
        updated_at="2026-01-01T10:00:00",
        tags=["metric"],
    )
    store.upsert_experience(experience)
    store.save()

    payload = (tmp_path / "experience_store.json").read_text(encoding="utf-8")

    assert "120.0" not in payload
    assert "135.0" not in payload
