"use client";

import { useState } from "react";

export default function UploadBox() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<string>("");

  async function upload() {
    if (!file) {
      setStatus("Please select a file first.");
      return;
    }
    const form = new FormData();
    form.append("file", file);
    setStatus("Uploading...");
    try {
      const res = await fetch("http://localhost:8000/upload", {
        method: "POST",
        body: form,
      });
      const data = await res.json();
      setStatus(`Done! Total variants: ${data.total_variants}`);
    } catch (e) {
      setStatus("Upload failed. Is the backend running on :8000?");
    }
  }

  return (
    <div style={{ border: "1px solid #ccc", padding: "1.5rem", borderRadius: 8 }}>
      <input
        type="file"
        accept=".vcf,.vcf.gz"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
      <button onClick={upload} style={{ marginLeft: 8 }}>
        Analyze
      </button>
      {status && <p style={{ marginTop: 12, color: "#555" }}>{status}</p>}
    </div>
  );
}
