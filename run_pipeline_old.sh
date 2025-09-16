#!/bin/bash
set -e

# === Config ===
CR_URL="https://mcp-gcs-340670699772.us-central1.run.app"
BUCKET="hackathon-assets-team1-healthcaretestcasegeneration"
REQ="Generate a pytest that validates basal rate = 0.5 units/hour. Only return Python code."

# === Step 1: Generate test code ===
echo ">> Generating test code..."
curl -s -X POST "$CR_URL/tools/genai.generate_test" \
  -H "Content-Type: application/json" \
  -d "{\"prompt\":\"$REQ\"}" \
  | jq -r '.candidates[0].content.parts[0].text' \
  | sed 's/^```.*//g' > test_basal_0_5.py

echo ">> Preview of generated test:"
head -n 5 test_basal_0_5.py

# === Step 2: Upload to GCS ===
echo ">> Uploading to GCS..."
curl -s -X POST "$CR_URL/tools/gcs.write" \
  -H "Content-Type: application/json" \
  -d @- <<EOF | jq .
{
  "path": "outputs/testcases/test_basal_0_5.py",
  "content": $(python3 -c 'import json; print(json.dumps(open("test_basal_0_5.py").read()))'),
  "bucket": "$BUCKET"
}
EOF

# === Step 3: Run pytest ===
echo ">> Running pytest..."
curl -s -X POST "$CR_URL/tools/pytest.run" \
  -H "Content-Type: application/json" \
  -d "{\"gs_uri\":\"gs://$BUCKET/outputs/testcases/test_basal_0_5.py\"}" \
  | tee pytest_output.json | jq .

# === Step 4: Write results to BigQuery ===
# === Step 4: Write results to BigQuery ===
echo ">> Writing results to BigQuery..."

# Extract fields dynamically from pytest output
RETURN_CODE=$(jq -r '.returncode' pytest_output.json)
STDOUT=$(jq -r '.stdout' pytest_output.json)

STATUS="passed"
if [ "$RETURN_CODE" != "0" ]; then
  STATUS="failed"
fi

# Duration in ms (quick parse: look for "X.XXs" at end of pytest output)
DURATION_MS=$(echo "$STDOUT" | grep -oE '[0-9]+\.[0-9]+s' | tail -1 | sed 's/s//' | awk '{printf("%d\n", $1 * 1000)}')
if [ -z "$DURATION_MS" ]; then
  DURATION_MS=0
fi

RUN_ID=$(uuidgen)
TEST_NAME="test_basal_0_5.py"
REQ_ID="auto-${RUN_ID}"   # you can later replace with real requirement IDs
HAZARD="N/A"              # placeholder for now
INVARIANT="N/A"           # placeholder for now

curl -s -X POST "$CR_URL/tools/bq.write_results" \
  -H "Content-Type: application/json" \
  -d "{
    \"dataset\": \"qa_metrics\",
    \"table\": \"test_results\",
    \"rows\": [{
      \"run_id\": \"$RUN_ID\",
      \"test_name\": \"$TEST_NAME\",
      \"req_id\": \"$REQ_ID\",
      \"hazard\": \"$HAZARD\",
      \"invariant\": \"$INVARIANT\",
      \"status\": \"$STATUS\",
      \"duration_ms\": $DURATION_MS,
      \"ts\": \"$(date -u +%FT%TZ)\"
    }]
  }" | jq .

