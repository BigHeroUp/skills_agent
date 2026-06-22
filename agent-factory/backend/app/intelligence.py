from __future__ import annotations

import csv
import math
import re
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from .dependency_manager import ensure_python_packages


SQLITE_SUFFIXES = {".db", ".sqlite", ".sqlite3"}


def generate_clarification_questions(prompt: str, business_requirements: str, filenames: list[str]) -> list[str]:
    merged = f"{prompt}\n{business_requirements}".strip()
    questions: list[str] = [
        "Qual e il risultato finale atteso e in quale formato vuoi riceverlo (report, dashboard, piano operativo, codice, altro)?",
        "Quali sono i vincoli principali (tempo, budget, policy, compliance, tecnologia da usare)?",
        "Qual e il livello di dettaglio desiderato (executive summary, operativo, tecnico profondo)?",
        "Quali KPI o criteri userai per giudicare se la soluzione e valida?",
    ]

    if not business_requirements.strip():
        questions.append("Puoi condividere i business requirement minimi o le priorita di business (must-have vs nice-to-have)?")

    if filenames:
        questions.append("Per i file caricati, quali colonne o metriche sono prioritarie e quali decisioni vuoi prendere dai dati?")
    else:
        questions.append("Hai dati da allegare (CSV/Excel) o dobbiamo lavorare solo su prompt e requirement testuali?")

    if "graf" in merged.lower() or "dashboard" in merged.lower():
        questions.append("Preferisci grafici specifici (linee, barre, scatter) e con quali segmentazioni?")

    # Keep the list short but meaningful.
    return questions[:7]


