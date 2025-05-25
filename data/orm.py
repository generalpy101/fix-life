import sqlite3
import os
import threading
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "game_tracker.db")
_LOCK = threading.Lock()

DEFAULT_TIME_LIMIT = 60  # Default time limit for games in minutes
DEFAULT_GLOBAL_TIMING_LIMIT = 60  # Default global timing limit in minutes


class DB:
    def __init__(self, path=DB_PATH):
        self.path = path
        self._ensure_db()

    def _connect(self):
        return sqlite3.connect(self.path, check_same_thread=False)

    def _ensure_db(self):
        """Create tables if not exists."""
        with self._connect() as conn:
            c = conn.cursor()
            c.execute(
                """CREATE TABLE IF NOT EXISTS is_game (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exe_name TEXT UNIQUE,
                is_game INTEGER DEFAULT 0,
                user_marked INTEGER DEFAULT 0
            )"""
            )

            c.execute(
                """CREATE TABLE IF NOT EXISTS timings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exe_name TEXT,
                date TEXT,
                duration INTEGER DEFAULT 0,
                PRIMARY KEY (exe_name, date)
            )"""
            )

            c.execute(
                """CREATE TABLE IF NOT EXISTS violations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exe_name TEXT,
                timestamp TEXT,
                reason TEXT
            )"""
            )

            c.execute(
                """CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )"""
            )

            c.execute(
                """CREATE TABLE IF NOT EXISTS daily_usage (
                date TEXT PRIMARY KEY,
                total_time INTEGER DEFAULT 0
            )"""
            )

            # Timing settings
            c.execute(
                """CREATE TABLE IF NOT EXISTS timing_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exe_name TEXT UNIQUE,
                max_time INTEGER DEFAULT 0,
                notify_limit INTEGER DEFAULT 0
            )"""
            )
            
            # Check if is_data_populated_today table exists, if not create it
            c.execute('''
                CREATE TABLE IF NOT EXISTS is_data_populated_today (
                    date TEXT PRIMARY KEY,
                    is_populated INTEGER
                )
            ''')

            conn.commit()

    def upsert_is_game(self, exe_name, is_game, user_marked=0):
        with _LOCK, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO is_game (exe_name, is_game, user_marked)
                VALUES (?, ?, ?)
                ON CONFLICT(exe_name) DO UPDATE SET
                is_game=excluded.is_game, user_marked=excluded.user_marked
            """,
                (exe_name, int(is_game), int(user_marked)),
            )
            # If is a game, add time limit setting entry for it
            if is_game:
                conn.execute(
                    """
                    INSERT INTO timing_settings (exe_name, max_time, notify_limit)
                    VALUES (?, 60, 0)
                    ON CONFLICT(exe_name) DO NOTHING
                """,
                    (exe_name,),
                )
            else:
                # If not a game, remove any existing timing settings for it
                conn.execute(
                    """
                    DELETE FROM timing_settings WHERE exe_name = ?
                """,
                    (exe_name,),
                )
            conn.commit()
    
    def get_game_names(self):
        with _LOCK, self._connect() as conn:
            rows = conn.execute("SELECT exe_name FROM is_game WHERE is_game = 1").fetchall()
            return [row[0] for row in rows]

    def get_is_game(self, exe_name):
        with _LOCK, self._connect() as conn:
            row = conn.execute(
                "SELECT is_game FROM is_game WHERE exe_name = ?", (exe_name,)
            ).fetchone()
            return bool(row[0]) if row else False

    def get_is_present(self, exe_name):
        with _LOCK, self._connect() as conn:
            row = conn.execute(
                "SELECT exe_name FROM is_game WHERE exe_name = ?", (exe_name,)
            ).fetchone()
            return row is not None

    def update_timing_by_duration(self, exe_name, duration):
        date = datetime.now().date().isoformat()
        with _LOCK, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO timings (exe_name, date, duration)
                VALUES (?, ?, ?)
                ON CONFLICT(exe_name, date) DO UPDATE SET
                duration = duration + excluded.duration
            """,
                (exe_name, date, duration),
            )
            conn.execute(
                """
                INSERT INTO daily_usage (date, total_time)
                VALUES (?, ?)
                ON CONFLICT(date) DO UPDATE SET
                total_time = total_time + excluded.total_time
            """,
                (date, duration),
            )
            conn.commit()

    def update_timing_to_a_specific_value(self, exe_name, value):
        date = datetime.now().date().isoformat()
        with _LOCK, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO timings (exe_name, date, duration)
                VALUES (?, ?, ?)
                ON CONFLICT(exe_name, date) DO UPDATE SET
                duration = excluded.duration
            """,
                (exe_name, date, value),
            )
            conn.execute(
                """
                INSERT INTO daily_usage (date, total_time)
                VALUES (?, ?)
                ON CONFLICT(date) DO UPDATE SET
                total_time = excluded.total_time
            """,
                (date, value),
            )
            conn.commit()

    def get_timing_for_exe(self, exe_name):
        date = datetime.now().date().isoformat()
        with _LOCK, self._connect() as conn:
            row = conn.execute(
                """
                SELECT duration FROM timings WHERE exe_name = ? AND date = ?
            """,
                (exe_name, date),
            ).fetchone()
            return row[0] if row else 0

    def get_timing_today(self):
        date = datetime.now().date().isoformat()
        with _LOCK, self._connect() as conn:
            row = conn.execute(
                """
                SELECT exe_name, duration, date FROM timings WHERE date = ?
            """,
                (date,),
            ).fetchall()
            return row

    def get_total_time_today(self):
        date = datetime.now().date().isoformat()
        with _LOCK, self._connect() as conn:
            # Use timings table to get total time for today
            row = conn.execute(
                """
                SELECT SUM(duration) FROM timings WHERE date = ?
            """,
                (date,),
            ).fetchone()
            return row[0] if row else 0

    def add_violation(self, exe_name, reason):
        now = datetime.now().isoformat()
        with _LOCK, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO violations (exe_name, timestamp, reason)
                VALUES (?, ?, ?)
            """,
                (exe_name, now, reason),
            )
            conn.commit()

    def get_settings(self, key, default=None):
        with _LOCK, self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            ).fetchone()
            return row[0] if row else default

    def set_settings(self, key, value):
        with _LOCK, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
                (key, value),
            )
            conn.commit()

    def get_all_processes(self):
        with _LOCK, self._connect() as conn:
            return conn.execute(
                "SELECT exe_name, is_game, user_marked FROM is_game"
            ).fetchall()

    def get_all_classified_processes(self):
        with _LOCK, self._connect() as conn:
            cur = conn.execute("SELECT exe_name FROM is_game")
            return [row[0] for row in cur.fetchall()]

    def get_daily_timings(self):
        with _LOCK, self._connect() as conn:
            return conn.execute(
                "SELECT exe_name, date, duration FROM timings ORDER BY date DESC"
            ).fetchall()

    ###### Settings ######
    def get_timing_settings_for_exe(self, exe_name):
        with _LOCK, self._connect() as conn:
            row = conn.execute(
                "SELECT max_time, notify_limit FROM timing_settings WHERE exe_name = ?",
                (exe_name,),
            ).fetchone()
            return row if row else (0, 0)

    def set_timing_settings_for_exe(
        self, exe_name, max_time=DEFAULT_TIME_LIMIT, notify_limit=0, commit=True
    ):
        with _LOCK, self._connect() as conn:
            # Check if exe is assigned as a game
            if not self.get_is_present(exe_name):
                raise ValueError(
                    f"Executable '{exe_name}' is not classified as a game."
                )
            conn.execute(
                """
                INSERT INTO timing_settings (exe_name, max_time, notify_limit)
                VALUES (?, ?, ?)
                ON CONFLICT(exe_name) DO UPDATE SET
                max_time = excluded.max_time, notify_limit = excluded.notify_limit
            """,
                (exe_name, max_time, notify_limit),
            )
            if commit:
                conn.commit()

    def update_global_timing_settings(self, limit=DEFAULT_GLOBAL_TIMING_LIMIT):
        with _LOCK, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO settings (key, value)
                VALUES ('global_timing_limit', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
                (limit,),
            )
            conn.commit()

    def update_timing_settings(
        self, exe_name, max_time=DEFAULT_TIME_LIMIT, notify_limit=DEFAULT_TIME_LIMIT
    ):
        """
        Update the timing settings for a specific game executable.
        If the executable is not classified as a game, raise an error.
        """
        with _LOCK, self._connect() as conn:
            # Check if exe is assigned as a game
            is_a_game = conn.execute(
                "SELECT is_game FROM is_game WHERE exe_name = ?", (exe_name,)
            ).fetchone()
            if not is_a_game or not is_a_game[0]:
                raise ValueError(
                    f"Executable '{exe_name}' is not classified as a game."
                )
            conn.execute(
                """
                INSERT INTO timing_settings (exe_name, max_time, notify_limit)
                VALUES (?, ?, ?)
                ON CONFLICT(exe_name) DO UPDATE SET
                max_time = excluded.max_time, notify_limit = excluded.notify_limit
            """,
                (exe_name, max_time, notify_limit),
            )
            conn.commit()

    def refresh_time_limit_list(self):
        """
        Refresh the timing settings for all games.
        Add default time limits for all classified games if not already set, else do nothing.
        """
        with _LOCK, self._connect() as conn:
            # Get all classified games
            games = conn.execute(
                "SELECT exe_name FROM is_game WHERE is_game = 1"
            ).fetchall()
            for game in games:
                exe_name = game[0]
                # Insert default timing settings if not exists
                conn.execute(
                    """
                    INSERT INTO timing_settings (exe_name, max_time, notify_limit)
                    VALUES (?, 60, 0)
                    ON CONFLICT(exe_name) DO NOTHING
                """,
                    (exe_name,),
                )
            conn.commit()

    def get_all_timing_settings(self):
        with _LOCK, self._connect() as conn:
            return conn.execute(
                "SELECT exe_name, max_time, notify_limit FROM timing_settings"
            ).fetchall()

    def get_global_timing_limit(self):
        with _LOCK, self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = 'global_timing_limit'"
            ).fetchone()
            return int(row[0]) if row else 60

    ##### Voilations #####
    def get_games_with_time_violations(self, running_processes):
        """
        Get all games which have violated the time limit.
        Will fetch from both the timings and is_game tables to get the necessary information.
        """        
        # Get today's timings
        current_timings = self.get_timing_today()
        current_timings_dict = {row[0]: row[1] for row in current_timings}
        timing_settings = self.get_all_timing_settings()
        timing_settings_dict = {row[0]: row[1] for row in timing_settings}
        
        with _LOCK, self._connect() as conn:
            # Fetch violations too to ignore duplicate entries
            current_violations = conn.execute(
                "SELECT exe_name FROM violations"
            ).fetchall()
            current_violations_set = set(row[0] for row in current_violations)

            violations = []
            seen_violations = set()  # To avoid duplicate entries in the violations list
            for exe_name, max_time in timing_settings_dict.items():
                # If already in violations, skip if not running
                if exe_name in current_violations_set and exe_name not in running_processes:
                    if exe_name not in seen_violations:
                        violations.append((exe_name, 0, max_time))
                    seen_violations.add(exe_name)
                    continue

                # Find current duration for this game
                current_duration = current_timings_dict.get(exe_name, 0)
                if (
                    (max_time > 0.1 and current_duration > 0.1) and current_duration > max_time * 60
                ):  # Only consider if max_time is set and greater than 0.1 minutes and current_duration is greater than 0.1 minutes
                    # If current duration exceeds max time, add to violations
                    violations.append((exe_name, current_duration, max_time))
            # Add entries to violations table
            for exe_name, current_duration, max_time in violations:
                reason = f"Exceeded time limit of {max_time} minutes. Current duration: {current_duration // 60} minutes."
                conn.execute(
                    """
                    INSERT INTO violations (exe_name, timestamp, reason)
                    VALUES (?, ?, ?)
                """,
                    (exe_name, datetime.now().isoformat(), reason),
                )
            conn.commit()
            return violations

    def get_all_violations(self):
        with _LOCK, self._connect() as conn:
            return conn.execute(
                "SELECT exe_name, timestamp, reason FROM violations ORDER BY timestamp DESC"
            ).fetchall()

    def get_violation_count_for_exe(self, exe_name):
        with _LOCK, self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM violations WHERE exe_name = ?", (exe_name,)
            ).fetchone()
            return row[0] if row else 0
    
    ##### Miscellaneous Methods #####
    def get_is_data_populated_today(self):
        """
        Check if the data for today is populated.
        Returns True if populated, False if not.
        """
        date = datetime.now().date().isoformat()
        with _LOCK, self._connect() as conn:
            row = conn.execute(
                "SELECT is_populated FROM is_data_populated_today WHERE date = ?",
                (date,),
            ).fetchone()
            return bool(row[0]) if row else False
    
    def populate_data_today(self):
        """
        Populate esssential data for today.
        """
        date = datetime.now().date().isoformat()
        
        # Add game timing entries for today
        games = self.get_game_names()
        
        with _LOCK, self._connect() as conn:
            for game in games:
                conn.execute(
                    """
                    INSERT INTO timings (exe_name, date, duration)
                    VALUES (?, ?, 0)
                    ON CONFLICT(exe_name, date) DO NOTHING
                """,
                    (game, date),
                )
            
            # Remove all violations. Fresh start for the day
            conn.execute("DELETE FROM violations")
            # Mark today's data as populated
            conn.execute(
                """
                INSERT INTO is_data_populated_today (date, is_populated)
                VALUES (?, 1)
                ON CONFLICT(date) DO UPDATE SET is_populated = 1
            """,
                (date,),
            )
            conn.commit()

    ##### Migration Methods #####

    def migrate_add_column(self, table, column, type_="TEXT", default=None):
        with _LOCK, self._connect() as conn:
            cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
            col_names = [col[1] for col in cols]
            if column not in col_names:
                alter = f"ALTER TABLE {table} ADD COLUMN {column} {type_}"
                if default is not None:
                    alter += f" DEFAULT {repr(default)}"
                conn.execute(alter)
                conn.commit()
