import spot
from typing import List, Dict, Set

import laws_store
from laws_store import INNER_MONOLOGUE_SOFT_LAWS_PATH, SAYCAN_SOFT_LAWS_PATH


OBS_VARIABLES_LIST = [
        "obs_has_log",
        "obs_has_plank",
        "obs_has_2x_plank",
        "obs_has_3x_plank",
        "obs_has_4x_plank",
        "obs_has_11x_plank",
        "obs_has_2x_stick",    
        "obs_has_3x_cobble",
        "obs_has_8x_cobble",
        "obs_has_11x_cobble",
        "obs_has_wood_pickaxe",
        "obs_has_stone_pickaxe",
        "obs_has_iron_pickaxe",
        "obs_has_diamond",
        "obs_has_iron_ingot",
        "obs_has_3x_iron_ingot",
        "obs_has_1x_iron_ore",
        "obs_has_2x_iron_ore",
        "obs_has_3x_iron_ore",
        "obs_has_crafting_table",
        "obs_has_furnace",
        "obs_has_fuel",
        "obs_near_crafting_table",
        "obs_near_furnace",
        "obs_diamond_in_chunk",
        "obs_iron_in_chunk",
        "obs_coal_in_chunk",
        "obs_iron_pickaxe_equipped",
        "obs_stone_pickaxe_equipped",
        "obs_wood_pickaxe_equipped"
]

ACTION_VARIABLES_LIST = [
    "action_mine_log",
    "action_mine_stone",   
    "action_mine_iron_ore",
    "action_mine_coal",
    "action_mine_diamond",
    "action_craft_planks",
    "action_craft_stick",
    "action_craft_wooden_pickaxe",
    "action_craft_stone_pickaxe",
    "action_craft_iron_pickaxe",
    "action_craft_crafting_table",
    "action_craft_furnace",
    "action_smelt_iron",
    "action_equip_wood_pickaxe",
    "action_equip_stone_pickaxe",
    "action_equip_iron_pickaxe",
    "action_explore_general",
    "action_place_crafting_table",
    "action_place_furnace",
    "action_explore_diamond_down"
]


HARD_LTL_RULES_SAYCAN = ['G(!obs_iron_pickaxe_equipped -> X(!action_mine_diamond))', #1
                         'G(!obs_near_crafting_table -> X(!action_craft_wooden_pickaxe & !action_craft_stone_pickaxe & !action_craft_iron_pickaxe))', #2
                         'G(!obs_near_crafting_table -> X(!action_craft_furnace))', #3
                         'G(!(obs_stone_pickaxe_equipped | obs_iron_pickaxe_equipped) -> X(!action_mine_iron_ore))', #4
                         'G(!(obs_wood_pickaxe_equipped | obs_stone_pickaxe_equipped | obs_iron_pickaxe_equipped)   -> X(!action_mine_stone))', #5
                         'G(!obs_has_iron_pickaxe -> X(!action_equip_iron_pickaxe))', #6
                         'G(!obs_has_3x_plank | !obs_has_2x_stick -> X(!action_craft_wooden_pickaxe))', #7
                         'G(!obs_has_4x_plank -> X(!action_craft_crafting_table))', #8
                         'G(!obs_has_8x_cobble -> X(!action_craft_furnace))', #9
                         'G(!(obs_has_2x_stick & obs_has_3x_iron_ingot) -> X(!action_craft_iron_pickaxe))', #10
                         'G(!obs_has_3x_cobble | !obs_has_2x_stick -> X(!action_craft_stone_pickaxe))', #11
                         'G(!obs_coal_in_chunk | !(obs_wood_pickaxe_equipped | obs_stone_pickaxe_equipped | obs_iron_pickaxe_equipped) -> X(!action_mine_coal))', #12
                         'G(!obs_has_log -> X(!action_craft_planks))', #13
                         'G(!obs_has_2x_plank -> X(!action_craft_stick))', #14
                         'G(!obs_near_furnace | !obs_has_1x_iron_ore | !obs_has_fuel  -> X(!action_smelt_iron))', #15
                         'G(!obs_has_wood_pickaxe -> X(!action_equip_wood_pickaxe))', #16
                         'G(!obs_has_stone_pickaxe -> X(!action_equip_stone_pickaxe))', #17
                         'G(!obs_has_crafting_table -> X(!action_place_crafting_table))', #18
                         'G(!obs_has_furnace -> X(!action_place_furnace))' #19
                        ]
