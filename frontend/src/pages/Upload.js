import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function Upload() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const nav = useNavigate();

  const uploadPDF = async () => {
    if (!file) return;

    const fd = new FormData();
    fd.append("file", file);

    setLoading(true);

    const r = await fetch("http://127.0.0.1:8000/upload", {
      method: "POST",
      body: fd,
    });

    const d = await r.json();
    setLoading(false);

    if (d.status === "ok") {
      nav(`/dashboard/${d.doc_id}`);
    }
  };

  return (
    <div style={{ padding: 30 }}>
      <h2>Upload PDF</h2>
      <input type="file" onChange={(e) => setFile(e.target.files[0])} />
      <br />
      <button onClick={uploadPDF} disabled={!file || loading}>
        {loading ? "Processing..." : "Upload"}
      </button>
    </div>
  );
}
