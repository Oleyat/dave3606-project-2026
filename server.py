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
    results = db.execute_and_fetch_all(query)

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
    
    db = Database()

    utfEncondings = ["UTF-8", "UTF-16-LE", "UTF-16-BE", "UTF-32-LE", "UTF-32-BE"]
    getEncoding = request.args.get('encoding')
    if (getEncoding is None or getEncoding.upper() not in utfEncondings):
        getEncoding = "UTF-8"

    start_time = perf_counter()
    try:
        rows = get_all_sets(db)
        print(f"Time to render all sets: {perf_counter() - start_time}")
    finally:
        db.close()


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