# Soft laws live in laws/saycan_soft_laws.json (written by critic.py, see laws_store.py)
SOFT_LTL_RULES_SAYCAN, SOFT_LTL_RULES_SAYCAN_EXPLAINER = laws_store.load_rules(SAYCAN_SOFT_LAWS_PATH)


def get_obs_props(state):

    return {
        "obs_has_log": any("log" in item.name for item in state.inventory),
        "obs_has_plank": any("planks" in item.name for item in state.inventory),
        "obs_has_2x_plank": sum(item.count for item in state.inventory if "planks" in item.name) >= 2,
        "obs_has_3x_plank": sum(item.count for item in state.inventory if "planks" in item.name) >= 3,
        "obs_has_4x_plank": sum(item.count for item in state.inventory if "planks" in item.name) >= 4,
        "obs_has_11x_plank": sum(item.count for item in state.inventory if "planks" in item.name) >= 11,
        "obs_has_2x_stick": sum(item.count for item in state.inventory if "stick" in item.name) >= 2,    
        "obs_has_3x_cobble": sum(item.count for item in state.inventory if "cobblestone" in item.name) >=3,
        "obs_has_8x_cobble": sum(item.count for item in state.inventory if "cobblestone" in item.name) >= 8,
        "obs_has_11x_cobble": sum(item.count for item in state.inventory if "cobblestone" in item.name) >=11,
        "obs_has_wood_pickaxe": any(item.name == "wooden_pickaxe" for item in state.inventory),
        "obs_has_stone_pickaxe": any(item.name == "stone_pickaxe" for item in state.inventory),
        "obs_has_iron_pickaxe": any(item.name == "iron_pickaxe" for item in state.inventory),
        "obs_has_diamond": any(item.name == "diamond" for item in state.inventory),
        "obs_has_iron_ingot": any(item.name == "iron_ingot" for item in state.inventory),
        "obs_has_3x_iron_ingot": sum(item.count for item in state.inventory if "iron_ingot" in item.name) >=3,
        "obs_has_1x_iron_ore": sum(item.name == "raw_iron" for item in state.inventory) >= 1,
        "obs_has_2x_iron_ore": sum(item.count for item in state.inventory if "raw_iron" in item.name) >=2,
        "obs_has_3x_iron_ore": sum(item.count for item in state.inventory if "raw_iron" in item.name) >=3,
        "obs_has_crafting_table": any(item.name == "crafting_table" for item in state.inventory),
        "obs_has_furnace": any(item.name == "furnace" for item in state.inventory),
        "obs_has_fuel": any("log" in item.name or "coal" in item.name or "planks" in item.name for item in state.inventory),
        "obs_near_crafting_table": any(block == "crafting_table" for block in state.nearbyBlocks),
        "obs_near_furnace": any(block == "furnace" for block in state.nearbyBlocks),
        "obs_diamond_in_chunk": any("diamond" in block for block in state.nearbyBlocks),
        "obs_iron_in_chunk": any("iron" in block for block in state.nearbyBlocks),
        "obs_coal_in_chunk": any("coal" in block for block in state.nearbyBlocks),
        "obs_iron_pickaxe_equipped": "iron_pickaxe" == state.equipment.hand,
        "obs_stone_pickaxe_equipped": "stone_pickaxe" == state.equipment.hand,
        "obs_wood_pickaxe_equipped": "wooden_pickaxe" == state.equipment.hand
    }


