import asyncio
import logging

import asyncssh

from app.config import get_settings


class SSHClientManager:
    """Manages a persistent, shared asyncssh connection."""

    def __init__(self):
        self._connection: asyncssh.SSHClientConnection | None = None
        self._lock = asyncio.Lock()

    async def connect(self):
        """Establishes the SSH connection if not already connected."""
        async with self._lock:
            if self._connection and not self._connection.is_closed():
                return

            settings = get_settings().teltonika
            logging.info(f"Establishing SSH connection to {settings.ip}...")
            try:
                self._connection = await asyncssh.connect(
                    host=settings.ip,
                    port=22,
                    username=settings.ssh_user,
                    password=settings.password.get_secret_value(),
                    known_hosts=None,
                )
                logging.info("SSH connection established successfully.")
            except Exception:
                logging.exception("Failed to establish SSH connection.")
                self._connection = None

    async def disconnect(self):
        """Closes the SSH connection."""
        async with self._lock:
            if self._connection:
                self._connection.close()
                await self._connection.wait_closed()
                logging.info("SSH connection closed.")
                self._connection = None

    async def execute_command(self, command: str, timeout: int = 30) -> str | None:
        """Executes a command over the shared SSH connection."""
        if not self._connection or self._connection.is_closed():
            await self.connect()
        if not self._connection:
            return None

        try:
            result = await self._connection.run(command, check=True, timeout=timeout)
            if isinstance(result.stdout, bytes):
                return result.stdout.decode("utf-8")
            else:
                return result.stdout  # type: ignore
        except Exception:
            logging.exception(f"An unexpected error occurred executing SSH command: {command}")
            self._connection = None  # Assume connection is bad
            return None


ssh_client = SSHClientManager()
