import threading
import webbrowser
from tracker import Tracker
from web import app
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
import sys
import random


class FixItTray:
    def __init__(self):
        self.icon = None
        self.web_app_thread = None
        self.web_app_port = random.randint(
            5001, 50000
        )  # Random port to avoid conflicts

        # Check if the port is available
        def is_port_in_use(port: int) -> bool:
            import socket

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(("localhost", port)) == 0

        while is_port_in_use(self.web_app_port):
            self.web_app_port = random.randint(5001, 50000)
        print(f"Using web app port: {self.web_app_port}")

        print("Initializing Tracker...")
        self.tracker = Tracker()

    def start(self):
        self.tracker.start()
        self.web_app_thread = threading.Thread(
            target=app.app.run,
            kwargs={"port": self.web_app_port, "debug": True, "use_reloader": False},
            daemon=True,
        )
        self.web_app_thread.start()

        print("Web app started on port:", self.web_app_port)

        self.icon = pystray.Icon("GameTracker")
        self.icon.icon = self._create_image()
        self.icon.menu = pystray.Menu(
            item("Open Dashboard", lambda: self._open_dashboard()),
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
        print("Shutting down cleanly...")
        sys.exit(0)

    def _open_dashboard(self):
        webbrowser.open(f"http://localhost:{self.web_app_port}/", new=2)

    def _create_image(self):
        image = Image.new("RGB", (64, 64), "black")
        dc = ImageDraw.Draw(image)
        dc.rectangle((16, 16, 48, 48), fill="white")
        return image

    def _quit_app(self, icon, item):
        self.stop()
        icon.stop()


if __name__ == "__main__":
    tray_app = FixItTray()
    try:
        tray_app.start()
    except KeyboardInterrupt:
        tray_app.stop()
