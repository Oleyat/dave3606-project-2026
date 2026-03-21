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
    create table lego_set(
        id text not null primary key,
        name text not null,
        year int null,
        category text null,
        preview_image_url text null
    );
    """
)
cur.execute(
    """
    create table lego_brick(
        brick_type_id text not null,
        color_id int not null,
        name text not null,
        preview_image_url text null,
        primary key (brick_type_id, color_id)
    );
    """
)
cur.execute(
    """
    create table lego_inventory(
        set_id text not null,
        brick_type_id text not null,
        color_id int not null,
        count int not null,
        primary key (set_id, brick_type_id, color_id),
        foreign key (set_id) references lego_set(id),
        foreign key (brick_type_id, color_id) references lego_brick(brick_type_id, color_id)
    );
    """
)
cur.close()
conn.commit()
conn.close()
