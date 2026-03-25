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
    return Response(gzip_page_html, headers={"Content-Encoding": "gzip", "Cache-Control" : "max-age=60"}, content_type=f"text/html; charset={used_encoding}")

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
    start_time = perf_counter()
    if set_id in set_cache:
        # Beveger til slutten av ordboken (Blir mest nylig lagt til)
        result = set_cache.pop(set_id)
        set_cache[set_id] = result
        print(f"Cache HIT for {set_id}: {perf_counter() - start_time:.6f}s")
        return Response(result, content_type="application/json")
    db = Database()
    try:
        result = get_set_and_inventory(db, set_id)
    finally:
        db.close()
    print(f"Cache MISS for {set_id}: {perf_counter() - start_time:.6f}s")

    # Oppdater cache
    set_cache[set_id] = result
    if len(set_cache) > MAX_CACHE_SIZE:
        oldest_key = next(iter(set_cache))
        del set_cache[oldest_key]
    return Response(result, content_type="application/json")


@app.route("/api/binary/set")
def apiBinarySet():
    set_id = request.args.get("id")
    db = Database()
    try:
        result = json.loads(get_set_and_inventory(db, set_id))
    finally:
        db.close()
    data = []
    data.append(struct.pack("B", len(set_id)))
    data.append(set_id.encode("utf-8")) #set_id

    data.append(struct.pack(">B", len(result["name"])))
    data.append(result["name"].encode("utf-8")) #name

    data.append(struct.pack(">H", int(result["year"])))

    data.append(struct.pack(">B", len(result["category"])))
    data.append(result["category"].encode("utf-8")) #category

    data.append(struct.pack(">H", len(result["preview_image_url"])))
    data.append(result["preview_image_url"].encode("utf-8")) #preview_image_url
    for row in result["inventory"]:
        if(int(row["color_id"]) < 255 and int(row["count"]) < 256):
            data.append(struct.pack(">BB", int(row["color_id"]), int(row["count"]))) 
        else:
            data.append(struct.pack(">BBH", 255,int(row["color_id"]), int(row["count"]))) #color_id, count #max col 255 max count 3100
        if(row["brick_type_id"].isdigit() and int(row["brick_type_id"]) < 65536): # #ingen brick_type_id er over 50 karakterer
            diglen = 100 + len(row["brick_type_id"])
            data.append(struct.pack(">B", diglen))
            data.append(struct.pack(">H", int(row["brick_type_id"])))
        elif(row["brick_type_id"].isdigit() and int(row["brick_type_id"]) < 4294967296):
            diglen = 200 + len(row["brick_type_id"])
            data.append(struct.pack(">B", diglen))
            data.append(struct.pack(">I", int(row["brick_type_id"])))
        else:
            data.append(struct.pack(">B", len(row["brick_type_id"]))) 
            data.append(str(row["brick_type_id"]).encode("utf-8"))
        # venter på svar om vi må ha disse med eller ikke, fjern kommentarer for å få bildet sendt.
        unik_image = row["preview_image_url"][26:-4] # 26 bytes på duplikat tekst for hver eneste brikke.
        siste_del = row["preview_image_url"][28:-4] 
        
        if(siste_del.isdigit() and int(siste_del) < 65536): # #ingen brick_type_id er over 50 karakterer
            diglen = 100 + len(siste_del)
            data.append(struct.pack(">B", diglen))
            data.append(struct.pack(">H", int(row["brick_type_id"])))
        elif(row["brick_type_id"].isdigit() and int(row["brick_type_id"]) < 4294967296):
            diglen = 200 + len(row["brick_type_id"])
            data.append(struct.pack(">B", diglen))
            data.append(struct.pack(">I", int(row["brick_type_id"])))
        else:
            data.append(struct.pack(">B", len(row["brick_type_id"]))) 
            data.append(str(row["brick_type_id"]).encode("utf-8"))

        data.append(struct.pack(">H", len(unik_image)))
        data.append(unik_image.encode("utf-8")) #preview_image_url

        #se om jeg får gjort om hvis det kun er tall til å sende tallene separat.
    
    string = b"".join(data)
    return Response(string, content_type="application/octet-stream")


if __name__ == "__main__":
    app.run(port=5000, debug=True)


## send en byte med størrelse 200 + lengden av brick_Type_id om den er tall
