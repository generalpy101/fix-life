import subprocess
import threading
import time
from collections import defaultdict
from datetime import datetime
from typing import List

import psutil

from activity import utils
from activity.classifier.game_classifier import GamesClassifier
from data import DB
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
                import traceback  # pylint: disable=import-outside-toplevel

                traceback.print_exc(file="tracker_error.log")

    def update_game_timings(self):
        game_process_cache = {}  # pid -> (name, create_time)
        previous_tick = time.time()

        while not self.stop_event.is_set():
            try:
                self._handle_first_run_today()  # Ensure DB is populated

                exes = utils.get_unique_windows_processes()
                updated_games = self._get_updated_games(exes, game_process_cache, previous_tick)

                for name, duration in updated_games.items():
                    self.db.update_timing_by_duration(name, duration)

                # Cleanup: remove dead PIDs
                live_pids = {exe.pid for exe in exes}
                game_process_cache = {
                    pid: data for pid, data in game_process_cache.items() if pid in live_pids
                }

                previous_tick = time.time()
                time.sleep(self.SLEEP_TIME)

            except Exception as e:
                logger.error(f"[{datetime.now()}] Error updating game timings: {e}")
                import traceback  # pylint: disable=import-outside-toplevel
                traceback.print_exc(file="tracker_error.log")
                break

    def _get_updated_games(self, exes, game_process_cache, previous_tick):
        updated_games = defaultdict(int)
        current_tick = time.time()

        for exe in exes:
            try:
                pid = exe.pid
                name = exe.name()
                create_time = exe.create_time()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

            try:
                if not self.classifier.is_game(exe):
                    continue
            except Exception:
                continue

            now = time.time()

            if pid not in game_process_cache:
                game_process_cache[pid] = (name, create_time)

                existing_time = self.db.get_timing_for_exe(name)
                if existing_time is None or existing_time == 0:
                    backfilled_duration = int(now - create_time)
                    self.db.update_timing_to_a_specific_value(name, backfilled_duration)
                    continue

            updated_time = int(current_tick - previous_tick)
            if updated_time > 0:
                updated_games[name] += updated_time

        return updated_games


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
                # Get current running process names
                running_processes = utils.get_unique_windows_processes()
                running_exe_names = set(
                    proc.name() for proc in running_processes if proc.name()
                )
                violations = self.db.get_games_with_time_violations(
                    running_processes=running_exe_names
                )

                # If the game is running, we can notify the user
                if violations:
                    running_games = self.check_if_processes_running(
                        [v[0] for v in violations]
                    )
                    for game, max_time, _ in violations:
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
                import traceback  # pylint: disable=import-outside-toplevel

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
            ],
            check=False
        )

    def _notify_user_for_violation(self, game_name: str, max_time: int):
        message = f"{game_name} has exceeded the time limit! Please stop playing. Max time: {max_time}"
        subprocess.run(
            [
                "powershell.exe",
                "-Command",
                f"[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null; "
                f"[System.Windows.Forms.MessageBox]::Show("
                f'"{message}", "Game Tracker Alert", '
                f"[System.Windows.Forms.MessageBoxButtons]::OK, "
                f"[System.Windows.Forms.MessageBoxIcon]::Warning)",
            ],
            check=False
        )

    def _handle_first_run_today(self):
        # Populate the DB with initial data if it is first run of the day
        is_data_populated = self.db.get_is_data_populated_today()
        if not is_data_populated:
            logger.info("Populating initial data for today...")
            self.db.populate_data_today()

    def stop(self):
        self.stop_event.set()
        self.classify_thread.join(timeout=2)
        self.update_thread.join(timeout=2)
        self.violation_handler_thread.join(timeout=2)

    def start(self):
        self._handle_first_run_today()
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
