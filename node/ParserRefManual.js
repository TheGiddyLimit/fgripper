const ut = require('./MiscUtils');
const ur = require('./RipUtils');

class ParserRefManual {
	constructor (root, parserRollTables, imageRipper) {
		this.root = root;
		this.parserRollTables = parserRollTables;
		this.imageRipper = imageRipper;
	}

	/**
	 * @param page Array of "refpage_X" objects
	 */
	runManualParse (page) {
		const parserRollTables  = this.parserRollTables;
		const imageRipper = this.imageRipper;

		const out = {data: []};
		global.done = () => {
			console.log(JSON.stringify(out.data, null, 2));
			return out.data;
		};
		global.blockIndex = 0;

		const _collectOtherHeaders = new Set(); // check if there's anything obviously being missed
		const _collectBlockAlt = new Set();
		const _collectLinkTypes = new Set();
		const _collectCaptions = new Set();
		const _collectors = {
			"otherHeaders": _collectOtherHeaders,
			"unhandledBlockTtypes": _collectBlockAlt,
			"linkTypes": _collectLinkTypes,
			"captions": _collectCaptions
		};

		// for each "refpage_X" page
		page.forEach((p, pageIndex) => {
			if (p["#name"].startsWith("refpage_appendix")) {
				console.warn("APPENDIX", `Skipping appendix ${p["#name"]}`);
				return;
			}

			// entries should be stored at a "page" level (some blocks are just titles)
			const curStack = [];
			function active (toSetAsActive) {
				if (toSetAsActive) { // "setter" mode
					while (curStack.length) curStack.pop();
					curStack.push(toSetAsActive);
				} else { // "getter" mode
					if (!curStack.length) return null;
					return curStack[curStack.length - 1];
				}
			}

			function activeEntryDepth () {
				return curStack.filter(it => it.type === "entries").length;
			}

			let attachKey = "entries";
			function pushActive (toPush, skipAttach = false) {
				const addTo = active();
				if (!addTo) throw new Error("Nothing to push to!");
				curStack.push(toPush);
				if (!skipAttach) addTo[attachKey].push(toPush); // attach it to it's parent
			}

			function popActive () {
				curStack.pop();
			}

			function getActiveOut () {
				if (!curStack.length) throw new Error("Nothing to output!");
				else return curStack[0];
			}

			const imageStack = [];
			let lastImage = null;
			function doOutputBlockImage (img, setLastImage) {
				function checkMatches (prev) {
					return prev && prev.type === "image" && prev.href.path === img.href.path;
				}

				function handleMatch (prev) {
					if (img.title != null && prev.title == null) prev.title = img.title;
					if (setLastImage) lastImage = prev;
				}

				if (active()) {
					const prev = active().entries.last();
					// if the previous image is the same, merge titles, but don't push it to output
					if (checkMatches(prev)) {
						handleMatch(prev);
					} else {
						active().entries.push(img);
						if (setLastImage) lastImage = img;
					}
				} else {
					if (!out.data.length) { // generally happens for front covers, etc
						ut.warn("IMAGE", `No parent to append image "${img.href.path}" to!`);
					} else {
						// handle images after the end of a chapter
						if (ur.isNewSubgroup(page, pageIndex, false)) {
							const prev = imageStack.last();
							if (checkMatches(prev)) {
								handleMatch(prev);
							} else {
								imageStack.push(img);
								if (setLastImage) lastImage = img;
							}
						} else {
							let appendTarget = out.data.last().entries;
							const prev = appendTarget.last();
							if (checkMatches(prev)) {
								handleMatch(prev);
							} else {
								appendTarget.push(img);
								if (setLastImage) lastImage = img;
							}
						}
					}
				}
			}

			function doOutputIfActive () {
				function getPushTarget () {
					if (!out.data.length) return out.data;
					else {
						if (ur.isNewSubgroup(page, pageIndex)) {
							if (out.data.last().entries && out.data.last().entries.length === 0) {
								ut.warn("CLEANER", `Empty entries in block "${out.data.last().name}"`);
							}
							return out.data;
						} else return out.data.last().entries; // might not always have entries..?
					}
				}

				if (active()) {
					if (!args.noblocks) {
						const toAdd = getActiveOut();
						if (toAdd.entries && toAdd.entries.length === 0) ut.warn("CLEANER", `Empty entries in block "${toAdd.name}"`);
						else {
							// add what we have to the output stack, and reset
							const pushTarget = getPushTarget();
							if (imageStack.length) {
								if (toAdd.entries) {
									while (imageStack.length) {
										toAdd.entries.unshift(imageStack.pop());
									}
								} else {
									throw new Error("No entries!");
								}
							}
							pushTarget.push(toAdd)
						}
					} else {
						// TODO this doesn't use getPushTarget -- should it?
						// check previous item to see if titles match; if so, append to previous
						const cur = getActiveOut();
						if (cur && out.data.last() && out.data.last().name === cur.name) out.data.last().entries = out.data.last().entries.concat(cur.entries);
						else out.data.push(cur);
					}
				}
			}

			global.show = () => { // debug function to print current collection to console
				const activeOut = getActiveOut();
				console.log(JSON.stringify(activeOut, null, 2));
				return activeOut;
			};

			const processBlock = (b, outerHeader, numBlocks) => {
				// flip these as required
				const mods = {
					bold: false,
					italic: false,
					append: false, // append the next __text__ to the previous line instead of creating a new line
					probablyQuote: false, // quotes look something like this: <i>There are no small betrayals.\n</i><b>-Mordenkainen</b>
					quoteeHasTitle: false, // sometimes the quoted dude has a title which is not in bold; track this here
				};

				let tableHeader = null;
				let table = false;
				let tableHeaderRow = false;

				function hasAnyModifiers () {
					return !!Object.values(mods).filter(it => it).length;
				}

				// some of these are just empty because FG
				b.$$.forEach(blockPart => {
					const n = blockPart["#name"];
					switch (n) {
						case "image": {
							const path = blockPart.bitmap.g()._;
							if (ur.isImageBlacklisted(path)) break;
							const img = imageRipper.ripImage(path);
							doOutputBlockImage(img, true);
							break;
						}
						case "caption": { // this should modify the image directly before it (if it's not null, which it can be)
							if (blockPart._) if (lastImage) lastImage.title = blockPart._;
							lastImage = null;
							break;
						}
						case "dualtext":
						case "text2":
						case "text": {
							if (blockPart.$$) parse(blockPart.$$);
							break;
						}
						case "imagelink":
							const imageId = blockPart.recordname.g()._.split(".")[1]; // TODO use this
							const img = imageRipper.ripImageId(imageId);
							if (img) doOutputBlockImage(img);
							break;
						case "size": // ignored -- image dimensions
						case "frame": // ignored -- text block framing
							// this might be useful? blockPart._ can be one of ["noframe", "blue", "brown", "yellow", null]
						case "align": // ignored -- page column alignment ("center" or "left,right")
						case "blocktype": // ignored -- seems to be duplicate information
							break;
						default: _collectBlockAlt.add(n);
					}
				});

				function isBI (t) {
					if (!(t.$$ && t.$$.length === 1)) return false;
					const bi = t.i && t.i.g().$$ && t.i.g().$$.length === 1;
					const ib = t.b && t.b.g().$$ && t.b.g().$$.length === 1;
					return bi || ib;
				}

				function isInlineTableHeader (t) {
					return t._IS_TABLE_HEADER;
				}

				function getBI (t) {
					return t[t.i ? "i" : "b"].g()._.trim().replace(/[.:]$/, "");
				}

				function isProbablyQuote (t) {
					return t.$$ && t.$$.length === 1 && t._ && t._.endsWith("\n");
				}

				function wasIndeedQuote (t) {
					return t.$$ && t.$$.length === 1 && t._ && t._.startsWith("-");
				}

				function checkSetTableHeader (kids, txt) {
					if (kids.length > 1) throw new Error("Had kids!");
					if (!txt) throw new Error("No text!");
					tableHeader = txt;
				}

				function doTagLinkables (biText) {
					// TODO implement tagging
					return biText;
				}

				function parse (ts) {
					// pre-scan for:
					//   any <p><b>table headers</b></p><table>...
					//   any <h>table headers</h><table>...
					//   any <p><b>things that should have been H tags</b></p><p>...
					for (let tX = 0; tX < ts.length - 1; tX++) {
						const t = ts[tX];
						const tNxt = ts[tX + 1];

						const ele = t["#name"];
						const eleNxt = tNxt["#name"];

						if (ele === "p" && t.b && t.$$.length === 1) {
							if (eleNxt === "table") {
								t.$$[0]._IS_TABLE_HEADER = true;
							} else if (t.b.g().i == null) {
								t._IS_HEADER_P_B = true;
							}
						} else if (ele === "h" && eleNxt === "table") {
							t._IS_TABLE_HEADER = true;
						}
					}

					function shouldUseOuterHeader (innerHeader) {
						// if the header is a substring of the outer header, it's probably missing a location number
						const txtClean = (innerHeader ? innerHeader.trim() : "").toLowerCase();
						if (outerHeader != null) {
							const outerClean = outerHeader.trim().toLowerCase();
							const isIncludedNotEqual = outerClean !== txtClean && outerClean.includes(txtClean);
							const isAreaId = !!/[A-Za-z]+\d+/.exec(outerClean);
							return isIncludedNotEqual && isAreaId;
						}
						return false;
					}

					function handleHeader (kids, headerText) {
						doOutputIfActive();
						if (kids.length > 1) throw new Error("Had kids!");
						if (!headerText) throw new Error("No text!");

						const header = headerText.trimLeft();
						let usingHeader = header;

						if (shouldUseOuterHeader(headerText)) {
							if (args.dbgheaders) ut.warn("HEADER", `Using outer header "${outerHeader}"`.padEnd(64), `instead of h-tag "${header}"`);
							usingHeader = outerHeader;
						}
						active({
							type: "entries",
							name: usingHeader,
							entries: []
						});
					}

					// main loop
					for (let tX = 0; tX < ts.length; tX++) {
						const t = ts[tX];

						const ele = t["#name"];
						const kids = t.$$;
						const txt = t._;

						switch (ele) { // element type
							case "h": {
								const isTableHeader = () => !!t._IS_TABLE_HEADER;

								if (isTableHeader()) {
									checkSetTableHeader(kids, txt);
								} else {
									handleHeader(kids, txt);
								}

								break;
							}
							case "p": {
								const isHeader = () => !!t._IS_HEADER_P_B;

								if (!active()) {
									if (ur.isUniqueOuterHeader(page, pageIndex)) { // the outer header was probably supposed to be an inner header, so use it...
										active({
											type: "entries",
											name: outerHeader.trimLeft(),
											entries: []
										});
									} else {
										throw new Error("No active!");
									}
								} else if (isHeader()) {
									const fauxKids = [];
									const headerTxt = t.b.g().$$.g()._.trimLeft();
									handleHeader(fauxKids, headerTxt);
								} else {
									mods.append = false;
									parse(t.$$);
								}
								break;
							}
							case "__text__": {
								if (mods.quoteeHasTitle) { // special case for run-on quotee titles
									active().by += txt;
									popActive();
									mods.quoteeHasTitle = false;
									return;
								}

								const cleanTxt = txt.trimLeft();
								const taggedText = ur.getTaggedText(cleanTxt); // returns null if nothing interesting was found

								const txtOut = taggedText || `${mods.bold ? "{@b " : ""}${mods.italic ? "{@i " : ""}${cleanTxt}${mods.bold ? "}" : ""}${mods.italic ? "}" : ""}`;

								const splitCarriageReturns = txtOut.split(/[\n\r]/g);

								const doPushNoAppend = () => {
									splitCarriageReturns.forEach(s => {
										active()[attachKey].push(s);
									})
								};

								if (mods.append && active()[attachKey].length) {
									const arr = active()[attachKey];
									if (arr[arr.length - 1].type === "table") {
										splitCarriageReturns.forEach(s => {
											arr.push(s);
										});
									} else {
										// get append target
										let appendIx = arr.length - 1;
										let appendable = typeof arr[appendIx] === "string";
										// if it's not a string, check backwards, skipping over any images
										if (!appendable) {
											for (let i = arr.length - 1; i >= 0; i--) {
												appendIx = i;
												const appendTarget = arr[i];
												if (appendTarget == null) break;

												const tp = typeof appendTarget;
												if (tp === "string") {
													appendable= true;
												} else if (appendTarget.type !== "image") {
													break;
												}
											}
											// if it's _really_ not appendable
											if (!appendable) doPushNoAppend();
										}

										// do append
										splitCarriageReturns.forEach((s, i) => {
											if (i === 0) {
												if (/[^ ]$/.exec(arr[appendIx])) {
													arr[appendIx] += ` ${s}`;
												} else {
													arr[appendIx] += s;
												}
											} else {
												active()[attachKey].push(s);
											}

											// if there are newlines included using \r or \n, handle them, finish the previous append, then handle the rest of the lines as single-lines (see above if-cond)
											// this might not handle more than one
											if (splitCarriageReturns.length > 1 && i < splitCarriageReturns.length - 1) {
												if (mods.italic) {
													arr[appendIx] += "}";
													splitCarriageReturns[i + 1] = "{@i " + splitCarriageReturns[i + 1];
													mods.append = false;
												}
												if (mods.bold) {
													arr[appendIx] += "}";
													splitCarriageReturns[i + 1] = "{@b " + splitCarriageReturns[i + 1];
													mods.append = false;
												}
											}
										});
									}
								} else {
									doPushNoAppend();
								}
								mods.append = false;
								break;
							}
							case "b": {
								if (mods.probablyQuote) {
									if (wasIndeedQuote(t)) {
										active().by = t._.trim().replace(/^-\s*/, "");
										mods.probablyQuote = false;
										if (!active().by.endsWith(",")) {
											popActive(); // we're done with the quote, so pop it
										} else {
											mods.probablyQuote = false;
											mods.quoteeHasTitle = true;
										}
									} else {
										throw new Error("It wasn't actually a quote?!");
									}
								} else if (isBI(t)) { // <b><i>HEADER</b></i> represents an inline entry header
									while (activeEntryDepth() > 1) popActive();
									pushActive({
										type: "entries",
										name: getBI(t),
										entries: []
									});
								} else if (isInlineTableHeader(t)) {
									checkSetTableHeader(kids, txt);
								} else {
									mods.bold = true;
									mods.append = true; // append to anything that came before
									if (t.$$) parse(t.$$); // output the current text -- if-cond is to handle e.g. "<b></b>" which FG occasionally includes
									mods.bold = false;
									mods.append = true; // and then append any thing after
								}

								break;
							}
							case "i": {
								if (isBI(t)) { // <b><i>HEADER</b></i> represents an inline entry header
									while (activeEntryDepth() > 1) popActive();
									pushActive({
										type: "entries",
										name: getBI(t),
										entries: []
									});
								} else if (isProbablyQuote(t)) {
									pushActive({
										type: "quote",
										entries: [
											txt.trimLeft().replace(/\n$/, "")
										],
										by: null
									});
									mods.probablyQuote = true;
								} else {
									mods.italic = true;
									mods.append = true;
									if (t.$$) parse(t.$$);
									mods.italic = false;
									mods.append = true;
								}

								break;
							}
							case "table": {
								if (hasAnyModifiers()) throw new Error("Had modifiers going into a table -- this shouldn't happen");

								const tbl = {
									type: "table",
									caption: tableHeader,
									colLabels: [],
									colStyles: [],
									rows: []
								};
								tableHeader = null;

								table = true;
								pushActive(tbl);
								parse(t.$$);

								// table post-processing
								if (!tbl.caption) delete tbl.caption;
								const widths = [...new Array(tbl.rows[0].length)].map(it => 0);
								for (let tblX = 0; tblX < tbl.rows[0].length; ++tblX) {
									tbl.rows.forEach(r => {
										widths[tblX] += r[tblX].length;
									});
								}
								const avgWidths = widths.map(it => it / tbl.rows.length); // average length of string in each column of the table
								const total = avgWidths.reduce((a, b) => a  + b, 0);
								const nmlxWidths = avgWidths.map(it => it / total);
								const twelfthWidths = nmlxWidths.map(it => Math.round(it * 12));
								tbl.colStyles = twelfthWidths.map(it => `col-xs-${it}`);

								// check if first column is dice
								let isDiceCol0 = true;
								tbl.rows.forEach(r => {
									if (isNaN(Number(r[0]))) isDiceCol0 = false;
								});
								if (isDiceCol0) {
									tbl.colStyles[0] += " text-align-center";
								}

								// aggressively scan for any following footnotes
								let tblX = 0;
								let fakeFooter = null;
								const dirtyIndices = [];
								while (ts[tX + tblX]) {
									const nxt = ts[tX + tblX];
									if (nxt._ && nxt._.trimLeft().startsWith("*")) {
										if (!fakeFooter) fakeFooter = {entries: []};
										pushActive(fakeFooter, true);
										parse([nxt]); // fake array
										dirtyIndices.push(tX + tblX); // remove these from consideration later
									}

									tblX++;
								}
								if (fakeFooter) {
									popActive();
									tbl.footnotes = fakeFooter.entries;
									dirtyIndices.reverse().forEach(it => ts.splice(it, 1)); // works cuz next loop "ts.length" will be the new value, so these will be skipped
								}

								table = false;
								popActive();

								break;
							}
							case "tr": {
								if (t.$ && t.$.decoration === "underline") tableHeaderRow = true;
								else active().rows.push([]);
								parse(t.$$);
								tableHeaderRow = false;

								break;
							}
							case "td": {
								if (tableHeaderRow) {
									if (!t.b) throw new Error("Table header wasn't bold!");
									const header = t.b.g()._;
									active().colLabels.push(header);
								} else {
									let toPush = txt;
									if (t.$$.length > 1) {
										const justBoldTags = () => {
											const bolds = t.$$.filter(t2 => {
												const nm = t2["#name"];
												if (nm === "__text__") return true;
												else if (nm === "b") {
													return t2.$$.length === 1;
												}
												return false;
											});
											return bolds.length === t.$$.length;
										};

										if (justBoldTags()) {
											const flat = t.$$.map(t2 => {
												const nm = t2["#name"];
												if (nm === "__text__") return t2._;
												else if (nm === "b") return doTagLinkables(t2._);
												else throw new Error("Unhandled name!");
											});
											toPush = flat.join("");
										} else throw new Error("td had multiple children!");
									}
									if (!txt) {
										if (t.b) {
											toPush = doTagLinkables(t.b.g()._);
										} else if (t.i) {
											toPush = doTagLinkables(t.i.g()._);
										} else {
											throw new Error("Unhandled TD child!");
										}
									}
									const l = active().rows.length;
									active().rows[l - 1].push(toPush);
								}

								break;
							}
							case "link": {
								// TODO make this a config option
								const recordName = t.$.recordname;
								// _collectLinkTypes.add(t.$.recordname.split(".")[0]);
								if (recordName.split(".")[0] === "image") {
									// _collectLinkTypes.add(t.$.recordname.split(".")[1]);
								}

								if (t.$.recordname.startsWith("reference.npcdata")) {
									// ignore -- monster data, which we already have
								} else if (t.$.recordname.startsWith("reference.racedata")) {
									// ignore -- race data, which we already have
								} else if (t.$.recordname.startsWith("storytemplate.")) {
									// ignore -- FG specific stuff? Looks like a quick generator comprising of rollable tables/etc
								} else if (t.$.recordname.startsWith("battlerandom.")) {
									// ignore -- random battles
								} else if (t.$.recordname.startsWith("reference.refmanualdata")) {
									// ignore -- links to DMG, etc
								} else if (t.$.recordname.startsWith("reference.imagedata")) {
									// ignore -- inline images
								} else if (t.$.recordname.startsWith("image.")) {
									if (!args.noimage) {
										const img = imageRipper.ripImageLink(t);
										if (img) active().entries.push(img);
									}
								} else if (t.$.recordname.startsWith("reference.spelllists")) {
									// ignore -- creature spell lists
								} else if (t.$.recordname.startsWith("reference.magicitemlists")) {
									// ignore -- magic item lists
								} else if (t.$.recordname.startsWith("reference.magicitemlists")) {
									// ignore -- magic item lists
								} else if (t.$.recordname.startsWith("reference.spelldata")) {
									// ignore -- spells
								} else if (t.$.recordname.startsWith("reference.equipmentlists")) {
									// ignore -- equipment
								} else if (t.$.recordname.startsWith("npc@")) {
									// ignore -- NPC
								} else if (t.$.recordname.startsWith("battle.bat")) {
									// ignore -- battles
								} else if (t.$.recordname.startsWith("treasureparcel")) {
									// ignore -- treasure parcels
								} else if (t.$.recordname.startsWith("npc.trap")) {
									// ignore -- traps
								} else if (t.$.recordname.startsWith("npc.hazard")) {
									// ignore -- hazard
								} else if (t.$.recordname.startsWith("npc.")) {
									// ignore -- npc
								} else if (t.$.recordname.startsWith("quest.")) {
									// ignore -- quest
								} else if (t.$.recordname.startsWith("tables.")) {
									const tbl = parserRollTables.runTableParse(t);
									if (tbl) active().entries.push(tbl);
								} else {
									throw new Error(`Unhandled link recordname '${t.$.recordname}'`);
								}

								break;
							}
							case "list": {
								if (t.li.length !== t.$$.length) throw new Error("List had other contents!");
								pushActive({
									type: "list",
									items: []
								});
								const _attachKey = attachKey;
								attachKey = "items";
								parse(t.$$);
								attachKey = _attachKey;
								popActive();
								break;
							}
							case "li": {
								parse(t.$$);
								break;
							}
							case "frame": {
								pushActive({
									type: "inset",
									entries: []
								});
								const _attachKey = attachKey;
								attachKey = "entries";
								parse(t.$$);
								attachKey = _attachKey;
								popActive(true);
								break;
							}
							default:
								throw new Error(`Unhandled element type ${ele}! Contents: '${1}'`);
						}
					}
				}

				blockIndex++;
			};

			if (args.noblocks) {
				const fakeText = p.text.g();
				const header = p.name ? p.name : p.subgroup;
				header.g()["#name"] = "h";
				fakeText.$$.unshift(header.g());
				const fakeBlock = {
					text: p.text
				};

				processBlock(fakeBlock);
			} else {
				// VGM has situations where `text` on the refpage contains stuff
				if (!p.blocks) {
					ut.warn("BLOCKS", "No blocks!");
					console.warn(JSON.stringify(p.text.g()));
					return;
				}

				// pass outer header and number of blocks, as there's often singleton blocks with the header outside in adventures
				// these should override internal header names, e.g. outer might be "Z4. Balcony" and inner "Balcony" -- outer is preferable
				const outerHeader = p.name ? p.name.g()._ : null;
				const numBlocks = p.blocks.g().$$.length;

				// for each "id-000YY" block
				p.blocks.g().$$.forEach(b => processBlock(b, outerHeader, numBlocks));
			}

			doOutputIfActive();
			if (args.dbgpage) console.log(`Page ${pageIndex} complete`);
		});

		// output
		Object.entries(_collectors).forEach(([k, s]) => {
			if (s.size) {
				ut.info("OUTPUT", `Dumping test collection "${k}"`);
				console.warn(JSON.stringify([...s], null, "\t"))
			} else ut.info("OUTPUT", `Test collection "${k}" was empty`);
		});

		return out;
	}
}

module.exports = {
	ParserRefManual
};
