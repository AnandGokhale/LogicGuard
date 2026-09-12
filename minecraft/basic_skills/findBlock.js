

async function findBlock(bot, name, maxDistance = 32, count = 1) {
    const { Movements } = require('mineflayer-pathfinder');
    const { GoalBlock } = require('mineflayer-pathfinder').goals;
    const blockId = bot.registry.blocksByName[name]?.id;
    if (!blockId) {
        throw new Error(`Unknown block type: ${name}`);
    }

    const found = new Map(); // Avoid duplicates
    const botPos = bot.entity.position.floored();
    const movements = new Movements(bot); // Uses safe movement logic
    bot.pathfinder.setMovements(movements);

    for (let r = 1; r <= maxDistance; r++) {
        const blocks = bot.findBlocks({
            matching: block => block.type === blockId,
            maxDistance: r,
            count: Infinity
        });

        for (const b of blocks) {
            const key = b.toString();
            if (!found.has(key)) {
                found.set(key, b);
            }
        }

        if (found.size >= count) break;
    }

    const allBlocks = Array.from(found.values());

    // For each block, compute path cost (length in number of moves)
    const blockPaths = await Promise.all(
        allBlocks.map(async pos => {
            const goal = new GoalBlock(pos.x, pos.y, pos.z);
            const result = bot.pathfinder.getPathTo(movements, goal);
            const cost = result.status === 'success' ? result.path.length : Infinity;
            return { pos, cost };
        })
    );


    // Sort by path length
    const sorted = blockPaths
        .filter(({ cost }) => cost < Infinity)
        .sort((a, b) => a.cost - b.cost)
        .map(({ pos }) => pos)
        .slice(0, count);

    bot.chat('closest blocks found: ' + sorted.map(b => b.toString()).join(', '));
    
    if (sorted.length === 0) {
        bot.chat(`No ${name} blocks found within ${maxDistance} blocks.`);
        return [];
    }
    return sorted
    
}
module.exports = findBlock;