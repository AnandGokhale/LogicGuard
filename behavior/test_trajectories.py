import spot
import numpy as np
import json
import os

import asyncio

from LTL_implementer import generate_trace_from_dicts, build_word_automaton, compile_automaton




def check_formula_with_spot(obs_props, rules, AP_list_observations, BDD_DICT):
    trace =  [obs_props]
    proposed_trace = generate_trace_from_dicts(trace)
    word_aut = build_word_automaton(proposed_trace, AP_list_observations, BDD_DICT)

    outputs = []

    for law in rules:
        automaton =  compile_automaton([law], BDD_DICT)
        run = automaton.intersecting_run(word_aut)
        if run is None:
            outputs.append(0)
            continue
        outputs.append(1)

    return outputs



def check_trajectory(traj_path, AP_file_path_1, AP_file_path_2, rule_data):

    with open(traj_path, "r") as f:
        traj_data = json.load(f)
    with open(AP_file_path_1, "r") as f:
        AP_data_1 = json.load(f)
    with open(AP_file_path_2, "r") as f:
        AP_data_2 = json.load(f)
    

    AP_list_observations = set(AP_data_1.get("obs_APs", []))
    AP_list_observations |= set(AP_data_2.get("obs_APs", []))
    BDD_DICT = spot.bdd_dict()
    
    for l in list(AP_list_observations):
        BDD_DICT.register_proposition(spot.formula(l), None)


    for i, timestep in enumerate(traj_data):
        AP_timestep = timestep['state_APs']
        outputs = check_formula_with_spot(AP_timestep, rule_data, AP_list_observations, BDD_DICT)
        if set(outputs) == {1}:
            BDD_DICT.unregister_all_my_variables(None)
            return True, i
        
    
    BDD_DICT.unregister_all_my_variables(None)

    return False, None





async def main():
    # read the file
    with open("behavior_action_sequencing_prompts.json", "r") as f:
        data = json.load(f)  # should be a list of dicts


    confusion = [[0, 0], [0, 0]]

    both_success_timesteps = []

    failed_old_identifiers = []

    successes = 0
    failures = 0
    # iterate over identifiers
    for i, entry in enumerate(data):
        identifier = entry["identifier"]

        traj_file = f"data/AP_logs/{identifier}_APs.json"
        old_traj_file = f"data_no_critic/AP_logs/{identifier}_APs.json"
        if not os.path.exists(traj_file):
            traj_file = old_traj_file

        rule_file = f"rules/rules/done/{identifier}_rules.json"
        AP_file = f"data/APs/{identifier}_APs.json"
        old_AP_file = f"data_no_critic/APs/{identifier}_APs.json"
        if not os.path.exists(AP_file):
            AP_file = old_AP_file

        try:
            with open(rule_file, "r") as f:
                rule_data = json.load(f)
        except Exception as e:
            print(f"{identifier} FAILED because {e}!! Please recheck")
            continue

        new_success, new_t = check_trajectory(traj_file,AP_file , old_AP_file, rule_data)
        old_success, old_t = check_trajectory(old_traj_file, AP_file , old_AP_file, rule_data)


        if(old_success == False):
            failed_old_identifiers.append(identifier)


        if not new_success and not old_success:
            confusion[0][0] += 1
        elif not new_success and old_success:
            confusion[0][1] += 1
            print(identifier)
        elif new_success and not old_success:
            confusion[1][0] += 1
        else:
            confusion[1][1] += 1
            both_success_timesteps.append([new_t, old_t])

    print(successes, failures)

    print("Confusion matrix (new vs old):")
    print("[[new_fail & old_fail, new_fail & old_success],")
    print(" [new_success & old_fail, new_success & old_success]]")
    print(confusion)

    if both_success_timesteps:
        avg_new = np.mean([t[0] for t in both_success_timesteps])
        avg_old = np.mean([t[1] for t in both_success_timesteps])
        print(f"Average success timestep (new): {avg_new:.2f}")
        print(f"Average success timestep (old): {avg_old:.2f}")
    else:
        print("No cases where both succeeded.")

    # with open("./failed_actor_cases.json", "w") as f:
    #     json.dump(failed_old_identifiers, f, indent=2)


if __name__ == "__main__":
    asyncio.run(main())        