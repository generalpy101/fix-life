import sys
import os
import threading
import time
import psutil
from psutil import Process
from typing import List
from datetime import datetime
from collections import defaultdict

import subprocess


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tracker.classifier.classifier import GamesClassifier
from db import DB
import utils
from log_utils import get_logger

logger = get_logger("tracker", "tracker.log")


class Tracker:
    SLEEP_TIME = 2
    CLASSIFY_INTERVAL = 60  # seconds
    VIOLATION_COUNT_LIMIT = 3

    def __init__(self):
        self.classifier = GamesClassifier()
        self.db = DB()
        self.stop_event = threading.Event()

        # Initialize set with already classified exe names
        self.seen_process_names = set(self.db.get_all_classified_processes())

        self.classify_thread = threading.Thread(
            target=self.classify_new_processes, daemon=True
        )
        self.update_thread = threading.Thread(
            target=self.update_game_timings, daemon=True
        )
        self.violation_handler_thread = threading.Thread(
            target=self.check_and_handle_timing_violations, daemon=True
        )

    def classify_new_processes(self):
        while not self.stop_event.is_set():
            try:
                exes = utils.get_unique_windows_processes()
                new_exes = [
                    exe for exe in exes if exe.name() not in self.seen_process_names
                ]

                if new_exes:
                    self.classifier.classify(
                        exes=new_exes
                    )  # This should save classification results to DB
                    for exe in new_exes:
                        self.seen_process_names.add(exe.name())

                    logger.info(
                        f"[{datetime.now()}] Classified {len(new_exes)} new processes."
                    )

                time.sleep(self.CLASSIFY_INTERVAL)
            except Exception as e:
                logger.error(f"Error classifying new processes: {e}")
                import traceback

                traceback.print_excf(file="tracker_error.log")

    def update_game_timings(self):
        game_process_cache = {}  # pid -> (name, create_time)

        while not self.stop_event.is_set():
            try:
                exes: List[Process] = utils.get_unique_windows_processes()
                now = time.time()
                updated_games = defaultdict(int)

                for exe in exes:
                    try:
                        pid = exe.pid
                        name = exe.name()
                        create_time = exe.create_time()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue  # Process has exited or is not accessible

                    try:
                        if not self.classifier.is_game(exe):
                            continue
                    except Exception:
                        continue  # Classifier failed, skip

                    # First-time seen process
                    if pid not in game_process_cache:
                        game_process_cache[pid] = (name, create_time)

                        # Check if already logged in DB
                        existing_time = self.db.get_timing_for_exe(name)
                        if existing_time is None or existing_time == 0:
                            # Game was already running when app started — backfill time
                            backfilled_duration = int(now - create_time)
                            self.db.update_timing_to_a_specific_value(
                                name, backfilled_duration
                            )
                            continue  # Avoid double-counting in updated_games

                    # If it's already tracked, increment normally
                    updated_time = updated_games[name] + self.SLEEP_TIME
                    # Also check time since process creation
                    if pid in game_process_cache:
                        _, create_time = game_process_cache[pid]
                        elapsed_time = int(now - create_time)

                        # If difference between elapsed time and updated time is greater than SLEEP_TIME, use elapsed time
                        if elapsed_time > updated_time:
                            updated_time = elapsed_time

                    updated_games[name] = updated_time

                # Batch update game durations
                for name, duration in updated_games.items():
                    self.db.update_timing_by_duration(name, duration)

                # Cleanup: remove dead PIDs from the cache
                live_pids = {exe.pid for exe in exes}
                game_process_cache = {
                    pid: data
                    for pid, data in game_process_cache.items()
                    if pid in live_pids
                }

                time.sleep(self.SLEEP_TIME)

            except Exception as e:
                logger.error(f"[{datetime.now()}] Error updating game timings: {e}")
                import traceback

                traceback.print_exc(file="tracker_error.log")
                break

    def check_if_processes_running(self, exe_names: List[str]) -> List[str]:
        running_exes = []
        for process in psutil.process_iter(["name"]):
            if process.info["name"] in exe_names:
                running_exes.append(process.info["name"])
        return running_exes

    def check_and_handle_timing_violations(self):
        """
        Check if any game has exceeded its time limit and handle notifications.
        This method should be called periodically, every 5 seconds or so, to check for timing violations.
        """
        while not self.stop_event.is_set():
            try:
                violations = self.db.get_games_with_time_violations()

                # If the game is running, we can notify the user
                if violations:
                    running_games = self.check_if_processes_running(
                        [v[0] for v in violations]
                    )
                    for game, max_time, notify_limit in violations:
                        if game in running_games:
                            current_time = self.db.get_timing_for_exe(game)
                            violation_count = self.db.get_violation_count_for_exe(game)

                            if (
                                current_time >= max_time
                                and violation_count < self.VIOLATION_COUNT_LIMIT
                            ):
                                self._notify_user_for_violation(game, max_time)
                            elif violation_count >= self.VIOLATION_COUNT_LIMIT:
                                # Kill the process if it has exceeded the violation limit
                                for proc in psutil.process_iter(["name"]):
                                    if proc.info["name"] == game:
                                        logger.warning(
                                            f"Killing process {game} for exceeding violation limit."
                                        )
                                        proc.kill()
                                self._notify_user_for_process_kill(game)

            except Exception as e:
                logger.error(f"Error checking timing violations: {e}")
                import traceback

                traceback.print_exc(file="tracker_error.log")
            time.sleep(10)  # Check every 10 seconds

    def _notify_user_for_process_kill(self, game_name: str):
        message = f"{game_name} has been running for too long, it was killed."
        subprocess.run(
            [
                "powershell.exe",
                "-Command",
                f"[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null; "
                f"[System.Windows.Forms.MessageBox]::Show("
                f'"{message}", "Game Tracker Alert", '
                f"[System.Windows.Forms.MessageBoxButtons]::OK, "
                f"[System.Windows.Forms.MessageBoxIcon]::Error)",
            ]
        )

    def _notify_user_for_violation(self, game_name: str, max_time: int):
        message = f"{game_name} has exceeded the time limit! Please stop playing."
        subprocess.run(
            [
                "powershell.exe",
                "-Command",
                f"[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null; "
                f"[System.Windows.Forms.MessageBox]::Show("
                f'"{message}", "Game Tracker Alert", '
                f"[System.Windows.Forms.MessageBoxButtons]::OK, "
                f"[System.Windows.Forms.MessageBoxIcon]::Warning)",
            ]
        )

    def stop(self):
        self.stop_event.set()
        self.classify_thread.join(timeout=2)
        self.update_thread.join(timeout=2)
        self.violation_handler_thread.join(timeout=2)

    def start(self):
        self.update_thread.start()
        self.classify_thread.start()
        self.violation_handler_thread.start()


if __name__ == "__main__":
    tracker = Tracker()
    logger.info("Game tracker started. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping game tracker...")
        tracker.stop()
        logger.info("Game tracker stopped.")
