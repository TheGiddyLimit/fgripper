# FG token grabbin' script for 5etools; requires Python 3

import xml.etree.ElementTree as ET
import json
import re
import os
from shutil import copyfile

OUT_DIR = "img/ToB (3pp)/"  # mirror the 5etools dir for ease of copy-paste. TRAILING SLASH IMPORTANT
IN_5ETOOLS_JSON = "bestiary/bestiary-3pp-tob.json"
IN_FG_ROOT = "other/Tome of Beasts/"  # TRAILING SLASH IMPORTANT
IN_FG_XML = IN_FG_ROOT + "db.xml"

beasts = []
from_fg = {}
out = {}


def throw(txt):
    raise Exception(txt)


def make_img_dir():
    img_dir = OUT_DIR
    if not os.path.exists(img_dir):
        os.makedirs(img_dir)


def load_names():
    from_src = json.load(open(IN_5ETOOLS_JSON))

    for mon in from_src["monster"]:
        beasts.append(mon["name"])

    print("loaded beasts")


def load_tokens():
    tree = ET.parse(IN_FG_XML)
    root = tree.getroot()
    for m_root in root.find("reference").find("npcdata"):
        name = m_root.find("name").text
        token = m_root.find("token").text.split("@")[0]
        from_fg[name] = token


def match_names():
    found = []
    for name in beasts:
        if name in from_fg:
            out[name] = from_fg[name]
            del from_fg[name]
            found.append(name)
    for f in found:
        beasts.remove(f)


def morph_names():
    to_add = {}
    to_remove = []
    for name in from_fg:
        if re.match(r"^([\w ]+), (.*)$", name):
            new_name = re.sub(r"^([\w ]+), (.*)$", r"\2 \1", name)
            to_add[new_name] = from_fg[name]
            to_remove.append(name)
    for r in to_remove:
        del from_fg[r]
    for a in to_add:
        from_fg[a] = to_add[a]


def manual_morph_names():
    map = {
        "Abolythe Nihilith":                                                          "Nihileth",
        "Akyishigal Demon Lord of Cockroaches":                                       "Akyishigal, Demon Lord of Cockroaches",
        "Alquam Demon Lord of Night":                                                 "Alquam, Demon Lord of Night",
        "Apau Perape Demon":                                                          "Apau Perape",
        "Arch-Devil Arbeyach, Prince of Swarms Devil":                                "Arch-Devil Arbeyach, Prince of Swarms",
        "Arch-Devil Ia'Affrat the Insatiable Devil":                                  "Arch-Devil Ia'Affrat the Insatiable",
        "Arch-Devil Mammon, Archduke of Greed Devil":                                 "Arch-Devil Mammon, Archduke of Greed",
        "Arch-Devil Totivillus, Scribe of Hell Devil":                                "Arch-Devil Totivillus, Scribe of Hell",
        "Baba Yaga's Horsemen, Black Knight":                                         "Baba Yaga's Horsemen (Black Night)",
        "Baba Yaga's Horsemen, Bright Day":                                           "Baba Yaga's Horsemen (Bright Day)",
        "Baba Yaga's Horsemen, Red Sun":                                              "Baba Yaga's Horsemen (Red Sun)",
        "Baba Yaga's Horsemen, base":                                                 "N/A",
        "Berstuc Demon":                                                              "Berstuc",
        "Boreas":                                                                     "Avatar of Boreas",
        "Camazotz Demon Lord of Bats and Fire":                                       "Camazotz, Demon Lord of Bats and Fire",
        "Emperor Ghoul":                                                              "Emperor of the Ghouls",
        "Fire Dancers Swarm":                                                         "Fire Dancer Swarm",
        "Gbahali":                                                                    "Gbahali (Postosuchus)",
        "Gypsosphinx Sphinx":                                                         "Gypsosphinx",
        "Havoc Runner Gnoll":                                                         "Gnoll Havoc Runner",
        "Hraesvelgr Giant":                                                           "Hraesvelgr, The Corpse Swallower",
        "Imy-ut Ushabti":                                                             "",
        "Koralk (Harvester Devil) Devil":                                             "Koralk (Harvester Devil)",
        "Malakbel Demon":                                                             "Malakbel",
        "Malphas":                                                                    "Malphas (Storm Crow)",
        "Mbielu Dinosaur":                                                            "Mbielu",
        "Mechuiti Demon Lord of Cannibal Apes":                                       "Mechuiti, Demon Lord of Apes",
        "Ngobou Dinosaur":                                                            "Ngobou",
        "Prismatic Beetles Swarm":                                                    "Prismatic Beetle Swarm",
        "Qorgeth Demon Lord of Worms":                                                "Qorgeth, Demon Lord of The Devouring Worm",
        "Rime Worm Adult":                                                            "Adult Rime Worm",
        "Rubezahl Demon":                                                             "Rubezahl",
        "Spinosaurus Dinosaur":                                                       "Spinosaurus",
        "Swamp Adder Snake":                                                          "Swamp Adder",
        "Theullai":                                                                   "Thuellai",
        "Urochar":                                                                    "Urochar (Strangling Watcher)",
        "Wolf Spirits Swarm":                                                         "Wolf Spirit Swarm",
        "Wyrmling Cave Dragon":                                                       "Cave Dragon Wyrmling",
        "Wyrmling Flame Dragon":                                                      "Flame Dragon Wyrmling",
        "Wyrmling Sea Dragon":                                                        "Sea Dragon Wyrmling",
        "Wyrmling Void Dragon":                                                       "Void Dragon Wyrmling",
        "Wyrmling Wind Dragon":                                                       "Wind Dragon Wyrmling",
        "Yakat-Shi Eater of Dust":                                                    "Eater of Dust (Yakat-Shi)",
        "Young Spinosaurus Dinosaur":                                                 "Young Spinosaurus",
        "Zanskaran Viper Snake":                                                      "Zanskaran Viper",
    }
    new_from_fg = {}
    global from_fg
    for name in from_fg:
        if name in map:
            new_from_fg[map[name]] = from_fg[name]
        else:
            throw("unmapped name: " + name)
    from_fg = new_from_fg


def make_images():
    for name in out:
        copyfile(IN_FG_ROOT + out[name], OUT_DIR + name + ".png")

make_img_dir()
load_names()
start_count = len(beasts)
load_tokens()
match_names()
morph_names()
match_names()
manual_morph_names()
match_names()
end = len(beasts)  # should be 0

if end != 0:
    throw("Beasts found in 5etools data that didn't exist in FG data?")
    for it in beasts:
        print(it)

make_images()


print("done!")
