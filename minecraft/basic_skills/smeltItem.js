async function smeltItem(bot, itemName, fuelName, count = 1) {
    const mcData = require('minecraft-data')(bot.version);
    const { GoalBlock, GoalNear, GoalLookAtBlock } = require('mineflayer-pathfinder').goals;
    //const {Movements} = require('mineflayer-pathfinder');
    //const safeMovements = new Movements(bot, mcData);
    //safeMovements.setBlockCost(mcData.blocksByName.lava.id, 1000);
    //safeMovements.setBlockCost(mcData.blocksByName.water.id, 1000);
    //safeMovements.setBlockCost(mcData.blocksByName.air.id, 100);
    
    //bot.pathfinder.setMovements(safeMovements);

    // return if itemName or fuelName is not string
    if (typeof itemName !== "string" || typeof fuelName !== "string") {
        throw new Error("itemName or fuelName for smeltItem must be a string");
    }
    // return if count is not a number
    if (typeof count !== "number") {
        throw new Error("count for smeltItem must be a number");
    }
    const item = mcData.itemsByName[itemName];
    const fuel = mcData.itemsByName[fuelName];
    if (!item) {
        throw new Error(`No item named ${itemName}`);
    }
    if (!fuel) {
        throw new Error(`No item named ${fuelName}`);
    }
    const availableItems = bot.inventory.count(item.id);
    console.log(
        `Available ${itemName} in inventory: ${availableItems}, need: ${count}`
    );
    if (availableItems < count) {
        bot.chat(`Not enough ${itemName} in inventory, found ${availableItems}, need ${count}`);
        throw new Error(`Not enough ${itemName} in inventory, found ${availableItems}, need ${count}`);
    }

    const availableFuel = bot.inventory.count(fuel.id);
    console.log(
        `Available ${fuelName} in inventory: ${availableFuel}, need: ${count}`
    );
    if (availableFuel < count) {
        bot.chat(`Not enough ${fuelName} in inventory, found ${availableFuel}, need ${count}`);
        throw new Error(`Not enough ${fuelName} in inventory, found ${availableFuel}, need ${count}`);
    }

    const furnaceBlock = bot.findBlock({
        matching: mcData.blocksByName.furnace.id,
        maxDistance: 32,
    });
    if (!furnaceBlock) {
        throw new Error("No furnace nearby");
    } else {
        await bot.pathfinder.goto(
            new GoalLookAtBlock(furnaceBlock.position, bot.world)
        );
    }
    const furnace = await bot.openFurnace(furnaceBlock);
    let success_count = 0;
    for (let i = 0; i < count; i++) {
        if (!bot.inventory.findInventoryItem(item.id, null)) {
            bot.chat(`No ${itemName} to smelt in inventory`);
            break;
        }
        if (furnace.fuelSeconds < 15 && furnace.fuelItem()?.name !== fuelName) {
            if (!bot.inventory.findInventoryItem(fuel.id, null)) {
                bot.chat(`No ${fuelName} as fuel in inventory`);
                break;
            }
            await furnace.putFuel(fuel.id, null, 1);
            await bot.waitForTicks(20);
            if (!furnace.fuel && furnace.fuelItem()?.name !== fuelName) {
                throw new Error(`${fuelName} is not a valid fuel`);
            }
        }
        await furnace.putInput(item.id, null, 1);
        await bot.waitForTicks(12 * 20);
        if (!furnace.outputItem()) {
            throw new Error(`${itemName} is not a valid input`);
        }
        await furnace.takeOutput();
        success_count++;
    }
    furnace.close();
    if (success_count > 0) bot.chat(`Smelted ${success_count} ${itemName}.`);
    else {
        bot.chat(
            `Failed to smelt ${itemName}, please check the fuel and input.`
        );
        throw new Error(
            `Failed to smelt ${itemName}, please check the fuel and input.`
        );
        
    }
}

module.exports = smeltItem;