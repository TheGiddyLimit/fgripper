const ut = require('./MiscUtils');
const ur = require('./RipUtils');
const fs = require('fs');

class ImageRipper {
	constructor (root) {
		this.root = root;
	}

	static initImageRipper () {
		if (!args.imgdir) {
			throw new Error(`No source directory specified!`);
		}
		const path = `img/${args.imgdir}`;
		if (!fs.existsSync(path)) {
			ut.mkdirs(path);
		}
		ut.cleanDir(path, true);
	}

	ripImageLink (t) {
		const imageId = t.$.recordname.split("@")[0].split(".")[1];
		return this.ripImageId(imageId);
	}

	ripImageId (imageId) {
		const root = this.root;
		const allImages = root.image.g().$$.map(it => it.$$).reduce((a, b) => a.concat(b), []);

		const imgRaw = allImages.filter(it => it["#name"] === imageId);
		if (!imgRaw) {
			ut.warn("IMAGE", `Missing image: ${imageId}`);
			return null;
		} else {
			// take the first as there can sometimes be two identical images...
			const first = imgRaw[0];

			const path = first.image.g().bitmap.g()._;
			if (ur.isImageBlacklisted(path)) {
				return null
			}
			const title = first.name.g()._.trim();
			return this.ripImage(path, title);
		}
	}

	/**
	 * In some cases, the image is embedded directly
	 * @param path Path to the image, according to FG's <bitmap/> element
	 * @param title Image caption/title
	 */
	ripImage (path, title) {
		const outDir = args.imgdir.split(/[/\\]/g).last();
		path = path.replace(/\\/g, "/");

		const fileName = path.split(/[/\\]/g).last();
		const pathRoot = args.file.split(/[/\\]/g);
		pathRoot.splice(pathRoot.length - 1, 1);
		fs.copyFileSync(`${pathRoot.join("/")}/${path}`, `img/${args.imgdir}/${fileName}`);
		const out = {
			type: "image",
			href: {
				type: "internal",
				path: `adventure/${outDir}/${fileName}`
			}
		};
		if (title) out.title = title;
		return out;
	}
}

module.exports = {
	ImageRipper
};
