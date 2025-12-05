
import React, { useState } from "react";
import { useParams } from "react-router-dom";

export default function Dashboard() {
  const { id } = useParams();

  // Summary / Notes
  const [summary, setSummary] = useState("");
  const [notes, setNotes] = useState(null);

  // MCQ data
  const [mcq, setMcq] = useState(null);
  const [mcqLevel, setMcqLevel] = useState("easy");
  const [mcqNum, setMcqNum] = useState(10); // slider: 5–20, default 10
  const [mcqIndex, setMcqIndex] = useState(0);
  const [mcqAnswers, setMcqAnswers] = useState({});
  const [mcqFeedback, setMcqFeedback] = useState(null);

  // Fillups data
  const [fillups, setFillups] = useState(null);
  const [fillLevel, setFillLevel] = useState("easy");
  const [fillNum, setFillNum] = useState(10);
  const [fillIndex, setFillIndex] = useState(0);
  const [fillUserAnswers, setFillUserAnswers] = useState({});
  const [fillFeedback, setFillFeedback] = useState(null);

  // Chat
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState([]);

  // Local loaders
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [notesLoading, setNotesLoading] = useState(false);
  const [mcqLoading, setMcqLoading] = useState(false);
  const [fillupsLoading, setFillupsLoading] = useState(false);

  const API = "http://127.0.0.1:8000";

  // -------------------------------
  // SUMMARY (separate)
  // -------------------------------
  const loadSummary = async () => {
    try {
      setSummaryLoading(true);

      await fetch(`${API}/summary`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ doc_id: id }),
      });

      const r = await fetch(`${API}/docs/${id}/summary`);
      const d = await r.json();
      setSummary(d.summary || "");
    } catch (e) {
      console.error(e);
      alert("Failed to load summary.");
    } finally {
      setSummaryLoading(false);
    }
  };

  // -------------------------------
  // NOTES (separate, heading-wise)
  // -------------------------------
  const loadNotes = async () => {
    try {
      setNotesLoading(true);

      await fetch(`${API}/notes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ doc_id: id }),
      });

      const r = await fetch(`${API}/docs/${id}/notes`);
      const d = await r.json();
      setNotes(d.notes || null);
    } catch (e) {
      console.error(e);
      alert("Failed to load notes.");
    } finally {
      setNotesLoading(false);
    }
  };

  // -------------------------------
  // MCQ GENERATION
  // -------------------------------
  const generateMcq = async () => {
    try {
      setMcqLoading(true);
      setMcq(null);
      setMcqIndex(0);
      setMcqAnswers({});
      setMcqFeedback(null);

      await fetch(`${API}/mcq`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          doc_id: id,
          difficulty: mcqLevel,
          num: mcqNum,
        }),
      });

      const r = await fetch(`${API}/docs/${id}/mcq`);
      const data = await r.json();
      setMcq(data || {});
    } catch (e) {
      console.error(e);
      alert("Failed to generate MCQs.");
    } finally {
      setMcqLoading(false);
    }
  };

  // -------------------------------
  // FILLUPS GENERATION
  // -------------------------------
  const generateFillups = async () => {
    try {
      setFillupsLoading(true);
      setFillups(null);
      setFillIndex(0);
      setFillUserAnswers({});
      setFillFeedback(null);

      await fetch(`${API}/fillups`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          doc_id: id,
          difficulty: fillLevel,
          num: fillNum,
        }),
      });

      const r = await fetch(`${API}/docs/${id}/fillups`);
      const data = await r.json();
      setFillups(data || {});
    } catch (e) {
      console.error(e);
      alert("Failed to generate fillups.");
    } finally {
      setFillupsLoading(false);
    }
  };

  // -------------------------------
  // CHAT
  // -------------------------------
  const sendChat = async () => {
    if (!chatInput.trim()) return;

    const userMsg = chatInput;
    setChatMessages((prev) => [...prev, { role: "user", text: userMsg }]);
    setChatInput("");

    try {
      const r = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: userMsg, doc_id: id }),
      });

      const d = await r.json();
      setChatMessages((prev) => [...prev, { role: "ai", text: d.answer }]);
    } catch (e) {
      console.error(e);
      alert("Failed to send chat.");
    }
  };

  // -------------------------------
  // MCQ LOGIC
  // -------------------------------
  const currentMCQSet =
    mcq && mcq[mcqLevel]
      ? mcq[mcqLevel].slice(mcqIndex, mcqIndex + 5)
      : [];

  const submitMCQ = async () => {
    if (!mcq || !mcq[mcqLevel]) return;

    const feedback = [];
    const batchIds = currentMCQSet.map((q) => q.id);
    const answers = {};

    currentMCQSet.forEach((q) => {
      const userAnswer = mcqAnswers[q.id];
      const correct = q.answer;

      if (userAnswer) {
        answers[q.id] = userAnswer;
      }

      if (!userAnswer) {
        feedback.push({ id: q.id, result: "not answered" });
      } else if (userAnswer === correct) {
        feedback.push({
          id: q.id,
          result: "correct",
          explanation: q.explanation,
          correct,
        });
      } else {
        feedback.push({
          id: q.id,
          result: "wrong",
          explanation: q.explanation,
          correct,
        });
      }
    });

    setMcqFeedback(feedback);

    // Save to backend
    try {
      await fetch(`${API}/mcq/save-progress`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          doc_id: id,
          difficulty: mcqLevel,
          batch_ids: batchIds,
          answers,
        }),
      });
    } catch (e) {
      console.error(e);
      // don't block UI on error
    }
  };

  const nextMCQ = () => {
    setMcqFeedback(null);
    if (!mcq || !mcq[mcqLevel]) return;

    const total = mcq[mcqLevel].length;
    if (mcqIndex + 5 < total) {
      setMcqIndex(mcqIndex + 5);
    } else {
      alert("You have completed all MCQs for this difficulty.");
    }
  };

  // -------------------------------
  // FILLUPS LOGIC
  // -------------------------------
  const currentFillSet =
    fillups && fillups[fillLevel]
      ? fillups[fillLevel].slice(fillIndex, fillIndex + 5)
      : [];

  const submitFillups = async () => {
    if (!fillups || !fillups[fillLevel]) return;

    const fb = [];
    const batchIds = currentFillSet.map((q) => q.id);
    const answers = {};

    currentFillSet.forEach((q) => {
      const rawUser = (fillUserAnswers[q.id] || "").trim();
      const user = rawUser.toLowerCase();
      const correct = (q.answer || "").trim().toLowerCase();

      if (rawUser) {
        answers[q.id] = rawUser;
      }

      fb.push({
        id: q.id,
        question: q.text,
        user: rawUser,
        correct: q.answer,
        result: user === correct ? "correct" : "wrong",
      });
    });

    setFillFeedback(fb);

    // Save to backend
    try {
      await fetch(`${API}/fillups/save-progress`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          doc_id: id,
          difficulty: fillLevel,
          batch_ids: batchIds,
          answers,
        }),
      });
    } catch (e) {
      console.error(e);
    }
  };

  const nextFill = () => {
    setFillFeedback(null);
    if (!fillups || !fillups[fillLevel]) return;

    const total = fillups[fillLevel].length;
    if (fillIndex + 5 < total) {
      setFillIndex(fillIndex + 5);
    } else {
      alert("You have completed all fill-in-the-blanks for this difficulty.");
    }
  };

  return (
    <div style={{ padding: 20 }}>
      {/* CHAT */}
      <div style={{ marginBottom: 30, padding: 20, border: "1px solid #aaa" }}>
        <h3>Ask Anything</h3>

        <div style={{ maxHeight: 200, overflowY: "auto", marginBottom: 10 }}>
          {chatMessages.map((c, i) => (
            <p key={i}>
              <b>{c.role}:</b> {c.text}
            </p>
          ))}
        </div>

        <input
          value={chatInput}
          onChange={(e) => setChatInput(e.target.value)}
          placeholder="Type your question…"
          style={{ width: "70%", padding: 8, marginRight: 8 }}
        />
        <button onClick={sendChat}>Send</button>
      </div>

      {/* SUMMARY */}
      <div style={{ padding: 20, border: "1px solid black", marginBottom: 20 }}>
        <h3>Summary</h3>
        <button onClick={loadSummary}>Generate Summary</button>
        {summaryLoading && (
          <p style={{ marginTop: 8 }}><b>Generating summary...</b></p>
        )}
        {summary && !summaryLoading && (
          <p style={{ marginTop: 10 }}>{summary}</p>
        )}
      </div>

      {/* NOTES */}
      <div style={{ padding: 20, border: "1px solid black", marginBottom: 20 }}>
        <h3>Notes (Heading-wise)</h3>
        <button onClick={loadNotes}>Generate Notes</button>
        {notesLoading && (
          <p style={{ marginTop: 8 }}><b>Generating notes...</b></p>
        )}

        {notes && notes.sections && notes.sections.length > 0 && !notesLoading && (
          <div style={{ marginTop: 15 }}>
            {notes.sections.map((sec, idx) => (
              <div key={idx} style={{ marginBottom: 20 }}>
                <h4>{sec.heading}</h4>
                <p>{sec.explanation}</p>
                {sec.points && sec.points.length > 0 && (
                  <>
                    <b>Key Points:</b>
                    <ul>
                      {sec.points.map((p, i) => (
                        <li key={i}>{p}</li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* MCQ */}
      <div style={{ padding: 20, border: "1px solid black", marginBottom: 20 }}>
        <h3>MCQ Practice</h3>

        {/* Difficulty + slider */}
        <div style={{ marginBottom: 10 }}>
          <label>
            Difficulty:&nbsp;
            <select
              value={mcqLevel}
              onChange={(e) => {
                setMcqLevel(e.target.value);
                setMcqIndex(0);
                setMcqFeedback(null);
              }}
            >
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </label>
        </div>

        <div style={{ marginBottom: 10 }}>
          <label>
            Number of questions: <b>{mcqNum}</b>
          </label>
          <br />
          <input
            type="range"
            min={5}
            max={20}
            value={mcqNum}
            onChange={(e) => setMcqNum(parseInt(e.target.value, 10))}
          />
        </div>

        <button onClick={generateMcq}>Generate MCQs</button>
        {mcqLoading && (
          <p style={{ marginTop: 8 }}><b>Generating MCQs...</b></p>
        )}

        {mcq && currentMCQSet.length > 0 && !mcqLoading && (
          <div style={{ marginTop: 15 }}>
            {currentMCQSet.map((q) => (
              <div key={q.id} style={{ marginBottom: 15 }}>
                <p>
                  <b>{q.question}</b>
                </p>
                {q.options.map((op) => (
                  <label key={op}>
                    <input
                      type="radio"
                      name={q.id}
                      value={op}
                      onChange={() =>
                        setMcqAnswers({ ...mcqAnswers, [q.id]: op })
                      }
                    />
                    {op}
                    <br />
                  </label>
                ))}
                <hr />
              </div>
            ))}

            {!mcqFeedback && (
              <button onClick={submitMCQ}>Submit this batch</button>
            )}

            {mcqFeedback && (
              <div style={{ marginTop: 10 }}>
                <h4>Feedback</h4>
                {mcqFeedback.map((fb) => (
                  <div key={fb.id}>
                    <p>
                      Q {fb.id}: {fb.result.toUpperCase()}
                      {fb.correct && ` (Correct: ${fb.correct})`}
                    </p>
                    {fb.explanation && <p>Explanation: {fb.explanation}</p>}
                    <hr />
                  </div>
                ))}
                <button onClick={nextMCQ}>Next 5</button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* FILLUPS */}
      <div style={{ padding: 20, border: "1px solid black", marginBottom: 20 }}>
        <h3>Fill in the Blanks</h3>

        {/* Difficulty + slider */}
        <div style={{ marginBottom: 10 }}>
          <label>
            Difficulty:&nbsp;
            <select
              value={fillLevel}
              onChange={(e) => {
                setFillLevel(e.target.value);
                setFillIndex(0);
                setFillFeedback(null);
              }}
            >
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </label>
        </div>

        <div style={{ marginBottom: 10 }}>
          <label>
            Number of questions: <b>{fillNum}</b>
          </label>
          <br />
          <input
            type="range"
            min={5}
            max={20}
            value={fillNum}
            onChange={(e) => setFillNum(parseInt(e.target.value, 10))}
          />
        </div>

        <button onClick={generateFillups}>Generate Fillups</button>
        {fillupsLoading && (
          <p style={{ marginTop: 8 }}><b>Generating fillups...</b></p>
        )}

        {fillups && currentFillSet.length > 0 && !fillupsLoading && (
          <div style={{ marginTop: 15 }}>
            {currentFillSet.map((q) => (
              <div key={q.id} style={{ marginBottom: 15 }}>
                <p>
                  <b>{q.text}</b>
                </p>
                <input
                  type="text"
                  style={{ width: "60%", padding: 6 }}
                  onChange={(e) =>
                    setFillUserAnswers({
                      ...fillUserAnswers,
                      [q.id]: e.target.value,
                    })
                  }
                />
                <hr />
              </div>
            ))}

            {!fillFeedback && (
              <button onClick={submitFillups}>Submit this batch</button>
            )}

            {fillFeedback && (
              <div style={{ marginTop: 10 }}>
                <h4>Feedback</h4>
                {fillFeedback.map((fb) => (
                  <div key={fb.id}>
                    <p>
                      {fb.question}
                      <br />
                      Your answer: {fb.user || "(empty)"}
                      <br />
                      Result: {fb.result.toUpperCase()}
                      <br />
                      Correct: {fb.correct}
                    </p>
                    <hr />
                  </div>
                ))}
                <button onClick={nextFill}>Next 5</button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
