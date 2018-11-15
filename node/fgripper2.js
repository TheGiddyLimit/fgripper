/**
 * Pass it an FG "db.xml" file with:
 *   `--file "books/DD Tome of Foes/db.xml"`
 * If refpage elements don't have blocks, pass:
 *    `--noblocks` // TODO this needs overhauled, many changes have been made since it was last used
 * To parse only tables, pass:
 *    `--rolltables`
 * To skip the manual indent stage, pass:
 *    `--autoindent`
 * To provide an image directory (required for image ripping to function), pass:
 *    `--imgdir="whatever/dir"`
 *
 * To skip item ripping, pass:
 *    `--noitems`
 * To skip creature ripping, pass:
 *    `--nocreatures`
 * To skip `image.` ripping, pass:
 *    `--noimages`
 *
 * Dbg options:
 * To show page completion, pass:
 *    `--dbgpage`
 * To show when a <h> tag name is replaced with a refpage name, pass:
 *    `--dbgheaders`
 * To show when a plural creature name is converted to a tag, pass:
 *    `--dbgplurals`
 * To skip disk writes, pass:
 *    `--dbgdry`
 *
 * When dbgging, use the command `show()` to see the current section parse, and `done()` to see finalised sections
 *
 * NOTES:
 *  - Headers (e.g. <h>Whatever</h>) are locked at depth 1
 *  - Inline headers (e.g. <b><i>Whatever</b></i>) are locked at depth 2
 *
 *
 * // TODO
 - auto-tag spells: check for /\w spell/ and loop backwards, splitting on spaces, taking on tokens until the max length of a spell name (split by spaces) is reached, trying each as spell names to tag
 - update image grabber: prefer "nice" titles, instead of inner titles? requires experimentation
 - handle double-dash pairs in strings? e.g. "this is-as some would say-supposed to be long dashes"
 - handle: find /(\{@\w+ )\s+/g -> " $1"
 - handle: find /(\{@spell [^}]+) (})/ -> "$1$2"
 - ambiguity re-tagger fucks up on e.g. {@ambiguous shield|phb|shields}
 - it outputs "[object Object]" in WDH's Badge of the Watch..? Something wrong with appends?
 - very last entry of the entire thing is skipped?
 */
const ut = require('./MiscUtils');
const ur = require('./RipUtils');
const prt = require("./ParserRollTable");
const prm = require("./ParserRefManual");
const rpi = require("./ItemRipper");
const rpg = require("./ImageRipper");

const fs = require('fs');
const xml = require('xml2js');
const readline = require('readline');

global.args = require('minimist')(process.argv.slice(2));

if (!args.file) {
	console.log(args);
	console.log(`Usage: npm run rip -- --file FILENAME`);
	return;
}

const parser = new xml.Parser({explicitChildren: true, preserveChildrenOrder: true, charsAsChildren: true});
fs.readFile(args.file, 'latin1', function (err, data) {
	if (err) console.error(err);
	parser.parseString(data, function (err, doc) {
		if (err) console.error(err);

		const root = doc.root;

		const parserRollTables = new prt.ParserRollTable(root);
		const imageRipper = new rpg.ImageRipper(root);
		rpg.ImageRipper.initImageRipper();
		const parserRefManual = new prm.ParserRefManual(root, parserRollTables, imageRipper);
		const itemRipper = new rpi.ItemRipper(root);

		function doTeardown () {
			console.log("\nDonezo");
			process.exit(); // since it seems to dislike doing it itself
		}

		function doGetFileOrder (toSave) {
			function saveHeaderFile (location) {
				function getHeaderString () {
					return toSave.data.map((it, i) => {
						if (!it.name) throw new Error("Block did not have name!");
						return `${it.name} :: ${i}`
					}).join("\n");
				}

				fs.writeFileSync(location, getHeaderString(), "utf8");
			}

			function readHeaderFile (location) {
				function tail (arr) {
					return arr[arr.length - 1];
				}

				const layers = [];
				let last = null;

				const loaded = fs.readFileSync(location, "utf8");
				const lines = loaded.split("\n");

				lines.forEach(l => {
					const depth = /^(\t*).*?/.exec(l)[1].length;
					if (!layers.length && depth !== 0) throw new Error("Did not start at depth 0!");
					l = l.trim();

					const indent = l.startsWith(">");
					l = l.replace(/^>/, "").trim();

					const [text, index] = l.split("::").map((it, i) => i === 1 ? Number(it.trim()) : it.trim());

					const real = toSave.data[index];
					if (!real) throw new Error(`Could not find data array item with index ${index}`);

					if (indent) {
						real.type = "inset";
						last.entries.push(real);
					} else {
						if (depth === 0 || depth === 1) real.type = "section";

						layers[depth] = layers[depth] || [];
						if (depth > 0) tail(layers[depth - 1]).entries.push(real);
						layers[depth].push(real);
						last = real;
					}
				});

				toSave.data = layers[0];
			}

			// https://jttan.com/2016/06/node-js-basic-command-line-interactive-loop/
			const rl = readline.createInterface({
				input: process.stdin,
				output: process.stdout
			});

			const headerFile = `trash/_HEADERS.txt`;
			saveHeaderFile(headerFile);

			function doFinalise () {
				readHeaderFile(headerFile);

				toSave._contents = toSave.data.map(it => {
					const chapter = {
						name: it.name
					};

					chapter.headers = (it.entries || []).map(e => e.name).filter(e => e);
					if (!chapter.headers.length) delete chapter.headers;
					return chapter;
				});

				if (!args.dbgdry) ut.doJsonWrite("_TEMP", toSave);
				doTeardown();
			}

			if (args.autoindent) {
				doFinalise();
			} else {
				console.log(`Output header file to ${headerFile} -- please edit it and re-save when you're happy with the formatting`);
				console.log(`Formatting help:`);
				console.log(`    \\t* :: depth       :: 0 = chapter start section; 1 = chapter section; etc`);
				console.log(`    >   :: inset block :: (will use the indent of the previous header)`);
				rl.question("(Press any key to re-process the file)", () => {
					rl.close();

					console.log("\n");
					console.log("Re-reading file...");
					doFinalise();
				});
			}
		}

		ur.pPreloadReferences().then(() => {
			if (args.rolltables) {
				// a rolltables run
				const out = root.tables.g().category.g().$$.map(t => {
					try {
						return parserRollTables.runTableParse(t)
					} catch (e) {
						ut.warn("ROLLTABLE", `Error processing table ${t.name.g()._.replace(/\t+/g, "").trim()} (${t["#name"]}): ${e.message}`)
					}
				}).filter(it => it);
				if (!args.dbgdry) ut.doJsonWrite("_TEMP_TABLES", out);
				doTeardown();
			} else {
				// a normal run

				// pre-rip items
				if (!args.noitems) {
					itemRipper.ripItems();
				}

				// pre-rip creatures
				if (!args.nocreatures) {
					// TODO
				}

				// rip text
				const refArray = root.reference.g().refmanualdata.g().$$;
				const toSave = parserRefManual.runManualParse(refArray);
				ur.doAmbiguityPass(toSave);
				ur.doBITagCleanPass(toSave);
				// manually do the indents
				if (!args.dbgdry) doGetFileOrder(toSave);
				else doTeardown();
			}
		});
	});
});
