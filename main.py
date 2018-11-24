import xml.etree.ElementTree as ET
import re
import json
import os
from shutil import copyfile
import inflection as inf
import sys
import titlecase
import codecs

srcFolder = sys.argv[1] + "/"
adventureAbv = sys.argv[2]
optional_adv_pre = ""
if len(sys.argv) > 3:
    optional_adv_pre = sys.argv[3]
SCRIPT_VER = 1
if adventureAbv in ["OotA", "CoS"]:
    SCRIPT_VER = 2
elif adventureAbv in ["SKT"]:
    SCRIPT_VER = 3
elif adventureAbv in ["TftYP"]:
    SCRIPT_VER = 4
    if optional_adv_pre in ["DiT", "TFoF", "THSoT", "TSC", "ToH", "WPM"]:
        SCRIPT_VER = 5
elif adventureAbv in ["ToA"]:
    SCRIPT_VER = 90
imgDir = "img/adventure/"+adventureAbv

path = "adventures/" + srcFolder

VALID_BRACKETED_ITEM_SUFFIXES = ["(vial)","(flask)","(bludgeoning)","(piercing)","(slashing)","(ingested)","(inhaled)","(20)","(contact)","(10 feet)","(1 piece)","(cp)","(injury)","(ep)","(gp)","(50 feet)","(1 ounce bottle)","(10)","(10-foot)","(one sheet)","(cloak of elvenkind)","(pp)","(1 day)","(sp)","(amber)","(bloodstone)","(diamond)","(jade)","(lapis lazuli)","(obsidian)","(quartz)","(ruby)","(star ruby)","(topaz)","(1st level)","(2nd level)","(3rd level)","(4th level)","(5th level)","(6th level)","(7th level)","(8th level)","(9th level)","(cantrip)","(phb)","(cos)","(eet)","(stick)","(per day)","(1 sq. yd.)","(beast)","(humanoid)","(monster)","(1 ounce)","(block of incense)","(greasy salve)","(answerer)","(back talker)","(concluder)","(last quip)","(rebutter)","(replier)","(retorter)","(scather)","(squelcher)","(50)","(generic)","(fiends)","(beasts)","(aberrations)","(celestials)","(elementals)","(fey)","(plants)","(undead)","(see below)","(fire giant)","(mammal)","(hill giant)","(spiders)"]
VALID_BRACKETED_SKILL_SUFFIXES = ["athletics","acrobatics","sleight of hand","stealth","arcana","history","investigation","nature","religion","animal handling","insight","medicine","perception","survival","deception","intimidation","performance","persuasion"]

# assorted garbage referred to within FG
IGNORED_LINKS = ["Link: Adventuring Gear Table","Zephyros' Staff","Link: Adventuring Gear","Link: Expenses","Battlemap: Ship Deck","Marks of Prestige","Marks of Presitge","Quest Reward: Silver Berries","Mounted Combat","Link: Wilderness",
                 "Link: Human Names and Ethnicities", "Owning a Ship", "Link: Iron Flask","Supernatural Gift: ","Wilderness Survival","Wyrmskull Throne","Korolnor Scepter","Weather Tables","Banner of the","Blod Stone","Rune}",
                 "Conch of Teleportation","Gurt's Greataxe","Navigation Orb","Potion of Giant Size","Robe of Serpents","Rod of the Vonindod","Becoming Lost"]

IGNORED_TABLES = ["Demonic Attention", "Bolts from above","Coffers","Common Potions","Uncommon Potions","Latrines Parcel","Pagoda Parcel","Dream Tincture Parcel","Weretiger Parcel","Dwarven Gear Parcel","Omuan Art Object","Random Treasure",
                  "Magic Fountain Effects","Alien Growth","Polymorphed","Random Prisoner"

]

IGNORED_TABLE_CAPTION_STRINGS = ["Random Chance", "Random Encounter Chance", "Random Encounter Check", "Random Encouters", "Random Teleport"

]

# script ver : list of tables. If the key is absent, assume we want everything
WHITELISTED_TABLES = {
    5: []
}

MANUAL_SINGULARISE = {
    "young remorhazes": "young remorhaz",
    "rugs of smothering": "rug of smothering",
    "telekinesis": "telekinesis"
}
BEAST_MAP = {
    "half-ogre": "half-ogre (ogrillon)",
    "swarm of insects (spiders": "swarm of spiders",
    "swarm of insects (spiders)": "swarm of spiders",
    "iymrith": "iymrith, ancient blue dragon",
    "yuan-ti malison": "yuan-ti malison (type 1)"
}

ITEM_AND_SPELL_MAP = {
    "scroll of protection (fiends)": "scroll of protection from fiends", "potion of mind control (mammal)": "potion of mind control (beast)", "potion of mind control (fire giant)": "potion of mind control (monster)",
    "supreme healing": "potion of supreme healing", "potion of mind control (hill giant)": "potion of mind control (monster)", "arrow of giant slaying": "arrow of slaying",

    "sansuri's simulacrum (see below)": "simulacrum"
}

ADDITIONAL_JSON = json.load(open("additional_data.json", encoding="utf-8"))

def make_img_dir():
    if not os.path.exists(imgDir):
        os.makedirs(imgDir)

out_dir = "adventure-out/"
def make_out_dir():
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

make_img_dir()
make_out_dir()
root = ET.parse(path+'db.xml').getroot()

out = {"data": []}

beasts = {}
comma_items = []
items = {}
spells = {}
backgrounds = {}


def load_beasts():
    global beasts
    beast_dir = "bestiary/"
    beast_index = json.load(open(beast_dir + "index.json", encoding="utf-8"))

    for src in beast_index:
        from_src = json.load(open(beast_dir + beast_index[src], encoding="utf-8"))

        for mon in from_src["monster"]:
            beasts[mon["name"].lower()] = mon["source"]

    print("loaded beasts")


def load_items():
    loaded = json.load(open("allitems.json", encoding="utf-8"))

    for ii in loaded["item"]:
        items[ii["name"].lower()] = ii["source"]

        if "," in ii["name"]:
            comma_items.append(ii["name"])

    print("loaded items")


def load_spells():
    loaded = json.load(open("allspells.json", encoding="utf-8"))

    for s in loaded["spell"]:
        spells[s["name"].lower()] = {"s": s["source"], "l": s["lvl"]}

    print("loaded spells")


def load_backgrounds():
    loaded = json.load(open("allbackgrounds.json", encoding="utf-8"))

    for b in loaded["background"]:
        backgrounds[b["name"].lower()] = b["source"]

    print("loaded backgrounds")


def get_clean_parts(name):
    clean_parts = re.sub("^([\n.,;:)(/ ]*)(.*?)([\n.,;:)(/ ]*)$", r"\1<SPLITME>\2<SPLITME>\3", name, flags=re.DOTALL)
    (pre, clean_name, suff) = clean_parts.split("<SPLITME>")
    if suff.startswith(")"):
        restored = False
        temp = clean_name.lower()+")"
        for v in VALID_BRACKETED_ITEM_SUFFIXES:
            if temp.endswith(v):
                restored = True
                break
        if not restored:
            temp = clean_name.lower()
            for v in VALID_BRACKETED_SKILL_SUFFIXES:
                if temp.endswith(v):
                    restored = True
                    break

        if restored:
            clean_name = clean_name + ")"
            suff = suff[1:]
    return (pre, clean_name, suff)


