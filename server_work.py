import os
import json
import pathlib
import subprocess
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from google.auth import default
from google.auth.transport.requests import Request
from google.cloud import storage, bigquery

# ------------ Config ------------
PROJECT_ID = os.getenv("PROJECT_ID", "healthcaretestcasegeneration")
REGION = os.getenv("REGION", "us-central1")
DEFAULT_BUCKET = os.getenv("ASSETS_BUCKET", "hackathon-assets-team1-healthcaretestcasegeneration")

# ------------ App ------------
app = Flask(__name__)

# ------------ Helpers ------------
def get_adc_access_token():
    creds, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(Request())
    return creds.token

def bq_client():
    return bigquery.Client(project=PROJECT_ID)

def gcs_client():
    return storage.Client(project=PROJECT_ID)

def upload_file_to_gcs(local_path: str, bucket: str, dest_path: str):
    client = gcs_client()
    bucket_obj = client.bucket(bucket)
    blob = bucket_obj.blob(dest_path)
    blob.upload_from_filename(local_path)
    return f"gs://{bucket}/{dest_path}"

def upload_dir_to_gcs(local_dir: str, bucket: str, prefix: str):
    uploaded = []
    client = gcs_client()
    for root, _, files in os.walk(local_dir):
        for f in files:
            lp = os.path.join(root, f)
            rel = os.path.relpath(lp, local_dir).replace("\", "/")
            dest = f"{prefix.rstrip('/')}/{rel}"
            bucket_obj = client.bucket(bucket)
            blob = bucket_obj.blob(dest)
            blob.upload_from_filename(lp)
            uploaded.append(f"gs://{bucket}/{dest}")
    return uploaded

def extract_json(text: str):
    """Extract JSON block from LLM text output."""
    try:
        if "```json" in text:
            text = text.split("```json", 1)[1].split("```", 1)[0]
        elif "```" in text:
            text = text.split("```", 1)[1].split("```", 1)[0]
        return json.loads(text)
    except Exception:
        try:
            return json.loads(text)
        except Exception:
            return {{}}

def gemini_generate_text(prompt: str) -> dict:
    """Call Gemini model with given prompt and return text response."""
    access_token = get_adc_access_token()
    model_id = "gemini-2.5-flash-lite"
    url = f"https://{REGION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{REGION}/publishers/google/models/{model_id}:generateContent"

    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}
        ],
        "generationConfig": {"responseMimeType": "text/plain"}
    }
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json=body, timeout=120)

    if resp.status_code != 200:
        return {"text": f"Error: {resp.text}"}

    data = resp.json()
    text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    return {"text": text}

def bq_insert_filtered(dataset, table, rows):
    client = bq_client()
    table_id = f"{PROJECT_ID}.{dataset}.{table}"
    try:
        errors = client.insert_rows_json(table_id, rows)
        return errors
    except Exception as e:
        return [{"error": str(e)}]

# ------------ Routes ------------
@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok"}), 200

@app.route("/tools/genai.generate_test", methods=["POST"])
def genai_generate_test():
    data = request.get_json(force=True) or {{}}
    prompt = data.get("prompt", "Generate a pytest for insulin pump 1 unit/hour basal rate.")
    result = gemini_generate_text(prompt)
    return jsonify(result)

@app.route("/tools/normalize_requirement", methods=["POST"])
def normalize_requirement():
    data = request.get_json(force=True) or {{}}
    prompt = data.get("prompt")
    if not prompt:
        return jsonify({"error": "prompt required"}), 400

    result = {{
        "requirement": None,
        "test_cases": None,
        "iso_validation": None,
        "artifacts": [],
        "bq_trace": None,
        "bq_test_cases": None,
        "bq_test_results": None,
    }}

    # Step 1: Normalize requirement
    norm_prompt = (
        "Normalize the medical-device requirement into JSON with fields: "
        "req_id, description, hazard, invariant, acceptance_criteria[].\n\n"
        f"Requirement: {prompt}"
    )
    norm_text = gemini_generate_text(norm_prompt).get("text", "{{}}")
    requirement = extract_json(norm_text)
    result["requirement"] = requirement

    # Log requirement to BQ.trace
    trace_row = {{
        "req_id": requirement.get("req_id"),
        "design_ref": requirement.get("invariant"),
        "code_symbol": requirement.get("hazard"),
        "test_name": requirement.get("description"),
        "artifact_hash": "; ".join(requirement.get("acceptance_criteria", [])),
        "version": "v1",
    }}
    trace_err = bq_insert_filtered("qa_metrics", "trace", [trace_row])
    result["bq_trace"] = "success" if not trace_err else {"errors": trace_err}

    # Step 2: Generate test cases
    tc_prompt = (
        f"Generate 3 detailed test cases in JSON for the requirement:\n{prompt}\n\n"
        "Each test case must include: test_case_id, title, steps[], preconditions[], expected_result."
    )
    tc_text = gemini_generate_text(tc_prompt).get("text", "[]")
    test_cases = extract_json(tc_text)
    result["test_cases"] = test_cases

    # Step 3: ISO Validation
    iso_prompt = (
        "You are an auditor for ISO 62304 (medical device software lifecycle) "
        "and ISO 14971 (risk management). "
        "Review the following requirement and test cases and return JSON with fields: "
        "req_id, test_case_id, compliant (true/false), missing_elements (string), related_iso_refs (string), suggestions (string).\n\n"
        f"Requirement: {json.dumps(requirement, indent=2)}\n\n"
        f"Test Cases: {json.dumps(test_cases, indent=2)}"
    )
    iso_text = gemini_generate_text(iso_prompt).get("text", "{{}}")
    iso_validation = extract_json(iso_text)
    result["iso_validation"] = iso_validation

    # Log ISO validation results to BigQuery
    iso_rows = []
    if isinstance(iso_validation, list):
        for entry in iso_validation:
            iso_rows.append({
                "req_id": entry.get("req_id", requirement.get("req_id")),
                "test_case_id": entry.get("test_case_id"),
                "compliant": entry.get("compliant"),
                "missing_elements": entry.get("missing_elements"),
                "related_iso_refs": entry.get("related_iso_refs"),
                "suggestions": entry.get("suggestions"),
                "validated_at": datetime.utcnow().isoformat()
            })
    elif isinstance(iso_validation, dict):
        iso_rows.append({
            "req_id": iso_validation.get("req_id", requirement.get("req_id")),
            "test_case_id": iso_validation.get("test_case_id"),
            "compliant": iso_validation.get("compliant")

    if intent == "requirement":
        with app.test_request_context("/tools/normalize_requirement", method="POST", json={"prompt": prompt}):
            resp = normalize_requirement()
            return resp
    else:
        answer = gemini_generate_text(prompt)
        return jsonify({"intent": "general", "answer": answer})

# ------------ Main ------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
