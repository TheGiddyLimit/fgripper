import json
import os
import codecs

pages = {}

mapped = {
    'Bone Devil Polearm': "Bone Devil", 'Half-Ogre (Ogrillon)': "Half-Ogre", 'Ice Devil Spear': "Ice Devil", 'Lizard King': "Lizard King/Queen", 'Lizard Queen': "Lizard King/Queen", 'Succubus': "Succubus/Incubus", 'Incubus': "Succubus/Incubus",
    "Bone Naga (Guardian)": "Bone Naga", "Bone Naga (Spirit)": "Bone Naga", "Cave Bear": "Polar Bear", 'Drider Spellcaster': "Drider", 'Giant Rat (Diseased)': "Giant Rat", 'Gray Ooze (Psychic)': "Gray Ooze",
    'Swarm of Beetles': "Swarm of Insects", 'Swarm of Centipedes': "Swarm of Insects", 'Swarm of Spiders': "Swarm of Insects", 'Swarm of Wasps': "Swarm of Insects", 'Thri-kreen (Psionic)': "Thri-kreen", 'Ultroloth': "Ultraloth",
    'Yuan-ti Malison (Type 1)': "Yuan-ti Malison", 'Yuan-ti Malison (Type 2)': "Yuan-ti Malison", 'Yuan-ti Malison (Type 3)': "Yuan-ti Malison", 'Duergar Kavalrachni': "Duergar Darkhaft", 'Duergar Keeper of the Flame': "Duergar Darkhaft",
    'Duergar Xarron': "Duergar Darkhaft", 'Ixitxachitl Cleric': "Ixitxachitl", 'Vampiric Ixitxachitl Cleric': "Vampiric Ixitxachitl", 'Burrowshark': 'Burrow Shark', 'Iymrith, Ancient Blue Dragon': "Iymrith the Dragon",
    'Black Guard Drake': "Guard Drake", 'Blue Guard Drake': "Guard Drake", 'Deep Rothé': "Rothe", 'Green Guard Drake': 'Guard Drake', 'Illithilich': "Mind Flayer Lich (Illithilich)", 'Mind Flayer Psion': "Mind Flayer Lich (Illithilich)",
    'Ox': "Dolphin", 'Red Guard Drake': "Guard Drake", 'Rothé': "Rothe", 'White Guard Drake': "Guard Drake", 'Al-Aeshma Genie': "Al-Aeshma", 'Arch-Devil Arbeyach, Prince of Swarms': "Arbeyach", 'Avatar of Boreas': "Boreas",
    'Baba Yaga\'s Horsemen (Bright Day)': "Baba Yagas Horsemen", 'Baba Yaga\'s Horsemen (Red Sun)': "Baba Yagas Horsemen", 'Baba Yaga\'s Horsemen (Black Night)': "Baba Yagas Horsemen", 'Chort Devil': "Cohort Devil",
    'Fidele Angel': "Fidele", 'Gbahali (Postosuchus)': "Gbahali", 'Darakhul Ghoul': "Darakhul", 'Hraesvelgr, The Corpse Swallower': "Hraesvelgr the Corpse Swallower", 'Arch-Devil Ia\'Affrat the Insatiable': "Ia'Affrat", 'Kishi Demon': "Kishi",
    'Malphas (Storm Crow)': "Malphas", 'Arch-Devil Mammon, Archduke of Greed':  "Mammon", 'Psoglav Demon': "Psoglav", 'Queen of Night and Magic': "Sarastra, Queen of Night and Magic", 'Queen of Witches': "Nicnevin, Queen of Witches",
    'Shadow Fey Duelist': "Shadow Fey", 'Shadow Fey Enchantress': "Shadow Fey",'Shadow Fey Forest Hunter': "Shadow Fey", 'Shadow Fey Guardian': "Shadow Fey",'Thuellai': "Theullai", 'Arch-Devil Totivillus, Scribe of Hell': "Totivillus, Scribe of Hell",
    'Vile Barber': "Vile Barber (Siabhra)", "Black Dracolisk": "Dracolisk", 'Blue Dracolisk': "Dracolisk", 'Green Dracolisk': "Dracolisk", 'Red Dracolisk': "Dracolisk", 'White Dracolisk': "Dracolisk", 'Teratashia, Demon Princess of Dimensions': "Teratashia",
'Thalasskoptis, Demon Prince': "Thalasskoptis"

}


def load_beasts():
    out_dir = "bestiary-out/"
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    beast_dir = "bestiary/"

    beast_index = json.load(open(beast_dir + "index.json", encoding="utf-8"))

    for src in beast_index:
        from_src = json.load(open(beast_dir + beast_index[src], encoding="utf-8"))

        if src.lower() in pages:
            for mon in from_src["monster"]:
                name = mon["name"]
                if name in mapped:
                    name = mapped[name]

                found = False
                for pg in pages[src.lower()]:
                    if name.lower().strip() == pg["name"].lower().strip():
                        mon["page"] = int(pg["source"].split(".")[1])
                        found = True

                if not found and ("page" not in mon or mon["page"] == 0):
                    print("couldnt find mosnter with name")

            with codecs.open(out_dir + beast_index[src], "w", encoding="utf-8") as outfile:
                json.dump(from_src, outfile, indent="\t")
        else:
            if src not in ["DMG", "LMoP", "PSA", "PSI", "PSK", "PSZ", "PSX", "XGE"]:
                print("no page number file for source!")

    print("loaded beasts")


def load_pages():
    global pages
    page_dir = "pagenum/"
    for root, dirs, files in os.walk(page_dir):
        for filename in files:
            from_src = json.load(open(page_dir + filename), encoding="utf-8")
            pages[filename.split(".")[0].lower()] = from_src


load_pages()
print("loaded pages")
load_beasts()
print("done!")
