import pytest

from utils.oracle_query_validator import QuerySafetyValidator


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM clienti",
        "  select nome from clienti where rownum <= 10",
        "WITH base AS (SELECT * FROM ordini) SELECT * FROM base",
        "/* commento */ SELECT 1 FROM dual",
        "-- commento\nSELECT 1 FROM dual",
    ],
)
def test_accepts_read_only_queries(sql):
    result = QuerySafetyValidator.validate_read_only(sql)
    assert result.is_valid, result.reason


@pytest.mark.parametrize(
    "sql",
    [
        "",
        "DELETE FROM clienti",
        "DROP TABLE clienti",
        "UPDATE clienti SET nome = 'x'",
        "INSERT INTO clienti VALUES (1)",
        "MERGE INTO clienti c USING altri a ON (c.id = a.id) WHEN MATCHED THEN UPDATE SET c.nome = a.nome",
        "TRUNCATE TABLE clienti",
        "SELECT * FROM clienti; DELETE FROM clienti",
        "WITH deleted AS (DELETE FROM clienti RETURNING id) SELECT * FROM deleted",
        "/* comment */ UPDATE clienti SET nome = 'x'",
    ],
)
def test_blocks_mutating_or_unsafe_queries(sql):
    result = QuerySafetyValidator.validate_read_only(sql)
    assert not result.is_valid


def test_assert_read_only_raises_clear_error():
    with pytest.raises(ValueError, match="keyword non consentite|Sono consentite"):
        QuerySafetyValidator.assert_read_only("DELETE FROM clienti")
