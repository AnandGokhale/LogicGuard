import behavior_eval
from behavior_eval.transition_model.eval_env import EvalEnv

import json
import os
import asyncio
import ast
import spot
import contextlib
import io

from observer import observer
from AP_generator import generate_APs_observer, extract_action_AP, generate_APs_action
from prompt_gen import generate_prompt
from LTL_implementer import initialize_APs, filter_actions_LTL_trace

from test_trajectories import check_formula_with_spot

from utils import *


os.environ['PYOPENGL_PLATFORM'] = 'egl'
os.environ['EGL_DEVICE_ID'] = '0'  # Use GPU 0



def save_new_rules(rules, explanations, demo_name):
    path = f"./data/rules/{demo_name}_rules.json"

    entries = []
    for i in range(len(rules)):
        entries.append({"rule": rules[i], "explanation": explanations[i]})

    # Write entries to JSON file (overwrite if exists)
    with open(path, "w") as f:
        json.dump(entries, f, indent=2)

    return



def failed_action_explainer(action, rules, explanations, AP_list_curr, AP_list_observations, AP_list_actions, BDD_DICT):
    res = []
    for i, rule in enumerate(rules):
        feasible_actions_rule = filter_actions_LTL_trace(AP_list_curr, rule , list(AP_list_observations), list(AP_list_actions), BDD_DICT)
        if action in feasible_actions_rule:
            continue
        print(f"{action} failed because the critic recommends that {explanations[i]}")
        res.append(f"{action} failed because the critic recommends that {explanations[i]}")




    return res


violation_counts = {}




