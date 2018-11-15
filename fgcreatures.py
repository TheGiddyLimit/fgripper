import xml.etree.ElementTree as ET
import re
import json
import os
from shutil import copyfile, rmtree
import codecs

# A script to rip FG module creatures
# If extracting fluff, before use, have to tag an image category in reference data with `id="pickme"` to have it be used
# NOTE: THERE CAN BE MULTIPLE. TAG THEM ALL.
# i.e. root -> image -> <category id="pickme" ... >

# After this script has been run, `mon-fix.js` in the main project should be used to convert the output to valid data
# FG has an annoying habit of including creatures from other sources, and objects, which will need to be removed
#  (Some filtering can be done here with FILTER_TRAPS and FILTER_EXISTING)
# Once the creatures are clean, the fluff can be cleaned, using `fluffer.js` in the main project

# CONFIGURABLE STUFF
SOURCE = "GGR"
IMG_DIR = "img/" + SOURCE + "/"
FLUFF_IMAGE_DIR = "img/bestiary/" + SOURCE + "/"
BASE_DIR = "books/DD Guildmaster's Guide to Ravnica/"
INPUT_DB = BASE_DIR + "db-cleaned.xml"
DO_FLUFF = True
IS_ADVENTURE = False
AUTO_YES = True # setting this to "true" forces all creatures to be exported, no matter how junky
ONLY_FLUFF = False
FILTER_OBJECTS = True
FILTER_EXISTING = False
SHOW_NAMES = True
DO_TRANSFER = True
_TRANSFER_DIR = "../astranauta.github.io/trash_in/"
# END CONFIGURABLE STUFF

def log(tag, text):
    print("[" + tag.rjust(13, " ") + "] " + text)

# load existing monsters, so we can avoid re-dumping them
beasts = {}

def load_beasts():
    global beasts
    beast_dir = "bestiary/"
    beast_index = json.load(open(beast_dir + "index.json", encoding="utf-8"))

    for src in beast_index:
        from_src = json.load(open(beast_dir + beast_index[src], encoding="utf-8"))

        for mon in from_src["monster"]:
            beasts[mon["name"].lower()] = mon["source"]

    log("META", "Loaded creatures.")
load_beasts()


MAPPED_NAMES = {
    "swarm of insects (centipedes)": "swarm of centipedes",
    "swarm of insects (spiders)": "swarm of spiders",
    "swarm of insects (wasps)": "swarm of wasps",
}


def map_clean_name(clean_name):
    if clean_name in MAPPED_NAMES:
        return MAPPED_NAMES[clean_name]
    return clean_name

def debug_stringify(ele):
    return ET.tostring(ele, encoding="utf8", method="html").decode('utf-8')


def make_img_dir():
    if os.path.exists(IMG_DIR):
        rmtree(IMG_DIR)
    os.makedirs(IMG_DIR)

    if os.path.exists(FLUFF_IMAGE_DIR):
        rmtree(FLUFF_IMAGE_DIR)
    os.makedirs(FLUFF_IMAGE_DIR)


def make_out_dir():
    out_dir = "bestiary-out/"
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)


def clean_dice_text(str):
    # clean bracketed dice stuff, e.g. (1d8+ 5) => (1d8+5)
    clean = re.sub('(\(\d+d\d+)\s*([+-])\s*(\d+\))', r'\1\2\3', str.strip())
    # clean non-bracketed dice stuff, e.g. 1d4 + 1 => 1d4+1
    clean = re.sub('(\d+d\d+)\s*([+-])\s*(\d+)', r'\1\2\3', clean)
    return clean


CAPITALISE_LANGUAGES = [
    "Abyssal",
    "Aquan",
    "Auran",
    "Celestial",
    "Common",
    "Draconic",
    "Dwarvish",
    "Elvish",
    "Giant",
    "Gnomish",
    "Goblin",
    "Halfling",
    "Infernal",
    "Orc",
    "Primordial",
    "Sylvan",
    "Terran",
    "Undercommon",

    "Thieves' cant",
    "Druidic"
]

CAPITALISE_LANGUAGES_RES = {}
for lang in CAPITALISE_LANGUAGES:
    CAPITALISE_LANGUAGES_RES[lang] = re.compile(lang, re.IGNORECASE)

