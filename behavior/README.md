This folder contains the necessary code for the Behavior-100 dataset

You will need to install:

1) embodied agent interface (https://github.com/embodied-agent-interface/embodied-agent-interface)
2) iGibson
3) Spot, for LTL execution (https://spot.lre.epita.fr/)
4) OpenAI's API


Directory structure:

1) Data no critic directory contains the actors actions for behavior without any critic.
2) Data with critic contains the actors actions for behavior after the critic rules
3) goal_APs describes the set of APs required to define the goal state
4) goal_rules describes the set of rules which need to be satisfied to consider the task completed. We use these to detect if a task is completed, and they arent used for anything else.


Each data directory has four folders:
1) AP_logs: summarizing which APs are true at which time instant
2) APs: summarizing the AP dictionary for each simulation
3) rules: the rules made by the critic. If there are rules new, it meant the critic was run a second time to generate more rules since the actor was close to completion with the original ruleset
4) Trajectory: this describes the full state of the system at each timestep

Files:
1) main_file.py: This implements the logicGuard architecture, and runs the actor given exisitng rules. 
2) AP_generator.py: generates APs autonomously via eai's API.
3) add_goal_APs_to_dictionary.py: initiates the AP set with goal APs
4) behavior_action_sequencing_prompts.json: the task description for each task
5) critic.py: is the LLM critic.
6) failed_actor_cases.json: Lists all the cases the actor has failed at for the use of the critic.
7) LTL_implementer.py: handles all spot related actions. 
8) observer.py: handles the observation module
9) prompt_gen.py: handles all prompt generation
10) readable_tasks.txt: shows tasks in a more reader friendly way, for humans only
11) test_trajectories.py: checks the success of trajectories and generates failed_actor_cases.py
12) utils.py: handles communication with openAI's APIs.


To evaluate, you run test_trajectories with the right directory names in the file
To generate new trajectories, you run main_file.py



