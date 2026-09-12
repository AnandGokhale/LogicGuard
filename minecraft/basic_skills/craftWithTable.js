const mcData = require('minecraft-data');

async function craftWithTable(bot, name, count, craftingTableBlock) {
  const mc = mcData(bot.version);
  const { GoalLookAtBlock } = require('mineflayer-pathfinder').goals;
  const { getIngredients } = require('./getMissingIngredients');

  if (!name || typeof name !== 'string') {
    throw new Error("Invalid item name");
  }

  const item = mc.itemsByName[name];
  if (!item) throw new Error(`No item named "${name}"`);

  // Move close and look at the crafting table
  await bot.pathfinder.goto(new GoalLookAtBlock(craftingTableBlock.position, bot.world));

  // Find recipes that use a crafting table
  let recipes = bot.recipesAll(item.id, null, 1, craftingTableBlock);
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
              await bot.craft(recipe, Math.ceil(count/recipe.result.count), craftingTableBlock);
              bot.chat(`Crafted ${name} x${count} using 3x3 grid.`);
              return;
          } catch (err) {
              throw new Error(`Failed to craft ${name} in 3x3 grid: ${err.message}`);
          }
      }
    }

    throw new Error(`No valid recipe found for ${name} in 3x3 grid with available ingredients.`);


}

module.exports = craftWithTable;