OUT = {"monster": []}

make_img_dir()
make_out_dir()
root = ET.parse(INPUT_DB).getroot()


def get_or_none(parent, key):
    if parent.find(key) is None:
        return None
    return parent.find(key).text


ALL_ELES = {}
FLUFF = {"bullshit": []}
img_total = 0


# if actions are wrapped in IDs, break them out
def handle_id(action):
    if len(action) == 1 and list(action)[0].tag.startswith("id-00"):
        return list(action)[0]
    return action


def dump_sters(to_loop):
    global img_total
    for mon in to_loop:
        if mon.find("name").text.strip().lower().endswith("template"):
            continue

        name = mon.find("name").text.strip()
        ster = {
            "name": name,
            "size": mon.find("size").text[0],
            "type": mon.find("type").text.strip(),
            "source": SOURCE,
            "alignment": mon.find("alignment").text.strip(),
            "ac": mon.find("ac").text.strip(),
            "hp": mon.find("hp").text.strip(),
            "speed": mon.find("speed").text.strip() if mon.find("speed") is not None else "0 ft.",
            "str": int(mon.find("abilities").find("strength").find("score").text),
            "dex": int(mon.find("abilities").find("dexterity").find("score").text),
            "con": int(mon.find("abilities").find("constitution").find("score").text),
            "int": int(mon.find("abilities").find("intelligence").find("score").text),
            "wis": int(mon.find("abilities").find("wisdom").find("score").text),
            "cha": int(mon.find("abilities").find("charisma").find("score").text),
            "save": get_or_none(mon, "savingthrows"),
            "skill": {},
            "resist": get_or_none(mon, "damageresistances"),
            "immune": get_or_none(mon, "damageimmunities"),
            "conditionImmune": get_or_none(mon, "conditionimmunities"),
            "vulnerable": get_or_none(mon, "damagevulnerabilities"),
            "passive": "",
            "languages": get_or_none(mon, "languages"),
            "cr": get_or_none(mon, "cr"),
            "page": 0
        } if not ONLY_FLUFF else None

        # remove e.g. "Drow (U)"
        clean_name = ster["name"].strip().lower()
        no_end_paren_name = re.sub(r" \([a-z]\)$", "", clean_name)
        if clean_name != no_end_paren_name:
            continue

        # check for traps
        if not ONLY_FLUFF and FILTER_OBJECTS:
            attribs = ["str", "dex", "con", "int", "wis", "cha"]
            clean_type = ster["type"].strip().lower()
            if (clean_type == "construct" and len([x for x in attribs if int(ster[x]) == 10]) == 6) or clean_type.startswith("object") or clean_type.startswith("hazard"):
                log("FILTER_OBJECT", "Filtered object/trap/hazard:" + ster["name"])
                continue

        # check for existing creatures
        if not ONLY_FLUFF and FILTER_EXISTING:
            mapped_clean_name = map_clean_name(clean_name)
            if mapped_clean_name in beasts:
                if beasts[mapped_clean_name] != "MM":
                    log("FILTER_CREATURE", "!!Filtered non-MM existing creature!!:" + ster["name"])
                else:
                    log("FILTER_CREATURE", "Filtered existing creature:" + ster["name"])
                continue

            # # FIXME this handles small substrings poorly (e.g. "ox" in "urstul floxin")
            # for low_name in beasts.keys():
            #     if low_name in clean_name:
            #         answer = input("'" + clean_name + "' was a sub-string of '" + low_name + "'. Skip it? (y/n)\n").lower().strip()
            #         if answer == "y":
            #             continue
            #         else:
            #             break

        if mon.find("text") is not None and DO_FLUFF:
            link = mon.find("text").find("link")
            if link is None:
                listlink = mon.find("text").find("linklist")
                if listlink is not None:
                    link = listlink.find("link")

            to_append = {
                "name": name,
                "fluff": ET.tostring(mon.find("text"), encoding="utf8", method="html").decode('utf-8')
            }
            if link is not None:
                img_loc = link.attrib["recordname"]
                img_loc_tag = img_loc.split("@")[0].split(".")[-1]

                # label it something we can easily find
                img_roots = root.find("reference").find("imagedata").findall(".//*[@id='pickme']") if not IS_ADVENTURE else root.find("image").findall("category")
                if len(img_roots) == 0:
                    raise Exception("No image categories specified")
                img_ele = None
                for img_root in img_roots:
                    it = img_root.find(img_loc_tag)
                    if it is not None:
                        img_ele = it

                if img_ele is not None:
                    img_path = img_ele.find("image").find("bitmap").text.strip()
                    clean_path = img_path.strip().replace("images\\", "")
                    to_append["image_path"] = clean_path
                    img_total += 1
                    copyfile(BASE_DIR + img_path, FLUFF_IMAGE_DIR + clean_path)

            FLUFF["bullshit"].append(to_append)

        if not ONLY_FLUFF:
            if "(" in ster["type"]:
                new_type = {}
                spl = ster["type"].split("(")
                spl[1] = spl[1].replace(")", "")
                new_type["type"] = spl[0].lower().strip()
                if "," in spl[1]:
                    new_type["tags"] = [x.strip() for x in spl[1].split(",")]
                else:
                    new_type["tags"] = [spl[1].strip()]
                ster["type"] = new_type
            else:
                ster["type"] = ster["type"].lower()

            if mon.find("actext") is not None and mon.find("actext").text is not None:
                ster["ac"] += " " + mon.find("actext").text

            raw_hd = mon.find("hd")
            if raw_hd is not None:
                hit_dice = raw_hd.text
                ster["hp"] += " " + clean_dice_text(hit_dice)

            if mon.find("skills") is not None:
                skill = [x.strip() for x in mon.find("skills").text.split(",")]
                for s in skill:
                    spl = s.split(" ")
                    bonus = spl[-1]
                    key = " ".join(spl[:-1]).lower().strip()
                    if key == "intimidate":
                        key = "intimidation"
                    ster["skill"][key] = bonus.strip()
            else:
                del(ster["skill"])

            # TODO test this
            if "skill" in ster and "perception" in ster["skill"]:
                ster["passive"] = 10 + int(ster["skill"]["perception"])
            else:
                ster["passive"] = 10 + int(mon.find("abilities").find("wisdom").find("bonus").text)

            senses = get_or_none(mon, "senses")
            if senses is not None:
                rx = re.compile(r"(, )?passive perception \d+", re.IGNORECASE)
                senses = re.sub(rx, "", senses)
                # if for some FG reason PP wasn't the final entry, clean any leading commas
                senses = re.sub(r"^,\s*", "", senses)
                ster["senses"] = senses.lower()

            if ster["languages"] is not None:
                for lang_title, lang_re in CAPITALISE_LANGUAGES_RES.items():
                    ster["languages"] = re.sub(lang_re, lang_title, ster["languages"])

            if mon.find("traits") is not None:
                traits = []
                for t in mon.find("traits"):
                    t = handle_id(t)
                    name_text = t.find("name").text
                    traits.append({
                        "name": name_text,
                        "entries": [x.strip() for x in t.find("desc").text.split(r"\r")]
                    })
                ster["trait"] = traits

            if mon.find("actions") is not None:
                actions = []
                for a in mon.find("actions"):
                    a = handle_id(a)
                    name = a.find("name").text
                    entries = []
                    if a.find("desc").text is None:
                        log("FLUFF", "Missing desc for action " + name + " in " + ster["name"])
                    else:
                        entries = [x.strip() for x in a.find("desc").text.split(r"\r")]

                    actions.append({
                        "name": name,
                        "entries": entries
                    })

                clean_actions = [a for a in actions if a["name"].strip().lower() != "none"]
                if len(clean_actions) > 0:
                    ster["action"] = clean_actions
                elif len(clean_actions) != len(actions):
                    log("ACTIONS", "Removed " + str(len(actions)) + " actions")
            else:
                log("ACTIONS", ster["name"] + " had no actions?!")

            if mon.find("legendaryactions") is not None:
                actions = []
                for a in mon.find("legendaryactions"):
                    a = handle_id(a)
                    name = a.find("name").text
                    if "actions per round" not in name.lower():
                        actions.append({
                            "name": name,
                            "entries": [x.strip() for x in a.find("desc").text.split(r"\r")]
                        })
                ster["legendary"] = actions

            if mon.find("reactions") is not None:
                reactions = []
                for a in mon.find("reactions"):
                    a = handle_id(a)
                    name = a.find("name").text
                    entries = []
                    if a.find("desc").text is None:
                        print("missing desc for action " + name + " in " + ster["name"])
                    else:
                        entries = [x.strip() for x in a.find("desc").text.split(r"\r")]

                        reactions.append({
                            "name": name,
                            "entries": entries
                        })
                ster["reaction"] = reactions

            if ster["passive"] == "":
                del ster["passive"]

            img = mon.find("token").text.split("@")[0]
            try:
                copyfile(BASE_DIR + img, IMG_DIR + ster["name"] + ".png")
            except:
                log("FLUFF_IMAGE", "Image error for " + ster["name"])

            for ele in mon:
                ALL_ELES[ele.tag] = 1

            to_clean = []
            for k in ster:
                if ster[k] is None:
                    to_clean.append(k)
            for k in to_clean:
                del ster[k]
            OUT["monster"].append(ster)

