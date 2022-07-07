import sqlite3
import os

dirname = os.path.dirname(__file__)
db_name = os.path.join(dirname, '../data/content_tags.db')

con = sqlite3.connect(db_name)

sql_create = """
    CREATE TABLE IF NOT EXISTS books (
        id      INTEGER PRIMARY KEY,
        title   TEXT NOT NULL,
        alt_title TEXT,
        tag     TEXT NOT NULL UNIQUE,
        alt_tag TEXT UNIQUE,
        era     TEXT,
        isbn    INTEGER
    );
    CREATE TABLE IF NOT EXISTS content_tags (
        id      INTEGER PRIMARY KEY,
        long    TEXT NOT NULL,
        short   TEXT NOT NULL,
        alt_long    TEXT,
        alt_short   TEXT,
        book_id INTEGER NOT NULL,
        UNIQUE(book_id, long)
        UNIQUE(book_id, short)
        FOREIGN KEY (book_id)
            REFERENCES books (id)
                ON UPDATE CASCADE
                ON DELETE RESTRICT
    );
    """

con.executescript(sql_create)
con.commit()
