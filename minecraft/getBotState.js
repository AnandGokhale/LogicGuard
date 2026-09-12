const { get } = require('lodash');

function getNearbyEntities(bot, maxDistance = 32) {
    const nearbyEntities = Object.values(bot.entities)
        .filter(e => e !== bot.entity)
        .sort((a, b) => bot.entity.position.distanceTo(a.position) - bot.entity.position.distanceTo(b.position))
        .map(entity => ({
            name: entity.name,
            type: entity.type,
            position: entity.position,
            distance: bot.entity.position.distanceTo(entity.position).toFixed(2)
        }));

    return nearbyEntities.filter(entity => entity.distance <= maxDistance);

}


function getNearbyBlocks(bot, radius = 32) {
    const seen = new Set();
    const uniqueBlocks = [];

    const origin = bot.entity.position.floored();
    const r = Math.floor(radius);

    for (let dx = -r; dx <= r; dx++) {
        for (let dy = -r; dy <= r; dy++) {
            for (let dz = -r; dz <= r; dz++) {
                const pos = origin.offset(dx, dy, dz);
                const block = bot.blockAt(pos);
                if (!block) continue;
                if (block.name === 'air' || block.name === 'cave_air' || block.boundingBox === 'empty') continue;

                if (!seen.has(block.name)) {
                    seen.add(block.name);
                    uniqueBlocks.push(block.name);
                }
            }
        }
    }

    return uniqueBlocks;
}

function getNeighbourhood(bot, radius = 2) {
    const nearbyBlocks = [];

    const origin = bot.entity.position.floored();
    for (let dx = -radius; dx <= radius; dx++) {
        for (let dy = -radius; dy <= radius; dy++) {
            for (let dz = -radius; dz <= radius; dz++) {
                const pos = origin.offset(dx, dy, dz);
                const block = bot.blockAt(pos);
                if (block && block.name !== 'air') {
                    nearbyBlocks.push({
                        name: block.name,
                        position: block.position,
                        distance: bot.entity.position.distanceTo(block.position).toFixed(2)
                    });
                }
            }
        }
    }

    // Optionally sort by distance
    nearbyBlocks.sort((a, b) => a.distance - b.distance);
    return nearbyBlocks;
}


function getBotState(bot, {
    lastCode = null,
    lastResponse = null,
    lastError = null,
    lastOutput = null,
    chatLog = [],
    currentTask = "idle",
    context = "",
    critique = "",
    nearbyChests = []
} = {}) {
    const mcData = require('minecraft-data')(bot.version);

    const state = {
        codeLastRound: lastCode,
        responseLastRound: lastResponse,
        executionError: lastError,
        Output: lastOutput,
        chatLog: chatLog,
        biome: bot.blockAt(bot.entity.position)?.biome?.name || "unknown",
        time: bot.time.timeOfDay,
        nearbyBlocks: getNearbyBlocks(bot, 32),
        neighbourhood: getNeighbourhood(bot, 2),
        nearbyEntities: getNearbyEntities(bot, 32),

        health: bot.health,
        hunger: bot.food,
        position: bot.entity.position,

        equipment: {
            hand: bot.heldItem?.name || "none",
            armor: {
                head: bot.inventory.slots[5]?.name || "none",
                chest: bot.inventory.slots[6]?.name || "none",
                legs: bot.inventory.slots[7]?.name || "none",
                feet: bot.inventory.slots[8]?.name || "none"
            }
        },

        inventory: bot.inventory.items().map(item => ({
            name: item.name,
            count: item.count
        })),

        inventoryCount: bot.inventory.items().length,

        chests: nearbyChests,

        task: currentTask,
        context: context,
        critic: critique
    };

    return state;
}


module.exports = getBotState;