if IS_ADVENTURE:
    def loop_cats():
        for cat in root.find("npc").findall("category"):
            looper = True
            while looper:
                answer = None
                if AUTO_YES:
                    print("Parsing this garbage... '" + cat.attrib["name"] + "'")
                    answer = "y"
                else:
                    answer = input("Parse this garbage: '" + cat.attrib["name"] + "'? (y/n)\n").lower().strip()

                if answer in ["y", "ya", "yes"]:
                    dump_sters(cat)
                    looper = False
                elif answer in ["n", "no"]:
                    looper = False
                elif answer in ["q", "quit"]:
                    return
                else:
                    print("Please answer y/n")
    loop_cats()

else:
    dump_sters(root.find("reference").find("npcdata"))

print("Total creatures: " + str(len(OUT["monster"])))
if SHOW_NAMES:
    print("===== SHOWING NAMES =====")
    lst = list(map(lambda x: x["name"], OUT["monster"]))
    lst.sort()
    for name in lst:
        print(name)
    print("===== ============= =====")

ALL_TEXT = json.dumps(OUT, indent='\t', ensure_ascii=False)
ALL_TEXT = re.sub(r" +", " ", ALL_TEXT)
ALL_TEXT = re.sub(r"([Ss]ee .*?, )(below)", r"\1above", ALL_TEXT)