def get_clean_parts__minimal(name):
    clean_parts = re.sub("^([ ]*)(.*?)([ ]*)$", r"\1<SPLITME>\2<SPLITME>\3", name, flags=re.DOTALL)
    (pre, clean_name, suff) = clean_parts.split("<SPLITME>")
    return (pre, clean_name, suff)


def get_single(to_convert):
    # to_convert should be lowercase
    to_convert = to_convert.lower()
    if to_convert in MANUAL_SINGULARISE:
        return MANUAL_SINGULARISE[to_convert]
    else:
        return inf.singularize(to_convert)


def getBeastLink(name):
    (pre, clean_name, suff) = get_clean_parts(name)

    if "," in clean_name and "Iymrith" not in clean_name:  # Iymrith has the only comma in a name in regular creatures
        split_names = [s.strip() for s in clean_name.split(",")]
        all_beasts = [getBeastLink(s) for s in split_names]
        is_all_beasts = True
        for b in all_beasts:
            if b is None:
                is_all_beasts = False
                break

        if is_all_beasts:
            to_ret = ", ".join(all_beasts)
            to_ret = pre + to_ret + suff
            return to_ret
        else:
            return None

    low_name = clean_name.lower()
    single = get_single(low_name)

    if low_name in BEAST_MAP:
        low_name = BEAST_MAP[low_name]
    if single in BEAST_MAP:
        single = BEAST_MAP[single]

    if single == low_name:
        single = None

    oot = None
    if low_name in beasts:
        if clean_name.lower() == low_name:
            oot = pre + "{@creature " + clean_name + "|" + beasts[low_name] + "}" + suff
        else:
            oot = pre + "{@creature " + low_name + "|" + beasts[low_name] + "|" + clean_name + "}" + suff
    if single in beasts:
        if oot is not None:
            raize("both single and plural were a beast??")
        else:
            oot = pre + "{@creature " + single + "|" + beasts[single] + "|" + clean_name + "}" + suff

    return oot


def getSpellLevel(name):
    (pre, clean_name, suff) = get_clean_parts(name)

    oot = None
    if len(clean_name.split(" ")) < 10:  # 9 is the longest; there's an item with 9 spaces in the name
        low_name = clean_name.lower()
        vect = vectorise(low_name)

        for v in vect:
            if v in spells:
                oot = int(spells[v]["l"])
                break

        if oot is not None:
            if oot == 0:
                oot = "Cantrip"
            elif oot == 1:
                oot = "1st level"
            elif oot == 2:
                oot = "2nd level"
            elif oot == 3:
                oot = "3rd level"
            else:
                oot = str(oot) + "th level"

        if oot is not None:
            oot = "Spell Scroll (" + oot + ")"

    return oot

# these are both in italics
def getItemOrSpellLink(name, is_probably_spell=False, is_probably_item=False, is_probably_potion_list=False):
    def get_cleaned_potion_name(pot):
        p = pot.strip()
        if p.startswith("oil"):
            return pot
        elif p.startswith("and"):
            temp = p.split(" ", 1)
            return temp[0] + " potion of " + temp[1]
        else:
            return "potion of " + p

    (pre, clean_name, suff) = get_clean_parts(name)
    m = re.fullmatch(r"(a(n)?|and a pair of|and)\s+(.*?)", clean_name)
    if m is not None:
        clean_name = m.group(3)
        pre += m.group(1) + " "

    if "," in clean_name:
        found = False
        for fine in comma_items:
            if fine.strip().lower() == clean_name.strip().lower():
                found = True
                break

        if not found:  # TODO handle combinations of comma-sep items and items with commas in names
            splitNames = [s.strip() for s in clean_name.split(",")]

            if is_probably_potion_list:
                splitNames = [get_cleaned_potion_name(s) for s in splitNames]

            ootStack = []
            for spl in splitNames:
                toAdd = getItemOrSpellLink(spl, is_probably_spell=is_probably_spell, is_probably_item=is_probably_item, is_probably_potion_list=is_probably_potion_list)
                if toAdd is not None:
                    ootStack.append(toAdd)
                else:
                    splitFirstSpace = spl.split(" ", 1)
                    toAdd2 = None
                    if len(splitFirstSpace) > 1:
                        toAdd2 = getItemOrSpellLink(splitFirstSpace[1], is_probably_spell=is_probably_spell, is_probably_item=is_probably_item, is_probably_potion_list=is_probably_potion_list)
                    if toAdd2 is not None:
                        ootStack.append(splitFirstSpace[0] + " " + toAdd2)
                    else:
                        ootStack.append(None)

            if None in ootStack:
                return None
            else:
                to_ret = ", ".join(ootStack)
                to_ret = pre + to_ret + suff
                return to_ret

    oot = None
    if (clean_name.startswith("scroll of ") or clean_name.startswith("spell scroll of ")) and re.search("[,.;]", clean_name) is None:  # TODO handle comma-sep lists?
        if clean_name.startswith("scroll of "):
            spell_name = clean_name.replace("scroll of ", "").strip()
        else:
            spell_name = clean_name[len("spell scroll of "):].strip()
        scrollPart = getSpellLevel(spell_name)
        spellPart = getItemOrSpellLink(spell_name, is_probably_spell=True)

        if scrollPart is not None and spellPart is not None:
            oot = "{@item " + scrollPart + "|DMG|scroll of" + "} " + spellPart
            return pre + oot + suff

    if len(clean_name.split(" ")) < 10:  # 9 is the longest; there's an item with 9 spaces in the name
        low_name = clean_name.lower()

        to_process = low_name

        # check for e.g. "+1 weapon"
        plus_weap = re.fullmatch(r"(\+\d) (.*?)", low_name)
        if plus_weap is not None:
            to_process = plus_weap.group(2) + " " + plus_weap.group(1)

        if to_process in ITEM_AND_SPELL_MAP:
            to_process = ITEM_AND_SPELL_MAP[to_process]

        vect = vectorise(to_process)

        for v in vect:
            if v in items:
                if v == low_name:
                    oot = pre + "{@item " + clean_name + "|" + items[v] + "}" + suff
                else:
                    oot = pre + "{@item " + v + "|" + items[v] + "|" + clean_name + "}" + suff
                break

        for v in vect:
            if v in spells:
                if oot is not None and not is_probably_spell and not is_probably_item:
                    raize("was an item AND a spell?! " + v)

                if v == low_name:
                    oot = pre + "{@spell " + clean_name + "|" + spells[v]["s"] + "}" + suff
                else:
                    oot = pre + "{@spell " + v + "|" + spells[v]["s"] + "|" + clean_name + "}" + suff
                break

    return oot


def vectorise(name):
    spl = name.split(" ")

    perms = 2 ** len(spl)
    oot = [["" for i in range(len(spl))] for j in range(perms)]

    for i in range(len(spl)):
        pos = 0
        alternateAt = 2 ** i
        flip = False
        for j in range(len(oot)):
            if pos % alternateAt == 0:
                flip = not(flip)
            if flip:
                oot[j][i] = get_single(spl[i])
            else:
                oot[j][i] = inf.pluralize(spl[i])
            pos += 1

    for i in range(len(oot)):
        oot[i] = " ".join(oot[i])

    return oot


