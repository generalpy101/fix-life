import sqlite3

# with sqlite3.connect("game_tracker.db") as conn:
#     cur = conn.cursor()

#     # timings migration
#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS timings_new (
#             exe_name TEXT NOT NULL,
#             date TEXT NOT NULL,
#             duration INTEGER DEFAULT 0,
#             PRIMARY KEY (exe_name, date)
#         );
#     """)
#     cur.execute("INSERT INTO timings_new (exe_name, date, duration) SELECT exe_name, date, duration FROM timings;")
#     cur.execute("DROP TABLE timings;")
#     cur.execute("ALTER TABLE timings_new RENAME TO timings;")

#     # daily_usage migration
#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS daily_usage_new (
#             date TEXT PRIMARY KEY,
#             total_time INTEGER DEFAULT 0
#         );
#     """)
#     cur.execute("INSERT INTO daily_usage_new (date, total_time) SELECT date, total_time FROM daily_usage;")
#     cur.execute("DROP TABLE daily_usage;")
#     cur.execute("ALTER TABLE daily_usage_new RENAME TO daily_usage;")

#     conn.commit()

with sqlite3.connect("game_tracker.db") as conn:
    cur = conn.cursor()

    # Add new settings table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """
    )

    # Add new timing_settings table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS timing_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exe_name TEXT UNIQUE,
            max_time INTEGER DEFAULT 0,
            notify_limit INTEGER DEFAULT 0
        );
    """
    )

    # Commit changes
    conn.commit()
