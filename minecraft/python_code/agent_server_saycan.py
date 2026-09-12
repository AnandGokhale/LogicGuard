from fastapi import FastAPI, Request
from pydantic import BaseModel, validator
import time

from typing import Optional, List, Dict
import uvicorn
import json
from LTL_implementer import get_obs_props, get_action_props, filter_actions_LTL_trace,compile_automaton, HARD_LTL_RULES, SOFT_LTL_RULES,convert_action_to_string, SOFT_LTL_RULES_EXPLAINER, HARD_LTL_RULES_SAYCAN
from utils import get_response_4_1,get_response_4_nano, extract_javascript_code_block
from laws_store import DEFAULT_LAWS_PATH, load_rules

import argparse



app = FastAPI()

# Laws proposed by the critic, loaded from JSON in __main__ (see laws_store.py).
SOFT_LAWS = []
SOFT_LAW_EXPLAINERS = []
HARD_RULESET = HARD_LTL_RULES_SAYCAN
SOFT_RULESET = HARD_LTL_RULES_SAYCAN

class Position(BaseModel):
    x: float
    y: float
    z: float

class Armor(BaseModel):
    head: str
    chest: str
    legs: str
    feet: str

class Equipment(BaseModel):
    hand: str
    armor: Armor

class Block(BaseModel):
    name: str
    position: Position
    distance: Optional[float]  # category may or may not be present

class Entity(BaseModel):
    name: str
    position: Position
    distance: Optional[float]  # health may or may not be present
    type: Optional[str]  # type may or may not be present, e.g., "mob", "animal", etc.

class InventoryItem(BaseModel):
    name: str
    count: int

class ChatlogItem(BaseModel):
    username: str
    message: str


class BotState(BaseModel):
    codeLastRound: str
    executionError: Optional[str]
    Output: Optional[str]  # This can be used to store the output of the last command
    chatLog: List[ChatlogItem]
    biome: str
    time: int
    nearbyBlocks: List[str]
    neighbourhood: List[Block]  # This can be used to store blocks in the neighbourhood
    nearbyEntities: List[Entity]  # List of entity names, e.g., ["cow", "sheep"]
    health: int = 20 # Default health value
    hunger: int = 20 # Default hunger value
    position: Position
    equipment: Equipment
    inventory: List[InventoryItem]
    inventoryCount: int
    chests: List  # If you want, you can define a Chest model too
    task: str
    context: str
    critic: str

    @validator('chatLog', pre=True)
    def coerce_chatlog(cls, value):
        # Accept list of dicts or ChatlogItems
        return [ChatlogItem(**item) if not isinstance(item, ChatlogItem) else item for item in value]




def parse_saycan_output(llm_output: str):
    """
    Parses the LLM output expected to be a JSON list of dicts containing:
    - action (str)
    - value (float)
    - code (str)

    Returns:
        A list of dictionaries with keys: 'action', 'value', 'code'
    Raises:
        ValueError if parsing fails.
    """
    try:
        # Trim unwanted formatting or code block indicators
        if "```json" in llm_output:
            llm_output = llm_output.split("```json")[-1].split("```")[0].strip()
        elif "```" in llm_output:
            llm_output = llm_output.split("```")[1].strip()

        data = json.loads(llm_output)

        if not isinstance(data, list):
            raise ValueError("Parsed data is not a list.")

        for item in data:
            if not all(k in item for k in ["action", "value", "explanation", "code"]):
                raise ValueError(f"Missing keys in item: {item}")

        return data

    except Exception as e:
        raise ValueError(f"Failed to parse SayCan output: {e}")


def get_best_code(action_list):
    """
    Given a list of action dictionaries (each with 'action', 'value', 'code'),
    returns the code string of the action with the highest value.

    Parameters:
        action_list (list): List of dictionaries containing 'action', 'value', and 'code'.

    Returns:
        str: Code string corresponding to the highest value action.
    """
    if not action_list:
        return None
    best_action = max(action_list, key=lambda x: x.get("value", 0.0))
    return best_action.get("code", None), best_action.get("action", None)



