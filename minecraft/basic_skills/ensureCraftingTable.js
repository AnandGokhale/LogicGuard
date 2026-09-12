async function ensureCraftingTable(bot) {
    const {craftItem} = require('./craftItem');
    const {placeItem} = require('./placeItem');
  const tableBlock = bot.findBlock({ matching: block => block.name === 'crafting_table', maxDistance: 32 });
  if (tableBlock) return tableBlock.position;
  
  const tableItem = bot.inventory.items().find(i => i.name === 'crafting_table');
  if (!tableItem) {
    await craftItem(bot, 'crafting_table', 1);
  }
  const position = bot.entity.position.offset(1, 0, 0).floored();
  await placeItem(bot, 'crafting_table', position);
  return position;
}

module.exports = ensureCraftingTable;