def get_action_props(action):
    # substrings log and mineBlock in code
    action = action.lower()
    return {
        "action_mine_log": "log" in action and "mineblock" in action,
        "action_mine_stone": "stone" in action and "mineblock" in action,
        "action_mine_iron_ore": "iron_ore" in action and "mineblock" in action,
        "action_mine_coal": "coal" in action and "mineblock" in action,
        "action_mine_diamond": "diamond" in action and "mineblock" in action,
        "action_craft_planks": "planks" in action and "craftitem" in action,
        "action_craft_stick": "stick" in action and "craftitem" in action,
        "action_craft_wooden_pickaxe": "wooden_pickaxe" in action and "craftitem" in action,
        "action_craft_stone_pickaxe": "stone_pickaxe" in action and "craftitem" in action,
        "action_craft_iron_pickaxe": "iron_pickaxe" in action and "craftitem" in action,
        "action_craft_crafting_table": "table" in action and "craftitem" in action,
        "action_craft_furnace": "furnace" in action and "craftitem" in action,
        "action_smelt_iron": "iron" in action and "smeltitem" in action,
        "action_equip_wood_pickaxe": "wooden_pickaxe" in action and "equipitem" in action,
        "action_equip_stone_pickaxe": "stone_pickaxe" in action and "equipitem" in action,
        "action_equip_iron_pickaxe": "iron_pickaxe" in action and "equipitem" in action,
        "action_explore_general": "explore" in action and ("diamond" not in action or "(0, -1, 0)" not in action),
        "action_place_crafting_table": "crafting_table" in action and "placeitem" in action,
        "action_place_furnace": "furnace" in action and "placeitem" in action,
        "action_explore_diamond_down": "explore" in action and "diamond" in action and "(0, -1, 0)" in action
    }


def convert_action_to_string(action):
    DICT = {
        "action_mine_log": "Mine Log",
        "action_mine_stone": "Mine Stone",
        "action_mine_iron_ore": "Mine Iron Ore",    
        "action_mine_coal": "Mine Coal",
        "action_mine_diamond": "Mine Diamond",
        "action_mine_seeds": "Mine Seeds",
        "action_harvest_wheat": "Harvest Wheat",
        "action_craft_planks": "Craft Planks",
        "action_craft_stick": "Craft Stick",
        "action_craft_wooden_pickaxe": "Craft Wooden Pickaxe",
        "action_craft_stone_pickaxe": "Craft Stone Pickaxe",
        "action_craft_iron_pickaxe": "Craft Iron Pickaxe",
        "action_craft_hoe": "Craft Hoe",
        "action_craft_crafting_table": "Craft Crafting Table",
        "action_craft_furnace": "Craft Furnace",
        "action_craft_bucket": "Craft Bucket",
        "action_craft_cake": "Craft Cake",
        "action_craft_sugar": "Craft Sugar",
        "action_smelt_iron": "Smelt Iron",
        "action_till_soil": "Till Soil",
        "action_plant_seeds": "Plant Seeds",
        "action_wait_egg": "Wait for Egg",
        "action_equip_wood_pickaxe": "Equip Wooden Pickaxe",
        "action_equip_stone_pickaxe": "Equip Stone Pickaxe",
        "action_equip_iron_pickaxe": "Equip Iron Pickaxe",
        "action_explore_general": "Explore for any item you think is useful EXCEPT DIAMONDS",
        "action_place_crafting_table": "Place Crafting Table",
        "action_place_furnace": "Place Furnace",
        "action_explore_diamond_down": "Explore for Diamonds Downwards"
    }
    return DICT.get(action, "Unknown Action")

HARD_LTL_RULES = ['G(True)']

HARD_LTL_RULES_EXPLAINER = [
    "Always true, serves as a base rule."
]

# Soft laws live in laws/inner_monologue_soft_laws.json (see laws_store.py).
# The two lists stay index-aligned, which the servers rely on.
SOFT_LTL_RULES_INNER_MONOLOGUE, SOFT_LTL_RULES_INNER_MONOLOGUE_EXPLAINER = laws_store.load_rules(
    INNER_MONOLOGUE_SOFT_LAWS_PATH
)


