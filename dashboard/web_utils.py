import psutil
from typing import List


def convert_seconds_to_human_readable(seconds: int) -> str:
    """
    Convert seconds to a human-readable format (HH:MM:SS).

    Args:
        seconds (int): The number of seconds to convert.

    Returns:
        str: A string in the format HH:MM:SS.
    """
    if seconds < 0:
        return "00:00:00"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60

    return f"{hours:02}:{minutes:02}:{remaining_seconds:02}"


def convert_seconds_to_human_readable_extended(seconds: int) -> str:
    """
    Convert seconds to a human-readable format (HH:MM:SS).

    Args:
        seconds (int): The number of seconds to convert.

    Returns:
        str: A string in the format HH:MM:SS.
    """
    if seconds <= 0:
        return "00:00:00"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60

    return f"{hours} hours, {minutes} minutes, {remaining_seconds} seconds"


def check_if_processes_running(exe_names: List[str]) -> dict[str, bool]:
    running_exes = {exe_name: False for exe_name in exe_names}
    running_processes = psutil.process_iter(["name", "exe"])
    # Create a set of running process names for quick lookup
    for process in running_processes:
        try:
            if process.name() in exe_names:
                running_exes[process.name()] = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return running_exes
