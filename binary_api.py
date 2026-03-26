import json

import requests
import struct

setid = "71799-1"
filename = "result"

length = 0
offset = 0

result = {"set_id": setid,
        "name": "",
        "year": "",
        "category": "",
        "preview_image_url": "",
        "inventory": []}

formats = {
    "B": 1,
    ">B": 1,
    ">H": 2,
    ">I": 4,
    ">BB": 2
}

links = {
    1: "jpg",
    2: "png",
    3: "gif"
}

def retLen(offset, format):
    return struct.unpack_from(format, res.content, offset)[0]

def retData(offset, length):
    return res.content[offset:offset+length].decode("utf-8")

def readData(format):
    # utf8 encoded data
    global offset
    length = retLen(offset, format)
    offset += formats[format]
    binData = retData(offset, length)
    offset += length
    return binData
def readDataRaw(format):
    # integer data
    global offset
    length = formats[format]
    binData = struct.unpack_from(format, res.content, offset)[0]
    offset += length
    return binData

res = requests.get(f"http://localhost:5000/api/binary/set?id={setid}")

result["set_id"] = readData("B")

result["name"] = readData(">B")

result["year"] = readDataRaw(">H")

result["category"] = readData(">B")

result["preview_image_url"] = readData(">H")

while offset + 2 < len(res.content):
    brick_type_id = 0
    color_id = 0
    count = 0

    mix = res.content[offset]
    if (mix==255): # sjekk om kontroll byte
        offset += 1
        color_id = readDataRaw(">B")
        count = readDataRaw(">H")
        
    else:
        color_id = readDataRaw(">B")
        count = readDataRaw(">B")
    digcheck = res.content[offset]
    if(digcheck >= 100 and digcheck < 200): # tall under 2^16
        offset += 1
        digint = digcheck - 100
        brick_type_id = str(readDataRaw(">H"))
    elif(digcheck >= 200): # 200 er for tall over 2^16
        offset += 1
        digint = digcheck - 200
        brick_type_id = str(readDataRaw(">I"))
    else:
        brick_type_id = readData(">B")

    digcheck = res.content[offset]
    digint = 0
    if(digcheck >= 100 and digcheck < 200): # tall under 2^16
        offset += 1
        digint = digcheck - 100
        brick_image_url = str(readDataRaw(">H"))
    elif(digcheck >= 200): # 200 er for tall over 2^16
        offset += 1
        digint = digcheck - 200
        brick_image_url = str(readDataRaw(">I"))
    else:
        brick_image_url = readData(">B")
        digint = readDataRaw(">B")
    brick_name = readData(">B")
    result["inventory"].append({
        "brick_type_id": brick_type_id,
        "color_id": color_id,
        "count": count,
        "brick_name": brick_name,
        "preview_image_url": f"https://img.bricklink.com/P/{color_id}/{brick_image_url}.{links[digint]}"
    })                          # sparer 25 bytes per image ved å kun sende unike delen.
                                # har observert at color_id sendes, og at P sannsynligvis står for PART., trenger da kun image url, og hvilken link type det er.

with open(f"{filename}.json", "w") as f:
    json.dump(result, f, indent=4)

print(size := len(res.content), "bytes received")


