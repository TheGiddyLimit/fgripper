/* eslint-disable */
const prevOutput = require("../trash/_TEMP.json");
const fs = require('fs');

prevOutput.data.forEach(ch => {
	function check (entry) {
		if (entry.entries) {
			const mapped = entry.entries.map(it => check(it));
			entry.entries = mapped.reduce((acc, val) => acc.concat(val), []);
			return entry;
		} else if (entry.items) {
			const mapped = entry.items.map(it => check(it));
			entry.items = mapped.reduce((acc, val) => acc.concat(val), []);
			return entry;
		} else if (typeof entry === "string") {
			if (/{@b ([A-Z].*?)[.?]}/.exec(entry)) {
				const [one, ...others] = entry.split(/{@b ([A-Z].*?)[.?]}/);
				const out = [one.trim()];
				let temp;
				const getTemp = () => temp = {type: "entries", name: "", entries: []};
				others.forEach((it, i) => {
					if (i % 2 === 0) {
						if (temp) out.push(temp);
						getTemp();
						temp.name = it.trim();
					} else {
						temp.entries.push(it.trim());
					}
				});
				if (temp) out.push(temp);
				return out;
			} else if (/{@b ([A-Z].*?)[:]}/.exec(entry)) {
				const [one, ...others] = entry.split(/{@b ([A-Z].*?)[:]}/);
				const out = [one.trim(), {type: "list", style: "list-hang-notitle", items: []}];
				let temp;
				const getTemp = () => temp = {type: "item", name: "", entry: ""};
				others.forEach((it, i) => {
					if (i % 2 === 0) {
						if (temp) out[1].items.push(temp);
						getTemp();
						temp.name = it.trim();
					} else {
						temp.entry = it.trim();
					}
				});
				if (temp) out[1].items.push(temp);
				return out;
			} else {
				return [entry];
			}
		} else {
			return [entry];
		}
	}

	if (ch.entries) {
		ch = check(ch);
	}
});

prevOutput.data.forEach(ch => {
	function group (entry) {
		if (entry.entries) {
			const out = [];
			let hasSeenEntries = false;
			let target = null;
			for (let i = 0; i < entry.entries.length; ++i) {
				const cur = entry.entries[i];
				if (cur.entries) {
					hasSeenEntries = true;
					target = cur;
					out.push(cur)
				} else if (typeof cur === "string" && hasSeenEntries) {
					target.entries.push(cur);
				} else {
					out.push(cur);
				}
			}
			entry.entries = out;

			entry.entries  = entry.entries.map(it => group(it));
			return entry;
		} else {
			return entry;
		}
	}

	if (ch.entries) {
		ch = group(ch);
	}
});

const out = JSON.stringify(prevOutput, null, "\t").replace(/\s*\u2014\s&/g, "\\u2014").replace(/\s*\u2013\s*/g, "\\u2014");
fs.writeFileSync(`trash/_TEMP_1.json`, out, "utf8");