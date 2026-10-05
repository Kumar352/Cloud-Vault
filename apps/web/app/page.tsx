"use client";

import { Fragment, useCallback, useEffect, useState } from "react";

type Identity = { user_id: string; email: string };
type FileRow = {
  id: string;
  name: string;
  owner_id: string;
  access: string;
  version: number;
  version_id: string;
  size_bytes: number;
  scan_state: string;
  version_created: string;
};
type AuditRow = { id: number; action: string; resource_id: string | null; created_at: string };
type Citation = { filename: string; version: number; chunk: number };
type ShareRow = { user_id: string; email: string; permission: string; created_at: string };
type VersionRow = { id: string; version: number; size_bytes: number; sha256: string; scan_state: string; scan_detail: string | null; created_at: string };
type Answer = { answer: string; mode: string; citations: Citation[] };
type Finding = { id: string; score: number; reasons: string[]; event_count: number; created_at: string };
type Analysis = { model: string; score: number; event_count: number; finding_created: boolean; action: string; findings: Finding[] };

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const issuer = process.env.NEXT_PUBLIC_OIDC_ISSUER ?? "http://localhost:5556/dex";

async function request<T>(token: string, path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    headers: { Accept: "application/json", Authorization: `Bearer ${token}`, ...init.headers },
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({})) as { detail?: string };
    throw new Error(detail.detail ?? `Request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function base64Url(bytes: Uint8Array): string {
  let binary = "";
  bytes.forEach((byte) => (binary += String.fromCharCode(byte)));
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function prettyDate(value: string): string {
  return new Date(value).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}

function prettySize(bytes: number): string {
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [health, setHealth] = useState("Checking local services…");
  const [files, setFiles] = useState<FileRow[]>([]);
  const [events, setEvents] = useState<AuditRow[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [shareFile, setShareFile] = useState<string | null>(null);
  const [shares, setShares] = useState<ShareRow[]>([]);
  const [shareEmail, setShareEmail] = useState("bob@example.test");
  const [versionFile, setVersionFile] = useState<string | null>(null);
  const [versions, setVersions] = useState<VersionRow[]>([]);
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState("");

  const refresh = useCallback(async (activeToken: string) => {
    try {
      const [me, listedFiles, listedEvents] = await Promise.all([
        request<Identity>(activeToken, "/auth/me"),
        request<FileRow[]>(activeToken, "/files"),
        request<AuditRow[]>(activeToken, "/audit?limit=8"),
      ]);
      setIdentity(me);
      setFiles(listedFiles);
      setEvents(listedEvents);
      setHealth("API and identity ready");
    } catch (error) {
      if (error instanceof Error && /401|Invalid or expired/.test(error.message)) {
        sessionStorage.removeItem("cloudvault_access_token");
        setToken(null);
      }
      setHealth(error instanceof Error ? error.message : "Local API unavailable");
    }
  }, []);

  useEffect(() => {
    const stored = sessionStorage.getItem("cloudvault_access_token");
    const expires = Number(sessionStorage.getItem("cloudvault_token_expires") ?? 0);
    if (stored && expires > Date.now()) setToken(stored);
    fetch(`${apiBase}/health`).then((response) => {
      if (response.ok) setHealth("Local API online");
      else setHealth("Local API not ready");
    }).catch(() => setHealth("Start the local API to begin"));
  }, []);

  useEffect(() => {
    if (token) void refresh(token);
  }, [token, refresh]);

  async function signIn() {
    try {
      const state = base64Url(crypto.getRandomValues(new Uint8Array(24)));
      const verifier = base64Url(crypto.getRandomValues(new Uint8Array(32)));
      const challengeBytes = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
      const challenge = base64Url(new Uint8Array(challengeBytes));
      sessionStorage.setItem("cloudvault_oidc_state", state);
      sessionStorage.setItem("cloudvault_pkce_verifier", verifier);
      const params = new URLSearchParams({
        client_id: "cloudvault-api",
        redirect_uri: `${window.location.origin}/auth/callback`,
        response_type: "code",
        scope: "openid profile email",
        state,
        code_challenge: challenge,
        code_challenge_method: "S256",
      });
      window.location.assign(`${issuer}/auth?${params.toString()}`);
    } catch {
      setNotice("Sign-in needs a secure local browser context and an available Dex service.");
    }
  }

  function signOut() {
    sessionStorage.removeItem("cloudvault_access_token");
    sessionStorage.removeItem("cloudvault_token_expires");
    setToken(null);
    setIdentity(null);
    setFiles([]);
    setEvents([]);
    setAnswer(null);
    setAnalysis(null);
    setNotice("Signed out of this browser session.");
  }

  async function upload() {
    if (!token || !selectedFile) return;
    setBusy("upload"); setNotice("");
    try {
      const result = await request<{ scan_state: string; message: string }>(token, "/files", {
        method: "POST",
        headers: { "Content-Type": selectedFile.type || "application/octet-stream", "X-File-Name": encodeURIComponent(selectedFile.name) },
        body: selectedFile,
      });
      setNotice(result.message);
      setSelectedFile(null);
      const input = document.getElementById("file-picker") as HTMLInputElement | null;
      if (input) input.value = "";
      await refresh(token);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Upload failed"); }
    finally { setBusy(""); }
  }

  async function download(file: FileRow) {
    if (!token) return;
    setBusy(`download:${file.id}`); setNotice("");
    try {
      const response = await fetch(`${apiBase}/files/${file.id}/download`, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) throw new Error((await response.json()).detail ?? "Download unavailable");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a"); anchor.href = url; anchor.download = file.name; anchor.click(); URL.revokeObjectURL(url);
      await refresh(token);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Download failed"); }
    finally { setBusy(""); }
  }

  async function manageShares(file: FileRow) {
    if (!token) return;
    if (shareFile === file.id) { setShareFile(null); return; }
    try {
      setShares(await request<ShareRow[]>(token, `/files/${file.id}/shares`));
      setShareFile(file.id);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Could not load sharing settings"); }
  }

  async function addShare() {
    if (!token || !shareFile) return;
    try {
      await request(token, `/files/${shareFile}/shares`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: shareEmail, permission: "read" }),
      });
      setShares(await request<ShareRow[]>(token, `/files/${shareFile}/shares`));
      setNotice("Read access granted.");
      await refresh(token);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Sharing failed"); }
  }

  async function revokeShare(userId: string) {
    if (!token || !shareFile) return;
    try {
      await request<void>(token, `/files/${shareFile}/shares/${userId}`, { method: "DELETE" });
      setShares(await request<ShareRow[]>(token, `/files/${shareFile}/shares`));
      setNotice("File access revoked.");
      await refresh(token);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Could not revoke access"); }
  }

  async function showVersions(file: FileRow) {
    if (!token) return;
    if (versionFile === file.id) { setVersionFile(null); return; }
    try {
      setVersions(await request<VersionRow[]>(token, `/files/${file.id}/versions`));
      setVersionFile(file.id);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Could not load versions"); }
  }

  async function retryScan(versionId: string) {
    if (!token) return;
    try {
      await request(token, `/versions/${versionId}/retry-scan`, { method: "POST" });
      setNotice("Scan added back to the local queue.");
      await refresh(token);
      if (versionFile) setVersions(await request<VersionRow[]>(token, `/files/${versionFile}/versions`));
    } catch (error) { setNotice(error instanceof Error ? error.message : "Could not retry the scan"); }
  }

  async function removeFile(file: FileRow) {
    if (!token || !window.confirm(`Permanently delete ${file.name} and all of its versions from this local vault?`)) return;
    try {
      await request<void>(token, `/files/${file.id}`, { method: "DELETE" });
      setNotice("File and its local versions were deleted.");
      if (shareFile === file.id) setShareFile(null);
      if (versionFile === file.id) setVersionFile(null);
      await refresh(token);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Could not delete this file"); }
  }

  async function ask() {
    if (!token || question.trim().length < 2) return;
    setBusy("assistant"); setAnswer(null); setNotice("");
    try {
      setAnswer(await request<Answer>(token, "/assistant/ask", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question }),
      }));
      await refresh(token);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Assistant request failed"); }
    finally { setBusy(""); }
  }

  async function analyze() {
    if (!token) return;
    setBusy("analysis"); setNotice("");
    try {
      setAnalysis(await request<Analysis>(token, "/analytics/analyze", { method: "POST" }));
      await refresh(token);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Analysis failed"); }
    finally { setBusy(""); }
  }

  return (
    <main className="workspace">
      <aside className="sidebar">
        <a className="wordmark" href="#top"><span className="brand-mark">C</span><span>cloudvault<span className="wordmark-dot">.</span></span></a>
        <p className="side-label">Workspace</p>
        <a className="side-link active" href="#files"><span>▦</span> My files</a>
        <a className="side-link" href="#assistant"><span>✳</span> AI assistant</a>
        <a className="side-link" href="#activity"><span>◷</span> Activity</a>
        <div className="side-bottom">
          <div className="local-badge"><span className="pulse-dot" /> Local environment</div>
          <p>This app uses local services only.</p>
          {identity && <button className="side-signout" onClick={signOut}>Sign out</button>}
        </div>
      </aside>

      <section className="main-column" id="top">
        <header className="topbar">
          <div className="breadcrumb">CloudVault <span>/</span> Overview</div>
          <div className="account-area">
            <span className={`api-state ${health.includes("ready") || health.includes("online") ? "api-good" : ""}`}><i />{health}</span>
            {identity ? <><span className="user-chip">{identity.email}</span><button className="avatar" aria-label="Sign out" onClick={signOut}>{identity.user_id.slice(0, 1).toUpperCase()}</button></> : <button className="button button-dark button-small" onClick={signIn}>Sign in</button>}
          </div>
        </header>

        <div className="content">
          <section className="welcome-row">
            <div><p className="eyebrow">Your secure workspace</p><h1>Good to see you{identity ? `, ${identity.user_id}` : ""}<span className="period">.</span></h1><p className="subtitle">Files stay private, scanned, and ready when you are.</p></div>
            <div className="local-note"><span>◉</span><div><strong>Local-first mode</strong><small>Data stays on this computer</small></div></div>
          </section>

          {notice && <div className="notice" role="status"><span>{notice}</span><button onClick={() => setNotice("")} aria-label="Dismiss">×</button></div>}

          {!identity ? (
            <section className="signin-panel">
              <div className="signin-art"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="vault-glyph">C</div></div>
              <div><p className="eyebrow">Private by design</p><h2>Everything in its right place.</h2><p>Sign in with one of the local demo accounts to try secure uploads, file sharing, and your AI assistant.</p><button className="button button-green" onClick={signIn}>Continue with local identity <span>→</span></button><small className="demo-hint">Demo users: alice@example.test or bob@example.test · password: password</small></div>
            </section>
          ) : (
            <>
              <section className="stats-grid" aria-label="Workspace summary">
                <article className="stat-card"><span className="stat-icon icon-lilac">▤</span><p>Files in workspace</p><strong>{files.length.toString().padStart(2, "0")}</strong><small>Across your shared vault</small></article>
                <article className="stat-card"><span className="stat-icon icon-mint">✓</span><p>Scanned &amp; clean</p><strong>{files.filter((file) => file.scan_state === "clean").length.toString().padStart(2, "0")}</strong><small>Available for safe download</small></article>
                <article className="stat-card"><span className="stat-icon icon-amber">◷</span><p>Waiting for scan</p><strong>{files.filter((file) => ["queued", "scanning"].includes(file.scan_state)).length.toString().padStart(2, "0")}</strong><small>Quarantined until cleared</small></article>
              </section>

              <section className="panel files-panel" id="files">
                <div className="panel-heading"><div><p className="eyebrow">Secure storage</p><h2>Your files <span className="count-pill">{files.length}</span></h2></div><div className="upload-control"><label htmlFor="file-picker" className="button button-outline">{selectedFile ? selectedFile.name : "Choose a file"}</label><input id="file-picker" type="file" onChange={(event) => setSelectedFile(event.currentTarget.files?.[0] ?? null)} /><button className="button button-green" disabled={!selectedFile || busy === "upload"} onClick={() => void upload()}>{busy === "upload" ? "Uploading…" : "Upload file"}</button></div></div>
                <p className="panel-subtitle">Every upload starts in quarantine and stays unavailable until the scanner clears it. Maximum size 10 MB.</p>
                {files.length ? (
                  <div className="file-list">
                    <div className="file-list-head"><span>Name</span><span>Version</span><span>Scan status</span><span>Access</span><span>Added</span><span /></div>
                    {files.map((file) => (
                      <Fragment key={file.id}>
                      <div className="file-row">
                        <div className="file-name"><span className="file-icon">{file.name.split(".").pop()?.slice(0, 3).toUpperCase() || "FILE"}</span><div><strong>{file.name}</strong><small>{prettySize(file.size_bytes)}</small></div></div>
                        <span className="version-label">v{file.version}</span>
                        <span className={`scan-label scan-${file.scan_state}`}>{file.scan_state === "clean" ? "✓ Clean" : file.scan_state === "infected" ? "! Quarantined" : file.scan_state === "error" ? "! Scan issue" : "◷ Scanning"}</span>
                        <span className="access-label">{file.access === "owner" ? "Owner" : `Shared · ${file.access}`}</span>
                        <span className="date-label">{prettyDate(file.version_created)}</span>
                        <div className="row-actions">
                          <button title="Download clean version" disabled={file.scan_state !== "clean" || busy === `download:${file.id}`} onClick={() => void download(file)}>↓</button>
                          <button title="Version history" onClick={() => void showVersions(file)}>▤</button>
                          {file.access === "owner" && <><button title="Manage sharing" onClick={() => void manageShares(file)}>↗</button><button title="Delete file and versions" onClick={() => void removeFile(file)}>×</button></>}
                        </div>
                      </div>
                      {versionFile === file.id && <div className="version-history">{versions.map((version) => <div className="version-entry" key={version.id}><span>v{version.version}</span><span>{prettySize(version.size_bytes)}</span><span className={`scan-label scan-${version.scan_state}`}>{version.scan_state}</span><code>{version.sha256.slice(0, 12)}…</code><span>{prettyDate(version.created_at)}</span>{file.access === "owner" && version.scan_state === "error" && <button className="text-button" onClick={() => void retryScan(version.id)}>Retry scan</button>}</div>)}</div>}
                      </Fragment>
                    ))}
                    {shareFile && <div className="sharing-box"><div className="sharing-title"><strong>Manage access</strong><button className="text-button" onClick={() => setShareFile(null)}>Close</button></div><div className="share-add"><label htmlFor="share-email">Local account email</label><input id="share-email" value={shareEmail} onChange={(event) => setShareEmail(event.currentTarget.value)} /><button className="button button-green" onClick={() => void addShare()}>Grant read access</button></div>{shares.length ? shares.map((share) => <div className="share-row" key={share.user_id}><span>{share.email}<small>{share.permission} access</small></span><button className="text-button" onClick={() => void revokeShare(share.user_id)}>Revoke</button></div>) : <p className="share-empty">No one else has access to this file.</p>}</div>}
                  </div>
                ) : <div className="empty-state"><div className="empty-icon">▤</div><strong>Your vault is ready</strong><p>Choose a small synthetic file to start. It will be encrypted and quarantined until the local scanner approves it.</p></div>}
                <div className="storage-footnote"><span>⌑</span> AES-GCM encrypted on this device <span className="foot-separator">·</span> versioned <span className="foot-separator">·</span> private until scanned</div>
              </section>

              <div className="lower-grid">
                <section className="panel assistant-panel" id="assistant"><div className="panel-heading"><div><p className="eyebrow">Ask your files</p><h2>Vault assistant <span className="ai-pill">AI</span></h2></div><span className="sparkle">✳</span></div><p className="panel-subtitle">Answers use only clean files you can access, with a citation for every source.</p><label className="sr-only" htmlFor="question">Ask a question about your files</label><textarea id="question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="What does my project plan say about security?" maxLength={1000} /><div className="assistant-foot"><span>Local Ollama if available · grounded mock otherwise</span><button className="button button-dark" disabled={!question.trim() || busy === "assistant"} onClick={() => void ask()}>{busy === "assistant" ? "Thinking…" : "Ask assistant →"}</button></div>{answer && <div className="answer-card"><div className="answer-mode">{answer.mode === "ollama" ? "Local model" : "Grounded demo response"}</div><p>{answer.answer}</p>{answer.citations.length > 0 && <div className="citations"><strong>Sources</strong>{answer.citations.map((citation, index) => <span key={`${citation.filename}-${index}`}>[{index + 1}] {citation.filename} · v{citation.version} · section {citation.chunk}</span>)}</div>}</div>}</section>
                <section className="panel activity-panel" id="activity"><div className="panel-heading"><div><p className="eyebrow">Security overview</p><h2>Recent activity</h2></div><button className="text-button" onClick={() => token && void refresh(token)}>Refresh</button></div><p className="panel-subtitle">Actions for your account. File contents and tokens are never logged.</p>{events.length ? <div className="activity-list">{events.map((event) => <div className="activity-row" key={event.id}><span className="activity-dot" /><div><strong>{event.action.replaceAll(".", " · ").replaceAll("_", " ")}</strong><small>{event.resource_id ? `File ${event.resource_id.slice(0, 8)}` : "Your account"}</small></div><time>{new Date(event.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</time></div>)}</div> : <div className="empty-activity">Your security activity will appear here.</div>}</section>
              </div>

              <section className="panel detection-panel"><div className="detection-copy"><span className="detection-icon">⌁</span><div><p className="eyebrow">Explainable security</p><h2>Unusual activity review</h2><p>A local Isolation Forest looks for surprising activity patterns. Findings are for human review and never block or delete files.</p></div></div><button className="button button-outline" disabled={busy === "analysis"} onClick={() => void analyze()}>{busy === "analysis" ? "Reviewing…" : "Analyze recent activity"}</button>{analysis && <div className="analysis-result"><div><span className="result-label">Anomaly score</span><strong>{analysis.score.toFixed(3)}</strong></div><div><span className="result-label">Events reviewed</span><strong>{analysis.event_count}</strong></div><div className="analysis-explanation">{analysis.finding_created ? "Flagged for your review. " : "No review alert from this sample. "}{analysis.action}{analysis.findings.flatMap((finding) => finding.reasons).slice(0, 2).map((reason) => <p key={reason}>{reason}</p>)}</div></div>}</section>
            </>
          )}

          <footer className="page-footer"><span>CloudVault 2.0 · Phase 1 local portfolio build</span><span>Local data only · AWS and Vercel are off</span></footer>
        </div>
      </section>
    </main>
  );
}
