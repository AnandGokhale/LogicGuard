async function hasItem(bot, name, count) {
    const items = bot.inventory.items().filter(item => item.name === name);
    const total = items.reduce((sum, item) => sum + item.count, 0);
    
    if (total < count) {
        bot.chat(`Not enough ${name} in inventory: need ${count}, have ${total}`);
        return false;
    }
    return true;
}

module.exports = hasItem;