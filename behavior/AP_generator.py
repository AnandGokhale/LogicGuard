

import behavior_eval
from igibson.object_states.robot_related_states import _get_robot
from igibson.robots.manipulation_robot import IsGraspingState

from igibson.object_states import *

import re

def sanitize_string(s: str) -> str:
    # Replace all characters that are not alphanumeric or underscore with "_"
    return re.sub(r'[^0-9A-Za-z_]', '_', s)


def generate_APs_observer(env):
    observer_APs = []
    for hand in ['left_hand', 'right_hand']:
        if env.action_env.robot_inventory[hand] is not None:
            observer_APs.append(env.action_env.robot_inventory[hand].name + "_in_hand")

    for obj in env.addressable_objects:
        obj_name = obj.name
        for cls, state in obj.states.items() :
            if cls is InsideRoomTypes and obj.category != 'room_floor' and state._compute_value():
                observer_APs.append( f"{obj_name}_in_{state._compute_value()[0]}")
            if cls is Burnt and state._get_value():
                observer_APs.append( obj_name + "_is_burnt")
            if cls is Cooked and state._get_value():
                observer_APs.append( obj_name + "_is_cooked")
            if cls is Stained and state._get_value():
                observer_APs.append( obj_name + "_is_stained")
            if cls is Dusty and state._get_value():
                observer_APs.append( obj_name + "_is_dusty")
            if cls is Frozen and state._get_value():
                observer_APs.append( obj_name + "_is_frozen")
            if cls is HeatSourceOrSink and state._get_value()[0]:
                observer_APs.append( obj_name + "_is_heat_source_or_sink")
            if cls is Open and state._compute_value():
                observer_APs.append( obj_name + "_is_open")
            if cls is Sliced and state._get_value():
                observer_APs.append( obj_name + "_is_sliced")
            if cls is Soaked and state._get_value():
                observer_APs.append( obj_name + "_is_soaked")
            if cls is ToggledOn and state._get_value():
                observer_APs.append( obj_name + "_is_toggled_on")
            for obj_other in env.addressable_objects:
                other_name = obj_other.name
                if obj_other == obj or obj.category == 'room_floor':
                    continue


                if cls is Inside:
                    if state._get_value(obj_other):
                        observer_APs.append(f"{obj_name}_inside_{other_name}")
                if cls is NextTo:
                    if state._get_value(obj_other):
                        observer_APs.append(f"{obj_name}_next_to_{other_name}")
                if cls is OnFloor and obj.category != 'room_floor':
                    if state._get_value(obj_other):
                        observer_APs.append(f"{obj_name}_on_floor")
                if cls is OnTop and obj_other.category != 'room_floor':
                    if state._get_value(obj_other) :
                        observer_APs.append(f"{obj_name}_on_top_of_{other_name}")
                if cls is Under:
                    if state._get_value(obj_other):
                        observer_APs.append(f"{obj_name}_is_under_{other_name}")

    sanitized_APs = [sanitize_string(AP) for AP in observer_APs]

    return sanitized_APs


def generate_APs_action(env):

    actions_list = [
        "grasp", # marker
        "place_ontop", # marker
        "place_inside", # marker
        "release", # marker
        "open",
        "close",
        "clean",
        "freeze",
        "unfreeze",
        "slice",
        "soak",
        "dry",
        "toggle_on",
        "toggle_off",
        "place_nextto", # marker
        "transfer_contents_inside", # marker
        "transfer_contents_ontop", # marker
        "place_nextto_ontop", # marker
        "place_under" # marker
    ]

    object_list = []
    for obj in env.addressable_objects:
        object_list.append(obj.name)

    actions_aps = []

    for action in actions_list:
        if action in ["place_ontop", "place_inside", "release", "place_nextto", "transfer_contents_inside", "transfer_contents_ontop", 
                      "place_nextto_ontop", "place_under"]:
            for obj1 in object_list:
                for obj2 in object_list:
                    if (obj1 != obj2):
                        actions_aps.append(obj1 + "_" + action + "_" + obj2)
        else:
            for obj1 in object_list:
                actions_aps.append(action + "_" + obj1)


    actions_aps.append("done")

    sanitized_APs = [sanitize_string(AP) for AP in actions_aps]


    return sanitized_APs


def extract_action_AP(action_dict, env):

    action = action_dict['action'].lower()
    action_obj = action_dict['object'].lower().replace(",", "_")

    if(action == "done"):
        return "done"
    
    if(action.startswith(("right_", "left_"))):
        if (not action.endswith("grasp")):
            if (action.startswith("right_")):
                obj = env.action_env.robot_inventory['right_hand']
                if obj is None:
                    print(generate_APs_observer(env))
                    raise ValueError("Right Hand is empty. DO NOT USE YOUR RIGHT HAND TO PLACE OR RELEASE OBJECTS")
                
                
                base_action = action.replace("right_", "")
                if(base_action not in ["place_ontop", "place_inside", "release", "place_nextto", "transfer_contents_inside", "transfer_contents_ontop", 
                      "place_nextto_ontop", "place_under"]):
                    raise ValueError("Invalid action")
                
                action_AP = f"{obj.name}_{base_action}_{action_obj}"
                return sanitize_string(action_AP)

            if (action.startswith("left_")):
                obj = env.action_env.robot_inventory['left_hand']

                if obj is None:
                    print(generate_APs_observer(env))
                    raise ValueError("Left Hand is empty. DO NOT USE YOUR LEFT HAND TO PLACE OR RELEASE OBJECTS")


                base_action = action.replace("left_", "")

                if(base_action not in ["place_ontop", "place_inside", "release", "place_nextto", "transfer_contents_inside", "transfer_contents_ontop", 
                      "place_nextto_ontop", "place_under"]):
                    raise ValueError("Invalid action")
                action_AP = f"{obj.name}_{base_action}_{action_obj}"
                return sanitize_string(action_AP)
            
    
    return sanitize_string(f"{action}_{action_obj}")
