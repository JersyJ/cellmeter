import asyncio
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app import db_client, poller, session_manager
from app.models import SessionResponse

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
    poller.get_teltonika_token()
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
        session_id = session_manager.get_session_id()
        iccid = session_manager.get_iccid()

        modem_data = poller.get_modem_status()

        if modem_data:
            db_client.write_state_metrics(session_id, iccid, modem_data)

        await asyncio.sleep(1.0)

@app.post(
    "/session/start",
    summary="Start a new measurement session",
    description="Starts a new measurement session and begins polling the Teltonika modem for data.",
    response_model=SessionResponse,
)
async def start_session() -> SessionResponse:
    if session_manager.is_session_active():
        raise HTTPException(status_code=400, detail="Session is already active.")

    # Generate a unique ID for this session
    session_id = f"flight-{uuid.uuid4()}"

    # You would also get the active SIM ICCID here from Teltonika API
    iccid = "8944100000000000001F"  # Placeholder

    session_manager.start_new_session(session_id, iccid)

    # Start the high_frequency_polling_loop as a background task
    hf_task = asyncio.create_task(high_frequency_polling_loop())
    background_tasks["high_frequency_task"] = hf_task
    # # TODO:
    # # Start the low_frequency_benchmark_loop as a background task
    # lf_task = asyncio.create_task(low_frequency_benchmark_loop())
    # background_tasks["low_frequency_task"] = lf_task

    return SessionResponse(
        message="Measurement session started", session_id=session_id, iccid=iccid
    )


@app.post(
    "/session/end",
    summary="End the current measurement session",
    description="Ends the current measurement session and stops polling the Teltonika modem for data.",
    response_model=SessionResponse,
)
async def end_session() -> SessionResponse:
    if not session_manager.is_session_active():
        raise HTTPException(status_code=400, detail="No active session to end.")

    base_session_response = session_manager.end_session()

    # Stop ALL background tasks
    for task_name, task in list(background_tasks.items()):
        task.cancel()
        del background_tasks[task_name]


    return SessionResponse(
        message="Measurement session ended.",
        session_id=base_session_response.session_id,
        iccid=base_session_response.iccid,
    )


@app.get(
    "/status",
    summary="Get current session status",
    description="Retrieves the current session status including session ID and ICCID if a session is active.",
    response_model=SessionResponse,
)
def get_status() -> SessionResponse:
    state = session_manager.get_session_state()
    if state and state.get("is_active") == 1:
        return SessionResponse.model_validate(SessionResponse(message="Session is active", session_id=state.get("session_id"), iccid=state.get("iccid")))
    return SessionResponse(message="No active session.", session_id=None, iccid=None)
