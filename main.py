import random
import socket
import sys
import threading
import webbrowser

import pystray
from dotenv import load_dotenv
from PIL import Image
from pystray import MenuItem as item

from activity.tracker import Tracker
from dashboard import app
from log_utils import get_logger

load_dotenv()
logger = get_logger("main", "main.log")

ICON_PATH = "./img/icons/fixlife.ico"


class FixItTray:
    def __init__(self):
        self.icon = None
        self.web_app_thread = None
        self.web_app_port = random.randint(
            5001, 50000
        )  # Random port to avoid conflicts

        # Check if the port is available
        def is_port_in_use(port: int) -> bool:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(("localhost", port)) == 0

        while is_port_in_use(self.web_app_port):
            self.web_app_port = random.randint(5001, 50000)
        logger.info(f"Using web app port: {self.web_app_port}")

        logger.info("Initializing Tracker...")
        self.tracker = Tracker()

    def start(self):
        self.tracker.start()
        self.web_app_thread = threading.Thread(
            target=app.app.run,
            kwargs={"port": self.web_app_port, "debug": True, "use_reloader": False},
            daemon=True,
        )
        self.web_app_thread.start()

        logger.info(f"Web app started on port: {self.web_app_port}")

        self.icon = pystray.Icon("GameTracker")
        self.icon.icon = self._create_image()
        self.icon.menu = pystray.Menu(
            item("Open Dashboard", lambda: self._open_dashboard()),  # pylint: disable=unnecessary-lambda
            item("Quit", self._quit_app),
        )
        self.icon.run()

    def stop(self):
        self.tracker.stop()
        if self.icon:
            self.icon.stop()
        if self.web_app_thread and self.web_app_thread.is_alive():
            self.web_app_thread.join(timeout=2)

        # Final cleanup
        logger.info("Shutting down cleanly...")
        sys.exit(0)

    def _open_dashboard(self):
        webbrowser.open(f"http://localhost:{self.web_app_port}/", new=2)

    def _create_image(self):
        image = Image.open(ICON_PATH)
        return image

    def _quit_app(self, icon, *args, **kwargs):  # pylint: disable=unused-argument
        self.stop()
        icon.stop()


if __name__ == "__main__":
    try:
        tray_app = FixItTray()
        tray_app.start()
    except KeyboardInterrupt:
        tray_app.stop()
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"Unexpected error: {e}")
        # Write a traceback to a log file
        import traceback

        with open("error.log", "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        tray_app.stop()
        sys.exit(1)
