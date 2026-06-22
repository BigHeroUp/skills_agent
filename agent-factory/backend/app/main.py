from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .agents.orchestrator import ChiefOrchestrator
from .intelligence import (
    enrich_business_requirements_from_files,
    execute_database_request,
    generate_clarification_questions,
    mask_connection_string,
    test_database_connection,
)
from .schemas import (
    ClarificationAnswers,
    DatabaseConnectionTestRequest,
    DatabaseConnectionTestResponse,
    DatabaseQueryRequest,
    DatabaseQueryResponse,
    JobCreateResponse,
    JobSnapshot,
)
from .state import JobStore

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
STATIC_DIR = BASE_DIR / "static"

DATA_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Agent Factory", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = JobStore(db_path=DATA_DIR / "agent_memory.db")
orchestrator = ChiefOrchestrator(store)
db_connections: dict[str, dict[str, object]] = {}


@app.post("/api/jobs", response_model=JobCreateResponse)
async def create_job(
    prompt: Annotated[str, Form(...)],
    business_requirements: Annotated[str, Form()] = "",
    db_connection_id: Annotated[str, Form()] = "",
    files: Annotated[list[UploadFile], File()] = [],
) -> JobCreateResponse:
    uploaded_files: list[str] = []
    file_paths: list[Path] = []

    # Create job first to get job id and then persist files under job folder.
    job = await store.create_job(prompt, business_requirements, [], [])
    job_dir = DATA_DIR / job.job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    for file in files:
        target = job_dir / file.filename
        content = await file.read()
        target.write_bytes(content)
        uploaded_files.append(file.filename)
        file_paths.append(target)

    await store.set_uploaded_files(job.job_id, uploaded_files, file_paths)
    enriched_requirements, extracted_files = enrich_business_requirements_from_files(business_requirements, file_paths)
    if extracted_files:
        await store.set_business_requirements(job.job_id, enriched_requirements)
        await store.append_event(
            job.job_id,
            "chief-orchestrator",
            "info",
            "info",
            "Business requirement arricchito da file testuali caricati.",
            {"files": extracted_files},
        )

    if db_connection_id:
        db_connection = db_connections.get(db_connection_id)
        if not db_connection:
            raise HTTPException(status_code=400, detail="Database connection not verified or expired")
        connection_string = str(db_connection["connection_string"])
        db_result = execute_database_request(connection_string, f"{prompt}\n{business_requirements}")
        db_schema = db_result.pop("schema", db_connection.get("schema", {}))
        await store.merge_artifacts(
            job.job_id,
            {
                "db_connection": {
                    "connection_id": db_connection_id,
                    "masked_connection_string": mask_connection_string(connection_string),
                },
                "db_insights": [
                    {
                        **dict(db_schema),
                        "natural_language_result": db_result,
                    }
                ],
            },
        )
        await store.append_event(
            job.job_id,
            "data-intake-agent",
            "db-connected",
            "info",
            "Database collegato, schema introspezionato e richiesta iniziale eseguita.",
            {"connection_id": db_connection_id, "mode": db_result.get("mode")},
        )

    await orchestrator.run_intake(job.job_id)
    updated = await store.get_job(job.job_id)
    return JobCreateResponse(
        job_id=job.job_id,
        status=updated.status if updated else "awaiting_clarification",
        clarification_questions=updated.clarification_questions if updated else [],
    )


