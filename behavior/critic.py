import json
import os
import asyncio
import spot

from utils import *

from LTL_implementer import initialize_APs, compile_automaton


"""
        AP_log.append(
            {
                "timestep": len(AP_log),
                "state_APs": list(AP_list_curr),
                "action_APs": action_AP,
                "goal": goal_description
            }
        )

"""

import re



def strip_json_fences(s: str) -> str:
    """
    Removes ```json ... ``` or ``` ... ``` wrappers from an LLM response.
    """
    pattern = r"```(?:json)?\s*(.*?)\s*```"
    match = re.search(pattern, s, flags=re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # fallback: try to extract text between first [ and last ]
    start = s.find("[")
    end = s.rfind("]")
    if start != -1 and end != -1 and start < end:
        return s[start:end+1].strip()
    
    # nothing found
    return ""


def check_validity(response: str, bdd_dict) -> bool:
    """
    Validate an LLM response for LTL rules.

    Checks:
    1. Valid JSON
    2. Must be a list of dicts with 'rule' and 'explanation'
    3. Each 'rule' must compile with compile_automaton

    Returns:
        True if all checks pass, False otherwise.
    """

    # Step 1: Strip whitespace/fences
    response = response.strip()



    # Step 2: Try to parse JSON
    try:
        parsed = json.loads(response)
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        return False

    # Step 3: Must be a list
    if not isinstance(parsed, list):
        print("❌ Response is not a list.")
        return False

    # Step 4: Each item must be dict with 'rule' and 'explanation'
    for i, item in enumerate(parsed):
        if not isinstance(item, dict):
            print(f"❌ Item {i} is not a dict: {item}")
            return False
        if "rule" not in item or "explanation" not in item:
            print(f"❌ Item {i} missing required keys: {item}")
            return False

    # Step 5: Check each rule with compile_automaton
    all_valid = True
    for i, item in enumerate(parsed):
        try:
            compile_automaton([item["rule"]], bdd_dict)
        except Exception as e:
            print(f"❌ Rule {i} failed to compile: {item['rule']}\n   Error: {e}")
            all_valid = False

    return all_valid


def format_AP_log_for_critic(AP_log):
    lines = []
    for i in range(len(AP_log)):
        step = AP_log[i]
        next_step = AP_log[i + 1] if i + 1 < len(AP_log) else None

        state_APs = set(step["state_APs"])
        action_APs = step["action_APs"]
        goal = step.get("goal", "None")

        # Changed APs = symmetric difference between current and next state_APs
        if next_step:
            next_state_APs = set(next_step["state_APs"])
            changed_aps = list(state_APs.symmetric_difference(next_state_APs))
        else:
            changed_aps = []

        lines.append(
            f"Step {i + 1}:\n"
            f"- State APs: {', '.join(state_APs) if state_APs else 'None'}\n"
            f"- Action APs: {', '.join(action_APs) if action_APs else 'action_idle'}\n"
            f"- Changed APs: {', '.join(changed_aps) if changed_aps else 'None'}\n"
            f"-Result: {'Success' if changed_aps else 'Failed'}"
        )

    return "\n".join(lines)


async def analyze_trace(demo_name):
    ap_logs_path = f"./data_no_critic/AP_logs/{demo_name}_APs.json"
    with open(ap_logs_path,"r") as f:
        AP_log = json.load(f)

    
    ap_path = f"./data_no_critic/APs/{demo_name}_APs.json"
    with open(ap_path,"r") as f:
        APs = json.load(f)

    rule_file = f"rules/rules/done/{demo_name}_rules.json"
    with open(rule_file, "r") as f:
        rule_data = json.load(f)

    
    BDD_DICT = spot.bdd_dict()
    
    with open(ap_path, 'r') as f:
        saved = json.load(f)
        AP_list_observations = set(saved.get("obs_APs", []))
        AP_list_actions = set(saved.get("action_APs_true", []))
    for l in list(AP_list_observations) + list(AP_list_actions):
        BDD_DICT.register_proposition(spot.formula(l), None)


    intro_prompt =f"""
        You are an expert symbolic critic analyzing a robot's task execution trajectory. '
        Your goal is to propose Linear Temporal Logic (LTL) laws that will improve the robot's 
        efficiency, prevent common mistakes, and ensure task completion.
    
        ## ROBOT'S GOAL
        {rule_data}

        This goal is written in terms of a list of formulas involving APs. All of these formulas need to be true in order to finish the task. 

        ## ATOMIC PROPOSITIONS

        ### Observation Variables (Environment State):
        {chr(10).join([f"  - {ap}" for ap in APs['obs_APs']])}
        **Key Observation Categories:**
        - Object locations: `object_X_in_location`, `object_X_on_Y`, `object_X_inside_Y`
        - Hand states: `object_X_in_hand` (what robot is holding)
        - Object properties: `object_X_is_open`, `object_X_is_clean`, etc.
        - Spatial relations: `object_X_next_to_Y`, `object_X_under_Y`


        ### Action Variables (Robot Actions):
        {chr(10).join([f"  - {ap}" for ap in APs['action_APs_true']])}

        **Action Categories:**
        1. **Direct object actions**: `action_object` (grasp, open, close, clean, freeze, unfreeze, slice, soak, dry, toggle_on, toggle_off)
        2. **Placement actions**: `object1_place_relation_object2` (place_ontop, place_inside, place_nextto, place_under, release)
        3. **Transfer actions**: `object1_transfer_contents_relation_object2`
        4. **Complex placement**: `object1_place_nextto_ontop_object2_object3`
        5. **Task completion**: `done`

        ## LTL SYNTAX RULES
        - **Operators**: `&` (and), `|` (or), `!` (not), `G` (globally), `X` (next), `->` (implies)
        - **Format**: `G(observation_condition -> X(action_condition))`
        - **Focus**: Prefer blocking bad actions rather than forcing specific actions
        - **Trace structure**: (obs, action, obs, action, ...)

        ## YOUR TASK
        Analyze the robot's trajectory and propose LTL laws that:
        1. **Prevent inefficiencies**: Stop redundant or counterproductive actions
        2. **Ensure prerequisites**: Block actions when preconditions aren't met. ( for example, a fridge must be open to place something inside it or take something out of it)
        3. **Promote task completion**: Add rules to recognize when goals are achieved
        4. **Maintain feasibility**: Avoid over-constraining the action space

    """

    main_prompt = f"""
        ## TRAJECTORY ANALYSIS

        ### Robot Goal:
        {rule_data}

        ### Execution Trace:
        {format_AP_log_for_critic(AP_log)}
        ## ANALYSIS FRAMEWORK

        **Step 1: Goal Decomposition**
        - Break down the main goal into sequential subgoals. It is possible that some formulas need to be satisifed before others.
        - Identify what objects need to be manipulated and how
        - Determine the final success conditions

        **Step 2: Trajectory Evaluation**
        - Identify successful action sequences that made progress
        - Spot inefficiencies: repeated actions, unnecessary movements, missed opportunities
        - Find missing prerequisites: actions attempted without proper setup

        **Step 3: LTL Law Design**
        - **Prerequisite laws**: Ensure preconditions are met before actions
        - **Efficiency laws**: Block wasteful or redundant actions  
        - **Completion laws**: Trigger task termination when goals are achieved
        - **Safety laws**: Prevent actions that could undo progress

        ## EXAMPLES OF GOOD LTL LAWS

        **Prerequisite checking:**
        ```
        G(object_X_in_hand -> object_X_place_in_target_position)
        "Only place objects you're actually holding"
        ```

        **Efficiency enforcement:**
        ```
        G((task_complete_for_X) -> X(!grasp_object_X))
        "Don't grasp objects that are already correctly placed"
        ```


        The goal consists of many parts as there are many objects in the environment. 
        CREATE AT LEAST TWO LAWS PER LINE OF THE GOAL.

        You must address each part of the goal with at least one law to ensure the robot knows when to stop.


        ## OUTPUT REQUIREMENTS

        Provide your analysis in exactly this format:

        **Explanation:**
        1. **Initial State**: Describe the starting configuration
        2. **Goal Interpretation**: What the robot needs to accomplish
        3. **Required Steps**: Logical sequence to achieve the goal  
        4. **Successful Actions**: What the robot did correctly
        5. **Identified Problems**: Inefficiencies, errors, or missing actions
        6. **Law Strategy**: How your proposed laws address these issues

        **Laws:**
        ```json
        [
        {{
            "rule": "G(observation_condition -> X(action_condition))",
            "explanation": "Clear explanation of why this law improves performance"
        }},
        {{
            "rule": "G(another_condition -> X(another_action))", 
            "explanation": "Another law addressing a different issue"
        }}
        ]
        ```

        **CRITICAL REMINDERS:**
        - Use ONLY the provided observation and action APs
        - Laws should be in format: `G(obs_condition -> X(action_condition))`
        - Focus on blocking problematic actions, not forcing specific ones
        - Ensure laws don't make the task impossible by over-constraining
    """




    response = await get_response_o3(intro_prompt, main_prompt)


    print(response)

    response = strip_json_fences(response)

    print("STRIPPED RESPONSE: ", response)



    if check_validity(response, BDD_DICT):
        outpath = f"./data/rules/{demo_name}_rules.json"
        with open(outpath, "w") as f:
            json.dump(json.loads(response), f, indent = 4)
            print("rules_saved")
    else:
        print(response)


    BDD_DICT.unregister_all_my_variables(None)

    return



async def analyze_trace_repeated(demo_name):
    ap_logs_path = f"./data/AP_logs/{demo_name}_APs.json"
    with open(ap_logs_path,"r") as f:
        AP_log = json.load(f)

    
    ap_path = f"./data/APs/{demo_name}_APs.json"
    with open(ap_path,"r") as f:
        APs = json.load(f)

    rule_file = f"rules/rules/done/{demo_name}_rules.json"
    with open(rule_file, "r") as f:
        rule_data = json.load(f)


    with open(f"./data/rules/{demo_name}_rules.json", "r") as f:
        existing_rules = json.load(f)

    
    BDD_DICT = spot.bdd_dict()
    
    with open(ap_path, 'r') as f:
        saved = json.load(f)
        AP_list_observations = set(saved.get("obs_APs", []))
        AP_list_actions = set(saved.get("action_APs_true", []))
    for l in list(AP_list_observations) + list(AP_list_actions):
        BDD_DICT.register_proposition(spot.formula(l), None)


    intro_prompt =f"""
        You are an expert symbolic critic analyzing a robot's task execution trajectory. '
        Your goal is to propose Linear Temporal Logic (LTL) laws that will improve the robot's 
        efficiency, prevent common mistakes, and ensure task completion.
    
        ## ROBOT'S GOAL
        {rule_data}

        This goal is written in terms of a list of formulas involving APs. All of these formulas need to be true in order to finish the task. 

        ## ATOMIC PROPOSITIONS

        ### Observation Variables (Environment State):
        {chr(10).join([f"  - {ap}" for ap in APs['obs_APs']])}
        **Key Observation Categories:**
        - Object locations: `object_X_in_location`, `object_X_on_Y`, `object_X_inside_Y`
        - Hand states: `object_X_in_hand` (what robot is holding)
        - Object properties: `object_X_is_open`, `object_X_is_clean`, etc.
        - Spatial relations: `object_X_next_to_Y`, `object_X_under_Y`


        ### Action Variables (Robot Actions):
        {chr(10).join([f"  - {ap}" for ap in APs['action_APs_true']])}

        **Action Categories:**
        1. **Direct object actions**: `action_object` (grasp, open, close, clean, freeze, unfreeze, slice, soak, dry, toggle_on, toggle_off)
        2. **Placement actions**: `object1_place_relation_object2` (place_ontop, place_inside, place_nextto, place_under, release)
        3. **Transfer actions**: `object1_transfer_contents_relation_object2`
        4. **Complex placement**: `object1_place_nextto_ontop_object2_object3`
        5. **Task completion**: `done`

        ## LTL SYNTAX RULES
        - **Operators**: `&` (and), `|` (or), `!` (not), `G` (globally), `X` (next), `->` (implies)
        - **Format**: `G(observation_condition -> X(action_condition))`
        - **Focus**: Prefer blocking bad actions rather than forcing specific actions
        - **Trace structure**: (obs, action, obs, action, ...)

        ## YOUR TASK
        Analyze the robot's trajectory and propose LTL laws that:
        1. **Prevent inefficiencies**: Stop redundant or counterproductive actions
        2. **Ensure prerequisites**: Block actions when preconditions aren't met. ( for example, a fridge must be open to place something inside it or take something out of it)
        3. **Promote task completion**: Add rules to recognize when goals are achieved
        4. **Maintain feasibility**: Avoid over-constraining the action space

    """

    main_prompt = f"""
        ## TRAJECTORY ANALYSIS

        You have already designed a few rules, however they were not enough to accomplish the task. You need to add an additional number of rules to get there!


        ### Robot Goal:
        {rule_data}

        ### Execution Trace for the UNSUCCESSFUL RUN:
        {format_AP_log_for_critic(AP_log)}


        ### Previous Rules:

        Previously, you have already designed some rules based on priot traces, now, given a new trace, suggest a small number of ADDITIONAL RULES

        The previous rules are:
        {existing_rules}

        ## ANALYSIS FRAMEWORK

        **Step 1: Identify the most repeated action in the trajectory
        **Step 2: Understand why this action was repeated, and why it is necessary to repeat this action
        **Step 3: Define LTL Laws which block this action when it is unnecessary

        ## EXAMPLES OF GOOD LTL LAWS

        **Prerequisite checking:**
        ```
        G(object_X_in_hand -> object_X_place_in_target_position)
        "Only place objects you're actually holding"
        ```

        **Efficiency enforcement:**
        ```
        G((task_complete_for_X) -> X(!grasp_object_X))
        "Don't grasp objects that are already correctly placed"
        ```


        The goal consists of many parts as there are many objects in the environment. 
        You are refining an existing trajectory, focus on eliminating repeated, useless actions.
        Do not constrain yourself to a small number of laws, make as many laws as you need. These laws are boolean, so be very precise.
        Make different laws about different items. Dont try to merge all your laws into one big law, write many SIMPLE laws


        ## OUTPUT REQUIREMENTS

        Provide your analysis in exactly this format:

        **Explanation:**
        1. **Initial State**: Describe the starting configuration across all relevant objects
        2. **Goal Interpretation**: What the robot needs to accomplish for all listed sub-goals (treat them as possibly dependent)
        3. **Required Steps**: Logical sequence to achieve the full multi-object goal  
        4. **Most repetitive action** : What was the most repetitive action in the trajctory provided?
        5. **Law Strategy**: Propose a law to block this action when not necessary

        **Laws:**
        ```json
        [
        {{
            "rule": "G(observation_condition -> X(action_condition))",
            "explanation": "Clear explanation of why this law improves performance"
        }},
        {{
            "rule": "G(another_condition -> X(another_action))", 
            "explanation": "Another law addressing a different issue"
        }}
        ]
        ```

        **CRITICAL REMINDERS:**
        - Use ONLY the provided observation and action APs
        - Laws should be in format: `G(obs_condition -> X(action_condition))`
        - Focus on blocking problematic actions, not forcing specific ones
        - Ensure laws don't make the task impossible by over-constraining
    """




    response = await get_response_o3(intro_prompt, main_prompt)


    print(response)

    response = strip_json_fences(response)

    print("STRIPPED RESPONSE: ", response)



    if check_validity(response, BDD_DICT):
        outpath = f"./data/rules_new/{demo_name}_rules.json"
        with open(outpath, "w") as f:
            json.dump(json.loads(response), f, indent = 4)
            print("rules_saved")
    else:
        print(response)


    BDD_DICT.unregister_all_my_variables(None)

    return






async def constraint_driven_modification(rules, constraining_rules, AP_list_curr, demo_name, valid_actions):
    ap_logs_path = f"./data/AP_logs/{demo_name}_APs.json"
    with open(ap_logs_path,"r") as f:
        AP_log = json.load(f)
    ap_path = f"./data/APs/{demo_name}_APs.json"
    with open(ap_path,"r") as f:
        APs = json.load(f)


    intro_prompt = f"""
            You are an expert symbolic critic observing a robot's behavior.

            The robot's goal is:
            {AP_log[-1]['goal']}

            You are given:
            1. A list of all atomic observation and action variables
            2. The observation variables true at the current timestep
            3. A set of LTL rules that are overconstraining (they block all actions)
            4. The actions currently allowed by those laws (conflicting actions)

            Your task:
            - Analyze why the constraining rules conflict.
            - Replace ONLY the constraining rules with new ones that resolve the deadlock.
            - Keep all other rules unchanged.
            - New rules must enforce **sequentiality** by adding conditions like `!o2` to break ties.
            - New rules must strictly follow this format:
            `G(expression1 -> X(expression2))`

            Allowed operators:
            - & (and), | (or), ! (not), G (globally), X (next), -> (implies)

            Important:
            - Each output must be valid JSON.
            - Each rule must have the structure: {{"rule": "...", "explanation": "..."}}
            - Output must be a JSON array of objects, with **double quotes only**.
            - Do not output anything except the JSON array.

            Example of correction:
            If both rules are `G(o1 -> X(a1))` and `G(o2 -> X(a2))` and both o1, o2 hold,
            replace one with `G(o1 & !o2 -> X(a1))` and keep the second as G(o2 -> X(a2)).
            Make sure to return both.

            Think carefully about the goal and current state first.
            Then output the replacement rules as JSON only.
    """

    main_prompt = f"""
        Observation variables:
        {",".join(APs['obs_APs'])}

        Action variables:
        {",".join(APs['action_APs'])}
        

        True observation variables at current timestep:
        {AP_list_curr}

        Overconstraining rules (to be replaced):
        {constraining_rules}

        Conflicting actions:
        {valid_actions}

        Now output the replacement rules in the following strict JSON format:

        [
        {{
            "rule": "G(... -> X(...))",
            "explanation": "..."
        }},
        {{
            "rule": "G(... -> X(...))",
            "explanation": "..."
        }}
        ]

        Nothing else.
    """
    BDD_DICT = spot.bdd_dict()
    
    with open(ap_path, 'r') as f:
        saved = json.load(f)
        AP_list_observations = set(saved.get("obs_APs", []))
        AP_list_actions = set(saved.get("action_APs", []))
    for l in list(AP_list_observations) + list(AP_list_actions):
        BDD_DICT.register_proposition(spot.formula(l), None)


    response = await get_response_o3(intro_prompt, main_prompt)


    print(response)

    response = extract_json_list(response)

    print(response)


    path = f"./data/rules/{demo_name}_rules.json"
    
    with open(path, "r") as f:
        rules_data = json.load(f)

    rules = [d for d in rules_data if d["rule"] not in constraining_rules]







    if check_validity(response, BDD_DICT):
        outpath = f"./data/rules/{demo_name}_rules.json"
        with open(outpath, "w") as f:

            new_rules = json.loads(response)

            rules.extend(new_rules)

            json.dump(rules, f, indent = 4)
            print("rules_saved")
    else:
        print(response)
        print("There is an error")

    BDD_DICT.unregister_all_my_variables(None)

    x = input()





    

if __name__ == "__main__":


    demo_names = []
    folder = "./data/AP_logs"
    with open("failed_actor_cases.json", "r") as f:
        failed_cases = json.load(f)



    
    for fname in os.listdir(folder):
        if fname.endswith("_APs.json"):
            demo_name = fname.replace("_APs.json", "")
            demo_names.append(demo_name)
    

    for demo_name in demo_names:
        if(demo_name in failed_cases):
            traj_file = f"data/rules/{demo_name}_rules.json"
            if os.path.exists(traj_file):
                print(f"{demo_name}: skipping as done rn")
                continue
            print("ANALYZING: ", demo_name)
            asyncio.run(analyze_trace(demo_name))

        else:
            print(f"{demo_name} succeeded the first time, does not need critic")