def get_all_text(tag):
    to_ret = "".join(tag.itertext())
    if tag.tail is not None:
        to_ret += tag.tail.strip()  # generally the tail has a bunch of shitty whitespace; clean it
    return to_ret

def raize(str):
    raise Exception(str)


def checkRaiseText(t):
    if t.text is not None:
        raize("had text!")

def checkRaiseTail(t):
    if t.text is not None:
        raize("had text!")

def checkAddText(t):
    if t.text is not None:
        return t.text
    return ""


def checkAddTail(t):
    if t.tail is not None:
        return t.tail
    return ""

def getQuest(tagName):
    quest = None
    q_ele = root.find("quest").find(tagName)
    if q_ele is not None:
        e = {"type": "entries", "name": "", "entries": []}
        name_ele = q_ele.find("name")
        if name_ele is not None:
            e["name"] = "Quest: " + get_all_text(name_ele)
        desc_ele = q_ele.find("description")
        if desc_ele is not None:
            for c in desc_ele:
                procChild(e, "entries", c)
        quest = e

    return quest


def clean_dice_text(str):
    # clean bracketed dice stuff, e.g. (1d8+ 5) => (1d8+5)
    clean = re.sub('(\(\d+d\d+)\s*([+-])\s*(\d+\))', r'\1\2\3', str.strip())
    # clean non-bracketed dice stuff, e.g. 1d4 + 1 => 1d4+1
    clean = re.sub('(\d+d\d+)\s*([+-])\s*(\d+)', r'\1\2\3', clean)
    return clean


def clean_table_caption(cap):
    oot = re.sub(r"E\d+-\d+-\d+", "", cap).strip()
    oot = re.sub(r"^\d+\.\d+\.\d+", "", oot)
    oot = re.sub(r"^\d+ ", "", oot)
    return oot.strip()


def getTable(tagName):
    tbl = None
    for a in root:
        if a.tag == "tables":

            allTables = []

            for cat in a:
                for t in list(cat):
                    allTables.append(t)

            for table in allTables:
                if table.tag == tagName:
                    e = {
                        "type": "table",
                        "caption": "",
                        "colLabels": [],
                        "colStyles": [],
                        "rows": []
                    }

                    diceCol = None
                    labelCols = None
                    tableRows = None
                    numbered_lbl_cols = {}
                    for ele in table:
                        if ele.tag == "name":
                            e["caption"] = get_all_text(ele)
                        elif ele.tag == "labelcol1":
                            labelCols = get_all_text(ele).strip().split("\t")
                        elif ele.tag.startswith("labelcol"):
                            num = re.sub(r"^labelcol(\d+)$", r"\1", ele.tag)
                            numbered_lbl_cols[num] = ele
                        elif ele.tag == "dice":
                            diceCol = ele
                        elif ele.tag == "tablerows":
                            tableRows = ele
                            if SCRIPT_VER >= 3:
                                un_nested = []
                                for outer in tableRows:
                                    if outer.tag == "category":
                                        un_nested.append(list(outer)[0])
                                    else:
                                        un_nested.append(outer)
                                tableRows = un_nested




                    if e["caption"] == "":
                        del e["caption"]
                    else:
                        e["caption"] = clean_table_caption(e["caption"])

                    def proc_results(results_tag):
                        idE2s = list(results_tag)

                        for ide2 in idE2s:
                            result = ide2.find("result")
                            if result is not None:
                                raw = get_all_text(result)
                                clean = clean_dice_text(raw)
                                r.append(clean)
                                # TODO may need to handle other tag types

                    maxRowWidth = 0
                    if tableRows is not None:
                        for idE in tableRows:
                            r = []
                            stack = ""
                            fromrange_index = None
                            for f in idE:
                                if f.tag == "fromrange":
                                    stack = get_all_text(f)
                                    fromrange_index = len(r)
                                elif f.tag == "torange":
                                    nxt = get_all_text(f)
                                    if nxt != stack:
                                        stack += "-" + nxt
                                    if fromrange_index < len(r):
                                        r.insert(fromrange_index, stack)
                                    else:
                                        r.append(stack)
                                    fromrange_index = None
                                    stack = ""
                                elif f.tag == "results":
                                    proc_results(f)

                                elif f.tag == "category":  # this can be a wrapper around "results" sometimes...
                                    result_tag = f.find("results")
                                    proc_results(result_tag)

                                else:
                                    raize("unknown tag! " + f.tag)

                            e["rows"].append(r)
                            maxRowWidth = max(maxRowWidth, len(r))

                    if labelCols is not None:
                        for c in labelCols:
                            e["colLabels"].append(c)

                    if len(numbered_lbl_cols) > 0:
                        for i in range(2, len(numbered_lbl_cols)+2):
                            ele = numbered_lbl_cols[str(i)]
                            more_cols = get_all_text(ele).split("\t")
                            for col in more_cols:
                                e["colLabels"].append(col)

                    # prepend this if there are fewer cols than row width, as it probably means we left out a dice col
                    if diceCol is not None and len(e["colLabels"]) < maxRowWidth:
                        dice_str = get_all_text(diceCol)
                        if "," in dice_str:
                            # this _seems_ to be for when the dice are added together
                            split = list(filter(lambda ff: len(ff) > 0, list(map(lambda x: x.strip(), dice_str.split(",")))))
                            dice_str_out = "+".join(split)

                            e["colLabels"].insert(0, dice_str_out)
                        else:
                            if dice_str.strip() == "":
                                e["colLabels"].insert(0, "Dice")  # generic if there's no dice specified, handle this later in cleaning
                            else:
                                e["colLabels"].insert(0, dice_str)

                    e["colStyles"] = [""] * len(e["colLabels"])  # fill with blank style attributes

                    tbl = e

                    break
            break
    return tbl


def getImg(forTag):
    def check_name(nom):
        return nom.startswith("Maps") or nom.startswith("Artwork") or nom.endswith("Artwork") or nom.startswith("NPC") or ("Portraits" in nom and "Monster Manual" not in nom) or \
               nom.startswith("DM Maps") or nom.endswith("DM Maps") or \
               nom.endswith("Maps") or nom.endswith("Tarokka") or nom.endswith("Handouts") or nom.startswith("Handouts") or nom.startswith("Handounts") or nom.endswith("NPCs") or \
               nom.startswith("Battlemaps") or nom.endswith("Battlemaps") or nom.endswith("Images")

    title = None

    for cat in root.find("image"):
        nom = cat.attrib["name"]
        if check_name(nom):
            img = cat.find(forTag)
            if img is not None:
                for stuff in img:
                    if stuff.tag == "name":
                        title = stuff.text

    for cat in root.find("image"):
        nom = cat.attrib["name"]
        if check_name(nom):
            img = cat.find(forTag)
            if img is not None:
                for stuff in img:
                    if stuff.tag == "image":
                        for prop in stuff:
                            if prop.tag == "bitmap":

                                imgP = prop.text.split("\\")[-1]
                                outPath = "adventure/"+adventureAbv+"/"+optional_adv_pre+imgP

                                copyfile(path+prop.text, "img/"+outPath)

                                toRet = {"type": "image", "href": { "type": "internal", "path": outPath} }
                                if title is not None:
                                    has_title = True

                                    # clean title

                                    if has_title and "Adventure-Hook" in title or ("Symbol-" in title and "Symbol-of" not in title):
                                        print("REMOVED TITLE: \t" + title)
                                        has_title = False

                                    if "_" in title:
                                        # remove generic names
                                        if has_title and re.match(r"Episode\d+_Cover", title):
                                            has_title = False

                                        # handle "faction_" prefix
                                        if has_title and "faction_" in title:
                                            title = titlecase.titlecase(title.replace("faction_", ""))

                                        if has_title and "_" in title and "-" not in title:
                                            print("REMOVED TITLE: \t" + title)
                                            has_title = False

                                    # handle "Titles-That-Look-Like-This"
                                    if has_title and re.search(r"\w-\w", title):
                                        title = re.sub(r"(\w)-(\w)", r"\1 \2", title)

                                    # remove long runs of characters without spaces
                                    if " " not in title and len(title) > 15:
                                        print("REMOVED TITLE: \t" + title)
                                        has_title = False

                                    if has_title:
                                        toRet["title"] = title

                                return toRet

    otherTrash = None
    for a in root:
        if a.tag == "image":
            for cat in a:
                nom = cat.attrib["name"]
                if nom.startswith("Magic Item") or nom.startswith("Monster") or nom.endswith("Monsters"):
                    for img in cat:
                        if img.tag == forTag:
                            otherTrash = "found"

    if otherTrash is None:
        raize("oi")
    return None


