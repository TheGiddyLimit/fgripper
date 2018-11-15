const ut = require('./MiscUtils');
const ur = require('./RipUtils');

class ItemRipper {
	constructor (root) {
		this.root = root;
	}

	ripItems () {
		const root = this.root;
		const cats = root.item.g().$$;

		const ripped = new Set();

		cats.forEach(cat => {
			if (cat["#name"] !== "category") throw new Error("Wasn't a category?");

			cat.$$.forEach(it => {
				const name = it.name ? it.name.g()._ : null;
				if (!name) throw new Error("Item had no name!");

				const tagged = ur.getTaggedText(name);
				if (!tagged) {
					ripped.add(name);

					// TODO actually rip the items lol
				}
			});
		});
		if (ripped.size) {
			// TODO enable this
			// ut.dumpSet("ITEM_RIPPER", "Ripped item:", ripped, true);
		}
	}
}

module.exports = {
	ItemRipper
};
