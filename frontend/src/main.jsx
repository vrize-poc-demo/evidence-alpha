import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { FileUp, MessageSquare, Search, ShieldCheck } from "lucide-react";
import "./styles.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

function App() {
  const [filings, setFilings] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState("");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    fetchFilings();
  }, []);

  async function fetchFilings() {
    const response = await fetch(`${API}/filings`);
    const data = await response.json();
    setFilings(data);
    if (!selectedDoc && data.length) setSelectedDoc(data[0].doc_name);
  }

  async function uploadFiling(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    try {
      await fetch(`${API}/filings/upload`, { method: "POST", body: formData });
      await fetchFilings();
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  async function askQuestion(event) {
    event.preventDefault();
    const clean = question.trim();
    if (!clean) return;
    setMessages((items) => [...items, { role: "user", text: clean }]);
    setQuestion("");
    setLoading(true);
    try {
      const response = await fetch(`${API}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: clean, doc_name: selectedDoc }),
      });
      const data = await response.json();
      setMessages((items) => [...items, { role: "assistant", data }]);
    } finally {
      setLoading(false);
    }
  }

  const selectedFiling = useMemo(
    () => filings.find((filing) => filing.doc_name === selectedDoc),
    [filings, selectedDoc]
  );

  const samples = [
    {
      doc: "3M_2018_10K",
      question:
        "What is the FY2018 capital expenditure amount (in USD millions) for 3M? Give a response to the question by relying on the details shown in the cash flow statement.",
    },
    {
      doc: "3M_2022_10K",
      question: "Is 3M a capital-intensive business based on FY2022 data?",
    },
    {
      doc: "3M_2022_10K",
      question:
        "What drove operating margin change as of FY2022 for 3M? If operating margin is not a useful metric for a company like this, then please state that and explain why.",
    },
  ];

  return (
    <main className="app">
      <aside className="sidebar">
        <div className="brand">
          <ShieldCheck size={30} />
          <div>
            <h1>Evidence Alpha</h1>
            <p>SEC filing answers with proof.</p>
          </div>
        </div>

        <label className="upload">
          <FileUp size={18} />
          <span>{uploading ? "Processing..." : "Add filing"}</span>
          <input type="file" accept=".htm,.html" onChange={uploadFiling} disabled={uploading} />
        </label>

        <section className="panel">
          <h2>Indexed Filings</h2>
          <select value={selectedDoc} onChange={(event) => setSelectedDoc(event.target.value)}>
            {filings.map((filing) => (
              <option key={filing.doc_name} value={filing.doc_name}>
                {filing.doc_name}
              </option>
            ))}
          </select>
          {selectedFiling && (
            <dl className="meta">
              <div><dt>Company</dt><dd>{selectedFiling.company || "Uploaded filing"}</dd></div>
              <div><dt>Type</dt><dd>{selectedFiling.doc_type || "HTML"}</dd></div>
              <div><dt>Chunks</dt><dd>{selectedFiling.chunk_count}</dd></div>
            </dl>
          )}
        </section>

        <section className="panel">
          <h2>Sample Questions</h2>
          <div className="samples">
            {samples.map((sample) => (
              <button
                key={sample.question}
                onClick={() => {
                  setSelectedDoc(sample.doc);
                  setQuestion(sample.question);
                }}
              >
                {sample.question}
              </button>
            ))}
          </div>
        </section>
      </aside>

      <section className="chat">
        <header className="chatHeader">
          <div>
            <p className="eyebrow">Analyst workspace</p>
            <h2>{selectedDoc || "Choose a filing"}</h2>
          </div>
          <span className="status">Evidence required</span>
        </header>

        <div className="messages">
          {messages.length === 0 && (
            <div className="empty">
              <MessageSquare size={36} />
              <h3>Ask a filing question</h3>
              <p>Answers cite the document, page, and source passage. Unsupported questions are declined.</p>
            </div>
          )}
          {messages.map((message, index) =>
            message.role === "user" ? (
              <div className="bubble user" key={index}>{message.text}</div>
            ) : (
              <AnswerCard key={index} data={message.data} />
            )
          )}
          {loading && <div className="bubble assistant">Searching evidence...</div>}
        </div>

        <form className="ask" onSubmit={askQuestion}>
          <Search size={19} />
          <input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask about revenue, capex, operating margin, balance sheet items..."
          />
          <button disabled={loading || !selectedDoc}>Ask</button>
        </form>
      </section>
    </main>
  );
}

function AnswerCard({ data }) {
  return (
    <article className={`answer ${data.status}`}>
      <div className="answerTop">
        <span>{data.status === "answered" ? "Answered" : "Not found"}</span>
        <strong>{Math.round((data.confidence || 0) * 100)}% confidence</strong>
      </div>
      {data.model_used && <p className="model">Model: {data.model_used}</p>}
      <p className="answerText">{data.answer}</p>
      {data.calculation && <p className="calc">{data.calculation}</p>}
      {data.document && (
        <p className="cite">
          Source: {data.document}{data.page ? `, page ${data.page}` : ""}
        </p>
      )}
      <details>
        <summary>Evidence</summary>
        {(data.evidence || []).map((item, index) => (
          <div className="evidence" key={`${item.doc_name}-${index}`}>
            <div>
              <strong>{item.doc_name}</strong>
              <span>{item.page_num ? `Page ${item.page_num}` : "Page not detected"}</span>
            </div>
            <p>{item.text}</p>
          </div>
        ))}
      </details>
    </article>
  );
}

createRoot(document.getElementById("root")).render(<App />);
