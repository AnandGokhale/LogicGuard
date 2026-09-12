from fastapi import FastAPI, Request
from pydantic import BaseModel, validator
import time

from typing import Optional, List, Dict
import uvicorn
import json
from LTL_implementer import get_obs_props, get_action_props, filter_actions_LTL_trace,compile_automaton, HARD_LTL_RULES, SOFT_LTL_RULES,convert_action_to_string, SOFT_LTL_RULES_EXPLAINER
from utils import get_response_4_1,get_response_4_nano, extract_javascript_code_block

import argparse

app = FastAPI()

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


def generate_prompt(state: BotState, failed_codes) -> str:
    '''
    Generate a prompt for GPT-4o based on the bot state.
    '''

    response_format = """
            Code:
            ```javascript
            await yourChosenPrimitive(bot,corresponding arguments);
            ```
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
        Critique: ...
        Previous failed code: ...

        You should then respond to me with
        Code:
            1) You must respond with a single line of code that corresponds to one of the following primitives:
                - Use `mineBlock(bot, name, count)` to collect blocks. Do not use `bot.dig` directly.
                - Use `craftItem(bot, name, count)` to craft items. Do not use `bot.craft` or `bot.recipesFor` directly.
                - Use `smeltItem(bot, itemName, fuelName,count)` to smelt itemName using fuelName. Do not use `bot.openFurnace` directly.
                - Use `placeItem(bot, name, position)` to place blocks. Do not use `bot.placeBlock` directly.
                - Use exploreUntil(bot, direction, maxTime, callback) to explore, where,
                    - direction is a Vec3 with values -1, 0, or 1 (e.g., new Vec3(1, 0, 1) to explore diagonally).
                    - maxTime is in seconds (default is 60).
                    - callback is a function that returns a truthy value when the exploration goal is met. If it returns something truthy, the bot stops exploring early and exploreUntil returns that value. Otherwise, exploration continues until the time runs out. For example, callback can be () => {{
                                return bot.findBlock({{ matching: block => block.name === "iron_ore", maxDistance: 32 }});
                            }}
                - Use `equipItem(bot, name, destination)` to equip an item in the bot's hand or armor slots. The default for destination is 'hand'. For example, `equipItem(bot, "wooden_pickaxe")` equips a wooden pickaxe in the bot's hand.
            2)  Every primitive function must be awaited, as they are asynchronous.
            3)  Your code should make progress towards the task in the task description, and must be very specific to the inventory it has.
            4)  Functions in the "last chosen primitive" section will not be saved or executed. Do not reuse functions listed there. If there is no error, it was executed successfully, if there is an error, it was not executed successfully
            5) `maxDistance` should always be 32 for `bot.findBlocks` and `bot.findBlock`. Do not cheat.
            6)  Do not use `bot.on` or `bot.once` to register event listeners. You definitely do not need them.
            7)  Make sure you use the correct names for blocks and items, as they are case-sensitive. For example, use "stone" instead of "Stone", "oak_log" instead of "Oak Log", etc.
            8) Make sure that the primitive you choose is appropriate for the task and the current state of the bot (i.e. the inventory and the surroundings). 
            9) Make sure that if you try to mine a block, you have the right tool in your hand. For example, if you want to mine diamon, you need an iron pickaxe in your hand.
            10) Make sure to use the count in order to prevent repetitive actions. For example, if you want to mine 10 stone blocks, use `await mineBlock(bot, "stone", 10)` instead of `await mineBlock(bot, "stone", 1)` and then repeating the action 10 times.

        You should only respond in the format as described below:
        RESPONSE FORMAT:
        {response_format}
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
        Critique: {state.critic}
        Previous failed code: You previously attempted the following codes, and they didnt work because they violated the critics recommendation {failed_codes if failed_codes else "None"}
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

    #print("Observation props : ", obs_props)

    feasible_actions = filter_actions_LTL_trace(obs_props, trace, SOFT_LTL_RULES + HARD_LTL_RULES)



    feasible_action_descriptor = "The critic recommends one of the following actions based on LTL rules:\n"
    feasible_actions_list = []
    print("Feasible actions based on LTL rules:")
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




    failed_codes = []

    while True:
        try:
            intro_prompt, main_prompt = generate_prompt(state, failed_codes)
            print("Generated prompt:")
            print(main_prompt)
            response = await get_response_4_1(intro_prompt, main_prompt)
            #print("Generated response:")
            print(response)

            code = extract_javascript_code_block(response)
            action_prop = get_action_props(code)
            try: 
                action_keys = get_active_keys(action_prop)

            except ValueError as e:
                print(f"Error getting active keys from action prop: {e}")
                failed_codes.append(f"{code} failed because this action is invalid.")
                continue

            print("action keys:",  action_keys)

            if(action_keys in feasible_actions_list or len(feasible_actions_list) == 0):
                print("Either Action is feasible according to LTL rules, or nothing is feasible.")
                break

            # Figure out why the action is not feasible
            for i in range(len(SOFT_LTL_RULES)):
                law = SOFT_LTL_RULES[i]
                print(f"Checking law: {law}")
                feasible_action_law_wise = filter_actions_LTL_trace(obs_props, trace, [law])
                feasible_actions_list_law = []
                for action in feasible_action_law_wise:
                    feasible_actions_list_law.append(get_active_keys(action))
                if action_keys in feasible_actions_list_law or len(feasible_actions_list_law) == 0:
                    continue



                failed_codes.append(f"{code} failed because the critic recommends that {SOFT_LTL_RULES_EXPLAINER[i]} \n")


            print("Failed codes so far:", failed_codes)




        except Exception as e:
            print(f"Error generating response: {e}")
            print("Retrying...")
            continue


    code = extract_javascript_code_block(response)
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
        "failed_codes": failed_codes,
        "time": time.time()
    })




    import pickle

    #Save trace to file
    with open(FILENAME + ".pkl", "wb") as f:
        pickle.dump(saved_trajectory, f)
    with open(FILENAME + "_full_state.pkl", "wb") as f:
        pickle.dump(saved_trajectory_full_state, f)

    return {
        "code": extract_javascript_code_block(response)
    }




if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process some variables.")
    parser.add_argument('--file', type=str, required=True, help='Name of the user')
    args = parser.parse_args()

    #AUTOMATA = compile_automaton(HARD_LTL_RULES + SOFT_LTL_RULES)
    

    FILENAME = args.file
    uvicorn.run(app, host="127.0.0.1", port=8000)