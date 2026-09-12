async function ensureFurnace(bot) {
  const { craftItem } = require('./craftItem');
  const { placeItem } = require('./placeItem');
  const furnaceBlock = bot.findBlock({ matching: block => block.name === 'furnace', maxDistance: 32 });
  if (furnaceBlock) return furnaceBlock.position;

  const furnaceItem = bot.inventory.items().find(i => i.name === 'furnace');
  if (!furnaceItem) {
    await craftItem(bot, 'furnace', 1);
  }
  const position = bot.entity.position.offset(1, 0, 0).floored();
  await placeItem(bot, 'furnace', position);
  return position;
}