import subprocess
import re
import psutil
import json
from sentence_transformers import SentenceTransformer, util

from process_games_dataset import get_game_names

# Load game titles
GAME_TITLES = get_game_names()

# Heuristic keywords that hint it's a game
GAME_KEYWORDS = ['game', 'steam', 'crack', 'repack', 'gog', 'epic', 'valve', 'launcher']

# Initialize model
model = SentenceTransformer("all-MiniLM-L6-v2")
game_embeddings = model.encode(GAME_TITLES, convert_to_tensor=True)

def is_similar_game(exe_name):
    exe_clean = re.sub(r'[_\-\.]', ' ', exe_name.lower())
    query_embedding = model.encode(exe_clean, convert_to_tensor=True)
    cosine_scores = util.cos_sim(query_embedding, game_embeddings)
    top_score = cosine_scores.max().item()
    top_match = GAME_TITLES[cosine_scores.argmax().item()]

    if top_score >= 0.70:
        return ("match", top_match, round(top_score, 2))
    elif any(keyword in exe_clean for keyword in GAME_KEYWORDS):
        return ("heuristic", None, round(top_score, 2))
    else:
        return ("unknown", None, round(top_score, 2))

def get_running_exes():
    exes = []
    for proc in psutil.process_iter(['name']):
        try:
            name = proc.info['name']
            if name:
                exes.append(name.lower())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return list(set(exes))  # deduplicate

def get_windows_processes():
    cmd = [
        "powershell.exe",
        "Get-Process | Select-Object Name,Path | ConvertTo-Json"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    data = data if isinstance(data, list) else [data]
    
    # Prepare a list of executable names
    exes = set()
    for proc in data:
        if 'Name' in proc and 'Path' in proc:
            exe_name = proc['Name'] + ('.exe' if not proc['Name'].endswith('.exe') else '')
            exes.add(exe_name)
    
    return list(exes)


if __name__ == "__main__":
    exes = get_windows_processes()

    for exe in exes:
        result, match, score = is_similar_game(exe)
        if result == "match":
            print(f"[MATCH ✅] {exe} → {match} (score={score})")
        elif result == "heuristic":
            print(f"[HEURISTIC 🤖] {exe} might be a game (score={score})")
        else:
            print(f"[ASK USER ❓] Is '{exe}' a game? (score={score})")
