const ut = require('./MiscUtils');

class ParserRollTable {
	constructor (root) {
		this.root = root;
	}

	getXmlVer () {
		return this.root.$.version;
	}

	runTableParse (t) {
		const root = this.root;

		function cleanText (str) {
			if (!str) return null;
			return str.replace(/\t+/g, "").trim();
		}

		const tables = root.tables.g().category.g();
		const tableId = t.$.recordname.split("@")[0].split(".")[1];
		const foundTable = tables[tableId];


		if (foundTable) {
			const table = foundTable.g();

			const out = {
				type: "table",
				caption: "",
				colLabels: [],
				colStyles: [
					"col-2 text-align-center",
					"col-10"
				],
				rows: []
			};

			if (this.getXmlVer() === "3.1" || (ut.warn("ROLLTABLE", `Unknown rolltable version ${this.getXmlVer()}`) || true)) {
				const idRows = table.tablerows.g();

				// TODO doesn't deal well with e.g. "3d6" (see XGE lifegen tables)
				const maxKey = Object.keys(idRows).sort().reverse()[0];
				const max = cleanText(table.tablerows.g()[maxKey].g().torange.g()._);

				// TODO maybe this fixes it? need to test
				let dice = null;
				if (table.dice) {
					if (table.dice.length > 1) throw new Error("Multiple dice?");
					dice = cleanText(table.dice.g()._);
				}

				// name
				out.caption = cleanText(table.name.g()._);

				// labels
				if (dice) out.colLabels.push(dice);
				else out.colLabels.push(`d${max}`);
				for (let i = 0; i < 4; ++i) {
					if (table[`labelcol${i}`]) out.colLabels.push(cleanText(table[`labelcol${i}`].g()._));
				}
				if (table.labelcol4) {
					throw new Error("Unhandled column!");
				}

				// rows
				out.rows = Object.keys(idRows).sort()
					.filter(it => it !== "$$") // ignore double-dollar, this being the list of all keys and not a valid key itself
					.map(k => {
						const r = idRows[k].g();
						const from = cleanText(r.fromrange.g()._);
						const to = cleanText(r.torange.g()._);
						if (r.results.g().length > 1) throw new Error("Multiple results for one roll in roll table!");
						const resOuter = r.results.g()["id-00001"].g();
						let res;
						if (resOuter.result) res = cleanText(resOuter.result.g()._);
						else if (resOuter.resultlink) res = resOuter.resultlink.g().recordname.g()._; // FIXME this may not work
						else throw new Error("Unhandled result format!");
						return [
							from === to ? from : `${from}-${to}`,
							res
						]
					});

				return out;
			} else {
				throw new Error(`Unknown version ${this.getXmlVer()}`);
			}
		} else {
			ut.warn("LINK", `Missing table: "${tableId}" -- is it from another book?`);
			return null;
		}
	}
}

module.exports = {
	ParserRollTable
};
