import psycopg

class Database:
    def __init__(self):
        self.conn = psycopg.connect(
            host="localhost",
            port=9876,
            dbname="lego-db",
            user="lego",
            password=   "bricks",
        )
        self.cur = self.conn.cursor()

    def execute_and_fetch_all(self, query, params=None):
        self.cur.execute(query, params)
        return self.cur.fetchall()

    def close(self):
        self.cur.close()
        self.conn.close()