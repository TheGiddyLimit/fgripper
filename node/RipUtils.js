const fs = require("fs");
const ut = require("./MiscUtils");
const u5 = require("../5etools/utils");
const er = require("../5etools/entryrender");

const SKIP_UNOFFICIAL = true; // TODO allow this to be set somehow

let refsLoaded = false;

const _TAGGERS = {};
function taggerGenerator (it, tag, defSource) {
	const id = `${tag}___${it.source}`;
	if (_TAGGERS[id]) return _TAGGERS[id];
	else {
		const tagger = (text, baseName) => {
			if (baseName != null) {
				return `{@${tag} ${baseName}|${it.source}|${text}}`;
			} else {
				return `{@${tag} ${text}${it.source === defSource ? "" : `|${it.source}`}}`;
			}
		};
		_TAGGERS[id] = tagger;
		return tagger;
	}
}

function loadMulti (dir, prop, storage, tag, defSource) {
	const index = require(`../${dir}/index.json`);

	Object.keys(index).forEach(src => {
		if (SKIP_UNOFFICIAL && SourceUtil.isNonstandardSource(src)) return; // skip UA/etc

		const data = require(`../${dir}/${index[src]}`);
		data[prop].forEach(it => {
			storage[it.name.toLowerCase()] = taggerGenerator(it, tag, defSource);
		})
	});
}

// spell reference
const SPELLS = {};
function loadSpells () {
	loadMulti("spells", "spell", SPELLS, "spell", "PHB");
}

// creature reference
const CREATURES = {};
function loadCreatures () {
	loadMulti("bestiary", "monster", CREATURES, "creature", "MM");
}

// item reference
const ITEMS = {};
function pLoadItems () {
	const itemUrls = {
		items: "./items/items.json",
		basicitems: "./items/basicitems.json",
		magicvariants: "./items/magicvariants.json"
	};

	return new Promise(resolve => {
		DataUtil.loadJSON = (url, ...otherData) => {
			return new Promise(resolve => {
				const json = JSON.parse(fs.readFileSync(url, "utf8"));
				resolve(json, otherData)
			});
		};
		er.EntryRenderer.item.buildList(
			(allItems) => {
				allItems.forEach(it => {
					if (SKIP_UNOFFICIAL && SourceUtil.isNonstandardSource(it.source)) return; // skip UA/etc
					ITEMS[it.name.toLowerCase()] = taggerGenerator(it, "item", "DMG");
				});
				resolve();
			},
			itemUrls,
			true
		)
	});
}

