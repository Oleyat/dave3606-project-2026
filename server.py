import json
import html
import psycopg
import struct
import gzip
from flask import Flask, Response, render_template, request
from time import perf_counter
from database import Database

app = Flask(__name__)

def get_all_sets(db, page=1, limit=50): #returns fully rendered html string with all sets
    offset = (page - 1) * limit
    rows = []
    query = "SELECT id, name, year, category, preview_image_url FROM lego_set order by id LIMIT %s OFFSET %s"
    results = db.execute_and_fetch_all(query, (limit, offset))

    count_query = "SELECT COUNT(*) FROM lego_set"
    total = db.execute_and_fetch_all(count_query)[0][0]
    total_pages = (total + limit - 1) // limit

    for row in results:
        rows.append({  #no need to html.escape here, since Jinja will do it for us when we render the template.
            "id": row[0],
            "name": row[1],
            "year": row[2],
            "category": row[3],
            "preview_image_url": row[4]
        })
    page_html = render_template("sets.html", rows=rows, page=page, total_pages=total_pages, limit=limit)
    return page_html

def get_set_and_inventory(db, set_id): #returns a json string with information about set and inventiry.
    result = {"set_id": set_id,
            "name": "",
            "year": "",
            "category": "",
            "preview_image_url": "",
            "inventory": []}
    
    query = """
        SELECT s.id, s.name, COALESCE(s.year::text, ''), s.category, s.preview_image_url, inv.brick_type_id, inv.color_id, inv.count, b.name, b.preview_image_url
        FROM lego_set s 
        LEFT JOIN lego_inventory inv ON s.id=inv.set_id 
        LEFT JOIN lego_brick b ON inv.brick_type_id = b.brick_type_id AND inv.color_id = b.color_id
        WHERE s.id = %s
    """
    rows = db.execute_and_fetch_all(query, (set_id,))
    firstrow = rows[0]
    if firstrow is not None:
        result["name"] = html.escape(firstrow[1])
        result["year"] = html.escape(firstrow[2]) # kan bli null pga html.escape.
        result["category"] = html.escape(firstrow[3])
        result["preview_image_url"] = html.escape(firstrow[4])
        for row in rows:
            result["inventory"].append({
            "brick_type_id": html.escape(str(row[5])),
            "color_id": html.escape(str(row[6])),
            "count": html.escape(str(row[7])),
            "name": html.escape(str(row[8])),
            "preview_image_url": html.escape(str(row[9]))
        })
    json_result = json.dumps(result, indent=4)
    return json_result

def encode_page_html(page_html, encoding): #returns gzipped html encoded in the specified encoding.
    utfEncondings = ["UTF-8", "UTF-16", "UTF-16"]
    if (encoding is None or encoding.upper() not in utfEncondings):
        encoding = "UTF-8"

    page_html = page_html.replace("{CHARSET}", encoding)
    page_html = page_html.encode(encoding=encoding)
    gzip_page_html = gzip.compress(page_html)    

    return gzip_page_html,encoding.upper()


@app.route("/")
def index():
    with open("templates/index.html", 'r') as f:
        template = f.read()
    return Response(template)

@app.route("/sets")
def sets():
    db = Database()
    getEncoding = request.args.get('encoding')
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 50))
    start_time = perf_counter()
    try:
        page_html = get_all_sets(db, page, limit)
        print(f"Time to render sets page {page}: {perf_counter() - start_time}")
    finally:
        db.close()

    gzip_page_html, used_encoding = encode_page_html(page_html, getEncoding)
    return Response(gzip_page_html, headers={"Content-Encoding": "gzip"}, content_type=f"text/html; charset={used_encoding}")

@app.route("/set")
def legoSet():  # We don't want to call the function `set`, since that would hide the `set` data type.
    with open("templates/set.html", 'r') as f:
        template = f.read()
    return Response(template)


set_cache = {}
MAX_CACHE_SIZE = 100

@app.route("/api/set")
def apiSet():
    set_id = request.args.get("id")

    # Sjekk cache først
    if set_id in set_cache:
        # Move to end (most recently used)
        result = set_cache.pop(set_id)
        set_cache[set_id] = result
        return Response(json.dumps(result, indent=4), content_type="application/json")

    db = Database()
    try:
        result = get_set_and_inventory(db, set_id)
    finally:
        db.close()

    # Oppdater cache
    set_cache[set_id] = result
    if len(set_cache) > MAX_CACHE_SIZE:
        oldest_key = next(iter(set_cache))
        del set_cache[oldest_key]
    return Response(result, content_type="application/json")


@app.route("/api/binary/set")
def apiBinarySet():
    set_id = request.args.get("id")
    result = {"set_id": set_id,
            "name": "",
            "year": "",
            "category": "",
            "preview_image_url": "",
            "inventory": []}
    data = []

    try:
        conn = psycopg.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            cur.execute("SELECT s.id, s.name, COALESCE(s.year::text, ''), s.category, s.preview_image_url, inv.brick_type_id, inv.color_id, inv.count FROM lego_set s LEFT JOIN lego_inventory inv ON s.id=inv.set_id WHERE s.id = %s", (set_id,))
            rows = cur.fetchall()
            firstrow = rows[0]
            if firstrow is not None:
                data.append(struct.pack("B", len(result["set_id"])))
                data.append(result["set_id"].encode("utf-8")) #set_id

                data.append(struct.pack(">B", len(firstrow[1])))
                data.append(firstrow[1].encode("utf-8")) #name

                data.append(struct.pack(">H", int(firstrow[2])))

                data.append(struct.pack(">B", len(firstrow[3])))
                data.append(firstrow[3].encode("utf-8")) #category

                data.append(struct.pack(">H", len(firstrow[4])))
                data.append(firstrow[4].encode("utf-8")) #preview_image_url
                for row in rows:
                    if(row[6] < 255 and row[7] < 256):
                        data.append(struct.pack(">BB", row[6], row[7])) 
                    else:
                        data.append(struct.pack(">BBH", 255,row[6], row[7])) #color_id, count #max col 255 max count 3100
                    if(row[5].isdigit() and int(row[5]) < 65536): # #ingen brick_type_id er over 50 karakterer
                        diglen = 100 + len(row[5])
                        data.append(struct.pack(">B", diglen))
                        data.append(struct.pack(">H", int(row[5])))
                    elif(row[5].isdigit() and int(row[5]) < 4294967296):
                        diglen = 200 + len(row[5])
                        data.append(struct.pack(">B", diglen))
                        data.append(struct.pack(">I", int(row[5])))
                    else:
                        data.append(struct.pack(">B", len(row[5]))) 
                        data.append(str(row[5]).encode("utf-8"))
    finally:
        conn.close()
    
    string = b"".join(data)
    return Response(string, content_type="application/octet-stream")


if __name__ == "__main__":
    app.run(port=5000, debug=True)


## send en byte med størrelse 200 + lengden av brick_Type_id om den er tall
