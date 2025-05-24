import subprocess
import json

def get_windows_processes():
    cmd = [
        "powershell.exe",
        "Get-Process | Where-Object {$_.Path -ne $null} | Select-Object Name,Path | ConvertTo-Json"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    return data if isinstance(data, list) else [data]

procs = get_windows_processes()
for proc in procs:
    print(proc)
    exit()