def generate_prompt_saycan(state: BotState) -> str:
    '''
    Generate a prompt for GPT-4o based on the bot state.
    '''
    response_format = """
        [
        {
            "action": "High-level description of the action",
            "value": float between 0.0 and 1.0 (usefulness for mining a diamond),
            "code": "await yourChosenPrimitive(bot, ...);"
        },
        ...
        ]
    """

    intro_prompt = f"""

        You are a helpful assistant that responds with a primitive (built in mineflayer) which will lead to completing any Minecraft task specified by me.

        At each round of conversation, I will give you
        Code from the last round: ...
        Execution error: ...
        Chat log: ...
        Biome: ...
        Time: ...
        Nearby blocks: ... ( A list of all uniqque blocks in a 16 block radius, you may use mineBlock to collect any of these blocks)
        Nearby entities (nearest to farthest):
        Neighbourhood blocks: ... (A list of blocks in your immediate neighbourhood i.e. a 2 block radius)
        Health: ...
        Hunger: ...
        Position: ...
        Equipment: ...
        Inventory (xx/36): ... (A list of all items in your inventory, with their counts)
        Chests: ...
        Task: ...
        Context: ...
        List of FEASIBLE ACTIONS: ...

        You should then respond to me with
        Code:
            1) You must respond with a single line of code that corresponds to one of the following primitives:
                - Use `mineBlock(bot, name)` to collect blocks. Do not use `bot.dig` directly.
                - Use `craftItem(bot, name)` to craft items. Do not use `bot.craft` or `bot.recipesFor` directly.
                - Use `smeltItem(bot, itemName, fuelName)` to smelt itemName using fuelName. Do not use `bot.openFurnace` directly. Each item will consume one fuel.
                - Use `placeItem(bot, name, position)` to place blocks. Do not use `bot.placeBlock` directly.
                - Use exploreUntil(bot, direction, maxTime, callback) to explore, where,
                    - direction is a Vec3 with values -1, 0, or 1 (e.g., new Vec3(1, 0, 1) to explore diagonally).
                    - maxTime is in seconds (default is 60).
                    - callback is a function that returns a truthy value when the exploration goal is met. If it returns something truthy, the bot stops exploring early and exploreUntil returns that value. Otherwise, exploration continues until the time runs out. For example, callback can be () => {{
                                return bot.findBlock({{ matching: block => block.name === "iron_ore", maxDistance: 32 }});
                            }}
                - Use `equipItem(bot, name, destination)` to equip an item in the bot's hand or armor slots. The default for destination is 'hand'. For example, `equipItem(bot, "wooden_pickaxe")` equips a wooden pickaxe in the bot's hand.
            2)  Every primitive function must be awaited, as they are asynchronous.
            3)  Functions in the "last chosen primitive" section will not be saved or executed. Do not reuse functions listed there. If there is no error, it was executed successfully, if there is an error, it was not executed successfully
            4) `maxDistance` should always be 32 for `bot.findBlocks` and `bot.findBlock`. Do not cheat.
            5)  Do not use `bot.on` or `bot.once` to register event listeners. You definitely do not need them.
            6)  Make sure you use the correct names for blocks and items, as they are case-sensitive. For example, use "stone" instead of "Stone", "oak_log" instead of "Oak Log", etc.
            
            
            You must output a JSON list that includes **every FEASIBLE ACTION** in the same order they appear.

            Each JSON dictionary must contain:
            - `"action"`: the exact string from the feasible action list (no rewording)
            - `"value"`: a float between 0.0 and 1.0 which describes how important this action in making progress towards completing the task, given the current state of the agent and the environment.
            - `"explanation"` : a string explaining this choice of value
            - `"code"`: a string representing a single line of valid code, e.g., `"await mineBlock(bot, 'stone', 3);"`

            Do not include any explanation, commentary, or other text.

            Respond only with the following format:
            ```json
            [
            {{
                "action": "feasible_action_1",
                "value": 0.8,
                "explanation": "This action is very important as a next step towards completing the task",
                "code": "await mineBlock(bot, 'oak_log', 3);"
            }},
            {{
                "action": "feasible_action_2",
                "value": 0.1,
                "explanation": "This action is less important as a next step towards completing the task",
                "code": "await placeItem(bot, 'crafting_table', bot.entity.position.offset(1, 0, 0));"
            }},
            ...
            ]
    """

    chatlog_str = ", ".join(f"[{item.username}] {item.message}" for item in state.chatLog) if state.chatLog else "None"
    #Neighbourhood blocks: {", ".join([f"{block.name} at ({block.position.x}, {block.position.y}, {block.position.z})" for block in state.neighbourhood]) if state.neighbourhood else "None"}
        
    main_prompt = f"""
        Code from the last round: {state.codeLastRound}
        Execution error: {state.executionError if state.executionError else "None"}
        Biome: {state.biome}
        Time: {state.time}
        Nearby blocks: {state.nearbyBlocks if state.nearbyBlocks else "None"}
        Nearby entities (nearest to farthest): {", ".join([f"{entity.name} ({entity.type})" for entity in state.nearbyEntities]) if state.nearbyEntities else "None"}
        Health: {state.health}
        Hunger: {state.hunger}
        Position: ({state.position.x}, {state.position.y}, {state.position.z})          
        Equipment: Hand: {state.equipment.hand}, Armor: [Head: {state.equipment.armor.head}, Chest: {state.equipment.armor.chest}, Legs: {state.equipment.armor.legs}, Feet: {state.equipment.armor.feet}]
        Inventory (count: {state.inventoryCount}): {", ".join([f"{item.name} ({item.count})" for item in state.inventory]) if state.inventory else "None"}
        Chests: {", ".join(state.chests) if state.chests else "None"}
        Task: {state.task}
        Context: {state.context}
        List of feasible actions: {state.critic}
    """

    
    return intro_prompt, main_prompt



