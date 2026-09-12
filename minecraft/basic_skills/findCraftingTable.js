const mcData = require('minecraft-data');

async function findCraftingTable(bot, maxDistance = 32) {
  const data = mcData(bot.version);
  const craftingTableId = data.blocksByName.crafting_table.id;

  const table = bot.findBlock({
    matching: craftingTableId,
    maxDistance: maxDistance
  });

  if (table) {
    return table;
  } else {
    throw new Error('No crafting table found nearby');
  }
}

module.exports = findCraftingTable;