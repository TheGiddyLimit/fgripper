import xml.etree.ElementTree as ET
import re
import json
import os
from shutil import copyfile

gods = {}
out = []

data = json.load(open("gods/deities.json", encoding="utf-8"))

for g in data["deity"]:
    if g["source"] == "SCAG":
        gods[g["name"]] = g

root = ET.parse("gods/god.xml").getroot()

for ref in root:
    n = ref.find("name")
    if n.text.strip() not in gods:
        print("send help")

    proc_text = []
    append_to = proc_text

    for t in ref.find("text"):
        if t.tag == "p":
            head = t.text.strip() if t.text is not None else ""
            if len(head) > 0:
                append_to.append(head)

            for sub in t:
                if sub.tag == "i":
                    append_to.append("{@i " + sub.text.strip() + "}")
                else:
                    print("send help")

            tail = t.tail.strip() if t.tail is not None else ""
            if len(tail) > 0:
                append_to.append(tail)
        elif t.tag == "link":
            append_to.append({
                "type": "image",
                "href": {
                    "type": "internal",
                    "path": "deities/" + t.text.strip().replace("Image: ", "").strip() + ".jpg"
                }
            })
        elif t.tag == "h":
            nxt = {
                "type": "inset",
                "name": t.text.strip(),
                "entries": []
            }
            proc_text.append(nxt)
            append_to = nxt["entries"]
        else:
            print("send help")

    gods[n.text.strip()]["entries"] = proc_text

for nm, g in gods.items():
    out.append(g)

ALL_TEXT = json.dumps(out, indent="\t", ensure_ascii=False)
ALL_TEXT = ALL_TEXT.replace(u"\u2014", u"\\u2014")
print("done!")