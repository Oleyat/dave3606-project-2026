import json
import html
import struct
import gzip
from flask import Flask, Response, render_template, request
from time import perf_counter
from database import Database

app = Flask(__name__)

set_cache = {}
MAX_CACHE_SIZE = 100

def get_next_sets_forward(db, cursor = None, limit=50): #returns fully rendered html string with all sets
    rows = []
    if cursor is not None:
        query = """
        SELECT id, name, year, category, preview_image_url 
        FROM lego_set 
        WHERE id > %s
        ORDER BY id
        LIMIT %s
        """
        params = (cursor, limit + 1) #fetch extra row
    else:
        query = """
        SELECT id, name, year, category, preview_image_url 
        FROM lego_set order by id
        LIMIT %s
        """
        params = (limit + 1,)  
    results = db.execute_and_fetch_all(query, params)

    has_next = len(results) > limit 
    if has_next:
        results = results[:-1] #remove extra row
    
    for row in results:
        rows.append({  #no need to html.escape here, since Jinja will do it for us when we render the template.
            "id": row[0],
            "name": row[1],
            "year": row[2],
            "category": row[3],
            "preview_image_url": row[4]
        })
    next_cursor = rows[-1]["id"] if rows and has_next else None
    prev_cursor = rows[0]["id"] if rows and cursor is not None else None #fjerner previoud på første side

    return {
        "rows": rows,
        "next_cursor": next_cursor,
        "prev_cursor": prev_cursor,
        "limit": limit
    }


def get_next_sets_backward(db, cursor = None, limit=50): #returns fully rendered html string with all sets
    rows = []
    if cursor is not None:
        query = """
        SELECT id, name, year, category, preview_image_url 
        FROM lego_set 
        WHERE id < %s
        ORDER BY id DESC
        LIMIT %s
        """
        params = (cursor, limit +1) #fetch extra row
    else:
        query = """
        SELECT id, name, year, category, preview_image_url 
        FROM lego_set order by id desc
        LIMIT %s
        """
        params = (limit + 1,)   
    results = db.execute_and_fetch_all(query, params)

    has_prev = len(results) > limit
    if has_prev:
        results = results[:-1] #remove extra row

    results.reverse() #reverse to restore order.

    for row in results:
        rows.append({  #no need to html.escape here, since Jinja will do it for us when we render the template.
            "id": row[0],
            "name": row[1],
            "year": row[2],
            "category": row[3],
            "preview_image_url": row[4]
        })
    next_cursor = rows[-1]["id"] if rows else None  
    prev_cursor = rows[0]["id"] if rows and has_prev else None

    return{
        "rows": rows,
        "next_cursor": next_cursor,
        "prev_cursor": prev_cursor,
        "limit": limit
    }

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

    if not rows: #sjekker om man får rader
        return json.dumps(result, indent=4)

    firstrow = rows[0]
    if firstrow is not None:
        result["name"] = html.escape(firstrow[1])
        result["year"] = html.escape(firstrow[2] or "") # kan være None i databasen, så vi må håndtere det.
        result["category"] = html.escape(firstrow[3] or "")
        result["preview_image_url"] = html.escape(firstrow[4] or "")
        for row in rows:
            result["inventory"].append({
            "brick_type_id": html.escape(str(row[5] or "")),
            "color_id": html.escape(str(row[6] or "")),
            "count": html.escape(str(row[7] or "")),
            "brick_name": html.escape(str(row[8] or "")),
            "preview_image_url": html.escape(str(row[9] or ""))
        })
    json_result = json.dumps(result, indent=4)
    return json_result

def encode_page_html(page_html, encoding): #returns gzipped html encoded in the specified encoding.
    utfEncondings = ["UTF-8", "UTF-16"]
    if (encoding is None or encoding.upper() not in utfEncondings):
        encoding = "UTF-8"

    page_html = page_html.replace("{CHARSET}", encoding)
    page_html = page_html.encode(encoding=encoding)
    gzip_page_html = gzip.compress(page_html)    

    return gzip_page_html,encoding.upper()

