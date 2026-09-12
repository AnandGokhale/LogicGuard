#!/usr/bin/env python3
"""
Build the Section V figure from an existing query_complexity_results.json.
No API calls -- rerun this freely after re-plotting decisions change.

Single panel, one IEEE column: observed E[T_x] per deployed law set, with
the Theorem 3 bound marked per level and the Theorem 5 bound (which holds
uniformly over L_soft, the adversarial case included) as a ceiling.
NOTE: these labels must track the theorem numbers in main_LCSS_online.tex,
where theorems share a counter with lemmas, remarks and corollaries.
"""

import json
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SRC = sys.argv[1] if len(sys.argv) > 1 else "query_complexity_results.json"
OUT = sys.argv[2] if len(sys.argv) > 2 else "query_complexity.png"

r = json.load(open(SRC))
SWEEP = ["L0 none", "L1 mild", "L2 moderate", "L3 tight", "L4 converged"]
ADV = "L5 adversarial"

sizes = [len(r["config"]["levels"][n]) for n in SWEEP]
obs = [r["levels"][n]["obs_mean"] for n in SWEEP]
ci = [r["levels"][n]["obs_ci"] for n in SWEEP]
bnd = [r["levels"][n]["bound_best"] for n in SWEEP]

adv = r["levels"][ADV]
obs.append(adv["patient_mean"])
ci.append(adv["patient_ci"])
thm3 = r["theorem3_bound"]

x = np.arange(len(obs))
labels = [str(s) for s in sizes] + [r"$\emptyset$"]

fig, ax = plt.subplots(figsize=(3.45, 2.55))

colors = ["tab:orange"] * len(SWEEP) + ["tab:green"]
ax.bar(x, obs, 0.62, yerr=ci, capsize=3, color=colors, alpha=0.85,
       edgecolor="black", linewidth=0.6, label=r"observed $\mathbb{E}[T_x]$")

# Theorem 3 bound, per level (undefined for the adversarial set: alpha = 0).
ax.plot(x[:len(SWEEP)], bnd, "s--", color="tab:blue", lw=1.5, ms=5,
        label="bound, Thm. 3")

# Theorem 5 bound: uniform over L_soft, so it spans every bar.
ax.axhline(thm3, color="tab:red", ls="-.", lw=1.5, label="bound, Thm. 5")

ax.annotate("adversarial\ncritic", xy=(x[-1], obs[-1]),
            xytext=(x[-1] - 0.35, obs[-1] + 5.5), fontsize=7,
            color="tab:green", ha="center",
            arrowprops=dict(arrowstyle="->", color="tab:green", lw=0.9))

ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=8)
ax.set_xlabel(r"admissible set size $|U_L(A)|$", fontsize=9)
ax.set_ylabel(r"actor queries per visit", fontsize=9)
ax.set_ylim(0, thm3 * 1.52)          # headroom so the legend clears Thm. 5
ax.tick_params(labelsize=8)
ax.legend(fontsize=6.8, loc="upper left", ncol=1, framealpha=0.92,
          borderpad=0.35, handlelength=1.8)
ax.grid(True, axis="y", alpha=0.3)

plt.tight_layout(pad=0.3)
plt.savefig(OUT, dpi=300, bbox_inches="tight")
print(f"wrote {OUT}")
