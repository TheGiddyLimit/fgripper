/**
 * FIXME this thing is junk
 */

const fs = require('fs');
const readline = require('readline');
const ur = require('./RipUtils');
const ut = require('./MiscUtils');

global.args = require('minimist')(process.argv.slice(2));

if (!args.file) {
	console.log(args);
	console.log(`Usage: npm run rip --file FILENAME`);
	return;
}

function doTeardown () {
	console.log("\nReindent complete.");
	process.exit();
}

const json = JSON.parse(fs.readFileSync(args.file, "utf-8"));


function pDoGetFileOrder (toSave) {
	return new Promise(resolve => {
		function saveHeaderFile (location) {
			const stack = [];
			let uid = 1;

			function getSnippet (obj) {
				if (obj.entries && obj.entries[0]) {
					return JSON.stringify(obj.entries[0]).slice(0, 50);
				} else {
					return "NO ENTRIES"
				}
			}

			function process (obj, depth) {
				if (obj.type === "entries" || obj.type === "section") {
					const c = obj.type === "section" ? "$" : "";
					if (obj.name) stack.push(`${`\t`.repeat(depth)}${c}${obj.name}`);
					else {
						obj.uid = uid++;
						stack.push(`${`\t`.repeat(depth)}${c}UID_${obj.uid}_${getSnippet(obj)}`);
					}

					obj.entries.forEach(e => {
						process(e, depth + 1);
					});
				} else if (obj.type === "inset" || obj.type === "insetReadaloud") {
					const c = obj.type === "inset" ? ">" : "¬";
					if (obj.name) stack.push(`${`\t`.repeat(depth)}${c}${obj.name}`);
					else {
						obj.uid = uid++;
						stack.push(`${`\t`.repeat(depth)}${c}UID_${obj.uid}_${getSnippet(obj)}`);
					}
				}
			}

			// toSave will have a prop called "data" which is an array of chapters
			// everything else will be a "type"d object
			toSave.data.forEach(chapter => {
				process(chapter, 0);
			});

			fs.writeFileSync(location, stack.join("\n"), "utf8");
		}

		function readHeaderFile (location) {
			const loaded = fs.readFileSync(location, "utf8");
			const lines = loaded.split("\n");

			const depths = [];
			lines.forEach(l => {
				if (!l.trim()) return;

				const depth = /^(\t*).*?/.exec(l)[1].length;
				l = l.trim();

				const inset = l.startsWith(">");
				l = l.replace(/^>/, "");

				const insetReadaloud = l.startsWith("¬");
				l = l.replace(/^¬/, "");

				const section = l.startsWith("$");
				l = l.replace(/^\$/, "");

				let uid = null;
				let name = null;

				if (l.startsWith("UID_")) {
					uid = Number(l.split("_")[1]);
				} else {
					name = l;
				}

				const toPush = {
					depth
				};

				if (uid != null) toPush.uid = uid;
				else toPush.name = name;

				if (inset) toPush.type = "inset";
				else if (insetReadaloud) toPush.type = "insetReadaloud";
				else if (section) toPush.type = "section";
				depths.push(toPush)
			});

			// flatten current data
			const flat = [];
			// FIXME can't flatten using current process, because strings/etc can be mixed freely with blocks

			// FIXME doesn't work, produces duplicate output... children being added to multiple parents, perhaps?

			const chapters = [];
			toSave.data.forEach(chapter => {
				let first = true;
				let lasts = {"0": null};

				function process (obj, depth) {
					// handle initial push -- should only be one level 0 element, and it should be a section
					if (first) {
						getInfo(obj); // toss away the info (shifts the queue)
						obj.type = "section";
						lasts[0] = obj;
						chapters.push(obj);
						first = false;

						obj.entries.forEach(e => {
							process(e, depth + 1);
						});
						return;
					}

					function getInfo (obj) {
						const front = depths.shift();
						if (obj.name) {
							if (front.name !== obj.name) throw new Error("Mismatched name!");
							return front;
						} else if (obj.uid) {
							if (front.uid !== obj.uid) throw new Error("Mismatched UID!");
							delete obj.uid;
							return front;
						}
					}

					if (obj.type === "entries" || obj.type === "section") {
						const info = getInfo(obj);

						lasts[info.depth] = obj;

						// hook it to the last thing at the previous depth
						// TODO should create a chain until we get the depth we want, if there's nesting that jumps multiple indents
						lasts[info.depth - 1].entries.push(obj);

						obj.entries.forEach(e => {
							process(e, depth + 1);
						});
					} else if (obj.type === "inset" || obj.type === "insetReadaloud") {
						const info = getInfo(obj);

						lasts[info.depth - 1].entries.push(obj);
					}
				}

				process(chapter, 0);
			});

			toSave.data = chapters;
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
			if (!args.dbgdry) ut.doJsonWrite("_TEMP", toSave);
			resolve();
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
	});
}

pDoGetFileOrder(json).then(doTeardown);