@app.post("/api/jobs/{job_id}/clarifications", response_model=JobSnapshot)
async def submit_clarifications(job_id: str, body: ClarificationAnswers) -> JobSnapshot:
    job = await store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "awaiting_clarification":
        raise HTTPException(status_code=400, detail=f"Job status is '{job.status}', clarifications are not expected now")

    answers = dict(body.answers)
    if body.free_context.strip():
        answers["Richiesta libera / contesto aggiuntivo"] = body.free_context.strip()
        merged_requirements = "\n\n".join(
            [
                job.business_requirements.strip(),
                "[CONTESTO LIBERO PRIMA DELL'ESECUZIONE]",
                body.free_context.strip(),
            ]
        ).strip()
        await store.set_business_requirements(job_id, merged_requirements)

    await store.set_answers(job_id, answers)
    asyncio.create_task(orchestrator.continue_after_clarification(job_id))

    snapshot = await store.snapshot(job_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobSnapshot.model_validate(snapshot)


@app.post("/api/db/test", response_model=DatabaseConnectionTestResponse)
async def test_db_connection(body: DatabaseConnectionTestRequest) -> DatabaseConnectionTestResponse:
    result = test_database_connection(body.connection_string)
    if result.get("status") != "ok":
        return DatabaseConnectionTestResponse(
            connection_id="",
            status="error",
            masked_connection_string=mask_connection_string(body.connection_string),
            error=str(result.get("error", "Connection failed")),
        )

    connection_id = uuid4().hex
    db_connections[connection_id] = {
        "connection_string": body.connection_string,
        "schema": result.get("schema", {}),
    }
    return DatabaseConnectionTestResponse(
        connection_id=connection_id,
        status="ok",
        masked_connection_string=mask_connection_string(body.connection_string),
        db_schema=dict(result.get("schema", {})),
    )


@app.post("/api/db/query", response_model=DatabaseQueryResponse)
async def query_db_connection(body: DatabaseQueryRequest) -> DatabaseQueryResponse:
    db_connection = db_connections.get(body.connection_id)
    if not db_connection:
        raise HTTPException(status_code=404, detail="Database connection not found or expired")
    result = execute_database_request(str(db_connection["connection_string"]), body.request)
    error = result.get("error")
    mode = str(result.get("mode", "sql" if body.request.strip().lower().startswith(("select", "with", "pragma")) else "natural_language"))
    return DatabaseQueryResponse(mode=mode, result=result, error=str(error) if error else None)


@app.post("/api/jobs/{job_id}/clarification-turn", response_model=JobSnapshot)
async def add_clarification_turn(
    job_id: str,
    message: Annotated[str, Form()] = "",
    files: Annotated[list[UploadFile], File()] = [],
) -> JobSnapshot:
    job = await store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "awaiting_clarification":
        raise HTTPException(status_code=400, detail=f"Job status is '{job.status}', clarification updates are not expected now")

    clean_message = message.strip()
    if not clean_message and not files:
        raise HTTPException(status_code=400, detail="Provide a message or at least one file")

    job_dir = DATA_DIR / job.job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    uploaded_files = list(job.uploaded_files)
    file_paths = list(job.file_paths)
    new_file_paths: list[Path] = []

    for file in files:
        target = job_dir / file.filename
        content = await file.read()
        target.write_bytes(content)
        uploaded_files.append(file.filename)
        file_paths.append(target)
        new_file_paths.append(target)

    if new_file_paths:
        await store.set_uploaded_files(job_id, uploaded_files, file_paths)

    requirement_parts = [job.business_requirements.strip()]
    if clean_message:
        requirement_parts.extend(["[NUOVA RICHIESTA IN CHIARIMENTO]", clean_message])
    updated_requirements = "\n\n".join(part for part in requirement_parts if part).strip()

    if new_file_paths:
        updated_requirements, extracted_files = enrich_business_requirements_from_files(updated_requirements, new_file_paths)
    else:
        extracted_files = []

    await store.set_business_requirements(job_id, updated_requirements)

    conversation = list(job.artifacts.get("clarification_conversation", []))
    conversation.append(
        {
            "role": "user",
            "message": clean_message,
            "files": [path.name for path in new_file_paths],
        }
    )
    await store.merge_artifacts(job_id, {"clarification_conversation": conversation})

    refreshed_questions = generate_clarification_questions(job.prompt, updated_requirements, uploaded_files)
    await store.set_questions(job_id, refreshed_questions)
    await store.merge_artifacts(job_id, {"clarification_questions": refreshed_questions})
    await store.append_event(
        job_id,
        "clarification-agent",
        "context-update",
        "info",
        "Contesto aggiornato dalla conversazione libera.",
        {"files": [path.name for path in new_file_paths], "extracted_files": extracted_files, "questions": len(refreshed_questions)},
    )

    snapshot = await store.snapshot(job_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobSnapshot.model_validate(snapshot)


@app.get("/api/jobs/{job_id}", response_model=JobSnapshot)
async def get_job(job_id: str) -> JobSnapshot:
    snapshot = await store.snapshot(job_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobSnapshot.model_validate(snapshot)


@app.websocket("/api/jobs/{job_id}/stream")
async def job_stream(job_id: str, websocket: WebSocket) -> None:
    job = await store.get_job(job_id)
    if not job:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    queue = await store.subscribe(job_id)

    try:
        snapshot = await store.snapshot(job_id)
        await websocket.send_json({"type": "snapshot", "data": snapshot})

        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        await store.unsubscribe(job_id, queue)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def root() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
