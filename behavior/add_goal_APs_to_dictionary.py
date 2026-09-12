import re
import json
import asyncio

def extract_aps_from_formulas(formulas):
    """Extract all atomic propositions from SPOT formulas"""
    all_aps = set()
    
    # SPOT keywords to exclude
    spot_keywords = {
        'G', 'F', 'X', 'U', 'R', 'true', 'false', 'and', 'or', 'not', 
        '&', '|', '!', '->', '<->', 'until', 'release', 'W', 'M',
        'next', 'eventually', 'globally', 'weakuntil', 'strongrelease'
    }
    
    for formula in formulas:
        if isinstance(formula, dict):
            # If formula is in a dict, extract the formula string
            formula_str = str(formula.get('formula', formula))
        else:
            formula_str = str(formula)
        
        # Find all word-like tokens (potential APs)
        # This regex matches identifiers: word characters, underscores, numbers
        potential_aps = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', formula_str)
        
        for ap in potential_aps:
            # Filter out SPOT keywords, numbers, and common operators
            if (ap not in spot_keywords and 
                not ap.isdigit() and 
                ap.lower() not in spot_keywords):
                all_aps.add(ap)
    
    return sorted(list(all_aps))



async def main():
    # read the file
    with open("behavior_action_sequencing_prompts.json", "r") as f:
        data = json.load(f)  # should be a list of dicts


    # iterate over identifiers
    for i, entry in enumerate(data):
        identifier = entry["identifier"]

        formula_file = f"rules/rules/done/{identifier}_rules.json"
        AP_file = f"data_no_critic/APs/{identifier}_APs.json"
        try:
            with open(formula_file, "r") as f:
                formula_data = json.load(f)
        except Exception as e:
            print(f"{identifier} FAILED because {e}!! Please recheck")
            continue
        with open(AP_file, "r") as f:
            AP_data = json.load(f)

        
        print(extract_aps_from_formulas(formula_data))

        new_aps = set(extract_aps_from_formulas(formula_data))

        AP_list_observations = set(AP_data.get("obs_APs", []))

        AP_list_observations = AP_list_observations.union(new_aps)

        AP_data["obs_APs"] = list(AP_list_observations)

        with open(AP_file, "w") as f:
            json.dump(AP_data, f, indent=2)




if __name__ == "__main__":
    asyncio.run(main())        