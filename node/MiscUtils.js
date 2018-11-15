const fs = require('fs');

function doJsonWrite (name, data) {
	fs.writeFileSync(`trash/${name}.json`, JSON.stringify(data, null, "\t").replace(/\s*\u2014\s*/g, "\\u2014").replace(/\s*\u2013\s*/g, "\\u2014"), "utf8");
}

function warn (tag, ...args) {
	_taggedConsole(console.warn, tag, ...args);
}

function info (tag, ...args) {
	_taggedConsole(console.info, tag, ...args);
}

function _taggedConsole (fn, tag, ...args) {
	const expandedTag = tag.padStart(12, " ");
	fn(`[${expandedTag}]`, ...args);
}

const _KEY_BLACKLIST = new Set(["type"]);
function dataRecurse (obj, primitiveHandlers) {
	const to = typeof obj;
	if (obj == null) return obj;

	switch (to) {
		case undefined:
			if (primitiveHandlers.undefined) return primitiveHandlers.undefined(obj);
			return obj;
		case "boolean":
			if (primitiveHandlers.boolean) return primitiveHandlers.boolean(obj);
			return obj;
		case "number":
			if (primitiveHandlers.number) return primitiveHandlers.number(obj);
			return obj;
		case "string":
			if (primitiveHandlers.string) return primitiveHandlers.string(obj);
			return obj;

		case "object": {
			if (obj instanceof Array) return obj.map(it => dataRecurse(it, primitiveHandlers));
			else {
				Object.keys(obj).forEach(k => {
					const v = obj[k];
					if (!_KEY_BLACKLIST.has(k)) {
						obj[k] = dataRecurse(v, primitiveHandlers)
					}
				});
				return obj;
			}
		}
		default:
			console.warn("Unhandled type?!", to);
	}
}

function dumpSet (tag, message, set, sort = false) {
	const toPrint = [...set];
	if (sort) toPrint.sort();
	toPrint.forEach(tp => {
		info(tag, message, tp);
	})
}

function cleanDir (dirPath, initial) {
	try {
		const files = fs.readdirSync(dirPath);
		files.forEach(f => {
			const filePath = `${dirPath}/${f}`;

			if (fs.statSync(filePath).isFile()) fs.unlinkSync(filePath);
			else cleanDir(filePath);
		});
		if (!initial) fs.rmdirSync(dirPath);
	} catch (e) {
		console.error(e);
	}
}

function mkdirs (pathToCreate) {
	pathToCreate
		.split(/[\/]/g)
		.reduce((currentPath, folder) => {
			currentPath += `${folder}/`;
			if (!fs.existsSync(currentPath)) {
				fs.mkdirSync(currentPath);
			}
			return currentPath;
		}, "");
}

Array.prototype.g = Array.prototype.g ||
	function () {
		if (this.length === 1) return this[0];
		throw new Error("More than one item in the G array!")
	};

Array.prototype.f = Array.prototype.f ||
	function (name) {
		const out = this.find(it => it["#name"] === name);
		if (out) return out;
		throw new Error(`No child found with name ${name}!`);
	};

Array.prototype.last = Array.prototype.last ||
	function() {
		return this[this.length-1];
	};

Object.prototype.n = Object.prototype.n ||
	function () {
		return this["#name"];
	};

String.prototype.last = String.prototype.last ||
	function() {
		return this[this.length-1];
	};

String.prototype.replaceAt = String.prototype.replaceAt ||
	function (index, replacement, removeCount) {
		const replaceOffset = removeCount == null ? replacement.length : removeCount;
		return `${this.substr(0, index)}${replacement}${this.substr(index + replaceOffset)}`;
	};

String.prototype.countChar = String.prototype.countChar ||
	function (c) {
		let count = 0;
		for (let i = 0; i < this.length; ++i) {
			if (this[i] === c) count++;
		}
		return count;
	};

module.exports = {
	doJsonWrite,
	warn,
	info,
	dataRecurse,
	dumpSet,
	cleanDir,
	mkdirs
};
