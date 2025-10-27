import asyncio
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, HTTPException

from app import db_client, poller, session_manager
from app.models import ManualBenchmarkResponse, SessionRequest, SessionResponse

background_tasks: dict[str, asyncio.Task] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup
    session_manager.setup_database()

    # Ensure a clean state on startup by ending any stale sessions
    # This handles cases where the app crashed or was killed without graceful shutdown.
    if session_manager.is_session_active():
        logging.warning("A stale session was found on startup. Ending it now.")
        session_manager.end_session()
    await poller.get_teltonika_token()
    yield

    for task_name, task in list(background_tasks.items()):
        logging.info(f"Cancelling background task: {task_name}")
        task.cancel()
        del background_tasks[task_name]

    # End any active session to ensure a clean shutdown
    if session_manager.is_session_active():
        session_manager.end_session()


app = FastAPI(title="Edge Service", lifespan=lifespan, docs_url="/")


async def high_frequency_polling_loop():
    """The main data collection loop that runs in the background."""
    while session_manager.is_session_active():
        state = session_manager.get_session_state()

        modem_data = await poller.get_modem_status()

        if modem_data:
            db_client.write_state_metrics(state.session_id, state.iccid, modem_data)

        await asyncio.sleep(1.0)


# async def low_frequency_benchmark_loop():
#     """Periodically triggers the benchmark suite if the lock is free."""
#     logging.info("Low-frequency benchmark loop started.")
#     settings = get_settings().benchmarks
#     run_count = 0

#     while session_manager.is_session_active():
#         should_run_speedtest = (run_count == 0)

#         if session_manager.acquire_benchmark_lock():
#             try:
#                 await run_all_benchmarks()
#             finally:
#                 session_manager.release_benchmark_lock()
#         else:
#             logging.warning("Skipping auto benchmark run; lock is held by another task (e.g., manual trigger).")

#         await asyncio.sleep(settings.interval_seconds)

#     logging.info("Low-frequency benchmark loop stopped.")


@app.post(
    "/sessions/start",
    tags=["sessions"],
    summary="Start a new measurement session",
    description="Starts a new measurement session and begins polling the Teltonika modem for data.",
    response_model=SessionResponse,
)
async def start_session(session_request: SessionRequest) -> SessionResponse:
    if session_manager.is_session_active():
        raise HTTPException(status_code=409, detail="Session is already active.")

    # Generate a unique ID for this session
    session_id = f"flight-{uuid.uuid4()}"

    # You would also get the active SIM ICCID here from Teltonika API
    iccid = "8944100000000000001F"  # Placeholder

    session_manager.start_new_session(
        session_id, iccid, session_request.auto_benchmarks_enabled
    )

    background_tasks["high_frequency_task"] = asyncio.create_task(high_frequency_polling_loop())

    # if session_request.auto_benchmarks_enabled:
    #     background_tasks["low_frequency_task"] = asyncio.create_task(low_frequency_benchmark_loop())

    return SessionResponse(
        message="Measurement session started",
        session_id=session_id,
        iccid=iccid,
        benchmarks_running=session_request.auto_benchmarks_enabled,
    )


@app.post(
    "/sessions/end",
    tags=["sessions"],
    summary="End the current measurement session",
    description="Ends the current measurement session and stops polling the Teltonika modem for data.",
    response_model=SessionResponse,
)
async def end_session() -> SessionResponse:
    if not session_manager.is_session_active():
        raise HTTPException(status_code=404, detail="No active session to end.")

    base_session_response = session_manager.end_session()

    # Stop ALL background tasks
    for task_name, task in list(background_tasks.items()):
        task.cancel()
        del background_tasks[task_name]

    return SessionResponse(
        **base_session_response.model_dump(), message="Measurement session ended."
    )


@app.get(
    "/sessions/status",
    tags=["sessions"],
    summary="Get current session status",
    description="Retrieves the current session status including session ID and ICCID if a session is active.",
    response_model=SessionResponse,
)
async def get_status() -> SessionResponse:
    state = session_manager.get_session_state()
    if state.session_id:
        return SessionResponse(**state.model_dump(), message="Session is active")
    return SessionResponse(message="No active session.")


@app.post("/benchmarks/start", tags=["benchmarks"], response_model=ManualBenchmarkResponse, status_code=202)
async def trigger_manual_benchmarks(background_tasks: BackgroundTasks):
    # TODO: implement benchmarking functionality
    raise HTTPException(status_code=501, detail="Benchmarking functionality not yet implemented.")
    if not session_manager.is_session_active():
        raise HTTPException(
            status_code=404, detail="Cannot start benchmarks, no session is active."
        )

    if not session_manager.acquire_benchmark_lock():
        raise HTTPException(status_code=409, detail="A benchmark suite is already in progress.")

    async def wrapper():
        try:
            pass
            # await run_all_benchmarks(run_speedtest=True)
        finally:
            session_manager.release_benchmark_lock()
    background_tasks.add_task(wrapper)
    return ManualBenchmarkResponse(message="Benchmark suite successfully triggered.")
