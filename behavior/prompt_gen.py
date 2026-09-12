import json


def extract_substring(s, start, end):
    i = s.find(start)
    if i == -1:
        return None  # start not found
    j = s.find(end, i + len(start))
    if j == -1:
        return None  # end not found
    return s[i:]
    return s[i : j + len(end)]


def generate_prompt(robot_state, object_state, APs,  failed_actions, baseline_prompt_id, feedback, inner_monologue, old_action):
    with open("behavior_action_sequencing_prompts.json",'r') as file:
        data = json.load(file)
    
    for entry in data:
        if entry['identifier'] == baseline_prompt_id:
            llm_prompt = entry['llm_prompt']
            break

    intro_prompt = """
    
    Problem:
    You are designing instructions for a household robot. 
    The goal is to guide the robot to modify its environment from its current state to a desired final state. 
    The input will be the current environment state, the target environment state, the objects you can interact with in the environment. 
    The output should be the next action command that the robot may execute in order to make progress towards achieving the target state. 
    
    Data format: After # is the explanation.
    
    Format of the states:
    The current environment state is described as a list of dictionaries. Each dictionary describes an object, its category, followed by its description, which includes several of its properties including a description of its location.
    For example: 
    {'name': 'plywood_1', 
    'category': 'plywood', 
    'State description ': 
    ['Location: living_room', 'Stain status: Clean', 'Dust status: Clean', 'Touching: room_floor_living_room_0', 'Touching: plywood_0', 'Touching: room_floor_kitchen_0', 'On top of: room_floor_living_room_0', 'On top of: room_floor_kitchen_0', 'On floor: room_floor_living_room_0', 'Next to: plywood_0']}

    You will be provided with the environment state of each object in the environment in the above format. 

    Format of the action commands:
    Action commands is a dictionary with the following format:
    {
            \"action\": \"action_name\", 
            \"object\": \"target_obj_name\",
            \"thoughts\": \"inner monologue describing why this action is chosen\",
    }
    
    or 
    
    {
            \"action\": \"action_name\", 
            \"object\": \"target_obj_name1,target_obj_name2\",
            \"thoughts\": \"inner monologue describing why this action is chosen\",
    }
    
    The action_name must be one of the following:
    LEFT_GRASP # the robot grasps the object with its left hand, to execute the action, the robot's left hand must be empty, e.g. {'action': 'LEFT_GRASP', 'object': 'apple_0'}.
    RIGHT_GRASP # the robot grasps the object with its right hand, to execute the action, the robot's right hand must be empty, e.g. {'action': 'RIGHT_GRASP', 'object': 'apple_0'}.
    LEFT_PLACE_ONTOP # the robot places the object in its left hand on top of the target object and release the object in its left hand, e.g. {'action': 'LEFT_PLACE_ONTOP', 'object': 'table_1'}.
    RIGHT_PLACE_ONTOP # the robot places the object in its right hand on top of the target object and release the object in its left hand, e.g. {'action': 'RIGHT_PLACE_ONTOP', 'object': 'table_1'}.
    LEFT_PLACE_INSIDE # the robot places the object in its left hand inside the target object and release the object in its left hand, to execute the action, the robot's left hand must hold an object, and the target object can't be closed e.g. {'action': 'LEFT_PLACE_INSIDE', 'object': 'fridge_1'}.
    RIGHT_PLACE_INSIDE # the robot places the object in its right hand inside the target object and release the object in its left hand, to execute the action, the robot's right hand must hold an object, and the target object can't be closed, e.g. {'action': 'RIGHT_PLACE_INSIDE', 'object': 'fridge_1'}.
    RIGHT_RELEASE # the robot directly releases the object in its right hand, to execute the action, the robot's left hand must hold an object, e.g. {'action': 'RIGHT_RELEASE', 'object': 'apple_0'}.
    LEFT_RELEASE # the robot directly releases the object in its left hand, to execute the action, the robot's right hand must hold an object, e.g. {'action': 'LEFT_RELEASE', 'object': 'apple_0'}.
    OPEN # the robot opens the target object, to execute the action, the target object should be openable and closed, also, toggle off the target object first if want to open it, e.g. {'action': 'OPEN', 'object': 'fridge_1'}.
    CLOSE # the robot closes the target object, to execute the action, the target object should be openable and open, e.g. {'action': 'CLOSE', 'object': 'fridge_1'}.
    COOK # the robot cooks the target object, to execute the action, the target object should be put in a pan, e.g. {'action': 'COOK', 'object': 'apple_0'}.
    CLEAN # the robot cleans the target object, to execute the action, the robot should have a cleaning tool such as rag, the cleaning tool should be soaked if possible, or the target object should be put into a toggled on cleaner like a sink or a dishwasher, e.g. {'action': 'CLEAN', 'object': 'window_0'}.
    FREEZE # the robot freezes the target object e.g. {'action': 'FREEZE', 'object': 'apple_0'}.
    UNFREEZE # the robot unfreezes the target object, e.g. {'action': 'UNFREEZE', 'object': 'apple_0'}.
    SLICE # the robot slices the target object, to execute the action, the robot should have a knife in hand, e.g. {'action': 'SLICE', 'object': 'apple_0'}.
    SOAK # the robot soaks the target object, to execute the action, the target object must be put in a toggled on sink, e.g. {'action': 'SOAK', 'object': 'rag_0'}.
    DRY # the robot dries the target object, e.g. {'action': 'DRY', 'object': 'rag_0'}.
    TOGGLE_ON # the robot toggles on the target object, to execute the action, the target object must be closed if the target object is openable and open e.g. {'action': 'TOGGLE_ON', 'object': 'light_0'}.
    TOGGLE_OFF # the robot toggles off the target object, e.g. {'action': 'TOGGLE_OFF', 'object': 'light_0'}.
    LEFT_PLACE_NEXTTO # the robot places the object in its left hand next to the target object and release the object in its left hand, e.g. {'action': 'LEFT_PLACE_NEXTTO', 'object': 'table_1'}.
    RIGHT_PLACE_NEXTTO # the robot places the object in its right hand next to the target object and release the object in its right hand, e.g. {'action': 'RIGHT_PLACE_NEXTTO', 'object': 'table_1'}.
    LEFT_TRANSFER_CONTENTS_INSIDE # the robot transfers the contents in the object in its left hand inside the target object, e.g. {'action': 'LEFT_TRANSFER_CONTENTS_INSIDE', 'object': 'bow_1'}.
    RIGHT_TRANSFER_CONTENTS_INSIDE # the robot transfers the contents in the object in its right hand inside the target object, e.g. {'action': 'RIGHT_TRANSFER_CONTENTS_INSIDE', 'object': 'bow_1'}.
    LEFT_TRANSFER_CONTENTS_ONTOP # the robot transfers the contents in the object in its left hand on top of the target object, e.g. {'action': 'LEFT_TRANSFER_CONTENTS_ONTOP', 'object': 'table_1'}.
    RIGHT_TRANSFER_CONTENTS_ONTOP # the robot transfers the contents in the object in its right hand on top of the target object, e.g. {'action': 'RIGHT_TRANSFER_CONTENTS_ONTOP', 'object': 'table_1'}.
    LEFT_PLACE_NEXTTO_ONTOP # the robot places the object in its left hand next to target object 1 and on top of the target object 2 and release the object in its left hand, e.g. {'action': 'LEFT_PLACE_NEXTTO_ONTOP', 'object': 'window_0, table_1'}.
    RIGHT_PLACE_NEXTTO_ONTOP # the robot places the object in its right hand next to object 1 and on top of the target object 2 and release the object in its right hand, e.g. {'action': 'RIGHT_PLACE_NEXTTO_ONTOP', 'object': 'window_0, table_1'}.
    LEFT_PLACE_UNDER # the robot places the object in its left hand under the target object and release the object in its left hand, e.g. {'action': 'LEFT_PLACE_UNDER', 'object': 'table_1'}.
    RIGHT_PLACE_UNDER # the robot places the object in its right hand under the target object and release the object in its right hand, e.g. {'action': 'RIGHT_PLACE_UNDER', 'object': 'table_1'}.
    DONE # the robot has achieved the target environment as per your best judgement, e.g. {'action': 'DONE', 'object': 'none'}.

    Format of the interactable objects:
    Interactable object will contain multiple lines, each line is a dictionary with the following format:
    {
        \"name\": \"object_name\",
        \"category\": \"object_category\"
    }
    object_name is the name of the object, which you must use in the action command, object_category is the category of the object, which provides a hint for you in interpreting initial and goal condtions.


    thoughts: This is your inner monologue describing why you choose this action, it will be used as a feedback to improve your next action command.

    Please pay special attention:
    1. The robot can only hold one object in each hand.
    2. Action name must be one of the above action names, and the object name must be one of the object names listed in the interactable objects.
    3. All PLACE actions will release the object in the robot's hand, you don't need to explicitly RELEASE the object after the PLACE action.
    4. For LEFT_PLACE_NEXTTO_ONTOP and RIGHT_PLACE_NEXTTO_ONTOP, the action command are in the format of {'action': 'action_name', 'object': 'obj_name1, obj_name2'}
    5. If you want to perform an action to an target object, you must make sure the target object is not inside a closed object.
    6. For actions like OPEN, CLOSE, SLICE, COOK, CLEAN, SOAK, DRY, FREEZE, UNFREEZE, TOGGLE_ON, TOGGLE_OFF, at least one of the robot's hands must be empty, and the target object must have the corresponding property like they're openable, toggleable, etc.
    7. For PLACE actions and RELEASE actions, the robot must hold an object in the corresponding hand.
    8. Before slicing an object, the robot can only interact with the object (e.g. peach_0), after slicing the object, the robot can only interact with the sliced object (e.g. peach_0_part_0).
    9. You can only clean a stain with a soaked cleaning tool like rag, or put the stained object into a toggled on cleaner like sink or dishwasher.
    10. To soak an object, first place the object into a toggled on sink, then soak it. Do not soak an object outside a sink.
    11. Jars, Bags, and other objects must be OPENED, before you put things inside them.


    Please output a SINGLE action command(in the given format) that the robot may execute next in order to make progress towards achieving the target environment state.
    """

    task_description = extract_substring(llm_prompt, "target environment state:", "\n\n\n")


    main_prompt = f"""
    Your Task:
    
    Input: 

    Currently, the robot is holding:
    {robot_state}

    Current environment state: 
    {object_state}

    This may be summarized as the following atomic propositions being true:
    {', '.join(APs) if APs else 'No atomic propositions are true.'}

    Goal State description: 
    {task_description}

    Feedback on failed actions from the environment:
    {feedback if feedback else "No feedback yet."}


    Feedback from the critic:
    {failed_actions}

    The feedback includes instructions from your critic (via an LTL law with an explanation), which will block certain actions that they think will lead to failure. It also includes any failed actions you have tried to execute in the past.
    If you fail an action, please use the feedback to guide your next action choice.
    DO NOT REPEAT AN ACTION IF THE CRITIC HAS BLOCKED IT OR IF IT HAS FAILED BEFORE.

    Inner Monologue: 
    {inner_monologue}

    Previous Successful action:
    {old_action}



    Please output the A SINGLE ACTION COMMAND (in the given format), the current environment state will make progress towards the target environment state. 
    Only output the action command with nothing else.
    
    Output:
    """

    return intro_prompt, main_prompt, task_description
    


