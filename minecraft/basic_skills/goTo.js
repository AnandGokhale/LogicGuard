
async function goTo(bot, position, timeout = 15) {
    const { GoalBlock } = require('mineflayer-pathfinder').goals;

    return new Promise((resolve, reject) => {
        if (!position || typeof position.x !== 'number') {
            return reject(new Error('Invalid position provided to goTo'));
        }

        const goal = new GoalBlock(position.x, position.y, position.z);
        bot.pathfinder.setGoal(goal);

        const timeoutId = setTimeout(() => {
            bot.pathfinder.setGoal(null);
            reject(new Error('goTo timed out'));
        }, timeout * 1000);

        bot.once('goal_reached', () => {
            clearTimeout(timeoutId);
            resolve(true);
        });
    });
}

module.exports = goTo;