def getNpcText(recordNm):
    def extract_text(from_ele):
        temp_array = []
        temp_obj = {"tmp": temp_array}
        global inListLink
        inListLink = False
        for p_tag in from_ele:
            procChild(temp_obj, "tmp", p_tag)
        inListLink = True
        if len(temp_array) > 1 or len(temp_array) == 0:
            return ""  # FIXME this needs looking in to e.g. 'npc.id-00199' in OotA
            # raize("should only have one element")  # todo might need to merge stuff or have better handling
        return temp_array[0]

    cleanedTag = recordNm.split(".")[1].split("@")[0]

    for cat in root.find("npc"):
        nom = cat.attrib["name"]
        if SCRIPT_VER < 2:
            if "NPC" in nom:
                for npc in cat:
                    if npc.tag == cleanedTag:
                        for stuff in npc:
                            if stuff.tag == "text" and "type" in stuff.attrib and "formattedtext" in stuff.attrib["type"]:
                                return extract_text(stuff)
        else:
            match = cat.find(cleanedTag)
            if match is not None:
                txt = match.find("text")
                return extract_text(txt)

    raize("could not find NPC")



def getFromLink(linkT):
    if "class" in linkT.attrib and ("encounter" in linkT.attrib["class"] or "battle" in linkT.attrib["class"] or "treasureparcel" in linkT.attrib["class"]):
        return None

    if "recordname" in linkT.attrib and "image." in linkT.attrib["recordname"]:
        img = linkT.attrib["recordname"][len("image."):].split("@")[0]
        outtie = getImg(img)

        return outtie
    else:
        txt = get_all_text(linkT)

        if txt == "Parcel" or txt == "Encounter":
            return None

        outtie = ""

        if "class" in linkT.attrib and "npc" in linkT.attrib["class"]:
            if inListLink:
                if SCRIPT_VER >= 2:  # skip these for OotA
                    return None
                npc_text = getNpcText(linkT.attrib["recordname"])
                if npc_text is not "":
                    npc_text = " " + npc_text
                if "NPC:" in txt:
                    outtie += "{@b " + txt.split("NPC:")[1].strip() + "}" + npc_text
                elif " - " in txt and "NPC" in txt.split(" - ")[1]:
                    outtie += "{@b " + txt.split(" - ")[0].strip() + "}" + npc_text
                else:
                    raize("unknown NPC text format")
            else:
                return None

        else:
            outtie += "{@link "
            outtie += "".join(txt)
            outtie += "}"

        return outtie


def is_fake_h(para):
    # if it has one child which is a bold tag, and begins with chapter stuff
    return SCRIPT_VER >= 2 and para.tag == "p" and len(list(para)) == 1 and list(para)[0].tag == "b" and get_all_text(list(para)[0]).strip() == list(para)[0].text and re.match(r"^\d+(\w+)?\. ", list(para)[0].text.strip())

