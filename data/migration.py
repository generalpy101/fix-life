import sqlite3

db = sqlite3.connect('game_tracker.db')
cursor = db.cursor()

# Create is data populated today table
cursor.execute('''
delete from violations
''')

db.commit()
cursor.close()
db.close()