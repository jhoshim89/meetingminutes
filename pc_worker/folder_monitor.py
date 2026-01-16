"""
Folder Monitor Module
Monitors a directory for new audio files and triggers processing automatically.
Uses watchdog library for efficient file system event monitoring.
"""

import asyncio
import time
from pathlib import Path
from typing import Callable, Optional, Awaitable
from threading import Event

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

from logger import get_logger
from config import (
    WATCH_FOLDER_PATH,
    AUDIO_EXTENSIONS,
    FILE_STABLE_CHECK_INTERVAL,
    FILE_STABLE_CHECK_COUNT
)

logger = get_logger("folder_monitor", level="INFO")


class AudioFileHandler(FileSystemEventHandler):
    """
    File system event handler for audio files.
    Filters events to only process audio file creation.
    """

    def __init__(
        self,
        on_file_ready: Callable[[Path], Awaitable[None]],
        extensions: list[str],
        event_loop: asyncio.AbstractEventLoop
    ):
        """
        Initialize audio file handler.

        Args:
            on_file_ready: Async callback function to call when file is ready
            extensions: List of file extensions to monitor (e.g., ['.m4a', '.wav'])
            event_loop: Event loop to schedule async callbacks
        """
        super().__init__()
        self.on_file_ready = on_file_ready
        self.extensions = [ext.lower() for ext in extensions]
        self.event_loop = event_loop
        self.processing_files = set()  # Track files currently being processed

    def on_created(self, event: FileCreatedEvent):
        """
        Handle file creation events.

        Args:
            event: File system event
        """
        # Ignore directory creation events
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Check if file has valid audio extension
        if file_path.suffix.lower() not in self.extensions:
            logger.debug(f"Ignoring non-audio file: {file_path.name}")
            return

        # Check if already processing this file
        if str(file_path) in self.processing_files:
            logger.debug(f"Already processing file: {file_path.name}")
            return

        logger.info(f"New audio file detected: {file_path.name}")

        # Mark as processing
        self.processing_files.add(str(file_path))

        # Schedule async file stability check and processing
        asyncio.run_coroutine_threadsafe(
            self._handle_new_file(file_path),
            self.event_loop
        )

    async def _handle_new_file(self, file_path: Path):
        """
        Handle new file detection with stability check.

        Args:
            file_path: Path to the new audio file
        """
        try:
            # Wait for file to be completely written
            if await self._wait_for_file_stable(file_path):
                logger.info(
                    f"File ready for processing: {file_path.name}",
                    size_mb=f"{file_path.stat().st_size / (1024*1024):.2f}"
                )

                # Trigger callback
                await self.on_file_ready(file_path)
            else:
                logger.warning(f"File did not stabilize: {file_path.name}")
        except Exception as e:
            logger.error(
                f"Error handling file {file_path.name}: {e}",
                exc_info=True
            )
        finally:
            # Remove from processing set
            self.processing_files.discard(str(file_path))

    async def _wait_for_file_stable(self, file_path: Path) -> bool:
        """
        Wait for file size to stabilize (file copy/write complete).

        Checks file size multiple times with intervals to ensure
        the file is completely written before processing.

        Args:
            file_path: Path to check

        Returns:
            True if file is stable, False if timeout or error
        """
        stable_checks = 0
        previous_size = -1
        max_wait_time = 300  # 5 minutes maximum wait
        start_time = time.time()

        while stable_checks < FILE_STABLE_CHECK_COUNT:
            # Check timeout
            if time.time() - start_time > max_wait_time:
                logger.warning(
                    f"File stability check timeout: {file_path.name}",
                    elapsed=f"{time.time() - start_time:.2f}s"
                )
                return False

            try:
                # Check if file still exists
                if not file_path.exists():
                    logger.warning(f"File disappeared during stability check: {file_path.name}")
                    return False

                current_size = file_path.stat().st_size

                # Check if size changed
                if current_size == previous_size and current_size > 0:
                    stable_checks += 1
                    logger.debug(
                        f"File size stable ({stable_checks}/{FILE_STABLE_CHECK_COUNT}): "
                        f"{file_path.name} - {current_size / (1024*1024):.2f} MB"
                    )
                else:
                    # Size changed, reset counter
                    stable_checks = 0
                    logger.debug(
                        f"File size changed: {file_path.name} - "
                        f"{previous_size} -> {current_size} bytes"
                    )

                previous_size = current_size

                # Wait before next check
                if stable_checks < FILE_STABLE_CHECK_COUNT:
                    await asyncio.sleep(FILE_STABLE_CHECK_INTERVAL)

            except Exception as e:
                logger.error(
                    f"Error checking file stability for {file_path.name}: {e}",
                    exc_info=True
                )
                return False

        return True