inListLink = False
slashS = False
last_tag = None
list_link_template = False
def procChild(parent, parentKey, para):
    def clean_link(it):
        global list_link_template
        if it is None:
            return None
        if "(magic item)" in it:
            pass
        elif it.endswith("Item}") or "Item:" in it:
            pass
        elif it.endswith("Spell}") or "Spell: " in it or "Spell Rock: " in it:
            pass
        elif "Player's Handbook" in it or it.startswith("{@link D&D") or "Dungeon Masters Guide" in it or "Dungeon Master's Guide" in it:
            pass
        elif "Appendix" in it:
            pass
        elif re.match(r"^{@link (.*?)}$", it) is not None and re.sub(r"^{@link (.*?)}$", r"\1", it).lower().strip() in spells:
            pass
        elif "Ammunition:" in it or "Weapon:" in it or "Armor:" in it:
            pass
        elif "Template:" in it:
            if inListLink:
                list_link_template = True
            if len(appendTo) > 0 and isinstance(appendTo[-1], str) and "template" in appendTo[-1].lower():
                appendTo.pop()
        elif "Parcel:" in it:
            pass
        else:
            if SCRIPT_VER >= 3:
                for u in IGNORED_LINKS:
                    if u.lower() in it.lower():
                        return None
            return it

        return None

    def clean_list(l):
        c_l = []
        for it in l:
            if it is not None:
                if isinstance(it, str) and "{@link" in it:
                    cleaned = clean_link(it)

                    if cleaned is not None:
                        c_l.append(it)
                else:
                    c_l.append(it)
        return c_l

    global list_link_template
    global slashS
    global last_tag
    toSlashS = False
    appendTo = parent[parentKey]
    nextLevel = None

    stack = ""

    if para.tag == "p" or para.tag == "li":

        if para.text is not None:
            stack += para.text.replace("\\s", "\n")
            if "\\s" in para.text:
                # toSlashS = True
                pass

        lookahead_cache = list(para)
        # for each tag
        t_index = 0
        t_index_max = len(list(para))-1
        for t in para:
            if len(list(t)) > 0:
                if t.text is not None:
                    raize("had text!")

                if len(list(t)) == 1 and list(t)[0].tag == "i" and ("Dungeon Master's Guide" in list(t)[0].text or "Player's Handbook" in list(t)[0].text or "Monster Manual" in list(t)[0].text):
                    stack += get_all_text(list(t)[0])
                # an inline header
                elif len(list(t)) == 1 and ((t.tag == "b" and list(t)[0].tag == "i") or (t.tag == "i" and list(t)[0].tag == "b")):
                    if len(stack) > 0:
                        raize("probably a Fantasy Grounds data issue - clean the data")
                        appendTo.append(stack)
                        stack = ""

                    nextName = (""+list(t)[0].text).strip().rstrip(".")
                    next = {"type": "entries", "name": nextName, "entries": []}
                    appendTo.append(next)
                    appendTo = next["entries"]
                else:
                    raize("para p had children")

                if t.tail is not None:
                    stack += t.tail

            else:
                if t.tag == "b":
                    if is_fake_h(para):
                        # this seems to be a level 1 header
                        nextLevel = {"type": "entries", "name": t.text, "entries": []}
                        appendTo.append(nextLevel)
                        appendTo = nextLevel["entries"]
                    elif get_all_text(t).strip() != "":
                        beastLinkMb = getBeastLink(t.text)

                        # it might be an item link if it's in ToA
                        if beastLinkMb is None and adventureAbv == "ToA":
                            beastLinkMb = getItemOrSpellLink(t.text, is_probably_item=True)

                        if beastLinkMb is None:
                            pre, clean, suff = "", "", ""
                            if stack.strip() == "":
                                (pre, clean, suff) = get_clean_parts__minimal(t.text)
                            else:
                                (pre, clean, suff) = get_clean_parts(t.text)
                            stack += pre + "{@b " + clean + "}" + suff
                        else:
                            stack += beastLinkMb
                        stack += checkAddTail(t)
                elif t.tag == "i":
                    if get_all_text(t).strip() != "":
                        is_probably_spell = "spell" in stack.lower() or "cantrip" in stack.lower() or "slot" in stack.lower() or "level" in stack.lower()
                        is_probably_item = t.text is not None and ("gear" in t.text or "saddle" in t.text)
                        is_probably_potion_list = SCRIPT_VER >= 3 and len(stack) >= 12 and "potion" in stack[-12:]
                        itemLinkMb = getItemOrSpellLink(t.text, is_probably_spell=is_probably_spell, is_probably_item=is_probably_item, is_probably_potion_list=is_probably_potion_list)

                        # :^)
                        if t.text == "spell scrolls: command, cure wounds (2nd level), inflict wounds (2nd level), and guiding bolt (2nd level).":
                            itemLinkMb = "{@item spell scroll (2nd level)|DMG|spell scrolls}: {@spell command|PHB}, {@spell cure wounds|PHB|cure wounds (2nd level)}, {@spell inflict wounds|PHB|inflict wounds (2nd level)}, amd {@spell guiding bolt|PHB|guiding bolt (2nd level)}."

                        if itemLinkMb is None:
                            lookahead_index = lookahead_cache.index(t)
                            spell_scroll_link = None
                            if lookahead_index < len(lookahead_cache) - 1 and lookahead_cache[lookahead_index+1].tag == "i" and "scroll" in t.text:
                                next_text = lookahead_cache[lookahead_index+1].text
                                (nxtpre, nxtclean, nxtsuff) = get_clean_parts(next_text)
                                spell_level_mb = getSpellLevel(nxtclean)
                                if spell_level_mb is not None:
                                    (pre, clean, suff) = get_clean_parts(t.text)
                                    spell_scroll_link = pre + "{@item " + spell_level_mb + "|DMG|" + clean + "}" + suff

                            if spell_scroll_link is not None:
                                stack += spell_scroll_link
                            else:
                                pre, clean, suff = "", "", ""
                                if stack.strip() == "":
                                    (pre, clean, suff) = get_clean_parts__minimal(t.text)
                                else:
                                    (pre, clean, suff) = get_clean_parts(t.text)
                                stack += pre + "{@i " + clean + "}" + suff
                        else:
                            stack += itemLinkMb
                        stack += checkAddTail(t)
                else:
                    raize("unknown p para tag")
            t_index += 1

        if para.tail is not None and para.tail.strip() != "":
            stack += para.tail
    elif para.tag == "list":
        stack = {"type": "list", "items": []}

        # for each tag
        for t in para:
            if t.tag == "li":
                procChild(stack, "items", t)
            elif t.tag == "p":
                # append to the previous list item
                stack["items"][-1] = stack["items"][-1] + get_all_text(t)
            else:
                raize("unknown list para tag")

        stack["items"] = clean_list(stack["items"])
        if len(stack["items"]) == 0:
            stack = ""  # hack to ignore this list

    elif para.tag == "listlink" or para.tag == "linklist":
        global inListLink
        inListLink = True
        stack = {"type": "list", "items": []}

        # for each tag
        for t in para:
            if t.tag == "link":
                procChild(stack, "items", t)

                if len(appendTo) > 0 and list_link_template and isinstance(appendTo[-1], str) and "template" in appendTo[-1].lower():
                    appendTo.pop()
                list_link_template = False

                # move images and tables outside the list
                if len(stack["items"]) > 0 and isinstance(stack["items"][-1], dict) and "type" in stack["items"][-1] and (stack["items"][-1]["type"] == "image"):
                    appendTo.append(stack["items"].pop())

            elif t.tag == "h":  # todo add these to a list, check if we really want to ignore them all
                pass
            elif t.tag == "i" or t.tag == "b":
                if len(stack["items"]) > 0 and isinstance(stack["items"][-1], str) and re.match(r"{@link .*?}", stack["items"][-1]) is not None:
                    stack["items"][-1] = stack["items"][-1].split("}")[0] + get_all_text(t).strip() + "}"
            else:
                raize("unknown list para tag")

        stack["items"] = clean_list(stack["items"])
        if len(stack["items"]) == 0:
            stack = ""  # hack to ignore this list

        inListLink = False

    elif para.tag == "link":
        if para.attrib["class"] == "quest":
            quest = para.attrib["recordname"].split(".")[1].split("@")[0].strip()
            questOut = getQuest(quest)

            if len(stack) > 0:
                appendTo.append(stack)
                stack = ""

            appendTo.append(questOut)
        elif para.attrib["class"] == "table":
            tbl = para.attrib["recordname"].split(".")[1].split("@")[0].strip()
            tblOut = getTable(tbl)

            if len(stack) > 0:
                appendTo.append(stack)
                stack = ""

            appendTo.append(tblOut)

        else:
            fromLink = getFromLink(para)
            if fromLink is None:
                pass
            elif isinstance(fromLink, str):
                fromLink = clean_link(fromLink)
                if fromLink is not None:
                    stack += fromLink
            else:
                if len(stack) > 0:
                    appendTo.append(stack)
                    stack = ""

                appendTo.append(fromLink)


    elif para.tag == "table":
        if para.text is not None:
            stack += para.text

        overwrite_last = False
        if SCRIPT_VER >= 2 and len(appendTo) > 0:
            last = appendTo[-1]
            if isinstance(last, dict) and "type" in last and last["type"] == "list" and len(last["items"]) == 1 and last["items"][0]["type"] == "table":
                overwrite_last = True

        cap = None
        if SCRIPT_VER < 2:
            cpSrch = re.fullmatch('^.*{@b (.*)}$', stack)
            if cpSrch is not None:
                cap = cpSrch.group(1)
                stack = stack[:-cap.length]

        if len(stack.strip()) > 0:
            appendTo.append(stack)
        stack = ""

        tbl = {
            "type": "table",
            "caption": cap,
            "colLabels": [],
            "colStyles": [],
            "rows": []
        }

        # first TR is the headers
        # ... unless it's script 2.0+ in which case first TR is the caption :joy:
        def handle_head_row(tbl, tr):
            for td in tr:
                # TODO handle colspan
                # pad_to = None
                # if "colspan" in td.attrib:
                #     pad_to = int(td.attrib["colspan"])-1
                tbl["colLabels"].append(get_all_text(td).strip())
                # if pad_to is not None:
                #     for i in range(0, pad_to):
                #         tbl["colLabels"].append("")
            tbl["colStyles"] = [""] * len(tbl["colLabels"])  # fill with blank style attributes

        def handle_row_row(tbl, tr):
            # TODO handle colspan
            row = []
            for td in tr:
                temp = get_all_text(td)
                clean = clean_dice_text(temp)
                row.append(clean)
            tbl["rows"].append(row)

        use_last_header = False
        if SCRIPT_VER >= 2:
            if last_tag.tag == "h" and "name" in parent:
                cap = parent["name"]
                tbl["caption"] = cap
                use_last_header = True
            elif len(appendTo) > 0 and isinstance(appendTo[-1], str) and re.match(r"{@b .*?}", appendTo[-1].strip()):
                cap = re.sub(r"{@b (.*?)}", r"\1", appendTo.pop())
                tbl["caption"] = cap
                use_last_header = True

        no_caption = False
        def check_all_bold(tr):
            for td in tr:
                b_child = td.find("b")
                if b_child is not None and (td.text is None or td.text.strip() == "") and (td.tail is None or td.tail.strip() == ""):
                    pass
                else:
                    return False
            return True

        if SCRIPT_VER >= 2:
            first_row = list(para)[0]
            second_row = list(para)[1]
            # if the first rows is all bolded text and the second row is not, the first row is not a caption
            all_bold_first = check_all_bold(first_row)
            all_bold_second = check_all_bold(second_row)

            if all_bold_first and not all_bold_second:
                no_caption = True

        i = 0
        for tr in para:
            if i == 0:
                if SCRIPT_VER < 2 or use_last_header or no_caption:
                    handle_head_row(tbl, tr)
                else:
                    cap = get_all_text(tr).strip()
                    tbl["caption"] = cap

            elif i == 1:
                if SCRIPT_VER >= 2 and not use_last_header and not no_caption:
                    handle_head_row(tbl, tr)
                else:
                    handle_row_row(tbl, tr)

            else:
                handle_row_row(tbl, tr)

            i += 1

        if cap is None:
            del tbl["caption"]
        else:
            tbl["caption"] = clean_table_caption(tbl["caption"])

        if overwrite_last:
            appendTo[-1] = tbl
        else:
            appendTo.append(tbl)

        if para.tail is not None:
            stack += para.tail

    elif para.tag == "frame":
        if len(stack) > 0:
            appendTo.append(stack)
            stack = ""

        inset = {"type": "inset", "entries": []}
        has_prev_inset = False
        prev_inset = None  # multiple frame tags in a row are one frame
        if len(appendTo) > 0:
            if isinstance(appendTo[-1], dict) and "type" in appendTo[-1] and (appendTo[-1]["type"] == "inset" or appendTo[-1]["type"] == "insetReadaloud"):
                prev_inset = appendTo[-1]

        if len(list(para)) == 0:
            if prev_inset is not None:
                inset = prev_inset
                has_prev_inset = True
            inset["entries"].append(get_all_text(para))
        else:
            for c in para:
                if c.tag == "frameid":
                    if c.text == "DM":
                        if prev_inset is not None:
                            inset = prev_inset
                            has_prev_inset = True
                        inset["type"] = "insetReadaloud"
                        fakeP = ET.Element("p")
                        fakeP.text = c.tail
                        procChild(inset, "entries", fakeP)
                    else:
                        inset["name"] = c.text
                        if prev_inset is not None and "name" in prev_inset and prev_inset["name"] == inset["name"]:
                            inset = prev_inset
                            has_prev_inset = True
                        fakeP = ET.Element("p")
                        fakeP.text = c.tail
                        procChild(inset, "entries", fakeP)
                elif c.tag == "p" or c.tag == "link":
                    if prev_inset is not None:
                        inset = prev_inset
                        has_prev_inset = True
                    if para.text is not None:
                        inset["entries"].append(para.text)
                    procChild(inset, "entries", c)
                    if para.tail is not None:
                        inset["entries"].append(para.tail)
                elif c.tag == "b":
                    if prev_inset is not None:
                        inset = prev_inset
                        has_prev_inset = True
                    fakeP = ET.Element("p")
                    fakeP.text = para.text
                    fakeP.tail = para.tail
                    fakeP.append(c)
                    procChild(inset, "entries", fakeP)
                else:
                    raize("unknown frame child type")

        if not has_prev_inset:
            appendTo.append(inset)

    elif para.tag == "frameid":
        stack = para.tail

    elif para.tag == "h":
        if not is_ignored_header(para.text):
            header_text = titlecase.titlecase(para.text).strip()

            squash = False
            if "name" in parent and len(appendTo) == 0:
                intro_m = re.fullmatch(r"Chapter \d+ Introduction", parent["name"])
                if intro_m is not None:
                    squash = True

                intro_m = re.fullmatch(r"Epilogue Introduction", parent["name"])
                if intro_m is not None:
                    squash = True

                intro_m = re.fullmatch(r"Appendix \w+ Introduction", parent["name"])
                if intro_m is not None:
                    squash = True

                clean_parent_name = parent["name"].rstrip(".").lstrip(".")

                clean_parent_name = re.sub(r"^(\w+\.)(\w+(\.)?)+( .*?)$", r"\1\4", clean_parent_name)

                if header_text.lower() == clean_parent_name.lower():
                    squash = True

                if clean_parent_name.lower().endswith(header_text.lower()):
                    no_tail = clean_parent_name[:-len(header_text)]
                    m = re.fullmatch(r"(\w+(\.)?)* ", no_tail)
                    if m is not None:
                        squash = True

                    m = re.fullmatch(r"Level \d+[.:] ", no_tail)
                    if m is not None:
                        # inverse squash
                        header_text = clean_parent_name
                        squash = True

                if header_text.lower().endswith(clean_parent_name.lower()):
                    no_tail = header_text[:-len(clean_parent_name)]
                    m = re.fullmatch(r"(\w+(\.)?)* ", no_tail)
                    if m is not None:
                        squash = True

                if "Temple Reinforcements -" in clean_parent_name:
                    squash = True

            if squash:
                # TODO this is not always desirable
                # replace the name instead of going deeper
                parent["name"] = header_text
                nextLevel = parent
            else:
                nextLevel = {"type": "entries", "name": header_text, "entries": []}
                appendTo.append(nextLevel)
                appendTo = nextLevel["entries"]
        else:
            nextLevel = parent

    elif para.tag == "i" and get_all_text(para).strip() == "":  # handle random empty <i> tags
        pass
    elif para.tag == "b" and get_all_text(para).strip() == "":  # handle random empty <b> tags
        pass
    elif para.tag == "i" and "dungeon masters guide" in para.text.lower().replace("'", ""):
        stack += get_all_text(para).strip()
    else:
        raize("unknown para tag " + para.tag)


    if len(stack) > 0 and "Developer's Note:" not in stack and "NOTE:" not in stack and "{@b Note:" not in stack:
        if slashS:
            appendTo[-1] += stack
        else:
            slashS = False
            appendTo.append(stack)

    slashS = toSlashS
    last_tag = para

    return nextLevel

