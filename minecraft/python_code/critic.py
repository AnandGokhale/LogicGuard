import json
import pickle
from LTL_implementer import OBS_VARIABLES_LIST, ACTION_VARIABLES_LIST
import asyncio
from utils import get_response_4o, get_response_4o_mini, get_response_o3
import laws_store
from laws_store import DEFAULT_LAWS_PATH, extract_json_block


def get_active_keys(one_hot_dict):
    return [key for key, value in one_hot_dict.items() if value == 1]


def format_trajectory_for_critic(trajectory):
    lines = []
    for i in range(len(trajectory)):
        step = trajectory[i]
        next_step = trajectory[i + 1] if i + 1 < len(trajectory) else None

        obs = step["observation"]
        obs_next = next_step["observation"] if next_step else None

        action_keys = [k for k, v in step["action"].items() if v]
        result = "success" if not (next_step and next_step.get("previous_error")) else f"Error: {next_step['previous_error']}"

        # Show only the APs that changed between this step and the next
        if obs_next:
            changed_aps = [k for k in obs if obs.get(k) != obs_next.get(k)]
        else:
            changed_aps = []

        lines.append(f"Step {i + 1}:\n"
                     f"- Observations: {', '.join([k for k in obs if obs[k]]) or 'None'}\n"
                     f"- Action: {', '.join(action_keys) if action_keys else 'action_idle'}\n"
                     f"- Changed APs: {', '.join(changed_aps) if changed_aps else 'None'}\n"
                     f"- Result: {result}\n")
    
    return "\n".join(lines)





