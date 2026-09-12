function canActuallyHarvest(bot, block) {
    if (!block) return false;
    const tool = bot.heldItem;
    const required = block.harvestTools;
    if (!required) return true; // no tool needed
    if (!tool) return false; // bare hands
    return !!required[tool.type]; // tool type allowed
}


async function mineBlock_temp(bot, name, count = 1) {
    // return if name is not string
    const mcData = require('minecraft-data')(bot.version);
    const {Movements} = require('mineflayer-pathfinder');
    //const safeMovements = new Movements(bot, mcData);
    //safeMovements.maxDropDown = 1;
    //safeMovements.liquidCost = 100; // cost for moving through liquids
    //safeMovements.canDig = false;
    //safeMovements.setBlockCost(mcData.blocksByName.lava.id, 1000);
    //safeMovements.setBlockCost(mcData.blocksByName.water.id, 1000);
    //safeMovements.setBlockCost(mcData.blocksByName.air.id, 100);
    
    //bot.pathfinder.setMovements(safeMovements);


    if (typeof name !== "string") {
        throw new Error(`name for mineBlock must be a string`);
    }
    if (typeof count !== "number") {
        throw new Error(`count for mineBlock must be a number`);
    }
    const blockByName = mcData.blocksByName[name];
    if (!blockByName) {
        throw new Error(`No block named ${name}`);
    }
    if(!bot._mineBlockFailCount) {
        bot._mineBlockFailCount = 0;
    }
    const blocks = bot.findBlocks({
        matching: [blockByName.id],
        maxDistance: 64,
        count: count,
    });


    if (blocks.length === 0) {
        bot.chat(`No ${name} nearby, please explore first`);
        throw new Error(`No ${name} blocks found nearby`);
    }

    const targets = [];
    for (let i = 0; i < blocks.length; i++) {
        const block = bot.blockAt(blocks[i]);
        if (!block) {
            bot.chat(`Block at ${blocks[i]} not found`);
            continue;
        }
        const canHarvest = canActuallyHarvest(bot, block);
        if (!canHarvest) {
            bot.chat(`Cannot mine ${block.name} — need proper tool.`);
            continue;
        }
        targets.push(bot.blockAt(blocks[i]));
    }
    if (targets.length === 0) {
    throw new Error(`No ${name} blocks can be mined with current tool`);
    }
    console.log("Targets to mine:", targets.map(b => b.name).join(', '));

    bot.pathfinder.thinkTimeout = 5000;
    try {
    await bot.collectBlock.collect(targets, { ignoreNoPath: true, count });
    bot.chat(`Successfully mined ${name} x${count}`);
    } catch (err) {
        bot.chat(`Mining failed: ${err.message}`);
        throw new Error(`Failed to mine ${name}: ${err.message}`);
    }
    //bot.save(`${name}_mined`);
}




async function mineBlock(bot, name, count = 1) {
    // return if name is not string
    const mcData = require('minecraft-data')(bot.version);
    const {Movements} = require('mineflayer-pathfinder');
    //const safeMovements = new Movements(bot, mcData);
    //safeMovements.maxDropDown = 1;
    //safeMovements.liquidCost = 100; // cost for moving through liquids
    //safeMovements.canDig = false;
    //safeMovements.setBlockCost(mcData.blocksByName.lava.id, 1000);
    //safeMovements.setBlockCost(mcData.blocksByName.water.id, 1000);
    //safeMovements.setBlockCost(mcData.blocksByName.air.id, 100);
    
    //bot.pathfinder.setMovements(safeMovements);

    const originallyEquipped = bot.heldItem || null;  
    
    
    if (typeof name !== "string") {
        throw new Error(`name for mineBlock must be a string`);
    }
    if (typeof count !== "number") {
        throw new Error(`count for mineBlock must be a number`);
    }
    const blockByName = mcData.blocksByName[name];
    if (!blockByName) {
        throw new Error(`No block named ${name}`);
    }
    
    bot._mineBlockFailCount = 0;
    
    const blocks_total = bot.findBlocks({
        matching: [blockByName.id],
        maxDistance: 64,
        count: count,
    });
    if (blocks_total.length === 0) {
            bot.chat(`No ${name} nearby, please explore first`);
            throw new Error(`No ${name} blocks found nearby`);
    }

    let mined = 0;
    const maxTries = 40 * count;


    while (mined < count && bot._mineBlockFailCount < maxTries) {
        const blocks = bot.findBlocks({
            matching: [blockByName.id],
            maxDistance: 64,
            count: 1,
        });
        if (blocks.length === 0) {
            bot.chat(`No ${name} nearby, please explore first`);
            throw new Error(`No ${name} blocks found nearby`);
        }
        const targets = [];
        for (let i = 0; i < blocks.length; i++) {
            const block = bot.blockAt(blocks[i]);
            if (!block) {
                bot.chat(`Block at ${blocks[i]} not found`);
                continue;
            }
            if (originallyEquipped){
                await bot.equip(originallyEquipped, 'hand');
            }
            const canHarvest = canActuallyHarvest(bot, block);
            if (!canHarvest) {
                bot.chat(`Cannot mine ${block.name} — need proper tool.`);
                continue;
            }
            targets.push(bot.blockAt(blocks[i]));
        }
        if (targets.length === 0) {
            throw new Error(`No ${name} blocks can be mined with current tool`);
        }
        console.log("Targets to mine:", targets.map(b => b.name).join(', '));
        try {
            await bot.collectBlock.collect(targets, { ignoreNoPath: true, count: 1 });
            mined++;
            bot.chat(`Successfully mined ${name} (${mined}/${count})`);
        } catch (err) {
            bot._mineBlockFailCount++;
            if(bot._mineBlockFailCount >= maxTries) {
                bot.chat(`Mining failed: ${err.message}`);
                throw new Error(`Failed to mine ${name}: ${err.message}`);
            }
        }
    }

}

module.exports = mineBlock;