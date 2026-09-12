const { min } = require('lodash');

function getIngredients(recipe) {
  if (Array.isArray(recipe.ingredients) && recipe.ingredients !== null) {
    return recipe.ingredients;
  }
  let items = [];
  // Case 1: delta is a 2D array (shaped recipe)
  if (Array.isArray(recipe.delta[0])) {
    for (const row of recipe.delta) {
      for (const item of row) {
        if (item && item.count < 0) {
          items.push({
            id: item.id,
            count: -item.count,
            metadata: item.metadata,
          });
        }
      }
    }
  }

  // Case 2: delta is a flat array (shapeless recipe)
  else {
    for (const item of recipe.delta) {
      if (item && item.count < 0) {
        items.push({
          id: item.id,
          count: -item.count,
          metadata: item.metadata,
        });
      }
    }
  }
  return items;
}


async function getMissingIngredients(bot, name, craftingTable = null) {
  const mcData = require('minecraft-data');

  const mc = mcData(bot.version);
  const item = mc.itemsByName[name];
  if (!item) throw new Error(`Unknown item name: ${name}`);

  // Get all recipes for this item with/without crafting table
  let recipes = craftingTable
    ? bot.recipesAll(item.id, null, 1, craftingTable)
    : bot.recipesAll(item.id, null, 1, null);

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

  // For each recipe, find missing ingredients

  //const recipesMissing = [];

  let minMissing = Infinity;
  let bestRecipe = null;
  let bestMissing = [];
  let bestMissingList = [bestMissing];
  for (const recipe of recipes) {
    const ingredients = getIngredients(recipe);
    

    let totalMissing = 0
    let missingList = [];

    for (const ingredient of ingredients) {
        const have = invCounts[ingredient.id] || 0;
        const need = ingredient.count;
        totalMissing += Math.max(need - have, 0);
        if(need > have){
            missingList.push(
                {
                    id: ingredient.id,
                    count: need > have? need - have : 0,
                    name: mc.items[ingredient.id]?.name || 'unknown'
                }
            )
        }
    }

    if(totalMissing < minMissing){
        minMissing = totalMissing;
        bestRecipe = recipe;
        bestMissing = missingList;
        bestMissingList = [bestMissing];
    }
    if(totalMissing == minMissing){
        //Construct an object with both bestMissimg and missingList
        bestMissingList.push(missingList);
    }
    if(minMissing == 0){
      return {
        bestRecipe,
        missingCount: 0,
        bestMissingList: [],
        missingDescriptions: []
      }; // Found a recipe with no missing ingredients
    }
  }
  const uniqueMissingSets = new Set();
    for (const missingList of bestMissingList) {
    // Convert each list of items into a canonical string
    const key = missingList
        .map(item => `${item.count}x ${item.name}`) // convert each item
        .sort() // normalize the order
        .join(', '); // convert the list into a single string
    uniqueMissingSets.add(key); // add to set to deduplicate
    }

    // Convert set back to array for display
    const missingDescriptions = Array.from(uniqueMissingSets);
    return {
      bestRecipe,
      missingCount: minMissing,
      bestMissingList,
      missingDescriptions
    };
}

module.exports = {getMissingIngredients, getIngredients};