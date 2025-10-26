import asyncio
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, HTTPException

from app import db_client, poller, session_manager

background_tasks = {}


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

    if "polling_task" in background_tasks:
        logging.info("Cancelling background polling task...")
        background_tasks["polling_task"].cancel()

    # End any active session to ensure a clean shutdown
    if session_manager.is_session_active():
        session_manager.end_session()


app = FastAPI(title="Edge Service", lifespan=lifespan)


async def polling_loop():
    """The main data collection loop that runs in the background."""
    while session_manager.is_session_active():
        session_id = session_manager.get_session_id()
        iccid = session_manager.get_iccid()

        modem_data = poller.get_modem_status()

        if modem_data:
            # You'll need to parse the actual JSON response.
            # Example: data = parse_modem_data(modem_data)

            db_client.write_state_metrics(session_id, iccid, modem_data)

        await asyncio.sleep(1.0)


@app.post("/session/start")
async def start_session(background_task_runner: BackgroundTasks):
    if session_manager.is_session_active():
        raise HTTPException(status_code=400, detail="Session is already active.")

    # Generate a unique ID for this session
    session_id = f"flight-{uuid.uuid4()}"

    # You would also get the active SIM ICCID here from Teltonika API
    iccid = "8944100000000000001F"  # Placeholder

    session_manager.start_new_session(session_id, iccid)

    # Start the polling_loop as a background task
    task = asyncio.create_task(polling_loop())
    background_tasks["polling_task"] = task

    return {"message": "Measurement session started", "session_id": session_id, "iccid": iccid}


@app.post("/session/end")
async def end_session():
    if not session_manager.is_session_active():
        raise HTTPException(status_code=400, detail="No active session to end.")

    session_manager.end_session()

    # Stop the background task
    if "polling_task" in background_tasks:
        background_tasks["polling_task"].cancel()
        del background_tasks["polling_task"]

    return {"message": "Measurement session ended."}


@app.get("/status")
def get_status():
    state = session_manager.get_session_state()
    if state:
        return state
    return {"is_active": False, "session_id": None, "iccid": None}
