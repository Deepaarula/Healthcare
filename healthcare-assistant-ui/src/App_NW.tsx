import { useState } from "react";

const SectionCard = ({
  emoji,
  title,
  subtitle,
  onClick,
}: {
  emoji: string;
  title: string;
  subtitle: string;
  onClick: () => void;
}) => (
  <div className="card" onClick={onClick}>
    <div className="emoji">{emoji}</div>
    <h2>{title}</h2>
    <p>{subtitle}</p>
  </div>
);

export default function App() {
  const [mode, setMode] = useState<null | string>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleSubmit = async () => {
    setLoading(true);
    setResult(null);
    try {
      const resp = await fetch("http://127.0.0.1:8080/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: input }),
      });
      const data = await resp.json();
      setResult(data);
    } catch (err) {
      console.error("Error fetching:", err);
    } finally {
      setLoading(false);
    }
  };

  if (!mode) {
    return (
      <div>
        <header>
          <div>Powered by Google Cloud • Gemini • Vertex AI • BigQuery</div>
        </header>

        <main className="landing">
          <h1 className="title">🚀 Geminator Testcase Generator (GTG)</h1>
          <p>
            Select a domain below to chat with <b>MediAI</b>, generate compliant
            test cases, validate against ISO, or ask general questions.
          </p>

          <div className="cards">
            <SectionCard
              emoji="💉"
              title="Insulin Pumps"
              subtitle="Basal/bolus delivery, safety interlocks"
              onClick={() => setMode("insulin")}
            />
            <SectionCard
              emoji="🫁"
              title="Ventilators"
              subtitle="Alarms, modes, fail-safes"
              onClick={() => setMode("ventilator")}
            />
            <SectionCard
              emoji="🫀"
              title="Cardiology Devices"
              subtitle="ECG/HR monitoring & diagnostics"
              onClick={() => setMode("cardio")}
            />
            <SectionCard
              emoji="🏥"
              title="EHR/Clinical Software"
              subtitle="Security, audit trails, interoperability"
              onClick={() => setMode("ehr")}
            />
            <SectionCard
              emoji="⚠️"
              title="ISO/Regulatory Audit"
              subtitle="62304, 14971, CSV, 13485"
              onClick={() => setMode("iso")}
            />
            <SectionCard
              emoji="🧪"
              title="Sandbox / Samples"
              subtitle="Try with realistic sample data"
              onClick={() => setMode("samples")}
            />
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="chat-container">
      <button className="small-btn" onClick={() => setMode(null)}>
        ← Back
      </button>
      <h2>{mode.charAt(0).toUpperCase() + mode.slice(1)} Assistant</h2>

      <textarea
        className="chat-input"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Type your requirement or general question..."
      />

      <button className="small-btn" onClick={handleSubmit} disabled={loading}>
        {loading ? "⏳ Processing..." : "Scan Me"}
      </button>

      {loading && <p>Processing...</p>}

      {result && result.intent === "general" && (
        <div className="results">
          <h3>💡 Answer</h3>
          <p>{result.answer?.text || "No answer returned."}</p>
        </div>
      )}

      {result && result.requirement && (
        <div className="results">
          <h3>📌 Requirement</h3>
          <pre>{JSON.stringify(result.requirement, null, 2)}</pre>

          <h3>🧪 Test Cases</h3>
          {Array.isArray(result.test_cases) ? (
            <ul>
              {result.test_cases.map((tc: any, idx: number) => (
                <li key={idx}>
                  <b>{tc.test_case_id}:</b> {tc.title}
                  <br />
                  <small>{tc.expected_result}</small>
                </li>
              ))}
            </ul>
          ) : (
            <pre>{JSON.stringify(result.test_cases, null, 2)}</pre>
          )}

          <h3>✅ ISO Validation</h3>
          {Array.isArray(result.iso_validation) ? (
            <ul>
              {result.iso_validation.map((iv: any, idx: number) => (
                <li key={idx}>
                  <b>{iv.test_case_id}</b> –{" "}
                  {iv.compliant ? "Compliant ✅" : "❌ Not Compliant"} <br />
                  <small>{iv.related_iso_refs}</small>
                  <br />
                  <i>{iv.suggestions}</i>
                </li>
              ))}
            </ul>
          ) : (
            <pre>{JSON.stringify(result.iso_validation, null, 2)}</pre>
          )}
        </div>
      )}
    </div>
  );
}

