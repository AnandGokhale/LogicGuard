async function placeItem(bot, name, position) {
    const mcData = require('minecraft-data')(bot.version);
    const Vec3 = require('vec3').Vec3;
    const { pathfinder, Movements, goals } = require('mineflayer-pathfinder');
    const { GoalPlaceBlock } = goals;
    const safeMovements = new Movements(bot, mcData);
    safeMovements.maxDropDown = 1;
    safeMovements.liquidCost = 100; // cost for moving through liquids
    //safeMovements.canDig = false;
    //safeMovements.setBlockCost(mcData.blocksByName.lava.id, 1000);
    //safeMovements.setBlockCost(mcData.blocksByName.water.id, 1000);
    //safeMovements.setBlockCost(mcData.blocksByName.air.id, 100);
    
    bot.pathfinder.setMovements(safeMovements);


    if (!bot._placeItemFailCount) {
        bot._placeItemFailCount = 0;
    }

    // return if name is not string
    if (typeof name !== "string") {
        throw new Error(`name for placeItem must be a string`);
    }
    // return if position is not Vec3
    if (!(position instanceof Vec3)) {
        throw new Error(`position for placeItem must be a Vec3`);
    }
    const itemByName = mcData.itemsByName[name];
    if (!itemByName) {
        throw new Error(`No item named ${name}`);
    }
    const item = bot.inventory.findInventoryItem(itemByName.id);
    if (!item) {
        bot.chat(`No ${name} in inventory`);
        return;
    }
    const item_count = item.count;
    // find a reference block
    const faceVectors = [
        new Vec3(0, 1, 0),
        new Vec3(0, -1, 0),
        new Vec3(1, 0, 0),
        new Vec3(-1, 0, 0),
        new Vec3(0, 0, 1),
        new Vec3(0, 0, -1),
    ];
    let referenceBlock = null;
    let faceVector = null;
    for (const vector of faceVectors) {
        const block = bot.blockAt(position.minus(vector));
        if (block?.name !== "air") {
            referenceBlock = block;
            faceVector = vector;
            bot.chat(`Placing ${name} on ${block.name} at ${block.position}`);
            break;
        }
    }
    if (!referenceBlock) {
        bot.chat(
            `No block to place ${name} on. You cannot place a floating block.`
        );
        throw new Error(
            `No block to place ${name} on. You cannot place a floating block.`
        );
    }

    // You must use try catch to placeBlock
    try {
        // You must first go to the block position you want to place
        await bot.pathfinder.goto(new GoalPlaceBlock(position, bot.world, {}));
        // You must equip the item right before calling placeBlock
        bot.chat('Equipped ' + name);
        await bot.equip(item, "hand");
        bot.chat('Trying to place ' + name);
        await bot.placeBlock(referenceBlock, faceVector);
        bot.chat(`Placed ${name}`);
        //bot.save(`${name}_placed`);
    } catch (err) {
        const item = bot.inventory.findInventoryItem(itemByName.id);
        if (item?.count === item_count) {
            bot.chat(
                `Error placing ${name}: ${err.message}, please find another position to place`
            );
            throw new   Error(
                `Error placing ${name}: ${err.message}, please find another position to place`
            );
            
        } else {
            bot.chat(`Placed ${name}`);
            //bot.save(`${name}_placed`);
        }
    }
}

module.exports = placeItem;