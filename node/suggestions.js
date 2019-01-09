const fs = require('fs');

const TOKEN = fs.readFileSync("node/apitoken.txt", "utf8").trim();
const CHANNEL = "470673384552923136";
const MY_ID = "471422590829723665";

const Discord = require('discord.js');
const client = new Discord.Client();

function cleanContent (string, shorten) {
	const cleaned = string.replace(/[\n\r]+/g, " \\ ");
	if (shorten) return `${cleaned.substring(0, 20)}${cleaned.length > 20 ? "..." : ""}`;
	else return cleaned;
}

function cleanEmoji (emoji) {
	if (emoji.length > 2) return emoji.split(":")[0];
	return emoji;
}

async function asyncForEach(array, callback) {
	for (let index = 0; index < array.length; index++) {
		await callback(array[index], index, array)
	}
}

async function asyncMap(array, callback) {
	const out = [];
	for (let index = 0; index < array.length; index++) {
		out.push(await callback(array[index], index, array))
	}
	return out;
}

const MESSAGE_PULL_LIMIT = 100;
const USER_PULL_LIMIT = 100;
console.log(`Establishing uplink...`);
client.on('ready', async () => {
	console.log(`Logged in as ${client.user.tag}!`);
	const channel = client.channels.get(CHANNEL);

	let counter = 1;

	const allMessages = [];
	let lowestId = "0";
	let messages = await channel.fetchMessages({limit: MESSAGE_PULL_LIMIT});
	[...messages.values()].forEach(it => allMessages.push(it));
	while (messages.size === MESSAGE_PULL_LIMIT) {
		const longestKey = [...messages.keys()].reduce((a, b) => a.length > b.length ? {length: a.length} : {length: b.length}, ({length: 0})).length;
		const sorted = [...messages.keys()].filter(it => it.length >= longestKey).sort();
		lowestId = sorted[0];
		messages = await channel.fetchMessages({limit: MESSAGE_PULL_LIMIT, before: lowestId});
		[...messages.values()].forEach(it => allMessages.push(it));
	}

	const pullReactions = () => {
		console.log(`There are ${allMessages.length} approved suggestions.`);
		console.log(`\tLaunching processing tasks...`);
		const promises = allMessages.map((v, i) => {
			return new Promise(async (resolve, reject) => {
				const msg = v;
				const vals2 = [...msg.reactions.values()];
				const voterIds = new Set();
				for (let j = 0; j < vals2.length; ++j) {
					const reacts = vals2[j];
					let highestId = "0";
					let users = await reacts.fetchUsers(USER_PULL_LIMIT, {after: highestId});
					[...users.keys()].forEach(it => voterIds.add(it));
					let iter = 1;
					while (users.size === (USER_PULL_LIMIT * iter)) {
						iter++;
						const longestKey = [...users.keys()].reduce((a, b) => a.length > b.length ? {length: a.length} : {length: b.length}, ({length: 0})).length;
						const sorted = [...users.keys()].filter(it => it.length >= longestKey).sort().reverse();
						highestId = sorted[0];
						users = await reacts.fetchUsers(USER_PULL_LIMIT, {after: highestId});
						[...users.keys()].forEach(it => voterIds.add(it));
					}
				}
				console.log(`\tFetched suggestion ${msg.id} (${`${counter++}`.padStart(`${allMessages.length}`.length, " ")}/${allMessages.length})`);

				let total = voterIds.size;
				if (voterIds.has(MY_ID)) total += 9; // 10 votes total

				resolve({
					msgId: msg.id,
					content: msg.content,
					votes: total
				});
			});
		});
		return Promise.all(promises);
	};

	pullReactions().then(data => {
		console.log("Collecting votes...");
		const merged = {};
		data.forEach(it => merged[it.msgId] = it);

		const sorted = Object.values(merged).sort((a, b) => a.votes - b.votes);
		const sortedR20 = [];
		const sortedMain = sorted.filter(it => {
			if (it.content.toLowerCase().startsWith("roll20")) {
				sortedR20.push(it);
				return false;
			} else return true;
		});

		function joinOut (arr) {
			return arr.map(it => `${String(it.votes).padStart(3, " ")} :: ${it.content.replace(/[\n\r]+/g, " \\ ")}`);
		}

		console.log("##### ROLL20 RESULTS #####");
		console.log(joinOut(sortedR20).join("\n"));
		console.log("\n");
		console.log("#####  MAIN RESULTS  #####");
		console.log(joinOut(sortedMain).join("\n"));
		Promise.resolve();
		console.log("###################");
		console.log("Run complete. Shutting down.");
		process.exit();
	});
});

client.login(TOKEN);
