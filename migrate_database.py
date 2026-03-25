import psycopg

conn = psycopg.connect(
    host="localhost",
    port=9876,
    dbname="lego-db",
    user="lego",
    password="bricks",
)

cur = conn.cursor()
cur.execute(
    """
    CREATE TABLE lego_set(
        id TEXT NOT NULL PRIMARY KEY,
        name TEXT NOT NULL,
        year INT NULL,
        category TEXT NULL,
        preview_image_url TEXT NULL
    );
    """
)
cur.execute(
    """
    CREATE TABLE lego_brick(
        brick_type_id TEXT NOT NULL,
        color_id INT NOT NULL,
        name TEXT NOT NULL,
        preview_image_url TEXT NULL,
        PRIMARY KEY (brick_type_id, color_id)
    );
    """
)
cur.execute(
    """
    CREATE TABLE lego_inventory(
        set_id TEXT NOT NULL,
        brick_type_id TEXT NOT NULL,
        color_id INT NOT NULL,
        count INT NOT NULL,
        PRIMARY KEY (set_id, brick_type_id, color_id),
        FOREIGN KEY (set_id) REFERENCES lego_set(id),
        FOREIGN KEY (brick_type_id, color_id) REFERENCES lego_brick(brick_type_id, color_id)
    );
    """
)
cur.execute("CREATE INDEX ON lego_inventory (brick_type_id);")
cur.execute("CREATE INDEX ON lego_inventory (color_id);")
cur.close()
conn.commit()
conn.close()
