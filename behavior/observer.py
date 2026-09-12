

import behavior_eval


from igibson.object_states import *


def observer(env):

    robot_state = {'left_hand': None, 'right_hand': None}

    for hand in ['left_hand', 'right_hand']:
        if env.action_env.robot_inventory[hand] is not None:
            robot_state[hand] = env.action_env.robot_inventory[hand].name
        
    
    # Object description
    object_list = []
    for obj in env.addressable_objects:
        
        description = []

        for cls, state in obj.states.items():
            if cls is InsideRoomTypes and obj.category != 'room_floor' and state._compute_value():
                description.append(f"Location: {state._compute_value()[0]}")

            if cls is Burnt:
                description.append("Burnt status: Burnt" if state._get_value() else "Burnt status: Not burnt")
            if cls is CleaningTool:
                description.append("Is a Cleaning Tool")
            if cls is Cooked:
                description.append("Cooked status: Cooked" if state._get_value() else "Cooked status: Not cooked")
            if cls is Stained: 
                description.append("Stain status: Stained" if state._get_value() else "Stain status: Clean")
            if cls is Dusty:
                description.append("Dust status: Dusty" if state._get_value() else "Dust status: Clean")
            if cls is Frozen:
                description.append("Frozen status: Frozen" if state._get_value() else "Frozen status: Not frozen")
            if cls is HeatSourceOrSink:
                description.append("Heat source/sink? : True" if state._get_value()[0] else "Heat source/sink?: False")
            # Inside, Next to, On floor, On top, require me to iterate through objects
            if cls is Open:
                description.append("Open? : True" if state._compute_value() else "Open? : False")
            if cls is Sliced:
                description.append("Sliced? : True" if state._get_value() else "Sliced? : False")
            if cls is Slicer:
                description.append("Is a Slicer")
            if cls is Soaked:
                description.append("Soaked? : True" if state._get_value() else "Soaked? : False")
            if cls is ToggledOn:
                description.append("Toggled on? : True" if state._get_value() else "Toggled on? : False")
            if cls is WaterSource:
                description.append("Is a Water Source")
            

            for obj_other in env.addressable_objects:
                if obj_other == obj or obj.category == 'room_floor':
                    continue
                if cls is Inside:
                    if state._get_value(obj_other):
                        description.append(f"Inside: {obj_other.name}")
                if cls is NextTo:
                    if state._get_value(obj_other):
                        description.append(f"Next to: {obj_other.name}")
                if cls is OnFloor and obj.category != 'room_floor':
                    if state._get_value(obj_other):
                        description.append(f"On floor: {obj_other.name}")
                if cls is OnTop and obj_other.category != 'room_floor':
                    if state._get_value(obj_other):
                        description.append(f"On top of: {obj_other.name}")
                # if cls is Touching:
                #     if state._get_value(obj_other):
                #         description.append(f"Touching: {obj_other.name}")
                if cls is Under:
                    if state._get_value(obj_other):
                        description.append(f"Under: {obj_other.name}")

        object_list.append({"name": obj.name, "category": obj.category, "State description ": description})
        
        #print(object_list[-1])

    return robot_state, object_list