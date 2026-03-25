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
    binData = res.content[offset:offset+length]
    offset += length
    return binData

res = requests.get(f"http://localhost:5000/api/binary/set?id={setid}")

result["set_id"] = readData("B")

result["name"] = readData(">B")

result["year"] = readDataRaw(">H")[0]

result["category"] = readData(">B")

result["preview_image_url"] = readData(">H")

while offset + 2 < len(res.content):
    brick_type_id = 0
    color_id = 0
    count = 0

    mix = res.content[offset]
    if (mix==255): # sjekk om kontroll byte
        offset += 1
        color_id = readDataRaw(">B")[0]
        count = readDataRaw(">H")[0]
        
    else:
        color_id, count = readDataRaw(">BB")
    digcheck = res.content[offset]
    if(digcheck >= 100 and digcheck < 200): # tall under 2^16
        offset += 1
        digint = digcheck - 100
        brick_type_id = str(readDataRaw(">H")[0])
    elif(digcheck >= 200): # 200 er for tall over 2^16
        offset += 1
        digint = digcheck - 200
        brick_type_id = str(readDataRaw(">I")[0])
    else:
        brick_type_id = readData(">B")

    brick_image_url = readData(">H")

    result["inventory"].append({
        "brick_type_id": brick_type_id,
        "color_id": color_id,
        "count": count,
        "preview_image_url": brick_image_url
    })

with open(f"{filename}.json", "w") as f:
    json.dump(result, f, indent=4)

print(size := len(res.content), "bytes received")


