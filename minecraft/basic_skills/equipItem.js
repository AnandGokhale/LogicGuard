async function equipItem(bot, name, destination = 'hand') {
  const item = bot.inventory.items().find(item => item.name === name);
  if (!item) throw new Error(`Missing item to equip: ${name}`);
  await bot.equip(item, destination);
}

module.exports = equipItem;