observation_trajectory = []
action_trajectory = []

trace = []

saved_trajectory = []

saved_trajectory_full_state = []


def get_active_keys(one_hot_dict):
    active_keys = [key for key, value in one_hot_dict.items() if value == 1]
    if len(active_keys) != 1:
        raise ValueError(f"Expected exactly one active key, but found {len(active_keys)}: {active_keys}")
    return active_keys[0]

def get_all_feasible_keys(feasible_action_list):
    """
    Given a list of one-hot action dictionaries, return a set of all feasible action keys.
    """
    return {
        key
        for timestep in feasible_action_list
        for key, value in timestep.items()
        if value == 1
    }

@app.post("/generate-code")
async def generate_code(state: BotState):

    '''
    1) Parse the state
    2) Generate a prompt for GPT-4o
    3) Call the OpenAI API to get the code
    4) Return the generated code
    '''
    #print("Received state:")
    #print(json.dumps(state.dict(), indent=2))

    # Generate atomic props from the state
    obs_props = get_obs_props(state)

    if(obs_props['obs_has_diamond'] == 1):
        exit()





    #print("Observation props : ", obs_props)

    feasible_actions = filter_actions_LTL_trace(obs_props, trace, SOFT_RULESET)

    print(feasible_actions)
    if("action_mine_log" in feasible_actions):
        if(not any("log" in block for block in state.nearbyBlocks)):
            feasible_actions.remove("action_mine_log")

    if(len(feasible_actions) == 0):

        rule_stats = []

        for i, rule in enumerate(SOFT_LAWS):
            filtered_actions = filter_actions_LTL_trace(obs_props, trace, [rule])
            rule_stats.append((i, rule, len(filtered_actions), filtered_actions))

        # Sort by fewest allowed actions (most constraining first)
        rule_stats.sort(key=lambda x: x[2])

        for i, rule, num_allowed, actions in rule_stats:
            print("="*50)
            print(f"Rule {i}: {rule}")
            if SOFT_LAW_EXPLAINERS[i]:
                print(f"Explanation: {SOFT_LAW_EXPLAINERS[i]}")
            print(f"Number of actions allowed: {num_allowed}")
            print(f"Filtered actions:")
            feasible_actions_list = []
            for action in actions:
                feasible_actions_list.append(get_active_keys(action))

            print(feasible_actions_list)
            
            print("Observation Propositions (obs_props):")
            for k, v in obs_props.items():
                if v:
                    print(f"  {k}: {v}")

        x = input()



        print(feasible_actions)
        if("action_mine_log" in feasible_actions):
            if(not any("log" in block for block in state.nearbyBlocks)):
                feasible_actions.remove("action_mine_log")


    feasible_action_descriptor = ""
    feasible_actions_list = []
    for action in feasible_actions:
        feasible_action_descriptor += f"{convert_action_to_string(get_active_keys(action))}\n"
        feasible_actions_list.append(get_active_keys(action))

    print("Feasible actions list:", feasible_actions_list)




    print("feasible_action_descriptor:" + feasible_action_descriptor)

    observation_trajectory.append(obs_props)

    trace.append(obs_props)

    # Generate valid list of action props from obs_props and LTL rules.

    # populate state.critic with the valid action props

    state.critic = feasible_action_descriptor





    while True:
        try:
            # List all true keys in obs_props
            obs_props_str = ", ".join(f"{key}" for key, value in obs_props.items() if value == 1)
            print("obs_props_str:", obs_props_str)
            intro_prompt, main_prompt = generate_prompt_saycan(state)
            print("Generated prompt:")
            print(main_prompt)
            response = await get_response_4_1(intro_prompt, main_prompt)
            print("Generated response:")
            print(response)

            parsed_response = parse_saycan_output(response)
            code, action_best = get_best_code(parsed_response)


            print("Best code:", code, "Best Action: ", action_best)

            action_props = get_action_props(code)


            break

        except Exception as e:
            print(f"Error generating response: {e}")
            print("Retrying...")
            continue
            

    action_props = get_action_props(code)
    action_trajectory.append(action_props)
    trace.append(action_props)


    saved_trajectory.append({
        "observation": obs_props,
        "action": action_props,
        "code": code,
        "previous_error": state.executionError if state.executionError else "None",
        "time": time.time()
    })

    saved_trajectory_full_state.append({
        "state": state,
        "action": action_props,
        "code": code,
        "time": time.time()
    })




    import pickle

    #Save trace to file
    with open(FILENAME + ".pkl", "wb") as f:
        pickle.dump(saved_trajectory, f)
    with open(FILENAME + "_full_state.pkl", "wb") as f:
        pickle.dump(saved_trajectory_full_state, f)

    return {
        "code": code,
        "response": ""
    }




if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Process some variables.")
    parser.add_argument('--file', type=str, required=True, help='name of file to save the trajectory to')
    parser.add_argument('--mode', type=int, required=True, help='0 = actor 1 = critic')
    parser.add_argument('--laws', type=str, default=DEFAULT_LAWS_PATH,
                        help='JSON file of critic-proposed laws (written by critic.py)')

    args = parser.parse_args()

    SOFT_LAWS, SOFT_LAW_EXPLAINERS = load_rules(args.laws)
    print(f"Loaded {len(SOFT_LAWS)} soft laws from {args.laws}")

    if args.mode == 0:
        HARD_RULESET = HARD_LTL_RULES_SAYCAN
        SOFT_RULESET = HARD_LTL_RULES_SAYCAN
    else:
        # Use soft LTL rules for actor
        HARD_RULESET = HARD_LTL_RULES_SAYCAN 
        SOFT_RULESET = HARD_LTL_RULES_SAYCAN + SOFT_LAWS
        SOFT_FILTER = SOFT_LAWS

    FILENAME = args.file


    uvicorn.run(app, host="127.0.0.1", port=8000)