# init a dictionary of beast names
load_beasts()
# init a dictionary of item names
load_items()
# init a dictionary of spell names
load_spells()
# init a dictionary of backgrounds
load_backgrounds()


def is_ignored_header(text):
    to_compare = text.lower()

    if adventureAbv == "CoS" and ("appendix b" in to_compare or "appendix c" in to_compare or "appendix d" in to_compare):
        return False

    if adventureAbv == "SKT" and ("appendix a" in to_compare or "appendix b" in to_compare or "appendix c" in to_compare):
        return False

    return to_compare == "foreward" or to_compare == "forward" or "afterword" in to_compare or re.match(r"Z\w\. ", to_compare) or "conversion notes" in to_compare \
           or to_compare == "credits" or "table of contents" in to_compare or "foreword: " in to_compare or "fantasy grounds" in to_compare or "content" == to_compare or \
           "foreword" == to_compare or "appendix " in to_compare or "appendices" in to_compare


def handle_enc(enc):
    global out
    section = {}

    to_process = enc
    if SCRIPT_VER > 1:
        # handle "id-00001" wrappers and sort by name
        to_process = []
        temp = {}

        for id_head in enc:
            name = get_all_text(id_head.find("name"))
            temp[name] = id_head

        sorted_keys = list(temp.keys())
        sorted_keys.sort()
        for k in sorted_keys:
            to_process.append(temp[k])

    # process each header
    isFirst = True
    hasAny = False
    for head in to_process:
        if "contents" in head.tag or "credits" in head.tag or "conversionnotes" in head.tag or "_index_" in head.tag:
            pass
        else:
            name = head.find("name")
            text = head.find("text")

            # process name
            procName = re.sub('P\d+-\d+(\.\d+\w*)?(\.)?', '', name.text)  # handle LMoP style

            procName = re.sub('E\d+-\d+-\d+', '', procName).strip()  # handle HotDQ style

            procName = re.sub('P\d+-\d+', '', procName).strip()  # handle RoT style

            procName = re.sub('^\d+\.\d+\.\d+\.\d+(\w+)? ', '', procName).strip()  # handle OotA style

            procName = re.sub('^\d+\.\d+\.\d+ ', '', procName).strip()  # handleTftYP style

            procName = re.sub('^\d+\.\d+\.(\d+\w+\.)*(\d+\w+)*', '', procName).strip()  # handle CoS style

            procName = re.sub('^\d+\.\d+\.\w\d+(\w+) ', '', procName).strip()  # handle PotA style
            procName = re.sub('^\d+\.\d+\.\d+\.\d+ ', '', procName).strip()  # handle PotA style
            procName = re.sub('^\d+\.\d+\.\d+ ', '', procName).strip()  # handle PotA style
            procName = re.sub('^\d+\.\d+', '', procName).strip()  # handle PotA style

            procName = re.sub('\(Index\)', '', procName.strip())

            procName = re.sub(r"^\(+(.*)\)+$", r"\1", procName)  # remove leading and trailing brackets

            entry = {"type": "entries", "name": procName.strip(), "entries": []}

            workinOn = entry

            if is_ignored_header(entry["name"]):
                workinOn = None
                continue

            hasAny = True

            # make entries
            for para in text:
                if len(list(para)) > 0:

                    if is_fake_h(para):
                        workinOn = procChild(entry, "entries", para)
                    else:
                        procChild(workinOn, "entries", para)
                else:
                    if para.tag == "h":
                        workinOn = procChild(entry, "entries", para)
                    else:
                        procChild(workinOn, "entries", para)

            #
            if isFirst:
                section = entry
                section["type"] = "section"
                isFirst = False
            else:
                if not len(entry["entries"]) == 0:
                    section["entries"].append(entry)
    if hasAny:
        out["data"].append(section)