def varlenStruct(format, value):
    return struct.pack(format, len(value)) + value.encode("utf-8")

def fixLenStruct(format, *value):
    return struct.pack(format, *value)

def serialize_set_to_binary_data(result):
    data = []
    data.append(varlenStruct(">B", result["set_id"])) #set_id
    data.append(varlenStruct(">B", result["name"])) #name
    data.append(fixLenStruct(">H", int(result["year"])))
    data.append(varlenStruct(">B", result["category"])) #category
    data.append(varlenStruct(">H", result["preview_image_url"])) #preview_image_url

    for row in result["inventory"]:
        if(int(row["color_id"]) < 255 and int(row["count"]) < 256):
            data.append(fixLenStruct(">BB", int(row["color_id"]), int(row["count"]))) #color_id, count
        else:
            data.append(fixLenStruct(">BBH", 255, int(row["color_id"]), int(row["count"]))) #color_id, count #max col 255 max count 3100
        if(row["brick_type_id"].isdigit() and int(row["brick_type_id"]) < 65536): # #ingen brick_type_id er over 50 karakterer
            diglen = 100 + len(row["brick_type_id"])
            data.append(fixLenStruct(">BH", diglen, int(row["brick_type_id"]))) #brick_type_id
        elif(row["brick_type_id"].isdigit() and int(row["brick_type_id"]) < 4294967296):
            diglen = 200 + len(row["brick_type_id"])
            data.append(fixLenStruct(">BI", diglen, int(row["brick_type_id"])))
        else:
            data.append(varlenStruct(">B", row["brick_type_id"]))
        siste_del = row["preview_image_url"].split("/")[-1][:-4] 

        if row["preview_image_url"].split(".")[-1] == "jpg":
            linklen = 1
        elif row["preview_image_url"].split(".")[-1] == "png":
            linklen = 2

        if(siste_del.isdigit() and int(siste_del) < 65536): 
            diglen = 100 + linklen
            data.append(fixLenStruct(">BH", diglen, int(siste_del)))
        elif(siste_del.isdigit() and int(siste_del) < 4294967296):
            diglen = 200 + linklen
            data.append(fixLenStruct(">BI", diglen, int(siste_del)))
        else:
            data.append(varlenStruct(">B", siste_del))
            data.append(fixLenStruct(">B", linklen)) #link

            # mangler brick_name 

    return  b"".join(data)

@app.route("/")
def index():
    with open("templates/index.html", 'r') as f:
        template = f.read()
    return Response(template)

@app.route("/sets")
def sets():
    db = Database()
    getEncoding = request.args.get('encoding')
    cursor = request.args.get("cursor")
    direction = request.args.get("direction", "forward")
    start_time = perf_counter()
    try:
        if direction == "back":
            page_data= get_next_sets_backward(db, cursor)
        else:
            page_data = get_next_sets_forward(db, cursor)
        page_html = render_template("sets.html", **page_data)
        print(f"Time to render sets page {cursor}: {perf_counter() - start_time}")
    finally:
        db.close()

    gzip_page_html, used_encoding = encode_page_html(page_html, getEncoding)
    return Response(gzip_page_html, headers={"Content-Encoding": "gzip", "Cache-Control" : "max-age=60"}, content_type=f"text/html; charset={used_encoding}")

@app.route("/set")
def legoSet():  # We don't want to call the function `set`, since that would hide the `set` data type.
    with open("templates/set.html", 'r') as f:
        template = f.read()
    return Response(template)



@app.route("/api/set")
def apiSet():
    set_id = request.args.get("id")

    # Sjekk cache først
    if set_id in set_cache:
        # Move to end (most recently used)
        result = set_cache.pop(set_id)
        set_cache[set_id] = result
        return Response(result, content_type="application/json")
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
    db = Database()
    try:
        result = json.loads(get_set_and_inventory(db, set_id))
        string = serialize_set_to_binary_data(result)
    finally:
        db.close()
    
    return Response(string, content_type="application/octet-stream")


if __name__ == "__main__":
    app.run(port=5000, debug=True)


## send en byte med størrelse 200 + lengden av brick_Type_id om den er tall