async def analyze_trace(filename, laws_path=DEFAULT_LAWS_PATH, apply_changes=True):
    with open(filename, 'rb') as f:
        trace = pickle.load(f)

    print(format_trajectory_for_critic(trace))

    laws = laws_store.load(laws_path)
    existing_laws = laws_store.format_for_prompt(laws)


    intro_prompt = f"""
    You are an expert critic observing the trajectory of a Minecraft agent. The goal of the agent is to mine a diamond.

    You are given:
    1) A list of atomic observation and action variables
    2) A list of failures that occurred in trajectories
    3) Existing LTL rules implemented

    You will be given a series of steps taken by the agent, including observations, actions, and success/failure of the action with an error message.
    Your task is to analyze the trajectory and provide LTL laws that constrain the agent's actions in order to boost efficiency and performance. 
    The laws should be in the form of LTL formulas, and you should provide a brief explanation of each law. The boolean variables used in the laws are defined as follows:

    Observation Variables: 
    {", ".join(OBS_VARIABLES_LIST)}

    The observations in the atomic proposition space are described as follows:

    - `obs_has_x` corresponds to having the item `x` in the inventory of the agent. 
    - `obs_near_crafting_table` or `obs_near_furnace` define if the agent is within an interacting distance of a crafting table or furnace.
    - `obs_has_x_equipped` corresponds to an object `x` (e.g., an iron pickaxe) actively equipped.
    - Only one item can be equipped at any point in time. 
    - You may propose additional observation variables if needed to express useful rules.

    Action Variables:
    {", ".join(ACTION_VARIABLES_LIST)}

    The actions the agent can perform are limited to a few types:

    - `action_mine_x`: mines the item `x`. Certain blocks require certain tools:
        - stone: wood pickaxe or better
        - iron: stone pickaxe or better
        - diamond: iron pickaxe or better
    - `action_craft_x`: crafts an item `x`, if prerequisites and (if needed) a crafting table are present.
    - `action_smelt_iron`: smelts raw iron into ingots using fuel and a furnace.
    - `action_equip_x`: equips a tool for mining. Only one tool can be equipped at a time.
    - `action_explore`: used to find resources not currently visible.
    - `action_place_x`: places an item like a crafting table or furnace to enable usage.
    """
    main_prompt = f"""
    You are a symbolic critic observing the trajectory of a Minecraft agent. The agent is inefficient, often repeats work, and occasionally causes errors like trying to mine without the right tool or crafting without the ingredients.

    GOAL OF AGENT: MINE A DIAMOND  
    YOUR GOAL: PROPOSE LTL LAWS THAT PROMOTE THE AGENT'S PROGRESS TOWARD THIS GOAL AND PREVENT INEFFICIENCIES.

    THINK OF THE BASIC TASK GRAPH REQUIRED TO MINE A DIAMOND, and PROPOSE LTL LAWS TO GUIDE THE AGENT ALONG THAT GRAPH.

    Before forcing any action, think of checking if the subgoals to do that action are met.


    ### Your task:
    1. Decompose the task of mining a diamond into symbolic subgoals: acquiring wood, crafting tools, smelting, equipping tools, etc.
    2. For each subgoal transition (e.g., "has stone => craft stone_pickaxe"), propose an **LTL law** that enables or encourages this step.
    3. Also identify any **errors** or **inefficiencies** in the trajectory. For each one, propose an LTL law to prevent that mistake in the future.
    4. Focus on writing LTL laws in the form `G(condition => X(action))`. Use observation variables for `condition`, and action variables for `action`.
    5. Avoid overly specific or redundant laws. Try to generalize from the plan, not just from individual steps.
    6. You may also propose **new boolean observation variables** if needed to express useful constraints (e.g., `obs_has_stone_pickaxe`, `obs_seen_diamond_block`).
    7. Your final set of LTL laws should include:
    - ≥3 rules that **encourage efficient, goal-aligned behavior**
    - ≥1 rule that **discourages observed inefficient behavior**

    ### Existing Inputs:
    - Existing LTL laws (do not repeat these, they are already active):\n{existing_laws}
    - Action and observation variables:
        - Actions: {", ".join(ACTION_VARIABLES_LIST)}
        - Observations: {", ".join(OBS_VARIABLES_LIST)}


    ### Agent Trajectory:
    {format_trajectory_for_critic(trace)}

    
    ### Output Format:
    Return ONLY a single JSON object (no prose outside it, no markdown fence) with this shape:

    {{
      "reasoning": {{
        "plan_decomposition": "the full high-level plan to mine a diamond as a sequence of symbolic subgoals",
        "plan_conversion": "the sequence of obs props and action props that correspond to this plan",
        "observed_mistakes": "mistakes or inefficiencies you found in the trajectory"
      }},
      "efficiency_laws": [
        {{"law": "G(obs_... -> X(action_...))",
          "explanation": "why this law helps, and which part of the plan it covers"}}
      ],
      "inefficiency_laws": [
        {{"law": "G(obs_... -> X(!action_...))",
          "explanation": "which mistake in the trajectory this prevents"}}
      ]
    }}

    Requirements on the laws:
    - At least 3 entries in `efficiency_laws` and at least 1 in `inefficiency_laws`.
    - Write formulas in ASCII spot syntax: `G`, `X`, `&`, `|`, `!`, `->`. Example:
      `G(obs_has_1x_iron_ore & obs_near_furnace & obs_has_fuel -> X(action_smelt_iron))`
    - Use ONLY the observation and action variables listed above. Any law that mentions a
      variable outside those lists is rejected by the law compiler, so do not invent new ones.
    - Do not restate laws that are already active.
    """



    print("="   * 40)
    response = await get_response_o3(intro_prompt, main_prompt)
    print(response)

    try:
        parsed = extract_json_block(response)
    except Exception as e:
        print(f"Could not parse the critic response as JSON ({e}); no laws were written.")
        return None

    reasoning = parsed.get("reasoning", {})
    if reasoning:
        print("=" * 40)
        print("Reasoning:")
        print(json.dumps(reasoning, indent=2))

    proposed = parsed.get("efficiency_laws", []) + parsed.get("inefficiency_laws", [])

    print("=" * 40)
    print(f"{len(proposed)} laws proposed")

    added = 0
    for law in proposed:
        formula = (law.get("law") or law.get("formula") or "").strip()
        if not formula:
            continue
        index, status = laws_store.add(laws, formula, law.get("explanation", ""))
        if status == "added":
            print(f"  [{laws[index]['law_id']}] {formula}")
            added += 1
        else:
            print(f"  [skipped: {status}] {formula}")

    if not added:
        print("No new laws to write.")
    elif apply_changes:
        laws_store.save(laws, laws_path)
        print(f"Wrote {added} new laws to {laws_path}")
    else:
        print(f"--no-write set: {laws_path} left unchanged")

    return laws


