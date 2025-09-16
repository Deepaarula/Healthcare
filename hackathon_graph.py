import base64
import os, json, base64, argparse, textwrap, requests
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from langchain_google_vertexai import ChatVertexAI

# --------- Config from env ---------
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.popen("gcloud config get-value project").read().strip()
REGION = os.environ.get("GOOGLE_CLOUD_REGION") or os.popen("gcloud config get-value compute/region").read().strip() or "us-central1"
APP_URL = os.environ.get("APP_URL")  # e.g., https://mcp-gcs-....run.app
BUCKET = os.environ.get("BUCKET_NAME")  # e.g., hackathon-assets-team1-<project>

# --------- Graph state ---------
class State(TypedDict, total=False):
    req_text: str
    file_name: str
    test_code_b64: str
    gs_uri: str
    run_id: str
    summary: str

# --------- LLM (Gemini on Vertex AI) ---------
llm = MODEL = os.environ.get("LLM_MODEL", "gemini-1.0-pro")
LOCATION = os.environ.get("LLM_LOCATION", "us-central1")
MODEL = os.environ.get("LLM_MODEL", "gemini-1.5-pro-002")
LOCATION = os.environ.get("LLM_LOCATION", "us-east1")
print(f"[LangGraph] Using model={MODEL} location={LOCATION} project={PROJECT_ID}")

# --- LLM selection: prefer Gemini API if key is set, else Vertex AI ---
GENAI_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GENAI_API_KEY")
if GENAI_KEY:
    from langchain_google_genai import ChatGoogleGenerativeAI
    MODEL = os.getenv("LLM_MODEL", "gemini-1.5-pro")
    print(f"[LangGraph] Using Gemini API model={MODEL}")
    llm = ChatGoogleGenerativeAI(model=MODEL, google_api_key=GENAI_KEY, temperature=0.2)
else:
    from langchain_google_vertexai import ChatVertexAI
    MODEL = os.getenv("LLM_MODEL", "gemini-1.5-pro-002")
    LOCATION = os.getenv("LLM_LOCATION", "us-east1")
    PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("PROJECT_ID")
    print(f"[LangGraph] Using Vertex AI model={MODEL} location={LOCATION} project={PROJECT_ID}")
    llm = ChatVertexAI(model=MODEL, project=PROJECT_ID, location=LOCATION, temperature=0.2)

SYSTEM = """You are a test-generation agent for insulin pump software.
Rules:
- Never propose or permit autonomous bolus.
- Prefer small, deterministic pytest tests.
- Include docstring that cites requirement id if present.
- Name the test clearly.
Output ONLY Python code for a single test file.
"""

PROMPT_TMPL = """Requirement (healthcare context):
{req}

Write a single pytest file that:
- Asserts no autonomous bolus behavior
- Asserts an alarm when predicted glucose < 70 mg/dL in 30 minutes
- Is self-contained (no external I/O)
- Uses simple pure-Python assertions or stubs/mocks

Return ONLY valid Python code.
"""



def gen_test_node(state: State) -> State:
    req = state["req_text"]
    user_prompt = PROMPT_TMPL.format(req=req)
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GENAI_API_KEY")

    if api_key:
        # --- Direct REST call to Gemini (API key path) ---
        import requests
        model = os.getenv("LLM_MODEL", "gemini-1.5-pro")  # Gemini API model name
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
        parts = [{"text": SYSTEM + "\n\n" + user_prompt}]
        body = {"contents": [{"role": "user", "parts": parts}]}
        r = requests.post(url, headers=headers, json=body, timeout=60)
        r.raise_for_status()
        j = r.json()
        code = ""
        if isinstance(j, dict) and j.get("candidates"):
            cand = j["candidates"][0]
            content = cand.get("content", {})
            parts_out = content.get("parts", [])
            if parts_out:
                code = parts_out[0].get("text", "")
        if not code.strip():
            raise RuntimeError("Empty response from Gemini REST API")
    else:
        # Fall back to Vertex AI client if configured
        msg = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_prompt},
        ]
        code = llm.invoke(msg).content

    b64 = base64.b64encode(code.encode("utf-8")).decode("utf-8")
    return {"test_code_b64": b64}

def write_gcs_node(state: State) -> State:
    r = requests.post(f"{APP_URL}/tools/gcs.write", json={
        "bucket": BUCKET,
        "path": f"outputs/testcases/{state['file_name']}",
        "content_b64": state["test_code_b64"]
    }, timeout=120)
    r.raise_for_status()
    return {"gs_uri": r.json().get("gs_uri","")}

def run_pytest_node(state: State) -> State:
    r = requests.post(f"{APP_URL}/tools/pytest.run", json={
        "bucket": BUCKET,
        "tests_prefix": "outputs/testcases/"
    }, timeout=1800)
    r.raise_for_status()
    data = r.json()
    run_id = data.get("run_id","")
    # Make a one-liner summary
    summary = f"run_id={run_id} exit={data.get('exit_code')} tests_stdout_tail={data.get('stdout_tail','')[-120:]}"
    return {"run_id": run_id, "summary": summary}

def write_bq_node(state: State) -> State:
    r = requests.post(f"{APP_URL}/tools/bq.write_results", json={
        "bucket": BUCKET,
        "dataset": "qa_metrics",
        "run_id": state["run_id"]
    }, timeout=300)
    r.raise_for_status()
    return state

def build_graph():
    g = StateGraph(State)
    g.add_node("gen_test", gen_test_node)
    g.add_node("write_gcs", write_gcs_node)
    g.add_node("run_pytest", run_pytest_node)
    g.add_node("write_bq", write_bq_node)

    g.set_entry_point("gen_test")
    g.add_edge("gen_test", "write_gcs")
    g.add_edge("write_gcs", "run_pytest")
    g.add_edge("run_pytest", "write_bq")
    g.add_edge("write_bq", END)
    return g.compile()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--req", required=True, help="Requirement text")
    parser.add_argument("--file", required=True, help="Test file name, e.g. test_ip_req_006.py")
    args = parser.parse_args()

    # sanity for env
    if not APP_URL or not BUCKET:
        raise SystemExit("Set APP_URL and BUCKET_NAME env vars first.")

    graph = build_graph()
    result = graph.invoke({"req_text": args.req, "file_name": args.file})
    print("DONE\n", json.dumps({k:result.get(k) for k in ["gs_uri","run_id","summary"]}, indent=2))
