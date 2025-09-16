import os
import sys
import json
import pathlib
import subprocess
import requests
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from google.auth import default
from google.auth.transport.requests import Request
from google.cloud import storage, bigquery
from flask import Flask, request, jsonify
from flask_cors import CORS
#   from flask_cors import CORS
#from flask_cors import CORS


# ------------ Config ------------
PROJECT_ID = os.getenv("PROJECT_ID", "healthcaretestcasegeneration")
REGION = os.getenv("REGION", "us-central1")
DEFAULT_BUCKET = os.getenv("ASSETS_BUCKET", "hackathon-assets-team1-healthcaretestcasegeneration")

# ------------ Logging ------------
logging.basicConfig(
    level=logging.DEBUG,  # Debug to catch everything
    stream=sys.stderr,    # Force logs to stderr so Cloud Run captures them
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# ------------ App ------------
#app = Flask(__name__)
#CORS(app)

app = Flask(__name__)

# Allow CORS for all endpoints (UI <-> API)
CORS( app, resources={r"/*": {"origins": "*"}},  # 👈 in dev: allow all
    supports_credentials=True,
    expose_headers=["Content-Type"],
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "OPTIONS"]
)




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
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "text/plain"}
    }
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    logging.debug(f"Gemini request: {body}")
    resp = requests.post(url, headers=headers, json=body, timeout=120)

    if resp.status_code != 200:
        logging.error(f"Gemini error: {resp.text}")
        return {"text": f"Error: {resp.text}"}

    data = resp.json()
    text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    logging.debug(f"Gemini response: {text[:200]}...")
    return {"text": text}

def bq_insert_filtered(dataset, table, rows):
    client = bq_client()
    table_id = f"{PROJECT_ID}.{dataset}.{table}"
    try:
        errors = client.insert_rows_json(table_id, rows)
        return errors
    except Exception as e:
        logging.error(f"BigQuery insert error: {e}")
        return [{"error": str(e)}]

# ------------ Routes ------------

@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok"}), 200

@app.route("/chat", methods=["POST","OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        # Preflight CORS response
        return jsonify({"status": "ok"}), 200

    data = request.get_json(force=True) or {{}}
    prompt = data.get("prompt")
    if not prompt:
        logging.warning("/chat called with no prompt")
        return jsonify({"error": "prompt required"}), 400

    logging.info(f"/chat received prompt: {prompt}")

    classify_prompt = (
        "Classify the following input as either 'requirement' or 'general'. "
        "Respond with JSON only: {\"intent\": \"requirement\"} or {\"intent\": \"general\".}\n\n"
        f"Input: {prompt}"
    )
    classify_text = gemini_generate_text(classify_prompt).get("text", "{{}}")
    logging.debug(f"Classification raw: {classify_text}")

    intent_obj = extract_json(classify_text)
    intent = intent_obj.get("intent", "general")
    logging.info(f"Intent resolved: {intent}")

    if intent == "requirement":
        logging.info("Passing to normalize_requirement()")
        with app.test_request_context("/tools/normalize_requirement", method="POST", json={"prompt": prompt}):
            resp = normalize_requirement()
            logging.info("normalize_requirement() finished")
            return resp
    else:
        logging.info("Sending to Gemini general answer flow")
        answer = gemini_generate_text(prompt)
        logging.info(f"General answer: {answer}")
        return jsonify({"intent": "general", "answer": answer})

@app.route("/tools/normalize_requirement", methods=["POST"])
def normalize_requirement():
    data = request.get_json(force=True) or {{}}
    prompt = data.get("prompt")
    if not prompt:
        return jsonify({"error": "prompt required"}), 400

    logging.info(f"Normalizing requirement: {prompt}")
    result = {{"requirement": None, "test_cases": None, "iso_validation": None}}

    # Normalize requirement
    norm_prompt = (
        "Normalize the medical-device requirement into JSON with fields: "
        "req_id, description, hazard, invariant, acceptance_criteria[].\n\n"
        f"Requirement: {prompt}"
    )
    norm_text = gemini_generate_text(norm_prompt).get("text", "{{}}")
    requirement = extract_json(norm_text)
    logging.debug(f"Requirement parsed: {requirement}")
    result["requirement"] = requirement

    # Generate test cases
    tc_prompt = (
        f"Generate 3 detailed test cases in JSON for the requirement:\n{prompt}\n\n"
        "Each test case must include: test_case_id, title, steps[], preconditions[], expected_result."
    )
    tc_text = gemini_generate_text(tc_prompt).get("text", "[]")
    test_cases = extract_json(tc_text)
    logging.debug(f"Test cases parsed: {test_cases}")
    result["test_cases"] = test_cases

    # ISO Validation
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
    logging.debug(f"ISO validation parsed: {iso_validation}")
    result["iso_validation"] = iso_validation

    return jsonify(result)

@app.route("/upload-docs", methods=["POST"])
def upload_docs():
    if "files" not in request.files:
        return jsonify({"error": "No files uploaded"}), 400

    uploaded_files = request.files.getlist("files")
    uploaded_paths = []
    for file in uploaded_files:
        filename = secure_filename(file.filename)
        local_path = f"/tmp/{filename}"
        file.save(local_path)
        gcs_uri = upload_file_to_gcs(local_path, DEFAULT_BUCKET, f"uploads/{filename}")
        uploaded_paths.append(gcs_uri)

    return jsonify({"status": "success", "uploaded": uploaded_paths})

@app.route("/sample-data", methods=["GET"])
def sample_data():
    return jsonify({"status": "ok", "message": "Sample data endpoint"})


# ------------ Main ------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
