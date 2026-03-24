import json
import html
import psycopg
import gzip
from flask import Flask, Response, request
from time import perf_counter
from database import Database

app = Flask(__name__)

def get_all_sets(db, limit=None, offset=0): #returns a string of all sets in database 
    rows = []
    query = "SELECT id, name FROM lego_set order by id"
    params = []
    if limit is not None:
        query += " LIMIT %s"
        params.append(limit)
    if offset is not None:
        query += " OFFSET %s"
        params.append(offset)

    results = db.execute_and_fetch_all(query, params=params)

    for row in results:
        html_safe_id = html.escape(row[0])
        html_safe_name = html.escape(row[1])
        rows.append(f'<tr><td><a href="/set?id={html_safe_id}">{html_safe_id}</a></td><td>{html_safe_name}</td></tr>\n')
    return "".join(rows)

@app.route("/")
def index():
    with open("templates/index.html", 'r') as f:
        template = f.read()
    return Response(template)


@app.route("/sets")
def sets():
    with open("templates/sets.html", 'r') as f:
        template = f.read()
    rows = []

    # use paginator to only fetch 50 sets at a time for improved rendering performance 
    page = int(request.args.get("page", 1))
    page_size = 50
    offset = (page - 1) * page_size

    utfEncondings = ["UTF-8", "UTF-16-LE", "UTF-16-BE", "UTF-32-LE", "UTF-32-BE"]
    getEncoding = request.args.get('encoding')
    if (getEncoding is None or getEncoding.upper() not in utfEncondings):
        getEncoding = "UTF-8"

    start_time = perf_counter()
    conn = psycopg.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM lego_set ORDER BY id LIMIT %s OFFSET %s", (page_size, offset))
            for row in cur.fetchall():
                html_safe_id = html.escape(row[0])
                html_safe_name = html.escape(row[1])
                rows.append( f'<tr><td><a href="/set?id={html_safe_id}">{html_safe_id}</a></td><td>{html_safe_name}</td></tr>\n')
        print(f"Time to render all sets: {perf_counter() - start_time}")
    finally:
        conn.close()

    prev_page = page - 1 if page > 1 else 1
    next_page = page + 1

    page_html = template.replace("{ROWS}", "".join(rows))
    page_html = page_html.replace("{CURRENT_PAGE}", str(page))
    page_html = page_html.replace("{PREV_PAGE}", str(prev_page))
    page_html = page_html.replace("{NEXT_PAGE}", str(next_page))
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