for child in root:
    if child.tag == "encounter":
        # process each section
        for enc in child:
            handle_enc(enc)


def recursive_clean(map, do_tables=False, first_clean=False, first_table_clean=False):
    def remove_space_dot_comma(str):
        return re.sub(r" +([.,])", r"\1", str)

    def clean_it(old_list):
        new_list = []
        for e in old_list:
            if e is None:
                pass
            elif isinstance(e, dict):
                recursive_clean(e, do_tables=do_tables, first_clean=first_clean, first_table_clean=first_table_clean)
                new_list.append(e)
            else:
                # it's a string

                # fix any \n stuff
                if "\n" in e or "\t" in e or "\r" in e:
                    for nu in re.split(r"[\n\t\r]", e):
                        if len(nu.strip()) > 0:
                            new_list.append(remove_space_dot_comma(nu.strip()))
                else:
                    new_list.append(remove_space_dot_comma(e))

        return new_list

    def clean_rows(old_rows):
        new_rows = []
        for r in old_rows:
            new_r = []
            for cell in r:
                new_r.append(cell.replace("[", "").replace("]", ""))
            new_rows.append(new_r)
        return new_rows

    def clean_cols(old_cols, curr_rows):
        new_cols = old_cols
        if re.match(r"^Encounter(s)?(Dice)+$", "".join(old_cols)):
            new_cols = ["Dice", "Encounter"]

        if new_cols[0] == "Dice":
            # try and figure out what dice it should be from the row
            lowest = 999
            highest = 0
            probably_dice = True
            for r in curr_rows:
                m = re.match(r"^(\d+)(-(\d+))?$", r[0].strip())
                if m is not None:
                    if m.group(1) is not None:
                        lowest = min(lowest, int(m.group(1)))
                        highest = max(highest, int(m.group(1)))
                    if m.group(3) is not None:
                        highest = max(highest, int(m.group(3)))
                else:
                    probably_dice = False

            VALID_FACES = [3, 4, 6, 8, 10, 12, 20, 100]
            if probably_dice and lowest == 1 and highest in VALID_FACES:
                new_cols[0] = "d" + str(highest)
            elif probably_dice and lowest == 0 and highest == 99:
                new_cols[0] = "d100"
        return new_cols

    def clean_styles(curr_cols, curr_styles):
        new_styles = []
        for c in curr_cols:
            # if it's a dice column
            m = re.match(r"^(\d+)?d\d+(\+(\d+)?d\d+)?$", c.strip())
            if m is not None:
                new_styles.append("col-1 text-align-center")
            else:
                new_styles.append("")
        return new_styles

    def add_bgs(curr_cols, old_rows):
        if curr_cols[0] == "Background" and len(curr_cols) == 3:
            new_rows = []
            for r in old_rows:
                new_r = []
                i = 0
                for cell in r:
                    if i == 0:
                        if cell.lower() in backgrounds:
                            new_cell = "{@background " + cell + "|" + backgrounds[cell.lower()] + "}"
                            new_r.append(new_cell)
                        else:
                            raize("unknown background " + cell.lower())
                    else:
                        new_r.append(cell)
                    i += 1
                new_rows.append(new_r)
            return new_rows
        else:
            return old_rows

    if not isinstance(map, dict) or "type" not in map:
        return

    type = map["type"]
    if type == "entries" or type == "section" or type == "inset" or type == "insetReadaloud":
        map["entries"] = clean_it(map["entries"])

        # convert types
        if "name" in map and map["name"].startswith("Sidebar: "):
            map["name"] = map["name"][len("Sidebar: "):]
            map["type"] = "inset"

        # add missing content
        if first_clean:
            if adventureAbv == "LMoP" and "name" in map and map["name"] == "The Brown Horse":
                map["entries"].append(ADDITIONAL_JSON["LMOP_SIDEBAR_ASH_ZOMBIES"])
            if adventureAbv == "LMoP" and "name" in map and map["name"] == "Abbreviations":
                map["entries"] = ADDITIONAL_JSON["LMOP_TABLE_ABBREVIATIONS"]["entries"]

            if adventureAbv == "TftYP" and optional_adv_pre == "TFoF" and "name" in map and map["name"] == "Aftermath":
                for add in ADDITIONAL_JSON["TFTYP_TFOF_AFTERMATH"]:
                    map["entries"].append(add)
    elif type == "list":
        map["items"] = clean_it(map["items"])
    elif type == "table" and do_tables:
        map["rows"] = clean_rows(map["rows"])
        map["colLabels"] = clean_cols(map["colLabels"], map["rows"])
        if first_table_clean and adventureAbv == "ToA":
            map["rows"] = add_bgs(map["colLabels"], map["rows"])
        map["colStyles"] = clean_styles(map["colLabels"], map["colStyles"])