SOFT_LTL_RULES = [  'G(True)',
                  'G(!obs_wood_pickaxe_equipped & !obs_stone_pickaxe_equipped -> X(!action_mine_stone))',
                  'G(!obs_stone_pickaxe_equipped & !obs_iron_pickaxe_equipped -> X(!action_mine_iron_ore))',
                  'G(!obs_iron_pickaxe_equipped -> X(!action_mine_diamond))',
                  'G(!obs_near_crafting_table -> X(!action_craft_furnace & !action_craft_iron_pickaxe & !action_craft_stone_pickaxe & !action_craft_wooden_pickaxe))',
                  'G(!obs_near_furnace -> X(!action_smelt_iron))',
                  'G(!(obs_has_3x_plank & obs_has_2x_stick) -> X(!action_craft_wooden_pickaxe))',
                  'G(!obs_has_4x_plank -> X(!action_craft_crafting_table))',
                  'G(!obs_has_8x_cobble -> X(!action_craft_furnace))',
                  "G(!(obs_has_2x_stick & obs_has_3x_iron_ingot) -> X(!action_craft_iron_pickaxe))",
                  "G(!obs_has_iron_pickaxe -> X(!action_equip_iron_pickaxe))",
                  "G(obs_has_11x_plank -> X(!action_craft_planks))",
                  "G(obs_has_11x_plank -> X(!action_mine_log))",
                  "G(obs_stone_pickaxe_equipped -> X(!action_equip_stone_pickaxe))",
                  "G(obs_wood_pickaxe_equipped -> X(!action_equip_wood_pickaxe))",
                  "G(obs_has_3x_iron_ingot | obs_has_3x_iron_ore -> X(!action_mine_iron_ore))",
                  "G((obs_has_iron_pickaxe & !obs_iron_pickaxe_equipped) -> X(action_equip_iron_pickaxe))",
                  "G(obs_has_3x_iron_ingot -> X(!action_smelt_iron))",
                  "G(obs_has_crafting_table | obs_near_crafting_table -> X(!action_craft_crafting_table))",
                  "G((obs_has_2x_stick & obs_has_3x_iron_ingot & !obs_has_iron_pickaxe) -> X(action_craft_iron_pickaxe))",
                  "G((obs_has_11x_cobble) -> X(!action_mine_stone))",
                  "G(obs_has_log & obs_has_plank -> X(!action_mine_log))",
                  "G(obs_diamond_in_chunk & !obs_has_iron_pickaxe & obs_has_3x_iron_ingot & obs_has_2x_stick & obs_near_crafting_table -> X(action_craft_iron_pickaxe))",
                  "G((obs_has_log & !obs_has_2x_plank) -> X(action_craft_planks))",
                  "G((!obs_has_2x_plank) -> X(!action_craft_stick))",
                  "G((!obs_coal_in_chunk) -> X(!action_mine_coal))",
                  "G((obs_has_furnace & !obs_near_furnace & obs_has_1x_iron_ore) -> X(action_place_furnace))",
                  "G((obs_near_furnace & obs_has_3x_iron_ore & obs_has_fuel & !obs_has_3x_iron_ingot) -> X(action_smelt_iron))"
                  ]


SOFT_LTL_RULES_EXPLAINER = [
    "Always true, serves as a base rule.",
    "If the wooden pickaxe or stone pickaxe is not equipped, then the agent should not mine stone.",
    "If the stone pickaxe or iron pickaxe is not equipped, then the agent should not mine iron ore.",
    "If the iron pickaxe is not equipped, then the agent should not mine diamond.",
    "If the agent is not near a crafting table, then it should not craft a furnace, iron pickaxe, stone pickaxe, or wooden pickaxe.",
    "If the agent is not near a furnace, then it should not smelt iron.",
    "If the agent does not have at least 3 planks or 2 sticks, then it should not craft a wooden pickaxe.",
    "If the agent does not have at least 4 planks, then it should not craft a crafting table.",
    "If the agent does not have at least 8 cobblestones, then it should not craft a furnace.",
    "If the agent does not have at least 2 sticks and 3 iron ingots, then it should not craft an iron pickaxe.",
    "If the agent does not have an iron pickaxe, then it should not equip it.",
    "If the agent has at least 11 planks, then it should not craft planks.",
    "If the agent has at least 11 planks, then it should not mine logs.",
    "If the stone pickaxe is equipped, then the agent should not equip it again.",
    "If the wooden pickaxe is equipped, then the agent should not equip it again.",
    "If the agent has at least 3 iron ingots or 3 iron ores, then it should not mine iron ore.",
    "If the agent has an iron pickaxe and it is not equipped, then it should equip the iron pickaxe.",
    "If the agent has at least 3 iron ingots, then it should not smelt iron.",
    "If the agent has a crafting table or is near one, then it should not craft another crafting table.",
    "If the agent has at least 2 sticks and 3 iron ingots, and does not have an iron pickaxe, then it should craft an iron pickaxe.",
    "If the agent has at least 11 cobblestones, then it should not mine stone.",
    "If the agent has logs and planks, then it should not mine logs.",
    "If there are diamonds in the chunk, the agent does not have an iron pickaxe, has at least 3 iron ingots, 2 sticks, and is near a crafting table, then it should craft an iron pickaxe.",
    "If the agent has logs and does not have at least 2 planks, then it should craft planks.",
    "If the agent does not have at least 2 planks, then it should not craft sticks.",
    "If there are no coal blocks in the chunk, then the agent should not mine coal.",
    "If the agent has a furnace, is not near it, and has at least 1 iron ore, then it should immediately place the furnace.",
    "If the agent is near a furnace, has at least 3 iron ore, has fuel, and does not have an iron ingot, then it should smelt iron."
]

