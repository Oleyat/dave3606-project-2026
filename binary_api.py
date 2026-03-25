import json

import requests
import struct

setid = "10312-1"
filename = "result"

result = {"set_id": setid,
        "name": "",
        "year": "",
        "category": "",
        "preview_image_url": "",
        "inventory": []}

def retLen(offset, format):
    return struct.unpack_from(format, res.content, offset)[0]

def retData(offset, length):
    return res.content[offset:offset+length].decode("utf-8")

length, offset = 0
res = requests.get(f"http://localhost:5000/api/binary/set?id={setid}")
length = retLen(offset, "B")
offset += 1
result["set_id"] = retData(offset, length)

offset += length

length = retLen(offset, ">B")
offset += 1
result["name"] = retData(offset, length)

offset += length

result["year"] = struct.unpack_from(">H", res.content, offset)[0]

offset += 2

length = retLen(offset, ">B")
offset += 1
result["category"] = retData(offset, length)

offset += length

length = retLen(offset, ">H")
offset += 2
result["preview_image_url"] = retData(offset, length)

offset += length

while offset + 2 < len(res.content):
    brick_type_id = 0
    color_id = 0
    count = 0

    mix = res.content[offset]
    if (mix==255): # sjekk om kontroll byte
        offset += 1

        color_id = struct.unpack_from(">B", res.content, offset)[0]
        offset += 1
        count = struct.unpack_from(">H", res.content, offset)[0]
        offset +=2
        
    else:
        color_id, count = struct.unpack_from(">BB", res.content, offset)
        offset += 2
    digcheck = res.content[offset]
    if(digcheck >= 100 and digcheck < 200): # tall under 2^16
        offset += 1
        digint = digcheck - 100
        brick_type_id = str(struct.unpack_from(">H", res.content, offset)[0])
        offset += 2
    elif(digcheck >= 200): # 200 er for tall over 2^16
        offset += 1
        digint = digcheck - 200
        brick_type_id = str(struct.unpack_from(">I", res.content, offset)[0])
        offset += 4
    else:
        length = retLen(offset, ">B")
        offset += 1
        brick_type_id = retData(offset, length)
        offset += length

    result["inventory"].append({
        "brick_type_id": brick_type_id,
        "color_id": color_id,
        "count": count
    })

with open(f"{filename}.json", "w") as f:
    json.dump(result, f, indent=4)

print(size := len(res.content), "bytes received")


