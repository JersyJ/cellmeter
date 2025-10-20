# app/main.py
import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException
from contextlib import asynccontextmanager
import uuid

from . import poller, influx_client, session_manager

# This dictionary will hold our background polling task
background_tasks = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup, authenticate with Teltonika
    poller.get_teltonika_token()
    yield
    # On shutdown, clean up tasks
    if "polling_task" in background_tasks:
        background_tasks["polling_task"].cancel()

app = FastAPI(lifespan=lifespan)

async def polling_loop():
    """The main data collection loop that runs in the background."""
    while session_manager.is_session_active():
        session_id = session_manager.get_session_id()
        iccid = session_manager.get_iccid()
        
        modem_data = poller.get_modem_status()
        
        if modem_data:
            # You'll need to parse the actual JSON response.
            # Example: data = parse_modem_data(modem_data)
            
            # 2. Write to InfluxDB
            influx_client.write_state_metrics(session_id, iccid, modem_data)
        
        await asyncio.sleep(1)

# --- API Endpoints ---
@app.post("/session/start")
async def start_session(background_task_runner: BackgroundTasks):
    if session_manager.is_session_active():
        raise HTTPException(status_code=400, detail="Session is already active.")

    # Generate a unique ID for this session
    session_id = f"flight-{uuid.uuid4()}"
    
    # You would also get the active SIM ICCID here from Teltonika API
    iccid = "8944100000000000001F" # Placeholder
    
    session_manager.start_new_session(session_id, iccid)

    # Start the polling_loop as a background task
    task = asyncio.create_task(polling_loop())
    background_tasks["polling_task"] = task
    
    return {"message": "Measurement session started", "session_id": session_id}


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
    return {
        "is_session_active": session_manager.is_session_active(),
        "session_id": session_manager.get_session_id()
    }