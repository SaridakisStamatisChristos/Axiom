#!/usr/bin/env bash
set -euo pipefail
archive=$(cd "${1:?Path to the extracted v7 assessment archive}" && pwd)
mkdir "${2:?New evidence output directory}"
out=$(cd "$2" && pwd)
profile=${3:-legacy}
flags=()
case "$profile" in
    legacy) ;;
    certified-v1) flags+=(--novelty-profile "$profile") ;;
    *) printf 'Unknown discovery profile %s\n' "$profile" >&2; exit 2 ;;
esac
(cd "$archive" && sha256sum -c SHA256SUMS) > "$out/input-checksums.log"
cp "$archive/source/initial-ledger.sqlite3" "$out/ledger.sqlite3"
{
    git rev-parse HEAD
    python --version
    lean --version
    sha256sum lake-manifest.json lean-toolchain
    uname -sm
    nproc
    sed -n '/^MemTotal:/p' /proc/meminfo
} > "$out/environment.txt"
export TIMEFORMAT='wall_seconds=%R user_seconds=%U system_seconds=%S'
common=(--db "$archive/source/science.sqlite3" --legacy-v18 "$archive/source/compositional.json"
        --ledger "$out/ledger.sqlite3")
for seed in 1729 2718; do
    campaign=("${common[@]}" --campaign "frontier-audit-$seed")
    { time python -m axiom graph-discover "${campaign[@]}" --seed "$seed" "${flags[@]}" \
        --n6-training 192 --n7-training 128 --proof-beam 32 --holdout-budget 48 \
        --max-candidates 8 > "$out/candidates-$seed.json"; } 2> "$out/discovery-$seed.time"
    if [[ "$profile" == legacy ]]; then
        cmp "$archive/candidates-$seed.json" "$out/candidates-$seed.json"
    fi
    printf '%s %s generated\n' "$profile" "$seed"
done
for seed in 1729 2718; do
    campaign=("${common[@]}" --campaign "frontier-audit-$seed")
    { time python -m axiom graph-discover-audit "${campaign[@]}" \
        --artifact "$out/candidates-$seed.json" > "$out/candidate-audit-$seed.json"; } 2> "$out/audit-$seed.time"
    cmp "$out/candidates-$seed.json" "$out/candidate-audit-$seed.json"
    { time python -m axiom graph-discover-universal "${campaign[@]}" --timeout 45 \
        --proof-profile clique-independence > "$out/proofs-$seed.json"; } 2> "$out/proof-$seed.time"
    python -m axiom graph-discover-universal-audit "${campaign[@]}" \
        --artifact "$out/proofs-$seed.json" > "$out/proof-audit-$seed.json"
    cmp "$out/proofs-$seed.json" "$out/proof-audit-$seed.json"
    printf '%s %s checked\n' "$profile" "$seed"
done
{ time python "$archive/stress.py" "$out" 1729 2718 > "$out/stress.log"; } 2> "$out/stress.time"
if [[ "$profile" == legacy ]]; then
    cmp "$archive/stress.json" "$out/stress.json"
    python "$archive/summarize.py" "$out" > "$out/summary.log"
    cmp "$archive/summary.json" "$out/summary.json"
fi
