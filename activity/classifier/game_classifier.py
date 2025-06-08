import os
import pickle
import re
import sys
from typing import List

import psutil
from psutil import Process
from rapidfuzz import fuzz, process

from activity.classifier.heuristic_classify import HeuristicClassifier
from data import DB
from log_utils import get_logger

logger = get_logger("classifier", "classifier.log")

# Heuristic keywords that hint it's a game
GAME_KEYWORDS = ["game", "steam", "crack", "repack", "gog", "epic", "valve", "launcher"]

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))


class GamesClassifier:
    def __init__(self):
        self.db = DB()

        logger.info("Loading game titles and embeddings...")
        # Load game titles from pickle file or dataset
        if not os.path.exists(os.path.join(CURRENT_DIR, "game_names.pkl")):
            logger.info("No precomputed game names found. Loading from dataset...")
            # Set some default game titles
            self.game_titles = [
                "Counter-Strike: Global Offensive",
                "Dota 2",
                "The Witcher 3: Wild Hunt",
                "Cyberpunk 2077",
                "Half-Life 2",
                "Portal 2",
                "Stardew Valley",
                "Terraria",
                "Hades",
                "Celeste",
            ]
        else:
            logger.info("Loading precomputed game names from pickle file...")
            with open(os.path.join(CURRENT_DIR, "game_names.pkl"), "rb") as f:
                self.game_titles = pickle.load(f)

        logger.info(f"Loaded {len(self.game_titles)} game titles from dataset.")

    def classify(self, exes=[]):  # pylint: disable=dangerous-default-value
        if exes is None or len(exes) == 0:
            exes = self.get_windows_processes()

        classifier = HeuristicClassifier(exes)

        for exe in exes:
            try:
                is_game = False
                process_name = exe.name()
                # If already in database, skip
                already_classified = self.db.get_is_present(process_name)

                if already_classified is True:
                    logger.info(f"[SKIP] {process_name} already classified")
                    continue

                result, match, score = self.is_similar_game(process_name)
                if result == "match":
                    logger.info(f"[MATCH ✅] {exe} → {match} (score={score})")
                    is_game = True
                elif result == "heuristic":
                    logger.info(f"[HEURISTIC 🤖] {exe} might be a game (score={score})")
                else:
                    pass

                # Run heuristic classifier to be sure
                label, heuristic_score = classifier.classify_process(exe)
                if label == "game":
                    logger.info(
                        f"[HEURISTIC CLASSIFIER ✅] {exe} classified as game (score={heuristic_score:.2f})"
                    )
                    is_game = True
                else:
                    logger.info(
                        f"[HEURISTIC CLASSIFIER ❌] {exe} classified as {label} (score={heuristic_score:.2f})"
                    )
                    is_game = False  # To avoid false positives

                self.db.upsert_is_game(process_name, is_game, user_marked=0)
            except Exception as e:
                logger.info(f"Error classifying {process_name}: {e}")
                import traceback  # pylint: disable=import-outside-toplevel

                traceback.print_exc(file="classifier_error.log")
                sys.exit(1)

    def is_similar_game(self, exe_name, limit=5, score_cutoff=70):
        exe_clean = re.sub(r"[_\-\.]", " ", exe_name.lower().replace(".exe", ""))
        results = process.extract(
            exe_clean,
            self.game_titles,
            scorer=fuzz.WRatio,  # more lenient for substring-like matches
            limit=limit,
            score_cutoff=score_cutoff,
        )
        top_match = None
        top_score = 0.0

        for match, score, _ in results:
            if score > top_score:
                top_match = match
                top_score = score

        if top_score >= 0.75:
            return ("match", top_match, round(top_score, 2))

        if any(keyword in exe_clean for keyword in GAME_KEYWORDS):
            return ("heuristic", None, round(top_score, 2))

        return ("unknown", None, round(top_score, 2))

    def is_game(self, process_name: psutil.Process) -> bool:
        """
        Check if the given executable name is classified as a game.
        """
        if not process_name or not isinstance(process_name, psutil.Process):
            raise ValueError(
                "Invalid process provided. Must be a psutil.Process instance."
            )
        exe_name = process_name.name()
        if not exe_name:
            return False
        return self.db.get_is_game(exe_name)

    def get_windows_processes(self) -> List[Process]:
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


if __name__ == "__main__":
    logger.info("Classifying running processes...")
    classifier = GamesClassifier()

    classifier.classify()
