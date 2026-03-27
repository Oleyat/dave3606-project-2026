import psycopg



class Database:
    def __init__(self):
        self.conn = None
        self.cur = None

    def execute_and_fetch_all(self, query, params=None):
        try:
            self.conn = psycopg.connect(
                host="localhost",
                port=9876,
                dbname="lego-db",
                user="lego",
                password="bricks",
            )
            self.cur = self.conn.cursor()
            self.cur.execute(query, params)
            return self.cur.fetchall()

        except psycopg.Error as e:
            raise RuntimeError(f"Database query failed: {e}") from e

        finally:
            self.close()

    def close(self):
        if self.cur is not None:
            self.cur.close()
            self.cur = None
        if self.conn is not None:
            self.conn.close()
            self.conn = None