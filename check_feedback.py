import sqlite3

# Connect to your SQLite database file
conn = sqlite3.connect('music_project.db')
cursor = conn.cursor()

# Query all data from feedback table
cursor.execute("SELECT * FROM feedback;")
rows = cursor.fetchall()

print("Feedback table data:")
for row in rows:
    print(row)

# Close the connection
conn.close()
