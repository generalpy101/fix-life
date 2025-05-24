import os
import re
import psutil
import pickle
from sentence_transformers import SentenceTransformer, util

from psutil import Process
from typing import List, Tuple

from process_games_dataset import get_game_names
from heuristic_classify import HeuristicClassifier

import sqlite3

# Load game titles
GAME_TITLES = get_game_names()

# Heuristic keywords that hint it's a game
GAME_KEYWORDS = ['game', 'steam', 'crack', 'repack', 'gog', 'epic', 'valve', 'launcher']

# Load precomputed embeddings if available
print("Loading SentenceTransformer model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

print("Loading precomputed embeddings for game titles...")
if os.path.exists("game_embeddings.pkl"):
    with open("game_embeddings.pkl", "rb") as f:
        data = pickle.load(f)
        game_titles = data["titles"]
        game_embeddings = data["embeddings"]
else:
    print("No precomputed embeddings found. Recomputing...")
    game_embeddings = model.encode(GAME_TITLES, show_progress_bar=True)
    with open("game_embeddings.pkl", "wb") as f:
        pickle.dump({
            "titles": GAME_TITLES,
            "embeddings": game_embeddings
        }, f)
    game_titles = GAME_TITLES
    print("✅ Game embeddings saved.")

def is_similar_game(exe_name):
    exe_clean = re.sub(r'[_\-\.]', ' ', exe_name.lower().replace('.exe', ''))
    query_embedding = model.encode(exe_clean)
    cosine_scores = util.cos_sim(query_embedding, game_embeddings)[0]

    top_score = cosine_scores.max().item()
    top_index = cosine_scores.argmax().item()
    top_match = game_titles[top_index]

    if top_score >= 0.75:
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

def get_windows_processes() -> List[Process]:
    processes = list(psutil.process_iter(['pid', 'name', 'exe']))
    
    # Remove all processes we cannot access
    for proc in processes[:]:
        try:
            proc.exe()  # Access the executable path to check permissions
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            processes.remove(proc)
    
    # Make dictionary of processes by executable path
    exes = {}
    for proc in processes:
        exe_path = proc.info['exe']
        if exe_path and exe_path not in exes:
            exes[exe_path] = proc
    
    # Convert dictionary values to a list. This was done to remove duplicates
    exes = list(exes.values())
    
    return exes

if __name__ == "__main__":
    # Connect with SQLite database
    conn = sqlite3.connect('./games.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS games (name TEXT PRIMARY KEY, is_game INTEGER)')
    conn.commit()
    
    exes = get_windows_processes()
    classifier = HeuristicClassifier(exes)

    for exe in exes:
        is_game = False
        process_name = exe.name()
        # If already in database, skip
        cursor.execute('SELECT is_game FROM games WHERE name = ?', (process_name,))
        row = cursor.fetchone()
        if row is not None:
            print(f"[SKIP] {process_name} already classified as {'game' if row[0] else 'not game'}")
            continue
        result, match, score = is_similar_game(process_name)
        if result == "match":
            print(f"[MATCH ✅] {exe} → {match} (score={score})")
            is_game = True
        elif result == "heuristic":
            print(f"[HEURISTIC 🤖] {exe} might be a game (score={score})")
        else:
            # print(f"[ASK USER ❓] Is '{exe}' a game? (score={score})")
            pass
        
        # Run heuristic classifier to be sure
        label, heuristic_score = classifier.classify_process(exe)
        if label == "game":
            print(f"[HEURISTIC CLASSIFIER ✅] {exe} classified as game (score={heuristic_score:.2f})")
            is_game = True
        else:
            print(f"[HEURISTIC CLASSIFIER ❌] {exe} classified as {label} (score={heuristic_score:.2f})")
            is_game = False # To avoid false positives
        
        # Insert into database
        cursor.execute('INSERT OR REPLACE INTO games (name, is_game) VALUES (?, ?)', 
                       (process_name, int(is_game)))
    conn.commit()
    conn.close()