class FolderMonitor:
    """
    Folder monitor for automatic audio file processing.
    Monitors a directory for new audio files and triggers processing callbacks.
    """

    def __init__(
        self,
        watch_path: str,
        on_file_ready: Callable[[Path], Awaitable[None]],
        extensions: Optional[list[str]] = None
    ):
        """
        Initialize folder monitor.

        Args:
            watch_path: Directory path to monitor
            on_file_ready: Async callback function when file is ready for processing
            extensions: List of file extensions to monitor (defaults to AUDIO_EXTENSIONS)

        Raises:
            ValueError: If watch_path is empty or does not exist
        """
        if not watch_path:
            raise ValueError("watch_path cannot be empty")

        self.watch_path = Path(watch_path)

        if not self.watch_path.exists():
            raise ValueError(f"Watch path does not exist: {watch_path}")

        if not self.watch_path.is_dir():
            raise ValueError(f"Watch path is not a directory: {watch_path}")

        self.on_file_ready = on_file_ready
        self.extensions = extensions or AUDIO_EXTENSIONS

        self.observer: Optional[Observer] = None
        self.event_handler: Optional[AudioFileHandler] = None
        self.event_loop: Optional[asyncio.AbstractEventLoop] = None
        self.is_running = False
        self._stop_event = Event()

        logger.info(
            f"Folder monitor initialized",
            watch_path=str(self.watch_path),
            extensions=self.extensions
        )

    async def start(self):
        """
        Start monitoring the folder.
        Creates observer thread and begins watching for file events.
        """
        if self.is_running:
            logger.warning("Folder monitor is already running")
            return

        try:
            # Get current event loop
            self.event_loop = asyncio.get_running_loop()

            # Create event handler with callback
            self.event_handler = AudioFileHandler(
                on_file_ready=self.on_file_ready,
                extensions=self.extensions,
                event_loop=self.event_loop
            )

            # Create and start observer
            self.observer = Observer()
            self.observer.schedule(
                self.event_handler,
                path=str(self.watch_path),
                recursive=False  # Don't watch subdirectories
            )
            self.observer.start()

            self.is_running = True
            self._stop_event.clear()

            logger.info(
                f"Folder monitoring started",
                path=str(self.watch_path)
            )

        except Exception as e:
            logger.error(f"Failed to start folder monitor: {e}", exc_info=True)
            raise

    async def stop(self):
        """
        Stop monitoring the folder.
        Gracefully shuts down observer thread.
        """
        if not self.is_running:
            logger.warning("Folder monitor is not running")
            return

        try:
            logger.info("Stopping folder monitor...")

            self.is_running = False
            self._stop_event.set()

            if self.observer:
                self.observer.stop()
                self.observer.join(timeout=10)
                self.observer = None

            self.event_handler = None
            self.event_loop = None

            logger.info("Folder monitor stopped")

        except Exception as e:
            logger.error(f"Error stopping folder monitor: {e}", exc_info=True)
            raise

    def is_monitoring(self) -> bool:
        """
        Check if monitor is currently running.

        Returns:
            True if monitoring is active
        """
        return self.is_running and self.observer is not None and self.observer.is_alive()

    async def wait_for_shutdown(self):
        """
        Wait for monitor to be stopped.
        Useful for keeping monitor running until explicit shutdown.
        """
        while self.is_running:
            await asyncio.sleep(1)


def get_folder_monitor(
    watch_path: str,
    on_file_ready: Callable[[Path], Awaitable[None]],
    extensions: Optional[list[str]] = None
) -> FolderMonitor:
    """
    Factory function to create a folder monitor instance.

    Args:
        watch_path: Directory path to monitor
        on_file_ready: Async callback function when file is ready
        extensions: List of file extensions to monitor

    Returns:
        Configured FolderMonitor instance
    """
    return FolderMonitor(
        watch_path=watch_path,
        on_file_ready=on_file_ready,
        extensions=extensions
    )


# Example usage
async def example_callback(file_path: Path):
    """Example callback function for testing"""
    logger.info(f"Processing file: {file_path.name}")
    # Add your processing logic here


async def main():
    """Example main function for testing the monitor"""
    if not WATCH_FOLDER_PATH:
        logger.error("WATCH_FOLDER_PATH not configured in .env")
        return

    monitor = get_folder_monitor(
        watch_path=WATCH_FOLDER_PATH,
        on_file_ready=example_callback
    )

    try:
        await monitor.start()
        logger.info("Folder monitor running. Press Ctrl+C to stop.")
        await monitor.wait_for_shutdown()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await monitor.stop()


if __name__ == "__main__":
    asyncio.run(main())
