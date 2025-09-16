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
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("requirement");

  async function handleSubmit() {
    setLoading(true);
    try {
      const res = await fetch(
        "https://mcp-gcs-340670699772.us-central1.run.app/chat",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt: input }),
        }
      );
      const data = await res.json();
      setResult(data);

      // 👇 Auto-select tab based on intent
      if (data.intent === "general") {
        setActiveTab("answer");
      } else if (data.requirement) {
        setActiveTab("requirement");
      } else if (data.test_cases) {
        setActiveTab("testcases");
      } else if (data.iso_validation) {
        setActiveTab("iso");
      }
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  }

  if (!mode) {
    return (
      <div className="app-background">
        <div className="relative z-10">
          <header>
            <div className="powered">
              Powered by Google Cloud • Gemini • Vertex AI • BigQuery
            </div>
          </header>

          <main className="landing">
            <h1 className="title">🚀 Geminator Testcase Generator (GTG)</h1>
            <p>
              Select a domain below to chat with{" "}
              <span className="highlight">MediAI</span>, generate compliant test
              cases, validate against ISO, and track execution.
            </p>

            <div className="cards">
              <SectionCard
                emoji="💉"
                title="Insulin Pumps"
                subtitle="Basal/bolus delivery, safety interlocks"
                onClick={() => setMode("Insulin Pumps")}
              />
              <SectionCard
                emoji="🫁"
                title="Ventilators"
                subtitle="Alarms, modes, fail-safes"
                onClick={() => setMode("Ventilators")}
              />
              <SectionCard
                emoji="🫀"
                title="Cardiology Devices"
                subtitle="ECG/HR monitoring & diagnostics"
                onClick={() => setMode("Cardiology Devices")}
              />
              <SectionCard
                emoji="🏥"
                title="EHR/Clinical Software"
                subtitle="Security, audit trails, interoperability"
                onClick={() => setMode("EHR/Clinical Software")}
              />
              <SectionCard
                emoji="⚠️"
                title="ISO/Regulatory Audit"
                subtitle="62304, 14971, CSV, 13485"
                onClick={() => setMode("ISO/Regulatory Audit")}
              />
              <SectionCard
                emoji="🧪"
                title="Sandbox / Samples"
                subtitle="Try with realistic sample data"
                onClick={() => setMode("Sandbox")}
              />
            </div>
          </main>
        </div>
      </div>
    );
  }

  return (
    <div className="app-background flex items-center justify-center min-h-screen">
      <div className="chat-panel relative z-10 bg-black/70 text-white p-6 rounded-lg w-4/5 max-w-3xl">
        <button onClick={() => setMode(null)} className="mb-4 small-btn">
          ← Back
        </button>
        <h2 className="mb-2">{mode} Assistant</h2>

        <textarea
          className="w-full p-2 mb-3 rounded text-black"
          placeholder="Hey 👋 I’m here for both brains & health. Wanna spin up a test case or just chat health stuff?"
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />

        <button
          onClick={handleSubmit}
          disabled={loading}
          className="small-btn mb-4"
        >
          {loading ? "⏳ Generating..." : "Scan Me"}
        </button>

        {loading && <p>Processing...</p>}

        {result && (
          <div>
            {/* Tabs */}
            <div className="flex space-x-4 mb-4">
              {["requirement", "testcases", "iso", "answer"].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-3 py-1 rounded ${
                    activeTab === tab ? "bg-blue-600" : "bg-gray-700"
                  }`}
                >
                  {tab === "requirement" && "📌 Requirement"}
                  {tab === "testcases" && "🧪 Test Cases"}
                  {tab === "iso" && "✅ ISO Validation"}
                  {tab === "answer" && "💡 Answer"}
                </button>
              ))}
            </div>

            {/* Tab Content */}
            {activeTab === "requirement" && (
              <pre className="bg-gray-800 p-3 rounded overflow-auto text-sm">
                {JSON.stringify(result.requirement, null, 2)}
              </pre>
            )}

            {activeTab === "testcases" && (
              <div className="space-y-3">
                {Array.isArray(result.test_cases) &&
                  result.test_cases.map((tc: any) => (
                    <div
                      key={tc.test_case_id}
                      className="bg-gray-800 p-3 rounded"
                    >
                      <strong>{tc.title}</strong>
                      <p>{tc.expected_result}</p>
                      <button className="small-btn mt-2">
                        ✔ Mark as Passed
                      </button>
                    </div>
                  ))}
              </div>
            )}

            {activeTab === "iso" && (
              <pre className="bg-gray-800 p-3 rounded overflow-auto text-sm">
                {JSON.stringify(result.iso_validation, null, 2)}
              </pre>
            )}

            {activeTab === "answer" && (
              <div className="bg-gray-800 p-3 rounded">
                <p>{result.answer?.text || "No general answer returned."}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

