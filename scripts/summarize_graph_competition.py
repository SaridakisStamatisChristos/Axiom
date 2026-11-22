"""Compare matched discovery queues, proof outcomes, and external refutations."""
import argparse
from collections import Counter
import json
from pathlib import Path

from axiom.graph_proof_beam import OPEN_QUEUE


def read(folder, name):
    return json.loads((folder / name).read_bytes())


def evidence(folder, seed):
    campaign = read(folder, f"candidates-{seed}.json")
    proof = read(folder, f"proofs-{seed}.json")
    if campaign != read(folder, f"candidate-audit-{seed}.json") or proof != read(folder, f"proof-audit-{seed}.json"):
        raise ValueError("campaign or proof audit differs")
    selected = campaign["trials"] + campaign["proof_beam"]["trials"]
    external = read(folder, "stress.json")["hits"]
    output = {}
    for trial, result in zip(selected, proof["results"], strict=True):
        cid = trial["candidate_id"]
        if cid != result["candidate_id"] or trial["statement"] != result["statement"]:
            raise ValueError("proof dispatch does not match the selected statement")
        lane = trial.get("queue", "AFFINE")
        output[(lane, cid)] = {"id": cid, "lane": lane, "statement": trial["statement"],
                               "native_holdout": trial["status"], "proof": result["status"],
                               "holdout_count": len(trial["masks_checked"]),
                               "external_refutation": external.get(cid)}
    return campaign, output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("legacy", type=Path)
    parser.add_argument("certified", type=Path)
    args = parser.parse_args()
    rows = {}
    for seed in (1729, 2718):
        old, before = evidence(args.legacy, seed)
        new, after = evidence(args.certified, seed)
        if {k: v for k, v in new["configuration"].items() if k != "novelty_profile"} != old["configuration"]:
            raise ValueError("legacy and certified campaigns were assigned different generation budgets")
        decisions = new["novelty"]["decisions"]
        removed = [trial for key, trial in before.items() if key not in after
                   and decisions.get(trial["id"], {}).get("status") == "KNOWN_IMPLICATION"]
        arrivals = [trial for key, trial in after.items() if key not in before
                    and trial["lane"] in (OPEN_QUEUE, "AFFINE")]
        removed_beam = sum(row["lane"] == OPEN_QUEUE for row in removed)
        if seed == 1729 and removed_beam < 6:
            raise ValueError("seed 1729 did not reclaim the six rediscovery slots")
        rows[seed] = {
            "known_rediscoveries_removed": removed, "removed_open_beam_slots": removed_beam,
            "replacement_research_trials": arrivals,
            "before_proof_statuses": dict(Counter(row["proof"] for row in before.values())),
            "after_proof_statuses": dict(Counter(row["proof"] for row in after.values())),
            "after_filter_decisions": dict(Counter(row["status"] for row in decisions.values())),
            "after_filter_directions": dict(Counter(step["method"] for row in decisions.values()
                                                    for step in row["directions"])),
            "after_preflight": {"affine": new["preflight_counts"], "open_beam":
                                new["proof_beam"]["queues"][OPEN_QUEUE]["preflight_counts"]},
        }
    print(json.dumps({"schema": "axiom.graph.competition_ab.v1", "runs": rows}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