async def handle_conflicts(filename, laws_path=DEFAULT_LAWS_PATH, apply_changes=True):

    with open(filename, 'rb') as f:
        trace = pickle.load(f)

    laws = laws_store.load(laws_path)



    intro_prompt = f"""
    You are an expert critic observing the trajectory of a Minecraft agent. The goal of the agent is to mine a diamond.

    Sometimes, the laws you impose are too constraining and prevent all possible actions. Your job is to break these deadlocks

    You are given:
    1) A list of atomic observation and action variables

    You will be given a particular timestep where the LTL laws led to no feasible action, and your task is to resolve the conflict by either modifying or deleting one of the LTL laws.
    
    The laws should be in the form of LTL formulas, and you should provide a brief explanation of each law. The boolean variables used in the laws are defined as follows:

    Observation Variables: 
    {", ".join(OBS_VARIABLES_LIST)}

    The observations in the atomic proposition space are described as follows:

    - `obs_has_x` corresponds to having the item `x` in the inventory of the agent. 
    - `obs_near_crafting_table` or `obs_near_furnace` define if the agent is within an interacting distance of a crafting table or furnace.
    - `obs_has_x_equipped` corresponds to an object `x` (e.g., an iron pickaxe) actively equipped.
    - Only one item can be equipped at any point in time. 
    - You may propose additional observation variables if needed to express useful rules.

    Action Variables:
    {", ".join(ACTION_VARIABLES_LIST)}

    The actions the agent can perform are limited to a few types:

    - `action_mine_x`: mines the item `x`. Certain blocks require certain tools:
        - stone: wood pickaxe or better
        - iron: stone pickaxe or better
        - diamond: iron pickaxe or better
    - `action_craft_x`: crafts an item `x`, if prerequisites and (if needed) a crafting table are present.
    - `action_smelt_iron`: smelts raw iron into ingots using fuel and a furnace.
    - `action_equip_x`: equips a tool for mining. Only one tool can be equipped at a time.
    - `action_explore`: used to find resources not currently visible.
    - `action_place_x`: places an item like a crafting table or furnace to enable usage.
    """

    for t in trace:
        existing_laws = laws_store.format_for_prompt(laws)
        obs_props = t.get("observation", {})
        obs_listing = "\n".join(f"            {k}: True" for k, v in obs_props.items() if v) or "            (none)"

        main_prompt = f"""
        You are a symbolic critic observing the trajectory of a Minecraft agent. The agent is inefficient, often repeats work, and occasionally causes errors like trying to mine without the right tool or crafting without the ingredients.

        GOAL OF AGENT: MINE A DIAMOND
        YOUR GOAL: You are given a timestep where the LTL laws led to no feasible action, and your task is to resolve the conflict by either modifying or deleting one of the LTL laws.

        Given the set of observations, no actions are allowed in the given instance. Modify one or both of the laws to break this deadlock.

        ### Your task:
        1. First, reason about which rule is less useful given the constraints
        2. Modify that law
        3. Make sure there is atleast one feasible action in the given state after the modification of laws.

        ### Rules you should output:
        - Each rule should follow the form: `G(condition => X(action))`
        - Use **observation variables** (e.g., obs_has_x, obs_near_x, obs_equipped_x) in the `condition`.
        - Use **action variables** (e.g., action_mine_x, action_craft_x) in the `action`.
        - Conditions should reflect **states that actually occurred** in the trajectory, so the rule can generalize and not be overly specific or invalid. The corresponding action should either approve or disapprove of the corresponding action in the trajectory. 
        - Make sure the rules do not block **all** possible actions. The agent always needs at least one valid option.
        - Make sure to state which timesteps your rule is based on.
        - If necessary, propose **new observation variables** that could help express useful rules.



        ### Format:
        Return ONLY a single JSON object (no prose outside it, no markdown fence) with this shape:

        {{
          "intended_action": "the action the agent should be able to take in this state",
          "blocking_law_ids": ["law-002", "law-007"],
          "modifications": [
            {{"law_id": "law-002",
              "operation": "replace",
              "new_law": "G(... -> X(...))",
              "explanation": "why the relaxed law still helps and why it no longer blocks the agent"}},
            {{"law_id": "law-007",
              "operation": "delete",
              "explanation": "why this law is not worth keeping"}}
          ]
        }}

        - `law_id` is the required stable identifier shown in brackets beside each law.
        - `operation` is either "replace" (supply `new_law`) or "delete".
        - Write formulas in ASCII spot syntax: `G`, `X`, `&`, `|`, `!`, `->`.
        - Use ONLY the observation and action variables listed above; a law that mentions any
          other variable is rejected by the law compiler.
        - After your modifications at least one action must be feasible in this state.

        ### Example LTL Law:
        G(obs_has_1x_iron_ore & obs_near_furnace -> X(action_smelt_iron))
        Explanation: Smelting iron early helps the agent craft a better pickaxe sooner.

        ### Inputs:

        - Existing LTL laws (each one carries the id you must refer to):
{existing_laws}

        - Observation Propositions (obs_props) at the deadlocked timestep:
{obs_listing}

        These laws are too constraining in that state, modify them.


        - Feasible actions per step are available (so do not block everything)
        - Action and observation variables:
            - Actions: {", ".join(ACTION_VARIABLES_LIST)}
            - Observations: {", ".join(OBS_VARIABLES_LIST)}


        Answer with the following three things

        1. Identify the action the agent should take given this state
        2. Identify which rules are blocking that action from happening
        3. Modify those rules.
        

        Modify one of the rules, or delete one of them, so that the agent can take a feasible action at this timestep.
        """

        #print(t['obs_props'])
        print("="   * 40)

        response = await get_response_4o(intro_prompt, main_prompt)
        print(response)

        try:
            parsed = extract_json_block(response)
        except Exception as e:
            print(f"Could not parse the critic response as JSON ({e}); skipping this timestep.")
            input("Press enter to continue...")
            continue

        modifications = parsed.get("modifications", [])
        print(f"Intended action: {parsed.get('intended_action', 'unspecified')}")
        print(f"{len(modifications)} modifications proposed:")
        for mod in modifications:
            target = mod.get("law_id") or "<missing law_id>"
            print(f"  {mod.get('operation')} {target} -> {mod.get('new_law', '')}")
            print(f"    {mod.get('explanation', '')}")

        if not modifications:
            input("Press enter to continue...")
            continue

        if apply_changes and input("Apply these modifications? [y/N] ").strip().lower() != "y":
            print("Skipped.")
            continue

        applied = 0
        for mod in modifications:
            law_id = mod.get("law_id")
            operation = (mod.get("operation") or "replace").lower()

            if operation in ("delete", "remove", "disable"):
                entry, status = laws_store.remove(laws, law_id)
                detail = entry["law"] if entry else ""
            else:
                _, status = laws_store.replace(
                    laws, law_id, mod.get("new_law", ""), mod.get("explanation")
                )
                detail = mod.get("new_law", "")

            if status in ("replaced", "deleted"):
                print(f"  [{status}] {law_id}: {detail}")
                applied += 1
            else:
                print(f"  [rejected {law_id}: {status}]")

        if apply_changes and applied:
            laws_store.save(laws, laws_path)
            print(f"Updated {laws_path} ({applied} changes)")

