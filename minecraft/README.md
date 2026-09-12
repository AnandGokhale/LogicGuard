This folder contains the necessary code for the the mining diamond task in minecraft.


You will need :

1) Minecraft account
2) Node js
3) Spot
4) OpenAI
5) mineflayer


To run this, 
1) Start a minecraft world, and open to LAN on the port 25565
2) On one terminal window, run simple_bot.js
3) On a second terminal window, run the appropriate agent from minecraft, we have three kinds of agents, saycan, innermonologue and baseline.


The appropriate data and trajectories are in Saycan actor and critic folders, and IM_single actor and critic folders.


Where the LTL laws live
-----------------------

The soft law sets are JSON files under `python_code/laws/` rather than python lists in
`LTL_implementer.py`:

    laws/saycan_soft_laws.json            -> SOFT_LTL_RULES_SAYCAN
    laws/inner_monologue_soft_laws.json   -> SOFT_LTL_RULES_INNER_MONOLOGUE
                                             SOFT_LTL_RULES_INNER_MONOLOGUE_EXPLAINER

Each file is a list of `{"law": ..., "explanation": ...}`, in order, so the rules and the
explainers stay index-aligned. `LTL_implementer.py` loads them at import time through
`python_code/laws_store.py`, so every agent server keeps importing the same names as before.

The critic writes to `laws/saycan_soft_laws.json` instead of printing laws for you to paste in:

    python critic.py --file Saycan_critic/run1.pkl --mode 0        # propose laws, append them to the file
    python critic.py --file Saycan_critic/run1.pkl --mode 1        # break deadlocks, edit laws in place
    python agent_server_saycan.py --file run2 --mode 1             # actor reads the file at startup

Both sides take `--laws <path>` if you want to keep several law sets side by side, and the critic
takes `--no-write` to preview its proposals. A proposed law is rejected before it is written if
spot cannot parse it, if it duplicates an existing law, or if it mentions a proposition outside
OBS_VARIABLES_LIST / ACTION_VARIABLES_LIST (an unknown proposition is unconstrained in the word
automaton, so the law would silently never fire).
