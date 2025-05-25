import pandas as pd
import re
from rapidfuzz import process, fuzz

# Load CSV of past game names
df = pd.read_csv(r"D:\dev\fix-life\activity\datasets\games_all_platforms.csv")
game_names = df['title'].str.lower().tolist()

# Preprocessing function
def preprocess_name(name):
    name = name.lower()
    name = name.replace(".exe", "")
    name = name.replace("_", " ")
    name = name.replace("-", " ")
    name = re.sub(r'\b(win64|shipping|x64|x86|release|debug)\b', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

# Apply preprocessing to dataset names
game_names = [preprocess_name(name) for name in game_names]

def find_similar_games(query_name, limit=5, score_cutoff=70):
    query_name = preprocess_name(query_name)
    results = process.extract(
        query_name,
        game_names,
        scorer=fuzz.WRatio ,  # more lenient for substring-like matches
        limit=limit,
        score_cutoff=score_cutoff
    )
    return results

# Example usage
new_process = "ACUnity.exe"
matches = find_similar_games(new_process)

print(f"Top matches for '{new_process}':")
for match_name, score, _ in matches:
    print(f"{match_name} (score: {score})")