VARIABLES_LIST = OBS_VARIABLES_LIST + ACTION_VARIABLES_LIST

BDD_DICT = spot.bdd_dict()

for l in VARIABLES_LIST:
    BDD_DICT.register_proposition(spot.formula(l), None)


def compile_automaton(rules, bdd_dict = BDD_DICT):

    auts = [spot.translate(r, 'BA', dict=bdd_dict) for r in rules]
    combined = auts[0]
    for aut in auts[1:]:
        combined = spot.product(combined, aut)
    return combined


def build_word_automaton(trace, variables = VARIABLES_LIST, bdd_dict = BDD_DICT):
    """
    Builds a word automaton from a given trace.

    Parameters:
    - trace: List of sets, where each set contains atomic propositions true at a timestep.
    - variables: Full list of possible atomic propositions (strs).

    Returns:
    - A Spot automaton representing the trace.
    """
    
    aut = spot.make_twa_graph(bdd_dict)

    # Register all atomic propositions from the full variables list
    var_to_bdd = {var: spot.formula_to_bdd(spot.formula(var), bdd_dict, None) for var in variables}

    num_states = len(trace) + 1
    aut.new_states(num_states)
    aut.set_init_state(0)
    aut.set_buchi()

    for i, ap_set in enumerate(trace):
        #label = spot.bddtrue     #false_bdd = spot.formula_to_bdd(spot.formula.ff(), bdd_dict, None)

        label = spot.formula_to_bdd(spot.formula.tt(), bdd_dict, None)

        for var in variables:
            var_bdd = var_to_bdd[var]
            if var in ap_set:
                label &= var_bdd
            else:
                formula = spot.bdd_to_formula(var_bdd, bdd_dict)
                negated_formula = spot.formula.Not(formula)
                label &= spot.formula_to_bdd(negated_formula, bdd_dict,None)

        aut.new_edge(i, i + 1, label)

    # Add self-loop on the last state (to make it Büchi-accepting)
    aut.new_edge(num_states - 1, num_states - 1, spot.formula_to_bdd(spot.formula.tt(), bdd_dict, None), [0])


    return aut


def generate_trace_from_dicts(timestep_dicts: List[Dict[str, bool]]) -> List[Set[str]]:
    """
    Converts a list of dicts (one per timestep) of atomic propositions
    into a trace (list of sets of true propositions) for Spot.
    """
    trace = []
    for step in timestep_dicts:
        true_props = {prop for prop, val in step.items() if val}
        trace.append(true_props)
    return trace


def get_active_keys(one_hot_dict):
    return [key for key, value in one_hot_dict.items() if value == 1]


def filter_actions_LTL_trace(obs_props, trace, rules):
    filtered_actions = []
    actions = [
            {action_var: int(action_var == a) for action_var in ACTION_VARIABLES_LIST}
            for a in ACTION_VARIABLES_LIST
        ]
    trace =  [obs_props]
    for action in actions:

        proposed_trace = generate_trace_from_dicts(trace + [action])
        word_aut = build_word_automaton(proposed_trace)
        feasible =  True        
        for law in rules:
            automaton =  compile_automaton([law])
            run = automaton.intersecting_run(word_aut)
            if run is None:
                feasible = False
                #print(f"Action {proposed_trace[-1]} violates\n LTL rule: {law}")
                break
        if feasible:
            filtered_actions.append(action)
    
    return filtered_actions


        
