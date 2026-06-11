#!/usr/bin/env bash
# gen_synthea_fixtures.sh — Download Synthea JAR and generate FHIR R4B transaction bundle fixtures.
#
# Usage:
#   ./scripts/gen_synthea_fixtures.sh
#
# Outputs to libs/veridoc-fhir/tests/fixtures/fhir/ (committed as test fixtures).
#
# Pitfall 7 (D-13): --exporter.fhir.use_us_core_ig=false is REQUIRED.
# US Core IG adds profiles that cause fhir.resources R4B strict validation failures
# because R4B does not include all US Core extensions. Always disable for VeriDoc fixtures.
#
# Flags:
#   -p 5       — generate 5 synthetic patients (enough for Wave 0 fixture coverage)
#   -s 42      — deterministic random seed (reproducible fixtures across CI runs)
#   --exporter.fhir.export=true — output FHIR R4 JSON bundles
#   --exporter.fhir.use_us_core_ig=false — disable US Core IG (Pitfall 7)
#
# Requirements:
#   - Java 11+ on PATH (openjdk-21 available in CI and dev)
#   - Internet access to download synthea-with-dependencies.jar from GitHub

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="$REPO_ROOT/libs/veridoc-fhir/tests/fixtures/fhir"
SYNTHEA_VERSION="3.3.1"
SYNTHEA_JAR="$REPO_ROOT/.cache/synthea-with-dependencies-${SYNTHEA_VERSION}.jar"
SYNTHEA_URL="https://github.com/synthetichealth/synthea/releases/download/master-branch-latest/synthea-with-dependencies.jar"

mkdir -p "$OUTPUT_DIR"
mkdir -p "$(dirname "$SYNTHEA_JAR")"

if [ ! -f "$SYNTHEA_JAR" ]; then
    echo "[synthea] Downloading Synthea JAR from GitHub..."
    curl -fsSL -o "$SYNTHEA_JAR" "$SYNTHEA_URL"
    echo "[synthea] Downloaded: $SYNTHEA_JAR"
fi

echo "[synthea] Generating 5 patients (seed 42, R4B, US Core IG disabled)..."
TMPDIR=$(mktemp -d)
trap "rm -rf '$TMPDIR'" EXIT

java -jar "$SYNTHEA_JAR" \
    -p 5 \
    -s 42 \
    --exporter.fhir.export=true \
    --exporter.fhir.use_us_core_ig=false \
    --exporter.baseDirectory="$TMPDIR"

# Synthea outputs to $TMPDIR/fhir/
FHIR_SUBDIR="$TMPDIR/fhir"
if [ ! -d "$FHIR_SUBDIR" ]; then
    # Some Synthea versions output directly to TMPDIR
    FHIR_SUBDIR="$TMPDIR"
fi

echo "[synthea] Copying patient bundles to $OUTPUT_DIR ..."
COPIED=0
for f in "$FHIR_SUBDIR"/*.json; do
    # Skip hospitalInformation* and practitionerInformation* — these are not patient bundles
    basename_f="$(basename "$f")"
    if [[ "$basename_f" == hospitalInformation* || "$basename_f" == practitionerInformation* ]]; then
        continue
    fi
    cp "$f" "$OUTPUT_DIR/"
    COPIED=$((COPIED + 1))
done

echo "[synthea] Copied $COPIED patient bundles to $OUTPUT_DIR"
echo "[synthea] Done. Fixtures committed at libs/veridoc-fhir/tests/fixtures/fhir/"
