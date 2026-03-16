import json
import html
import psycopg
from flask import Flask, Response, request
from time import perf_counter
import gzip

app = Flask(__name__)

DB_CONFIG = {
    "host": "localhost",
    "port": 9876,
    "dbname": "lego-db",
    "user": "lego",
    "password": "bricks",
}


@app.route("/")
def index():
    with open("templates/index.html", 'r') as f:
        template = f.read()
    return Response(template)


@app.route("/sets")
def sets():
    with open("templates/sets.html", 'r') as f:
        template = f.read()
    rows = ""

    utfEncondings = ["UTF-8", "UTF-16-LE", "UTF-16-BE", "UTF-32-LE", "UTF-32-BE"]
    getEncoding = request.args.get('encoding')
    if (getEncoding is None or getEncoding.upper() not in utfEncondings):
        getEncoding = "UTF-8"

    start_time = perf_counter()
    conn = psycopg.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("select id, name from lego_set order by id")
            for row in cur.fetchall():
                html_safe_id = html.escape(row[0])
                html_safe_name = html.escape(row[1])
                existing_rows = rows
                rows = existing_rows + f'<tr><td><a href="/set?id={html_safe_id}">{html_safe_id}</a></td><td>{html_safe_name}</td></tr>\n'
        print(f"Time to render all sets: {perf_counter() - start_time}")
    finally:
        conn.close()

    page_html = template.replace("{ROWS}", rows)
    page_html = page_html.encode(encoding=getEncoding)
    gzip_page_html = gzip.compress(page_html)

    return Response(gzip_page_html, headers={"Content-Encoding": "gzip"}, content_type=f"text/html; charset={getEncoding.upper()}")


@app.route("/set")
def legoSet():  # We don't want to call the function `set`, since that would hide the `set` data type.
    with open("templates/set.html", 'r') as f:
        template = f.read()
    return Response(template)


@app.route("/api/set")
def apiSet():
    set_id = request.args.get("id")
    result = {"set_id": set_id}
    json_result = json.dumps(result, indent=4)
    return Response(json_result, content_type="application/json")


if __name__ == "__main__":
    app.run(port=5000, debug=True)

# Note: If you define new routes, they have to go above the call to `app.run`.
