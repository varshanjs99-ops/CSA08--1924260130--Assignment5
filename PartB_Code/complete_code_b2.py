"""B2 - Completed TODOs for safe SQLite insertion and parameterised station lookup."""
import sqlite3

readings = [
    ("Adyar", "2026-10-01", 48.0),
    ("Guindy", "2026-10-01", 95.0),
    ("Guindy", "2026-10-03", 121.0),
    ("Adyar", "2026-10-04", 60.0),
]

con = sqlite3.connect(":memory:")
con.execute("CREATE TABLE aq(station TEXT, day TEXT, pm25 REAL)")
# TODO 1: one executemany call with placeholders, followed by commit.
con.executemany("INSERT INTO aq(station, day, pm25) VALUES (?,?,?)", readings)
con.commit()


def station_average(name):
    # TODO 2: use a parameterised SELECT; never concatenate user input into SQL.
    row = con.execute("SELECT AVG(pm25) FROM aq WHERE station = ?", (name,)).fetchone()
    return row[0]


print(station_average("Adyar"), station_average("Guindy"))
print(station_average("Adyar' OR '1'='1"))
con.close()