async def run_simulation(demo_name):
    ap_file = f"data/APs/{demo_name}_APs.json"
    done_file = f"rules/rules/done/{demo_name}_rules.json"
    with open(done_file, "r") as f:
        done_data = json.load(f)


    env=EvalEnv(demo_name=demo_name,mode='headless')
    AP_list_observations,AP_true_actions, BDD_DICT = initialize_APs(ap_file, env)
    done = False
    trajectory = []
    AP_log = []
    counter = 0

    feedback = ""
    old_action = {"action": "", "object": "", "thoughts": "Starting the task."}

    print("\n\n\n")
    while not done:
        
        # get observations, both low level and AP-based
        # robot_state, object_state = observer(env)
        # AP_list_curr_obs = generate_APs_observer(env)
        # new_APs_obs = set(AP_list_curr_obs) - AP_list_observations

        # if new_APs_obs:
        #     AP_list_observations.update(new_APs_obs)
        
        # rules, explanations = rule_finder(demo_name)


        # valid_action_list = filter_actions_LTL_trace(AP_list_curr_obs, rules , list(AP_list_observations), list(AP_true_actions), BDD_DICT)
 
        failed_actions = []

        e = ""

        # Get LLM response
        while True:
            robot_state, object_state = observer(env)



            AP_list_curr_obs = generate_APs_observer(env)
            new_APs_obs = set(AP_list_curr_obs) - AP_list_observations



            if new_APs_obs:
                AP_list_observations.update(new_APs_obs)
            
            rules, explanations = rule_finder(demo_name)

            

            print("Current APs:", AP_list_curr_obs)
            print("\n\n")

            # check if done, 
            valid_action_list = filter_actions_LTL_trace(AP_list_curr_obs, rules , list(AP_list_observations), list(AP_true_actions), BDD_DICT)

            done_checker = check_formula_with_spot(AP_list_curr_obs, done_data , AP_list_observations, BDD_DICT)

            print(done_checker)
            pending_goals = []

            for ctr, goal in enumerate(done_data):
                if(done_checker[ctr] == 0):
                    print(f"{goal} is pending")
                    pending_goals.append(goal)
                else:
                    print(f"{goal} is done")

            print("\n\n")
            if(set(done_checker) == {1}):
                print(done_data)
                input()
                valid_action_list = ["done"]

            else:
                if "done" in valid_action_list:
                    valid_action_list.remove("done")
            


            try:
                intro_prompt, main_prompt, goal_description = generate_prompt(robot_state, object_state,AP_list_curr_obs,  failed_actions, baseline_prompt_id=demo_name, feedback = feedback + str(e), inner_monologue=old_action['thoughts'], old_action = old_action)
                response = await get_response_4_1(intro_prompt, main_prompt)
                
                print("\n\n")
                print(response)
                action = ast.literal_eval(response)
                action_AP = extract_action_AP(action, env)
                print(action_AP)
                print("\n\n")
                assert action.keys() == {'action', 'object', 'thoughts'}, "The response must have exactly three keys: 'action', 'object', and 'thoughts'."

                if (action_AP not in AP_true_actions):
                    AP_true_actions.update([action_AP])
                    break

                if(action_AP in valid_action_list):
                    break

                if(len(valid_action_list)== 0):
                    print("No valid actions available as per the critic. Proceeding with the LLM-suggested action.")
                    x = input("Should I continue with LLM Suggestion?")
                    if(x):
                        break
                    else:
                        continue
                else:

                    print(f"Valid action list: {valid_action_list}")
                    print(f"My action: {action_AP}")
                    if(valid_action_list == ["done"]):
                        failed_actions.append(f"{action} failed because the critic has imposed a rule. \n You are done with the task, please choose the done command")

                    if(action_AP == "done"):
                        print(f"You are not done, the goals that remain are: {pending_goals}. PLease pick a valid_action: {valid_action_list}")
                        failed_actions.append(f"You are not done, the goals that remain are: {pending_goals}. PLease pick a valid_action: {valid_action_list}")
                    for i in range(len(rules)):
                        law = rules[i]
                        explainer = explanations[i]
                        feasible_action_law_wise = filter_actions_LTL_trace(AP_list_curr_obs, [law], list(AP_list_observations), list(AP_true_actions), BDD_DICT)
                        if action_AP in feasible_action_law_wise:
                            continue
                        print(f"{action} failed because the critic recommends that {explainer}")
                        violation_counts[law] = violation_counts.get(law, 0) + 1
                        if violation_counts[law] > 5:
                            x =  input(f"Do you want to delete the law {law} ?")
                            if(x):
                                print(f"Removing law: {law} after repeated violations")
                                rules.remove(law)
                                explanations.remove(explainer)
                                save_new_rules(rules, explanations, demo_name)
                                del violation_counts[law]

                            continue

                        input()

                        failed_actions.append(f"{action} failed because the critic has imposed a rule. \n The rule is that {law}. This is because {explainer}")
                    continue

            except Exception as err:
                e = err
                print(f"{e}")
                continue

        old_action = action
    
        if action['action'] == 'DONE':
            done = True
            print("Task completed as per LLM judgement.")
            feedback = ""

        else:

            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                env.apply_action(action['action'], action['object'])
                env.simulator.step()
                env.simulator.sync()
            feedback = buffer.getvalue().strip()

            if action_AP == "action_failed":
                input()
            

        
        trajectory.append(
            {
                "robot_state": robot_state,
                "object_state": object_state,
                "action": action,
                "goal": goal_description,
                "feedback": feedback
            }
        )
        AP_log.append(
            {
                "timestep": len(AP_log),
                "state_APs": list(AP_list_curr_obs),
                "action_APs": action_AP,
                "goal": goal_description,
                "feedback": feedback
            }
        )

        #print(AP_list_curr_obs)


        with open(f"data/trajectories/{demo_name}_traj.json", 'w') as f:
            json.dump(trajectory, f, indent = 2)
        with open(f"data/AP_logs/{demo_name}_APs.json", 'w') as f:
            json.dump(AP_log, f, indent = 2)
        with open(f"data/APs/{demo_name}_APs.json", 'w') as f:
            json.dump({"obs_APs" : list(AP_list_observations), "action_APs_true": list(AP_true_actions)}, f, indent = 2)

        counter +=1
        if (counter >= 40):
                break



    BDD_DICT.unregister_all_my_variables(None)

        # Add critic stuff

# perhaps eventually 
async def main():
    # read the file
    with open("behavior_action_sequencing_prompts.json", "r") as f:
        data = json.load(f)  # should be a list of dicts

    with open("failed_actor_cases.json", "r") as f:
        failed_cases = json.load(f)


    # iterate over identifiers
    for i, entry in enumerate(data):
        identifier = entry["identifier"]
        if(identifier not in failed_cases):
            print("Skipping as it succeeded last time")
            continue
        traj_file = f"data/trajectories/{identifier}_traj.json"

        if os.path.exists(traj_file):
            print(f"{identifier}: skipping as done rn")

            continue
            with open(traj_file, "r") as f:
                traj_data = json.load(f)

            if isinstance(traj_data, list):
                print(f"{identifier}: trajectory length = {len(traj_data)}")
                if(len(traj_data) >= 40):
                    print(f"{identifier}: skipping as trajectory length is >= 40")
                    continue
            else:
                print(f"{identifier}: file exists but is not a list (type={type(traj_data)})")

        print(f"Running simulation number {i} for {identifier}")
        await run_simulation(identifier)
        violation_counts.clear()

        print(f"{i} done")

if __name__ == "__main__":
    asyncio.run(main())        