def enrich_business_requirements_from_files(business_requirements: str, file_paths: list[Path]) -> tuple[str, list[str]]:
    extracted_from: list[str] = []
    chunks: list[str] = []

    for path in file_paths:
        if path.suffix.lower() not in {".txt", ".md"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore").strip()
            if text:
                extracted_from.append(path.name)
                chunks.append(text[:8000])
        except Exception:  # noqa: BLE001
            continue

    if not chunks:
        return business_requirements, extracted_from

    merged = business_requirements.strip()
    file_section = "\n\n".join(chunks)
    if merged:
        merged = f"{merged}\n\n[BR estratto da file]\n{file_section}"
    else:
        merged = f"[BR estratto da file]\n{file_section}"
    return merged, extracted_from


def _safe_csv_preview(path: Path, limit: int = 5) -> dict[str, Any]:
    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        reader = csv.DictReader(fh)
        rows = []
        for idx, row in enumerate(reader):
            rows.append(row)
            if idx + 1 >= limit:
                break
        return {
            "columns": reader.fieldnames or [],
            "preview_rows": rows,
            "row_count_previewed": len(rows),
        }


def _tokenize_text(text: str) -> set[str]:
    tokens = set(re.findall(r"[a-zA-Z0-9_]+", text.lower()))
    expansions = set(tokens)
    synonyms = {
        "device": {"device", "devices", "dispositivo", "dispositivi", "asset", "assets"},
        "customer": {"customer", "customers", "cliente", "clienti", "client"},
        "delivered": {"delivered", "consegnato", "consegnati", "consegnata", "consegnate", "delivery", "delivered_at"},
        "total": {"totale", "totali", "numero", "quanti", "count", "conteggio"},
    }
    for canonical, values in synonyms.items():
        if tokens.intersection(values):
            expansions.add(canonical)
            expansions.update(values)
    return {token for token in expansions if len(token) > 1}


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _sqlite_connect_readonly(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _sqlite_path_from_connection_string(connection_string: str) -> Path:
    clean = connection_string.strip()
    if not clean:
        raise ValueError("Connection string vuota")

    if clean.startswith("sqlite:///"):
        parsed = urlparse(clean)
        raw_path = unquote(parsed.path)
        if parsed.netloc:
            raw_path = f"/{parsed.netloc}{raw_path}"
        return Path(raw_path).expanduser().resolve()

    if clean.startswith("sqlite://"):
        parsed = urlparse(clean)
        raw_path = unquote(parsed.path or parsed.netloc)
        return Path(raw_path).expanduser().resolve()

    if clean.startswith("file:"):
        parsed = urlparse(clean)
        return Path(unquote(parsed.path)).expanduser().resolve()

    path = Path(clean).expanduser()
    if path.suffix.lower() in SQLITE_SUFFIXES:
        return path.resolve()

    raise ValueError("Sono supportate connection string SQLite: sqlite:////percorso/db.sqlite, sqlite:///relativo.db o path locale .db/.sqlite")


def mask_connection_string(connection_string: str) -> str:
    parsed = urlparse(connection_string)
    if parsed.password:
        return connection_string.replace(parsed.password, "***")
    return connection_string


def test_database_connection(connection_string: str) -> dict[str, Any]:
    try:
        path = _sqlite_path_from_connection_string(connection_string)
        if not path.exists():
            return {"status": "error", "error": f"Database non trovato: {path}"}
        schema = _introspect_sqlite_database(path)
        return {"status": "ok", "schema": schema, "database_path": str(path)}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": str(exc)}


def is_sql_request(request: str) -> bool:
    stripped = request.strip().lower()
    return bool(re.match(r"^(select|with|pragma)\b", stripped))


def execute_database_sql(connection_string: str, sql: str) -> dict[str, Any]:
    if not is_sql_request(sql):
        return {"error": "Sono consentite solo query read-only: SELECT, WITH o PRAGMA."}

    path = _sqlite_path_from_connection_string(connection_string)
    try:
        with _sqlite_connect_readonly(path) as conn:
            rows = conn.execute(sql).fetchmany(200)
            result_rows = [dict(row) for row in rows]
        return {
            "request": sql,
            "sql": sql,
            "answer": f"Estratti {len(result_rows)} record.",
            "rows": result_rows,
        }
    except sqlite3.Error as exc:
        return {"request": sql, "sql": sql, "error": str(exc)}


def execute_database_request(connection_string: str, request: str) -> dict[str, Any]:
    path = _sqlite_path_from_connection_string(connection_string)
    schema = _introspect_sqlite_database(path)
    if is_sql_request(request):
        result = execute_database_sql(connection_string, request)
        result["schema"] = schema
        result["mode"] = "sql"
        return result

    result = _execute_natural_language_sqlite_request(path, schema, request)
    if not result:
        result = {
            "request": request,
            "answer": "Non sono riuscito a trasformare la richiesta in una query affidabile. Specifica tabella, metrica o filtro.",
            "rows": [],
        }
    result["schema"] = schema
    result["mode"] = "natural_language"
    return result


def _is_sqlite_file(path: Path) -> bool:
    return path.suffix.lower() in SQLITE_SUFFIXES


def _sqlite_table_names(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    return [str(row["name"]) for row in rows]


def _sample_column_values(conn: sqlite3.Connection, table: str, column: str, limit: int = 12) -> list[str]:
    try:
        rows = conn.execute(
            f"SELECT DISTINCT {_quote_identifier(column)} AS value FROM {_quote_identifier(table)} WHERE {_quote_identifier(column)} IS NOT NULL LIMIT ?",
            (limit,),
        ).fetchall()
    except sqlite3.Error:
        return []
    return [str(row["value"]) for row in rows]


def _introspect_sqlite_database(path: Path) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "filename": path.name,
        "path": str(path),
        "dialect": "sqlite",
        "tables": [],
        "relationships": [],
        "inferred_relationships": [],
    }
    with _sqlite_connect_readonly(path) as conn:
        tables = _sqlite_table_names(conn)
        table_columns: dict[str, list[dict[str, Any]]] = {}
        for table in tables:
            columns = []
            for col in conn.execute(f"PRAGMA table_info({_quote_identifier(table)})").fetchall():
                column = {
                    "name": str(col["name"]),
                    "type": str(col["type"] or ""),
                    "not_null": bool(col["notnull"]),
                    "primary_key": bool(col["pk"]),
                }
                sample_values = _sample_column_values(conn, table, column["name"], limit=6)
                if sample_values:
                    column["sample_values"] = sample_values
                columns.append(column)
            table_columns[table] = columns

            try:
                row_count = int(conn.execute(f"SELECT COUNT(*) AS c FROM {_quote_identifier(table)}").fetchone()["c"])
            except sqlite3.Error:
                row_count = 0

            schema["tables"].append({"name": table, "columns": columns, "row_count": row_count})

            for fk in conn.execute(f"PRAGMA foreign_key_list({_quote_identifier(table)})").fetchall():
                schema["relationships"].append(
                    {
                        "from_table": table,
                        "from_column": str(fk["from"]),
                        "to_table": str(fk["table"]),
                        "to_column": str(fk["to"]),
                        "type": "foreign_key",
                    }
                )

        table_lookup = {table.lower(): table for table in tables}
        for table, columns in table_columns.items():
            for col in columns:
                name = col["name"]
                if not name.lower().endswith("_id"):
                    continue
                stem = name[:-3].lower()
                candidates = [stem, f"{stem}s", f"{stem}es"]
                target = next((table_lookup[item] for item in candidates if item in table_lookup), None)
                if target and target != table:
                    inferred = {
                        "from_table": table,
                        "from_column": name,
                        "to_table": target,
                        "to_column": "id",
                        "type": "inferred_name_match",
                    }
                    has_real_relationship = any(
                        rel.get("from_table") == inferred["from_table"]
                        and rel.get("from_column") == inferred["from_column"]
                        and rel.get("to_table") == inferred["to_table"]
                        and rel.get("to_column") == inferred["to_column"]
                        for rel in schema["relationships"]
                    )
                    if not has_real_relationship:
                        schema["inferred_relationships"].append(inferred)
    return schema


def _score_table_for_request(table: dict[str, Any], request_tokens: set[str]) -> int:
    table_tokens = _tokenize_text(table.get("name", ""))
    column_tokens = set()
    for column in table.get("columns", []):
        column_tokens.update(_tokenize_text(column.get("name", "")))
    return len(request_tokens.intersection(table_tokens)) * 3 + len(request_tokens.intersection(column_tokens))


def _find_status_filter(table: dict[str, Any], request_tokens: set[str]) -> tuple[str, str] | None:
    if not request_tokens.intersection({"delivered", "consegnato", "consegnati", "consegnata", "consegnate"}):
        return None
    candidate_names = ["status", "stato", "state", "delivery_status", "delivered", "consegnato", "delivered_at", "delivery_date"]
    for column in table.get("columns", []):
        col_name = column.get("name", "")
        normalized = col_name.lower()
        if not any(candidate in normalized for candidate in candidate_names):
            continue
        samples = [str(value).lower() for value in column.get("sample_values", [])]
        delivered_sample = next(
            (
                sample
                for sample in samples
                if any(token in sample for token in ["delivered", "consegn", "shipped", "completed"])
            ),
            None,
        )
        if delivered_sample:
            return col_name, delivered_sample
        if normalized in {"delivered", "consegnato"}:
            return col_name, "1"
        if "date" in normalized or normalized.endswith("_at"):
            return col_name, "__NOT_NULL__"
    return None


def _execute_natural_language_sqlite_request(path: Path, schema: dict[str, Any], request: str) -> dict[str, Any] | None:
    request_tokens = _tokenize_text(request)
    if not request_tokens:
        return None

    tables = schema.get("tables", [])
    if not tables:
        return None

    wants_count = bool(request_tokens.intersection({"total", "totale", "numero", "quanti", "count", "conteggio"}))
    scored = sorted(((table, _score_table_for_request(table, request_tokens)) for table in tables), key=lambda item: item[1], reverse=True)
    best_table, score = scored[0]
    if score <= 0:
        return None

    table_name = best_table["name"]
    where_parts: list[str] = []
    params: list[Any] = []
    status_filter = _find_status_filter(best_table, request_tokens)
    if status_filter:
        column, value = status_filter
        if value == "__NOT_NULL__":
            where_parts.append(f"{_quote_identifier(column)} IS NOT NULL")
        elif value == "1":
            where_parts.append(f"{_quote_identifier(column)} = 1")
        else:
            where_parts.append(f"LOWER({_quote_identifier(column)}) = ?")
            params.append(value)

    if wants_count:
        select_expr = "COUNT(*) AS total"
    else:
        select_expr = "*"

    sql = f"SELECT {select_expr} FROM {_quote_identifier(table_name)}"
    if where_parts:
        sql += " WHERE " + " AND ".join(where_parts)
    if not wants_count:
        sql += " LIMIT 25"

    try:
        with _sqlite_connect_readonly(path) as conn:
            rows = conn.execute(sql, params).fetchall()
    except sqlite3.Error as exc:
        return {"request": request, "error": str(exc), "sql": sql}

    result_rows = [dict(row) for row in rows]
    answer = ""
    if wants_count and result_rows:
        answer = f"Totale record trovati in {table_name}: {result_rows[0].get('total', 0)}."
    elif result_rows:
        answer = f"Estratti {len(result_rows)} record da {table_name}."

    return {
        "request": request,
        "matched_table": table_name,
        "sql": sql,
        "params": params,
        "answer": answer,
        "rows": result_rows,
    }


def _find_column(columns: list[str], aliases: list[str]) -> str | None:
    normalized = {str(col).strip().lower().replace(" ", "_"): col for col in columns}
    for alias in aliases:
        if alias in normalized:
            return normalized[alias]
    for key, original in normalized.items():
        if any(alias in key for alias in aliases):
            return original
    return None


def _clean_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _fmt_number(value: Any) -> str:
    number = _clean_number(value)
    if number is None:
        return "N/D"
    return f"{number:,.0f}".replace(",", ".")


def _fmt_money(value: Any) -> str:
    number = _clean_number(value)
    if number is None:
        return "N/D"
    return f"{number:,.0f} EUR".replace(",", ".")


def _fmt_pct(value: Any) -> str:
    number = _clean_number(value)
    if number is None:
        return "N/D"
    if abs(number) <= 1:
        number *= 100
    return f"{number:.1f}%"


def _records_from_grouped(grouped: Any, revenue_col: str | None, cost_col: str | None, churn_col: str | None, limit: int = 6) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, group in grouped:
        revenue = float(group[revenue_col].sum()) if revenue_col else None
        cost = float(group[cost_col].sum()) if cost_col else None
        margin = (revenue - cost) if revenue is not None and cost is not None else None
        margin_rate = (margin / revenue) if margin is not None and revenue else None
        churn = float(group[churn_col].mean()) if churn_col else None
        rows.append(
            {
                "name": str(key),
                "revenue": revenue,
                "cost": cost,
                "margin": margin,
                "margin_rate": margin_rate,
                "churn_rate": churn,
            }
        )

    rows.sort(key=lambda row: (row.get("margin") is not None, row.get("margin") or 0), reverse=True)
    return rows[:limit]


def _compute_tabular_insights(df: Any) -> dict[str, Any]:
    columns = [str(col) for col in df.columns]
    revenue_col = _find_column(columns, ["revenue", "ricavi", "fatturato", "arr", "sales"])
    cost_col = _find_column(columns, ["cost", "costi", "spend", "expense", "opex"])
    channel_col = _find_column(columns, ["channel", "canale", "source", "fonte"])
    segment_col = _find_column(columns, ["segment", "segmento", "customer_segment", "cliente"])
    churn_col = _find_column(columns, ["churn_rate", "churn", "retention_loss"])
    customer_col = _find_column(columns, ["customers", "clienti", "accounts", "utenti"])
    month_col = _find_column(columns, ["month", "mese", "date", "data", "period"])

    if not any([revenue_col, cost_col, channel_col, segment_col, churn_col]):
        return {}

    work = df.copy()
    for col in [revenue_col, cost_col, churn_col, customer_col]:
        if col:
            work[col] = work[col].apply(_clean_number)

    summary: dict[str, Any] = {
        "detected_columns": {
            "revenue": revenue_col,
            "cost": cost_col,
            "channel": channel_col,
            "segment": segment_col,
            "churn_rate": churn_col,
            "customers": customer_col,
            "period": month_col,
        }
    }

    total_revenue = float(work[revenue_col].sum()) if revenue_col else None
    total_cost = float(work[cost_col].sum()) if cost_col else None
    total_margin = (total_revenue - total_cost) if total_revenue is not None and total_cost is not None else None
    margin_rate = (total_margin / total_revenue) if total_margin is not None and total_revenue else None
    avg_churn = float(work[churn_col].mean()) if churn_col else None

    summary["totals"] = {
        "revenue": total_revenue,
        "cost": total_cost,
        "margin": total_margin,
        "margin_rate": margin_rate,
        "avg_churn_rate": avg_churn,
    }

    if channel_col:
        summary["by_channel"] = _records_from_grouped(work.groupby(channel_col, dropna=False), revenue_col, cost_col, churn_col)

    if segment_col:
        summary["by_segment"] = _records_from_grouped(work.groupby(segment_col, dropna=False), revenue_col, cost_col, churn_col)

    if month_col and revenue_col:
        trend_rows = []
        for key, group in work.groupby(month_col, dropna=False):
            trend_rows.append({"period": str(key), "revenue": float(group[revenue_col].sum())})
        trend_rows.sort(key=lambda row: row["period"])
        if len(trend_rows) >= 2 and trend_rows[0]["revenue"]:
            first = trend_rows[0]["revenue"]
            last = trend_rows[-1]["revenue"]
            summary["trend"] = {
                "first_period": trend_rows[0]["period"],
                "last_period": trend_rows[-1]["period"],
                "first_revenue": first,
                "last_revenue": last,
                "revenue_growth_rate": (last - first) / first,
            }
        summary["periods"] = trend_rows[:12]

    anomalies: list[str] = []
    if channel_col and revenue_col and cost_col and summary.get("by_channel"):
        channel_rows = summary["by_channel"]
        worst_margin = sorted(channel_rows, key=lambda row: row.get("margin_rate") if row.get("margin_rate") is not None else 999)[0]
        highest_cost_ratio = sorted(
            channel_rows,
            key=lambda row: (row.get("cost") or 0) / row["revenue"] if row.get("revenue") else -1,
            reverse=True,
        )[0]
        anomalies.append(
            f"Canale con marginalita piu bassa: {worst_margin['name']} ({_fmt_pct(worst_margin.get('margin_rate'))})."
        )
        anomalies.append(
            f"Canale con peso costi piu alto: {highest_cost_ratio['name']} ({_fmt_pct((highest_cost_ratio.get('cost') or 0) / highest_cost_ratio['revenue'] if highest_cost_ratio.get('revenue') else None)} dei ricavi)."
        )
    if segment_col and churn_col and summary.get("by_segment"):
        worst_churn = sorted(summary["by_segment"], key=lambda row: row.get("churn_rate") or 0, reverse=True)[0]
        anomalies.append(f"Segmento con churn medio piu alto: {worst_churn['name']} ({_fmt_pct(worst_churn.get('churn_rate'))}).")
    summary["anomalies"] = anomalies

    recommendations: list[str] = []
    if anomalies:
        recommendations.append("Aprire una review sui driver di costo del canale meno efficiente prima di aumentare il budget.")
    if churn_col and segment_col:
        recommendations.append("Separare piano retention per segmento e misurare churn, upgrade e recupero margine su base mensile.")
    if revenue_col and month_col:
        recommendations.append("Monitorare crescita mese su mese con soglie di allarme su ricavi, costi e margine.")
    if not recommendations:
        recommendations.append("Definire KPI primari e raccogliere almeno una dimensione temporale o di segmento per rendere l'analisi azionabile.")
    summary["recommendations"] = recommendations
    return summary


def analyze_tabular_files(file_paths: list[Path], natural_language_request: str = "") -> tuple[dict[str, Any], dict[str, str]]:
    if not file_paths:
        return {"file_insights": [], "db_insights": []}, {}

    install_results = ensure_python_packages(["pandas", "openpyxl"])
    artifacts: dict[str, Any] = {"file_insights": [], "db_insights": []}

    has_pandas = install_results.get("pandas") in {"installed", "already-installed"}
    if has_pandas:
        import pandas as pd  # type: ignore

    for path in file_paths:
        suffix = path.suffix.lower()
        if _is_sqlite_file(path):
            db_insight = _introspect_sqlite_database(path)
            nl_result = _execute_natural_language_sqlite_request(path, db_insight, natural_language_request)
            if nl_result:
                db_insight["natural_language_result"] = nl_result
            artifacts["db_insights"].append(db_insight)
            continue

        insight: dict[str, Any] = {"filename": path.name, "path": str(path)}
        try:
            if has_pandas and suffix in {".csv", ".xlsx", ".xls"}:
                if suffix == ".csv":
                    df = pd.read_csv(path)
                else:
                    df = pd.read_excel(path)
                insight["columns"] = list(df.columns)
                insight["rows"] = int(df.shape[0])
                insight["null_counts"] = {k: int(v) for k, v in df.isnull().sum().to_dict().items()}
                insight["numeric_summary"] = df.describe(include="all").fillna("").to_dict()
                insight["preview_rows"] = df.head(5).fillna("").to_dict(orient="records")
                insight["computed_insights"] = _compute_tabular_insights(df)
            elif suffix == ".csv":
                preview = _safe_csv_preview(path)
                insight.update(preview)
            else:
                insight["warning"] = "Formato non analizzato: installare dipendenze o convertire in CSV/XLSX"
        except Exception as exc:  # noqa: BLE001
            insight["error"] = str(exc)
        artifacts["file_insights"].append(insight)

    return artifacts, install_results


def _data_insight_markdown(file_insights: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for item in file_insights:
        computed = item.get("computed_insights") or {}
        if not computed:
            lines.append(
                f"- **{item.get('filename', 'file')}**: colonne={len(item.get('columns', []))}, righe={item.get('rows', item.get('row_count_previewed', 'N/D'))}"
            )
            continue

        totals = computed.get("totals", {})
        lines.extend(
            [
                f"### {item.get('filename', 'file')}",
                f"- Righe analizzate: {_fmt_number(item.get('rows', item.get('row_count_previewed')))}",
                f"- Ricavi totali: {_fmt_money(totals.get('revenue'))}",
                f"- Costi totali: {_fmt_money(totals.get('cost'))}",
                f"- Margine stimato: {_fmt_money(totals.get('margin'))} ({_fmt_pct(totals.get('margin_rate'))})",
                f"- Churn medio: {_fmt_pct(totals.get('avg_churn_rate'))}",
            ]
        )

        by_channel = computed.get("by_channel") or []
        if by_channel:
            lines.extend(["", "#### Performance per canale"])
            for row in by_channel:
                lines.append(
                    f"- **{row.get('name')}**: ricavi {_fmt_money(row.get('revenue'))}, costi {_fmt_money(row.get('cost'))}, margine {_fmt_money(row.get('margin'))} ({_fmt_pct(row.get('margin_rate'))}), churn {_fmt_pct(row.get('churn_rate'))}"
                )

        by_segment = computed.get("by_segment") or []
        if by_segment:
            lines.extend(["", "#### Performance per segmento"])
            for row in by_segment:
                lines.append(
                    f"- **{row.get('name')}**: ricavi {_fmt_money(row.get('revenue'))}, margine {_fmt_money(row.get('margin'))} ({_fmt_pct(row.get('margin_rate'))}), churn {_fmt_pct(row.get('churn_rate'))}"
                )

        trend = computed.get("trend")
        if trend:
            lines.extend(
                [
                    "",
                    "#### Trend",
                    f"- Ricavi da {trend.get('first_period')} a {trend.get('last_period')}: {_fmt_money(trend.get('first_revenue'))} -> {_fmt_money(trend.get('last_revenue'))} ({_fmt_pct(trend.get('revenue_growth_rate'))}).",
                ]
            )

        anomalies = computed.get("anomalies") or []
        if anomalies:
            lines.extend(["", "#### Anomalie / Attenzioni"])
            for anomaly in anomalies:
                lines.append(f"- {anomaly}")

        recommendations = computed.get("recommendations") or []
        if recommendations:
            lines.extend(["", "#### Raccomandazioni dai dati"])
            for rec in recommendations:
                lines.append(f"- {rec}")

    return lines


def _db_insight_markdown(db_insights: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for db in db_insights:
        lines.extend(
            [
                f"### {db.get('filename', 'database')}",
                f"- Dialect: {db.get('dialect', 'N/D')}",
                f"- Tabelle rilevate: {len(db.get('tables', []))}",
            ]
        )

        for table in db.get("tables", [])[:12]:
            column_names = [column.get("name", "") for column in table.get("columns", [])]
            lines.append(
                f"- **{table.get('name')}**: {table.get('row_count', 0)} righe, colonne: {', '.join(column_names[:10])}"
            )

        relationships = [*db.get("relationships", []), *db.get("inferred_relationships", [])]
        if relationships:
            lines.extend(["", "#### Relazioni rilevate"])
            for rel in relationships[:20]:
                lines.append(
                    f"- {rel.get('from_table')}.{rel.get('from_column')} -> {rel.get('to_table')}.{rel.get('to_column')} ({rel.get('type')})"
                )

        nl_result = db.get("natural_language_result")
        if nl_result:
            lines.extend(["", "#### Richiesta in linguaggio naturale"])
            lines.append(f"- Richiesta: {nl_result.get('request')}")
            if nl_result.get("answer"):
                lines.append(f"- Risposta: {nl_result.get('answer')}")
            if nl_result.get("sql"):
                lines.append(f"- SQL generato: `{nl_result.get('sql')}`")
            rows = nl_result.get("rows") or []
            if rows:
                lines.append(f"- Anteprima risultato: `{rows[:5]}`")
            if nl_result.get("error"):
                lines.append(f"- Errore query: {nl_result.get('error')}")

    return lines


def build_solution_markdown(context: dict[str, Any]) -> str:
    prompt = context.get("prompt", "")
    requirements = context.get("business_requirements", "")
    answers = context.get("clarification_answers", {})
    file_insights = context.get("file_insights", [])
    db_insights = context.get("db_insights", [])
    learned_actions = context.get("learned_next_best_actions", [])
    merged_text = f"{prompt} {requirements}".lower()
    wants_business_plan = any(
        token in merged_text
        for token in [
            "business plan",
            "piano di business",
            "piano industriale",
            "business case",
        ]
    )

    if wants_business_plan:
        lines = [
            "# Business Plan",
            "",
            "## 1) Executive Summary",
            f"Obiettivo: {prompt or 'N/D'}",
            f"Vincoli e requirement: {requirements or 'N/D'}",
            "",
            "## 2) Problema e Opportunita",
            "- Definire il bisogno del cliente e il segmento prioritario.",
            "- Quantificare il valore economico atteso.",
            "",
            "## 3) Proposta di Valore",
            "- Soluzione principale e differenziazione rispetto alle alternative.",
            "- Benefici misurabili per utente/azienda.",
            "",
            "## 4) Strategia Go-To-Market",
            "- Canali acquisizione principali.",
            "- Offerta iniziale e pricing hypothesis.",
            "- Piano di attivazione in 90 giorni.",
            "",
            "## 5) Modello Economico",
            "- Ricavi: ipotesi per scenario base, prudente e aggressivo.",
            "- Costi: setup, operativi e scala.",
            "- Break-even: target e assunzioni da validare.",
            "",
            "## 6) Piano Operativo",
            "- Roadmap trimestrale con milestone e owner.",
            "- Capacita e competenze necessarie.",
            "",
            "## 7) KPI e Controllo",
            "- KPI North Star.",
            "- KPI di acquisizione, conversione, retention, marginalita.",
            "",
            "## 8) Rischi e Mitigazioni",
            "- Rischio mercato, esecuzione, finanziario, compliance.",
            "- Azioni preventive e trigger di escalation.",
            "",
            "## 9) Decisioni Richieste",
            "1. Confermare scenario economico di riferimento.",
            "2. Approvare roadmap e budget del prossimo trimestre.",
            "3. Definire criteri di go/no-go al checkpoint iniziale.",
        ]

        if answers:
            lines.extend(["", "## Allegato A) Chiarimenti Consolidati"])
            for q, a in answers.items():
                lines.append(f"- **{q}**: {a}")

        if file_insights:
            lines.extend(["", "## Allegato B) Insight Dati"])
            lines.extend(_data_insight_markdown(file_insights))
        if db_insights:
            lines.extend(["", "## Allegato C) Database Schema e Query"])
            lines.extend(_db_insight_markdown(db_insights))
        if learned_actions:
            lines.extend(["", "## 10) Next Best Actions Apprese"])
            for idx, action in enumerate(learned_actions[:5], start=1):
                lines.append(f"{idx}. {action}")
        return "\n".join(lines)

    lines = [
        "# Soluzione Proposta",
        "",
        "## 1) Obiettivo sintetizzato",
        prompt or "N/D",
        "",
        "## 2) Requisiti business consolidati",
        requirements or "N/D",
        "",
        "## 3) Chiarimenti ricevuti",
    ]
    if answers:
        for q, a in answers.items():
            lines.append(f"- **{q}**: {a}")
    else:
        lines.append("- Nessuna risposta di chiarimento ricevuta.")

    lines.extend(["", "## 4) Strategia operativa", "- Definire piano in fasi con milestone misurabili.", "- Eseguire analisi dati e validazioni intermedie.", "- Produrre output finale orientato ai KPI concordati."])

    if file_insights:
        lines.extend(["", "## 5) Insight dati iniziali"])
        lines.extend(_data_insight_markdown(file_insights))

    if db_insights:
        lines.extend(["", "## 6) Database: schema, relazioni e richiesta naturale"])
        lines.extend(_db_insight_markdown(db_insights))

    lines.extend(["", "## 7) Next Best Actions"])
    if learned_actions:
        for idx, action in enumerate(learned_actions[:5], start=1):
            lines.append(f"{idx}. {action}")
    else:
        lines.extend(
            [
                "1. Confermare priorita finali e criteri di successo.",
                "2. Eseguire pipeline analitica completa sui dataset.",
                "3. Applicare iterazioni guidate da metrica con loop di apprendimento.",
            ]
        )
    return "\n".join(lines)
