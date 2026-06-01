from pathlib import Path

from agents.query_suggestion_agent import QuerySuggestionAgent


def test_required_skill_files_exist():
    required = [
        Path("skills/data_validation/SKILL.md"),
        Path("skills/data_processing/SKILL.md"),
        Path("skills/analysis/SKILL.md"),
        Path("skills/query_suggestion/SKILL.md"),
    ]

    assert not [path for path in required if not path.exists()]


def test_agent_builds_prompt_with_skill_content():
    agent = QuerySuggestionAgent()
    prompt = agent.build_prompt_with_skill("Genera un suggerimento di test.")

    assert "ISTRUZIONI SKILL (query_suggestion)" in prompt
    assert "Query Suggestion Skill" in prompt
    assert "TASK CORRENTE" in prompt
    assert "Genera un suggerimento di test." in prompt
