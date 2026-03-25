import json
import html
import psycopg
import struct
from flask import Flask, Response, render_template, request
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
    rows = []

    utfEncondings = ["UTF-8", "UTF-16"]
    getEncoding = request.args.get('encoding')
    if (getEncoding is None or getEncoding.upper() not in utfEncondings):
        getEncoding = "UTF-8"

    start_time = perf_counter()
    conn = psycopg.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM lego_set ORDER BY id")
            for row in cur.fetchall():
                rows.append({  #no need to html.escape here, since Jinja will do it for us when we render the template.
                    "id": row[0],
                    "name": row[1]
                    })
        print(f"Time to render all sets: {perf_counter() - start_time}")
    finally:
        conn.close()

    page_html = render_template("sets.html", rows=rows)
    page_html = page_html.replace("{CHARSET}", getEncoding)
    page_html = page_html.encode(encoding=getEncoding)
    gzip_page_html = gzip.compress(page_html)

    return Response(gzip_page_html, headers={"Content-Encoding": "gzip"}, content_type=f"text/html; charset={getEncoding.upper()}")

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
<<<<<<< Oppgave6Frontend&Caching

    if set_id in set_cache:
        # Move to end (most recently used) by re-inserting
        result = set_cache.pop(set_id)
        set_cache[set_id] = result 
        json_result = json.dumps(result, indent=4)
        return Response(json_result, content_type="application/json")
    

    

    set_cache[set_id] = result
    if len(set_cache) > MAX_CACHE_SIZE:
        oldest_key = next(iter(set_cache))
        del set_cache[oldest_key]

    return Response(json.dumps(result, indent=4), content_type="application/json")
=======
    result = {"set_id": set_id,
            "name": "",
            "year": "",
            "category": "",
            "preview_image_url": "",
            "inventory": []}
    try:
        conn = psycopg.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            cur.execute("SELECT s.id, s.name, COALESCE(s.year::text, ''), s.category, s.preview_image_url, inv.brick_type_id, inv.color_id, inv.count FROM lego_set s LEFT JOIN lego_inventory inv ON s.id=inv.set_id WHERE s.id = %s", (set_id,))
            rows = cur.fetchall()
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
                    "count": html.escape(str(row[7]))
                })
    finally:
        conn.close()
    json_result = json.dumps(result, indent=4)
    return Response(json_result, content_type="application/json")
>>>>>>> main



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
