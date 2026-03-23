import json

import requests
import struct
setid = "10220-1"
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

length = 0
offset = 0
res = requests.get(f"http://localhost:5000/api/binary/set?id={setid}")
length = retLen(offset, "I")
offset += 4
result["set_id"] = retData(offset, length)

offset += length

length = retLen(offset, ">I")
offset += 4
result["name"] = retData(offset, length)

offset += length

length = retLen(offset, ">H")
offset += 2
result["year"] = retData(offset, length)

offset += length

length = retLen(offset, ">I")
offset += 4
result["category"] = retData(offset, length)

offset += length

length = retLen(offset, ">I")
offset += 4
result["preview_image_url"] = retData(offset, length)

while offset + 4 < len(res.content):
    brick_type_id = 0
    color_id = 0
    count = 0

    offset += length

    length = retLen(offset, ">I")
    offset += 4
    brick_type_id = retData(offset, length)

    offset += length

    length = retLen(offset, ">I")
    offset += 4
    color_id = retData(offset, length)

    offset += length

    length = retLen(offset, ">I")
    offset += 4
    count = retData(offset, length)

    result["inventory"].append({
        "brick_type_id": brick_type_id,
        "color_id": color_id,
        "count": count
    })

with open("result.json", "w") as f:
    json.dump(result, f, indent=4)



