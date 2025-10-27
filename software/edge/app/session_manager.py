import logging
import sqlite3
import threading

from fastapi import HTTPException

from app.config import get_settings

# Use a thread-local storage for the connection to ensure that
# each thread gets its own connection object.
local = threading.local()


def _get_db_connection() -> sqlite3.Connection:
    """Gets or creates a database connection for the current thread."""
    db = getattr(local, "_db", None)
    if db is None:
        db = sqlite3.connect(get_settings().session_db.path, check_same_thread=False)
        db.row_factory = sqlite3.Row  # Allows accessing columns by name
        local._db = db
    return db


def setup_database() -> None:
    """
    Initializes the database and creates the session table if it doesn't exist.
    This function should be called once when the FastAPI application starts.
    """
    conn = _get_db_connection()
    cursor = conn.cursor()
    # The session table is designed to hold ONLY ONE ROW.
    # The 'id' is fixed to 1 with a CHECK constraint to enforce this.
    # This is a robust way to manage a singleton state in a database.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS session (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            session_id TEXT NOT NULL,
            iccid TEXT NOT NULL,
            is_active BOOLEAN NOT NULL CHECK (is_active = 1)
        )
    """)
    conn.commit()
    logging.info("Session database initialized.")


def start_new_session(session_id: str, iccid: str) -> bool:
    """
    Starts a new measurement session by inserting a row into the SQLite DB.

    The table constraints will automatically prevent a new session from starting
    if one is already active, making this operation atomic and safe.

    Returns:
        True if the session was started, False if a session was already active.
    """
    conn = _get_db_connection()
    try:
        # The 'with conn:' block automatically handles transactions.
        # It will COMMIT on success or ROLLBACK on an error.
        with conn:
            conn.execute(
                "INSERT INTO session (id, session_id, iccid, is_active) VALUES (?, ?, ?, ?)",
                (1, session_id, iccid, True),
            )
        logging.info(f"Session '{session_id}' started with ICCID '{iccid}'.")
        return True
    except sqlite3.IntegrityError:
        # This error occurs if we try to INSERT a row with id=1 when one
        # already exists. This is our concurrency-safe way of checking.
        logging.warning("Attempted to start session, but one is already active.")
        raise HTTPException(status_code=400, detail="Session is already active.")


def end_session() -> tuple[str | None, str | None] | None:
    """Ends the current session by deleting the row from the session table."""
    conn = _get_db_connection()
    session_id = get_session_id()  # Get the ID before deleting
    iccid = get_iccid()

    with conn:
        cursor = conn.execute("DELETE FROM session WHERE id = 1")

    if cursor.rowcount > 0:
        logging.info(f"Session '{session_id}' has ended.")
        return session_id, iccid
    else:
        logging.warning("Attempted to end session, but none was active.")
        return None


def _get_session_row() -> sqlite3.Row | None:
    """Helper function to get the current session row if it exists."""
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM session WHERE id = 1")
    return cursor.fetchone()


def is_session_active() -> bool:
    """Checks if a session is active by seeing if a row exists."""
    return _get_session_row() is not None


def get_session_id() -> str | None:
    """Retrieves the session ID from the database."""
    row = _get_session_row()
    return row["session_id"] if row else None


def get_iccid() -> str | None:
    """Retrieves the ICCID from the database."""
    row = _get_session_row()
    return row["iccid"] if row else None


def get_session_state() -> dict | None:
    """Retrieves the entire session state as a dictionary."""
    row = _get_session_row()
    return dict(row) if row else None