function pPreloadReferences () {
	return new Promise(resolve => {
		if (!refsLoaded) {
			if (SKIP_UNOFFICIAL) ut.warn("SCRIPT", `Non-standard references are being skipped!`);
			loadSpells();
			loadCreatures();
			refsLoaded = true;
		}

		pLoadItems.then(() => resolve());
	});
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

const _AMBIGUOUS = {};

// TODO expand this as required
// null is used as "give this italics, but not a @book tag"
const BOOK_TITLES = {
	"player's handbook": "phb",
	"dungeon master's guide": "dmg",
	"monster manual": "mm",
	"xanathar's guide to everything": "xge",
	"volo's guide to monsters": "vgm",
	"mordenkainen's tome of foes": "mtf",
	"sword coast adventurer's guide": "scag",

	"volo's guide to spirits and specters": null
};

const ADVENTURE_TITLES = {
	"princes of the apocalypse": "pota",
	"waterdeep: dragon heist": "wdh"
};

// TODO expand this as required
const PLURALS = {
	// creatures
	"wolves": "wolf",
	"orc eyes of gruumsh": "orc eye of gruumsh",
	"mane": "manes",
	"gnoll fang of yeenoghu": "gnoll fang of yeenoghu",
	"spies": "spy",
	"harpies": "harpy",
	"swarms of rats": "swarm of rats",
	"rugs of smothering": "rug of smothering",

	// items
	"potions of healing": "potion of healing",
	"potions of invisibility": "potion of invisibility",

	// spells
	"glyphs of warding": "glyph of warding",
};

// TODO expand this as required
// TODO might need to split it up, too
const MAP_TO_5ET = {
	// creatures
	"deep gnome": "deep gnome (svirfneblin)",
	"faerie dragon": "faerie dragon (red)",
	"volothamp geddarm": "volothamp \"volo\" geddarm",
	"swarm of insects (spiders)": "swarm of spiders",

	// items
	"paper": "paper (one sheet)",
	"ring of resistance (force)": "ring of force resistance",
	"+1 plate armor": "plate armor +1",
	"+1 dagger": "dagger +1",
	"essence of ether": "essence of ether (inhaled)"
};

function isMaybePlural (tag) {
	return PLURALS[tag]
		|| tag.endsWith("ies") // e.g. mummies
		|| tag.endsWith("es")  // e.g. remorhazes
		|| tag.endsWith("s"); // e.g. orcs
}

function getSingulars (tag) {
	if (PLURALS[tag]) return [PLURALS[tag]];
	else {
		return [
			tag.replace(/ies$/, ""),
			tag.replace(/es$/, ""),
			tag.replace(/s$/, ""),
		]
	}
}

function getTaggedText (text) {
	let foundAny = false;

	function lookupOrMapped (lookup, text, dict, forceText) {
		const fn = dict[lookup];
		if (fn) return fn(text, forceText ? lookup : null);
		else if (MAP_TO_5ET[lookup]) {
			const mapped = MAP_TO_5ET[lookup];
			const fn = dict[mapped];
			if (fn) return fn(text, mapped);
			return null;
		} else return null;
	}

	function lookupOrMappedPlural (lookup, text, dict, logTag) {
		const single = lookupOrMapped(lookup, text, dict);
		if (single) return single;
		else {
			if (isMaybePlural(lookup)) {
				const singulars = getSingulars(lookup);
				for (const singular of singulars) {
					const fromPlural = lookupOrMapped(singular, text, dict, true);
					if (fromPlural) {
						if (args.dbgplurals) ut.info(logTag, `Singularised ${lookup} as ${singular}`);
						return fromPlural;
					}
				}
			}
		}
		return null;
	}

	function getSpell (lookup, text) {
		return lookupOrMappedPlural(lookup, text, SPELLS, "SPELL");
	}

	function getCreature (lookup, text) {
		return lookupOrMappedPlural(lookup, text, CREATURES, "CREATURE");
	}

	function getItem (lookup, text) {
		return lookupOrMappedPlural(lookup, text, ITEMS, "ITEM");
	}

	function getBookTitle (lookup, text) {
		function tagUsing (dict, tag) {
			const val = dict[lookup];
			if (val) {
				return `{@${tag} ${text}|${val}}`;
			} else {
				const splitEndPunct = text.split(/([,.;:()?!]+)$/); // CODE_PUNCTUATION
				const tail = splitEndPunct.length > 1 ? splitEndPunct.slice(1, -1).join("") : "";
				return `{@i ${splitEndPunct[0]}}${tail}`;
			}
		}

		if (BOOK_TITLES[lookup] !== undefined) {
			return tagUsing(BOOK_TITLES, "book");
		} else if (ADVENTURE_TITLES[lookup] !== undefined) {
			return tagUsing(ADVENTURE_TITLES, "adventure");
		}
		return null;
	}

	function stripPrePostJunk (str) {
		let lastLen = -1;
		do {
			lastLen = str.length;
			str = str.replace(/^\s*(and |or |[,.:;()?!]+)/gi, "").replace(/( and| or|[,.:;()?!]+)\s*$/gi, ""); // CODE_PUNCTUATION
		} while (lastLen !== str.length);
		return str;
	}

	const addSpacePre = text.startsWith(" ");
	const addSpaceSuff = text.endsWith(" ");
	const clean = text.trim();
	const splitter = new RegExp(/,\s?(?![^(]*\))/, "g"); // split on commas not within parentheses
	const parts = clean.split(splitter);

	const out = parts.map(it => {
		if (!it.trim()) return it;

		const noLeadingTrailingPunctuation = stripPrePostJunk(it);
		// check for book titles
		const bookTitle = getBookTitle(noLeadingTrailingPunctuation.trim().toLowerCase(), it);
		if (bookTitle) {
			foundAny = true;
			return bookTitle;
		}

		const splitByPunctuation = it.split(/((?: |^)and |(?: |^)or |[.:;?!])/gi); // CODE_PUNCTUATION
		return splitByPunctuation.map(c => {
			if (!c.trim()) return c;

			const leftParenCount = c.countChar(")");
			const rightParenCount = c.countChar("(");

			const startParens = [];
			const endParens = [];
			if ((/^[()]|[()]$/.exec(c)) && leftParenCount !== rightParenCount) {
				c = c.replace(/(^[()])|([()]$)/g, (...m) => {
					if (m[1]) startParens.push(m[1]);
					if (m[2]) endParens.push(m[2]);
					return "";
				});
			} else if (leftParenCount === rightParenCount && c.startsWith("(") && c.endsWith(")")) {
				c = c.replace(/^\(|\)$/g, "");
				startParens.push("(");
				endParens.push(")");
			}
			const reAddParens = (str) => {
				return `${startParens.join("")}${str}${endParens.join("")}`
			};

			const lookup = c.trim().toLowerCase();

			// check for book titles, again...
			const bookTitle = getBookTitle(lookup, c);
			if (bookTitle) {
				foundAny = true;
				return reAddParens(bookTitle);
			}

			// handle spell scrolls
			const scrollM = /^(spell scrolls?)( of )(.*$)/i.exec(c);
			if (scrollM) {
				const scrollPart = scrollM[1];
				const scrollPartClean = scrollPart.toLowerCase().replace(/s$/, "");
				const scroll = scrollPart.length === scrollPartClean.length
					? `{@item ${scrollPart}}`
					: `{@item ${scrollPartClean}|dmg|${scrollPart}}`;
				const spellPart = scrollM[3];
				const spell = getSpell(spellPart.toLowerCase(), spellPart);
				if (spell) {
					foundAny = true;
					const out = `${scroll}${scrollM[2]}${spell}`;
					return reAddParens(out);
				}
			}

			const spell = getSpell(lookup, c);
			const creature = getCreature(lookup, c);
			const item = getItem(lookup, c);

			// if creature + X are found, prefer the creature.
			// I don't _think_ there are any creature -> spell collisions, but there are creature -> item collisions, e.g. draft horse.
			// For these collisions, always prefer the creature
			const found = [spell, item].filter(it => it);
			if (found.length > 1) {
				if (!_AMBIGUOUS[c]) { // limit log spam...
					ut.warn("TAGGER", `"${c}" was ambiguous!`);
					_AMBIGUOUS[c] = 1;
				}

				foundAny = true;
				return reAddParens(found[0].replace(/@[A-Za-z]+ /g, "@ambiguous ").replace(/\|[^}]*?/g, ""));
			}

			if (creature) {
				foundAny = true;
				return reAddParens(creature);
			} else if (spell) {
				foundAny = true;
				return reAddParens(spell);
			} else if (item) {
				foundAny = true;
				return reAddParens(item);
			} else {
				return reAddParens(c);
			}
		}).join("");
	}).join(", ");

	return foundAny ? `${addSpacePre ? " " : ""}${out}${addSpaceSuff ? " " : ""}` : null;
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

function isUniqueOuterHeader (page, pIx) {
	const p = page[pIx];

	function getPHeader (myP) {
		return myP.name ? myP.name.g()._ : null;
	}

	function cleanPHeader (myPH) {
		if (myPH == null) return null;
		return myPH.toLowerCase().trim();
	}

	const pHeader = cleanPHeader(getPHeader(p));
	if (pHeader == null) return false; // no header is never useful, so always return false

	function checkPrev () {
		const pPrev = page[pIx - 1];
		const pHPrev = cleanPHeader(getPHeader(pPrev));
		return pHPrev !== pHeader;
	}

	function checkNext () {
		const pNext = page[pIx + 1];
		const pHNext = cleanPHeader(getPHeader(pNext));
		return pHNext !== pHeader;
	}

	if (pIx === 0) {
		return checkNext();
	} else if (pIx === page.length - 1) {
		return checkPrev();
	} else {
		return checkPrev() && checkNext();
	}
}

let lastChecked = -1;
function isNewSubgroup (page, pIx, updateState = true) {
	// handle the case where two headers are in the same block in the same refpage
	if (lastChecked === pIx) return false;
	if (updateState) lastChecked = pIx;

	const p = page[pIx];

	function getPGroup (myP) {
		return myP.subgroup ? myP.subgroup.g()._ : null;
	}

	function cleanPGroup (myPGroup) {
		if (myPGroup == null) return null;
		return myPGroup.toLowerCase().trim();
	}

	const pGroup = cleanPGroup(getPGroup(p));
	if (pGroup == null) {
		throw new Error("No subgroup!");
	}

	function checkPrev () {
		const pPrev = page[pIx - 1];
		const pGPrev = cleanPGroup(getPGroup(pPrev));
		return pGPrev !== pGroup;
	}

	if (pIx === 0) {
		return true
	} else {
		return checkPrev();
	}
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

function doAmbiguityPass (data) {
	ut.info("SCRIPT", "Doing ambiguity pass...");
	let ambCount = 0;

	const tag = "@ambiguous";
	const tagLen = tag.length;
	// TODO this doesn't handle references from non-default (e.g. PHB for spells, DMG for items) sources.
	function handleString (str) {
		let lastIndex = str.indexOf(tag);
		while (~lastIndex) {
			const sliceStart = Math.max(0, lastIndex - 20);
			const sliceEnd = Math.min(lastIndex + 40, str.length);
			const slice = str.slice(sliceStart, sliceEnd);

			if (slice.toLowerCase().includes("spell")) {
				str = str.replaceAt(lastIndex, "@spell", tagLen);
			} else {
				str = str.replaceAt(lastIndex, "@item", tagLen);
			}
			ambCount++;
			lastIndex = str.indexOf(tag);
		}

		return str;
	}
	const handlers = {string: handleString};
	ut.dataRecurse(data, handlers);
	ut.info("SCRIPT", `${ambCount} ambiguous reference${ambCount === 1 ? "" : "s"} replaced.`);
}

function doBITagCleanPass (data) {
	const PUNCT = new Set([".", ":", ";", "?", "!", // CODE_PUNCTUATION
		","]);
	const PAREN = new Set(["(", ")"]);

	ut.info("SCRIPT", "Doing bold/italic/book/adventure tag cleaning pass...");
	let tagCount = 0;

	// pull trailing punctuation out of the curly braces
	function handleStringBI (str) {
		return str.replace(/({@[ib] )([^}]+)(})/g, (...m) => {
			let raw = m[2];
			const stack = [];

			while (raw.length && (PUNCT.has(raw.last()) || (PAREN.has(raw.last()) && !raw.trim().startsWith("(")))) {
				stack.unshift(raw.last());
				raw = raw.slice(0, raw.length - 1);
			}

			if (stack.length) tagCount++;
			return `${m[1]}${raw}${m[3]}${stack.join("")}`;
		});
	}

	function handleStringBookAdventure (str) {
		return str.replace(/({@(?:book|adventure) )([^}]+)(})/g, (...m) => {
			const spl = m[2].split("|");
			let raw = spl[0];
			const stack = [];

			while (raw.length && (PUNCT.has(raw.last()) || (PAREN.has(raw.last()) && !raw.trim().startsWith("(")))) {
				stack.unshift(raw.last());
				raw = raw.slice(0, raw.length - 1);
			}

			if (stack.length) tagCount++;
			return `${m[1]}${raw}|${spl.slice(1, spl.length).join("")}${m[3]}${stack.join("")}`;
		});
	}

	const handlers = {string: handleStringBI};
	ut.dataRecurse(data, handlers);
	ut.info("SCRIPT", `${tagCount} b/i tag${tagCount === 1 ? "" : "s"} cleaned.`);

	tagCount = 0;
	handlers.string = handleStringBookAdventure;
	ut.dataRecurse(data, handlers);
	ut.info("SCRIPT", `${tagCount} adventure/book tag${tagCount === 1 ? "" : "s"} cleaned.`);
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

const IMAGE_PATH_BLACKLIST = {
	"adventure/WDH": new Set(["Line.jpg", "Front-Cover.jpg"])
};

function isImageBlacklisted (path) {
	const filename = path.split(/[/\\]/g).last();
	const set = IMAGE_PATH_BLACKLIST[args.imgdir];
	return set && set.has(filename);
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

module.exports = {
	getTaggedText,
	isUniqueOuterHeader,
	isNewSubgroup,
	pPreloadReferences,
	doAmbiguityPass,
	doBITagCleanPass,
	isImageBlacklisted
};