import argparse


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process some variables.")
    parser.add_argument('--file', type=str, required=True, help='Name of the user')
    parser.add_argument('--mode', type=int, required=True, help='0 = analyze trace, 1 = handle conflicts')
    parser.add_argument('--laws', type=str, default=DEFAULT_LAWS_PATH,
                        help='JSON file the laws are read from and written to')
    parser.add_argument('--no-write', action='store_true',
                        help='print the proposed laws without updating the JSON file')

    args = parser.parse_args()
    FILENAME = args.file

    # Run the async function to analyze the trace
    if( args.mode == 0):
        asyncio.run(analyze_trace(FILENAME, args.laws, apply_changes=not args.no_write))
    else:
        asyncio.run(handle_conflicts(FILENAME, args.laws, apply_changes=not args.no_write))


# # Load the first trace
# with open('saved_trajectory_2.pkl', 'rb') as f:
#     trace1 = pickle.load(f)



# # Print the result
# print("Combined Trace:")
# for i, step in enumerate(trace1):
#     print(f"\n=== Step {i + 1} ===")
#     print("Observation:")
#     print(get_active_keys(step["observation"]))
#     print("Action:")
#     print(get_active_keys(step["action"]))
#     print("Code:")
#     print(step["code"].strip())
#     if(get_active_keys(step["action"]) == []):
#         # Accept input and manually enter the action prop
#         print()
#         action_input = input("Enter the action (comma-separated): ")
#     print(f"Previous Error: {step['previous_error']}")

