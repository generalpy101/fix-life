import subprocess
import time
import datetime

# List of games to track (add your games here)
GAMES = {
    "VALORANT.exe": 100,   # 1 hour in seconds
    "cs2.exe": 1800,        # 30 mins
    "steam.exe": 2700       # 45 mins
}

# Time tracking for each game
usage = {game: 0 for game in GAMES}
reminder_interval = 60  # seconds after limit to repeat notification

# Reminder tracking
last_reminder = {game: None for game in GAMES}

def get_running_windows_processes():
    result = subprocess.run(["tasklist.exe"], capture_output=True, text=True)
    return result.stdout

def is_game_running(tasklist_output, game):
    return game.lower() in tasklist_output.lower()

def notify_user(game):
    message = f"{game} has exceeded the time limit! Please stop playing."
    powershell_cmd = (
        "[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null; "
        f"[System.Windows.Forms.MessageBox]::Show('{message}', 'Game Tracker Alert', 'OK', 'Warning')"
    )
    subprocess.run(["powershell.exe", "-Command", powershell_cmd])


def kill_game(game):
    subprocess.run(["taskkill.exe", "/F", "/IM", game], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    print("[*] Game time tracker started...")
    while True:
        tasklist = get_running_windows_processes()

        for game, limit in GAMES.items():
            if is_game_running(tasklist, game):
                usage[game] += 5
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {game} running: {usage[game]}s")

                if usage[game] >= limit:
                    now = time.time()

                    # Send reminders every 1 min
                    if last_reminder[game] is None or now - last_reminder[game] >= reminder_interval:
                        notify_user(game)
                        last_reminder[game] = now

                    # Optional: kill game
                    # kill_game(game)
                    # print(f"[!] Killed {game} due to time limit.")

            else:
                # Reset reminder if game is closed
                last_reminder[game] = None

        time.sleep(5)

if __name__ == "__main__":
    main()
