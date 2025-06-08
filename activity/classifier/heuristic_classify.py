import time
from typing import List

import psutil
import pygetwindow as gw
import pythoncom
import win32gui
import win32process
import wmi
from screeninfo import get_monitors

from log_utils import get_logger

# Static exclusions (false positives)
EXCLUDED_PROCESSES = {
    "chrome.exe",
    "teams.exe",
    "explorer.exe",
    "discord.exe",
    "steam.exe",
}
logger = get_logger("heuristic_classifier", "heuristic_classifier.log")


class HeuristicClassifier:
    SCORE_THRESHOLD = 3.0  # Threshold for classifying a process as a game

    def __init__(
        self,
        process_list: List[psutil.Process],
        exclude: List[str] = EXCLUDED_PROCESSES,
    ):
        self.process_list = process_list
        self.excluded_processes = exclude

    def classify(self, proc):
        return self.classify_process(proc)

    def classify_process(self, proc: psutil.Process):
        """
        Classifies a process as a game or non-game based on heuristic scoring.

        Args:
            proc (psutil.Process): The process to classify.

        Returns:
            tuple: (label, score) where label is 'game' or 'non-game' and score is the heuristic score.
        """
        if proc.name().lower() in self.excluded_processes:
            return "non-game", 0.0
        score = self._heuristic_process_score(proc)
        label = "game" if score >= self.SCORE_THRESHOLD else "non-game"
        return label, score

    def _heuristic_process_score(self, proc: psutil.Process):
        try:
            gpu_usage_map = self._get_gpu_usage_percent()

            cpu = 0
            # Loop for cpu usage
            _ = proc.cpu_percent(interval=None)  # Initial call to get a baseline
            time.sleep(1)  # Sleep to allow CPU usage to be calculated
            cpu = proc.cpu_percent(interval=None)  # Get CPU usage after sleep
            # Get the maximum CPU usage across all cores
            cpu = max(cpu) if isinstance(cpu, list) else cpu
            # If greater than 100, it means the process is using multiple cores
            if cpu > 100:
                cpu = cpu / psutil.cpu_count()
            gpu = gpu_usage_map.get(proc.pid, 0.0)  # Get GPU usage for this process
            mem = proc.memory_info().rss / (1024 * 1024)  # in MB
            exe = proc.exe().lower()
            pid = proc.pid
            score = 0

            if cpu > 15:
                score += 1.5
            elif cpu > 5:
                score += 0.5

            # Keeping single value for GPU for now
            if gpu > 50:
                score += 1.5

            if mem > 700:
                score += 1.5
            elif mem > 300:
                score += 0.5

            if "games" in exe or "steamapps" in exe or "epic" in exe:
                score += 1.0

            if self._check_fullscreen(pid):
                score += 1.0

            return score

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return 0.0

    def _get_gpu_usage_percent(self):
        try:
            pythoncom.CoInitialize()  # pylint: disable=no-member
            w = wmi.WMI(namespace="root\CIMV2")  # pylint: disable=anomalous-backslash-in-string
            gpu_info = w.Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine()
            usage = {}
            for gpu in gpu_info:
                name = gpu.Name
                pid_part = name.split("pid_")[-1].split("_")[0]
                try:
                    pid = int(pid_part)
                except ValueError:
                    continue
                usage[pid] = usage.get(pid, 0.0) + float(gpu.UtilizationPercentage)
            return usage  # {pid: gpu_percent, ...}
        except Exception as e:
            logger.error(f"[GPU-WMI] Error: {e}")
            return {}

    def _check_fullscreen(self, proc_pid):
        for hwnd in self._get_top_windows():
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid == proc_pid and self._is_fullscreen(hwnd):
                return True
        return False

    def _is_fullscreen(self, hwnd):
        if not win32gui.IsWindowVisible(hwnd):
            return False
        rect = win32gui.GetWindowRect(hwnd)
        width = rect[2] - rect[0]
        height = rect[3] - rect[1]

        for m in get_monitors():
            if abs(width - m.width) < 50 and abs(height - m.height) < 50:
                return True
        return False

    def _get_top_windows(self):
        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                windows.append(hwnd)
            return True

        windows = []
        win32gui.EnumWindows(callback, windows)
        return windows


# Example usage
if __name__ == "__main__":
    all_procs = list(psutil.process_iter(["pid", "name", "exe"]))
    # Remove processes that cannot be accessed
    for proc in all_procs[:]:
        try:
            proc.exe()  # Access the executable path to check permissions
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            all_procs.remove(proc)
    try:
        all_procs = [proc for proc in all_procs if "valorant" in proc.exe().lower()]
        classifier = HeuristicClassifier(all_procs)
        for proc in all_procs:
            label, score = classifier.classify_process(proc)
            if label == "game":
                logger.info(
                    f"Process: {proc.name()}, PID: {proc.pid}, Label: {label}, Score: {score:.2f}"
                )
    except Exception as e:
        logger.error(f"Error during classification: {e}")
        pass
