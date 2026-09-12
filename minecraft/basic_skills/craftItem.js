async function canCraftIn2x2(bot, itemName) {
  const mc = require('minecraft-data')(bot.version);
  const item = mc.itemsByName[itemName];
  if (!item) throw new Error(`No item named ${itemName}`);

  // Get all known recipes for this item (ignoring inventory)
  const allRecipes = bot.recipesAll(item.id, null);

  // Check if any recipe does NOT require a crafting table (2x2 grid)
  const has2x2Recipe = allRecipes.some(recipe => recipe.requiresTable === false);
  return has2x2Recipe;
}


async function craft2x2(bot, itemName, count = 1) {
    const mc = require('minecraft-data')(bot.version);
    const item = mc.itemsByName[itemName];
    const {getIngredients} = require('./getMissingIngredients');

    if (!item) {
        throw new Error(`Invalid item name: ${itemName}`);
    }

    //const recipes = bot.recipesFor(item.id, null, count, null); // null = 2x2 grid

    let recipes = bot.recipesAll(item.id, null, 1, null);
    if (recipes.length === 0) {
        throw new Error(`No recipes found for ${name} with the given crafting context`);
    }

    // Count inventory items by id for quick lookup
    const invCounts = {};
    for (const item of bot.inventory.items()) {
        const id = mc.itemsByName[item.name]?.id;    
        
        if(id != null){
            invCounts[id] = (invCounts[id] || 0) + item.count;
        }
    }

    for (const recipe of recipes) {
        const ingredients = getIngredients(recipe);
        let flag = 0
    
        for (const ingredient of ingredients) {
            const have = invCounts[ingredient.id] || 0;
            const need = ingredient.count;
            if(need > have){
                flag = 1;
                break;
            }
        }
        if(flag){
            continue; // Skip this recipe if any ingredient is missing
        }
        if(flag == 0){
            try {
                await bot.craft(recipe, Math.ceil(count/recipe.result.count), null);
                bot.chat(`Crafted ${itemName} x${count} using 2x2 grid.`);
                return;
            } catch (err) {
                throw new Error(`Failed to craft ${itemName} in 2x2 grid: ${err.message}`);
            }
        }
      }

      throw new Error(`No valid recipe found for ${itemName} in 2x2 grid with available ingredients.`);
}



async function craftItem(bot, name, count = 1) {
    const findCraftingTable = require('./findCraftingTable');
    const craftWithTable = require('./craftWithTable');
    const {getMissingIngredients} = require('./getMissingIngredients');

    if (await canCraftIn2x2(bot, name)) {
        const {missingCount, missingDescriptions} = await getMissingIngredients(bot, name, null);

        if (missingCount > 0) {
            throw new Error(`Missing ingredients for ${name}: ${missingDescriptions.join(' or ')}`);        
        }

        await bot.chat(`Crafting ${name} in 2x2 grid`);
        return await craft2x2(bot, name, count);
    }

    await bot.chat('Crafting in 3x3 grid, finding or placing crafting table...');



    let tableBlock = await findCraftingTable(bot);

    if (!tableBlock) {
        await bot.chat("Couldn't find a crafting table.");
        throw new Error("Crafting table required but not found placed anywhere nearby.");
    }


    try {
        const {missingCount, missingDescriptions} = await getMissingIngredients(bot, name, tableBlock);

        if (missingCount > 0) {
            throw new Error(`Missing ingredients for ${name}: ${missingDescriptions.join(' or ')}`);        
        }
        await craftWithTable(bot, name, count, tableBlock);
    } catch (err) {
        await bot.chat(`Crafting failed: ${err.message}`);
        throw err;
    }

    bot.chat(`Successfully crafted ${name} x${count}`);
}
module.exports = craftItem;