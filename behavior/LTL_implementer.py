import spot
import os
import json


from AP_generator import generate_APs_action

from typing import List, Dict, Set

def initialize_APs(file, env):
    if os.path.exists(file):
        with open(file, 'r') as f:
            saved = json.load(f)
            AP_list_observations = set(saved.get("obs_APs", []))
            AP_list_actions = set(saved.get("action_APs_true", []))
    else:
        AP_list_observations = set()
        AP_list_actions = set({'done'})
    
    BDD_DICT = spot.bdd_dict()
    
    for l in list(AP_list_observations) + list(AP_list_actions):
        BDD_DICT.register_proposition(spot.formula(l), None)


    return AP_list_observations, AP_list_actions, BDD_DICT




def compile_automaton(rules, bdd_dict):

    auts = []
    for r in rules:
        auts.append(spot.translate(r, 'BA', dict=bdd_dict))

    combined = auts[0]
    for aut in auts[1:]:
        combined = spot.product(combined, aut)
    return combined

def build_word_automaton(trace, variables, bdd_dict):
    """
    Builds a word automaton from a given trace.

    Parameters:
    - trace: List of sets, where each set contains atomic propositions true at a timestep.
    - variables: Full list of possible atomic propositions (strs).

    Returns:
    - A Spot automaton representing the trace.
    """
    
    aut = spot.make_twa_graph(bdd_dict)

    # Register all atomic propositions from the full variables list
    var_to_bdd = {var: spot.formula_to_bdd(spot.formula(var), bdd_dict, None) for var in variables}

    num_states = len(trace) + 1
    aut.new_states(num_states)
    aut.set_init_state(0)
    aut.set_buchi()

    for i, ap_set in enumerate(trace):
        #label = spot.bddtrue     #false_bdd = spot.formula_to_bdd(spot.formula.ff(), bdd_dict, None)

        label = spot.formula_to_bdd(spot.formula.tt(), bdd_dict, None)

        for var in variables:
            var_bdd = var_to_bdd[var]
            if var in ap_set:
                label &= var_bdd
            else:
                formula = spot.bdd_to_formula(var_bdd, bdd_dict)
                negated_formula = spot.formula.Not(formula)
                label &= spot.formula_to_bdd(negated_formula, bdd_dict,None)

        aut.new_edge(i, i + 1, label)

    # Add self-loop on the last state (to make it Büchi-accepting)
    aut.new_edge(num_states - 1, num_states - 1, spot.formula_to_bdd(spot.formula.tt(), bdd_dict, None), [0])


    return aut


def generate_trace_from_dicts(timestep_dicts: List[Dict[str, bool]]) -> List[Set[str]]:
    trace = []
    for step in timestep_dicts:
        true_props = set(step)
        trace.append(true_props)
    return trace




def filter_actions_LTL_trace(obs_props, rules, AP_list_observations, AP_list_actions, BDD_DICT):
    filtered_actions = []
    trace =  [obs_props]

    for action in AP_list_actions:
        proposed_trace = generate_trace_from_dicts(trace + [[action]])

        word_aut = build_word_automaton(proposed_trace, AP_list_observations + AP_list_actions, BDD_DICT)
        feasible =  True        
        for law in rules:
            automaton =  compile_automaton([law], BDD_DICT)
            run = automaton.intersecting_run(word_aut)
            if run is None:
                feasible = False
                break
        if feasible:
            filtered_actions.append(action)



    return filtered_actions


        