import os
import json
import codecs


damages = {}
resistances = {}

manual = {
    "spells-xge.json": {
        "Chaos Bolt": [
            "ASJKDHASJKDHSA" # TODO
        ]
    }
}

all_keys = {}

def load_spells():
    global damages
    global resistances
    out_dir = "spells-out/"
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    spells_dir = "spells/"

    spells_index = json.load(open(spells_dir + "index.json", encoding="utf-8"))

    for src in spells_index:
        filename = spells_index[src]
        from_src = json.load(open(spells_dir + filename, encoding="utf-8"))

        if filename in damages:
            for spl in from_src["spell"]:
                name = spl["name"]

                if name in damages[filename]:
                    for k, v in damages[filename][name].items():
                        proc_key = k
                        if proc_key == "distant":
                            proc_key = "inflict"
                        proc_key = "damage" + str(proc_key[0:1]).upper() + proc_key[1:]
                        all_keys[proc_key] = True
                        spl[proc_key] = v

        with codecs.open(out_dir + spells_index[src], "w", encoding="utf-8") as outfile:
            to_write = json.dumps(from_src, indent="\t", ensure_ascii=False)
            to_write = to_write.replace(u"\u2014", u"\\u2014")
            outfile.write(to_write)

    print("processed spells")


def load_damage():
    global damages
    global resistances
    with codecs.open("spell_damage.txt", "r", encoding="utf-8") as infile:
        for line in infile:
            line = line.strip()

            if line != "":
                spl = [x.replace("\"", "").strip() for x in line.split(",")]
                file = spl[0]
                nm = spl[1]
                prop = spl[2]
                typ = spl[3].lower()

                if file not in damages:
                    damages[file] = {}
                if nm not in damages[file]:
                    damages[file][nm] = {}
                if prop not in damages[file][nm]:
                    damages[file][nm][prop] = []
                damages[file][nm][prop].append(typ)


load_damage()
load_spells()
print("done!")
