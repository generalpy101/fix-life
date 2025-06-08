from typing import List

import psutil


def get_unique_windows_processes() -> List[psutil.Process]:
    processes = list(psutil.process_iter(["pid", "name", "exe"]))

    # Remove all processes we cannot access
    for proc in processes[:]:
        try:
            proc.exe()  # Access the executable path to check permissions
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            processes.remove(proc)

    # Make dictionary of processes by executable path
    exes = {}
    for proc in processes:
        exe_path = proc.info["exe"]
        if exe_path and exe_path not in exes:
            exes[exe_path] = proc

    # Convert dictionary values to a list. This was done to remove duplicates
    exes = list(exes.values())

    return exes