def recursive_prune(map):
    def are_all_rows_rollables(row_arr):
        all_rollables = True
        for row in row_arr:
            true_for_row = True
            for it in row:
                if re.match(r"^(\[.*?]|\d+)*$", it.strip()) is None:
                    true_for_row = False
                    break
            if not true_for_row:
                all_rollables = False
                break
        return all_rollables

    def is_single_rollable(row_arr):
        return (len(row_arr[0]) > 0 and re.match(r"^.*?\[.*?].*?$", row_arr[0][0]) is not None) or \
            (len(row_arr[0]) > 1 and re.match(r"^.*?\[.*?].*?$", row_arr[0][1]) is not None)

    def is_ignored_caption(caption):
        if caption.strip() in IGNORED_TABLES:
            print("REMOVED TABLE: " + caption)
            return True
        for sub in IGNORED_TABLE_CAPTION_STRINGS:
            if sub in caption.strip():
                print("REMOVED TABLE: " + caption)
                return True
        return False

    if not isinstance(map, dict) or "type" not in map or ("entries" not in map and "items" not in map):
        return

    rep = []
    key = "entries"
    if "items" in map and "entries" not in map:
        key = "items"
    for e in map[key]:
        # entries
        if isinstance(e, dict) and "type" in e and "entries" in e and len(e["entries"]) == 0:
            pass
        # if a table matches the header above it, shift it up
        elif isinstance(e, dict) and "type" in e and "entries" in e and len(e["entries"]) == 1 and "caption" in e["entries"][0] and e["entries"][0]["caption"] == e["name"]:
            rep.append(e["entries"][0])
        # table
        elif isinstance(e, dict) and "type" in e and "rows" in e and (
                                    ("caption" in e and is_ignored_caption(e["caption"])) or
                                    len(e["rows"]) == 0 or
                                  (len(e["rows"]) == 1 and len(e["rows"][0]) == 0) or
                                  (SCRIPT_VER <= 3 and len(e["rows"]) >= 1 and is_single_rollable(e["rows"])) or
                                  (SCRIPT_VER <= 4 and len(e["rows"]) == 1 and is_single_rollable(e["rows"])) or
                                  (SCRIPT_VER <= 4 and are_all_rows_rollables(e["rows"])) or
                                  (SCRIPT_VER >= 5 and (are_all_rows_rollables(e["rows"]) or (len(e["rows"]) == 1 and is_single_rollable(e["rows"]))) and SCRIPT_VER in WHITELISTED_TABLES and "caption" in e and e["caption"] not in WHITELISTED_TABLES[SCRIPT_VER]) or
                                  (len(e["rows"]) >= 1 and len(e["rows"][0]) == 1 and re.match(r"^\s*\d+\s*", e["rows"][0][0]) is not None)):
            pass
        else:
            recursive_prune(e)
            if isinstance(e, dict) and e["type"] == "list" and len(e["items"]) == 0:
                pass
            else:
                rep.append(e)
    map[key] = rep


def recursive_table_unlist(map):
    def clean_it(old_list):
        new_list = []
        for e in old_list:
            # if in entries and the child is a list with table(s) in it's items, pop them and add them after the list
            if isinstance(e, dict) and "type" in e and e["type"] == "list":
                bad_i_s = []
                put_after = []
                # pull all the tables out the list
                for i, li in enumerate(e["items"]):
                    if isinstance(li, dict) and li["type"] == "table":
                        bad_i_s.append(i)
                        put_after.append(li)

                # remove the tables from the original list
                for i in sorted(bad_i_s, reverse=True):
                    del e["items"][i]

                recursive_table_unlist(e)
                new_list.append(e)
                for after in put_after:
                    new_list.append(after)
            elif isinstance(e, dict):
                recursive_table_unlist(e)
                new_list.append(e)
            else:
                # it's a string
                new_list.append(e)

        return new_list

    # move tables outside of lists
    if not isinstance(map, dict) or "type" not in map:
        return

    type = map["type"]
    if type == "entries" or type == "section" or type == "inset" or type == "insetReadaloud":
        map["entries"] = clean_it(map["entries"])
    elif type == "list":
        map["items"] = clean_it(map["items"])


rep_list = {"data": []}
for s in out["data"]:
    skip_SKT = adventureAbv == "SKT" and (s["name"] == "Special NPCs")
    skip_ToA = s["name"] == "Character Backgrounds" and adventureAbv == "ToA"
    skip_WPM = s["name"] == "Note" and optional_adv_pre == "WPM"
    skip_ToH = s["name"] == "Legend of the Tomb" and optional_adv_pre == "ToH"
    skip_PotA = adventureAbv == "PotA" and s["name"] == "Aarakocra Scouts"

    if "Monsters and Magic Items" in s["name"] or "Appendices" in s["name"] or s["name"] == "Afterward" or s["name"] == "Sector Encounter" or \
            skip_ToH or skip_WPM or s["name"] == "Monsters and NPCs" or skip_ToA \
            or s["name"] == "Monster Hunter's Pack" or skip_SKT or skip_PotA:
        pass
    elif len(s["entries"]) == 0:
        pass
    else:
        recursive_clean(s, first_clean=True)
        recursive_prune(s)
        # second pass after pruning tables, to clean any remaining rollable stuff
        recursive_clean(s, do_tables=True, first_table_clean=True)
        # third pass, un-listing tables and cleaning/pruning
        recursive_table_unlist(s)
        recursive_clean(s, do_tables=True)
        recursive_prune(s)

        if not len(s["entries"]) == 0:
            rep_list["data"].append(s)
out = rep_list

ALL_TEXT = json.dumps(out, indent='\t', ensure_ascii=False)
ALL_TEXT = re.sub(" \([sS]ee [aA]ppendix .\)", "", ALL_TEXT)
ALL_TEXT = ALL_TEXT.replace("\u0093", "\\\"")
ALL_TEXT = ALL_TEXT.replace("\u0094", "\\\"")
ALL_TEXT = ALL_TEXT.replace("\u0092", "'")
ALL_TEXT = re.sub(r" +", " ", ALL_TEXT)
# compact dice expressions
ALL_TEXT = re.sub(r"([1-9]\d*)?d([1-9]\d*)(\s?)([+-])(\s?)(\d+)?", r"\1d\2\4\6", ALL_TEXT)

print("done!")

out_file = out_dir + "adventure-" + adventureAbv.lower()
if optional_adv_pre != "":
    out_file += "-" + optional_adv_pre.lower()
out_file += ".json"
with codecs.open(out_file, mode="w", encoding="utf-8") as out_f:
    out_f.write(ALL_TEXT)