ALL_FLUFF = json.dumps(FLUFF, indent='\t', ensure_ascii=False)
ALL_FLUFF = re.sub(r" +", " ", ALL_FLUFF)
ALL_FLUFF = re.sub(r"(\\t|\\n)+", "", ALL_FLUFF)
ALL_FLUFF = re.sub(r"([Ss]ee .*?, )(below)", r"\1above", ALL_FLUFF)
ALL_FLUFF = re.sub(r"<text.*?>", "", ALL_FLUFF)
ALL_FLUFF = re.sub(r"</text>", "", ALL_FLUFF)
ALL_FLUFF = re.sub(r"\s*<\s*b\s*>\s*Image\s*:\s*<\s*/\s*b\s*>\s*", "", ALL_FLUFF)
print("Total images: " + str(img_total))

out_path_filename = "bestiary-" + SOURCE.lower() + ".json"
out_path = "trash/" + out_path_filename
print("Writing data to " + out_path)
file = codecs.open(out_path, "w", "utf-8")
file.write(ALL_TEXT)
file.close()

out_path_fluff_filename = "fluff-bestiary-" + SOURCE.lower() + ".json"
out_path_fluff = "trash/" + out_path_fluff_filename
print("Writing fluff to " + out_path_fluff)
file = codecs.open(out_path_fluff, "w", "utf-8")
file.write(ALL_FLUFF)
file.close()

if DO_TRANSFER:
    print("Transferring to '" + _TRANSFER_DIR + "'")
    copyfile(out_path, _TRANSFER_DIR + out_path_filename)
    copyfile(out_path_fluff, _TRANSFER_DIR + out_path_fluff_filename)


print("Done!")
