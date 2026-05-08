from fastapi.responses import HTMLResponse


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dropbox Prototype</title>
  <style>
    :root { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f6f7f9; color: #1f2933; }
    main { max-width: 980px; margin: 0 auto; padding: 32px 20px 56px; }
    section { background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 18px; margin-top: 18px; }
    label { display: block; font-weight: 650; margin: 12px 0 6px; }
    input, textarea { width: 100%; box-sizing: border-box; border: 1px solid #bcccdc; border-radius: 6px; padding: 10px 12px; font: inherit; }
    button, a.button { display: inline-flex; align-items: center; justify-content: center; min-height: 38px; padding: 0 14px; border-radius: 6px; border: 1px solid #0b7285; background: #0c8599; color: white; font-weight: 650; text-decoration: none; cursor: pointer; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }
    .result { background: #f8fafc; border: 1px solid #d9e2ec; border-radius: 6px; padding: 12px; margin-top: 14px; white-space: pre-wrap; overflow-wrap: anywhere; }
    @media (max-width: 720px) { .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <h1>Dropbox File Sync</h1>
    <p>Upload through a presigned URL, simulate an object-store event, share it, download it, and poll change events.</p>
    <section>
      <h2>Upload File</h2>
      <div class="row">
        <div><label>User</label><input id="user" value="alice"></div>
        <div><label>File name</label><input id="name" value="notes.txt"></div>
      </div>
      <label>File contents</label><textarea id="content" rows="4">Dropbox prototype file contents</textarea>
      <div class="actions"><button id="upload">Upload and send storage event</button><button id="download">Download current file</button></div>
      <div id="upload-result" class="result">No file uploaded yet.</div>
    </section>
    <section>
      <h2>Share and Sync</h2>
      <div class="row">
        <div><label>Share with user</label><input id="share-user" value="bob"></div>
        <div><label>Changes since event id</label><input id="since" value="0"></div>
      </div>
      <div class="actions"><button id="share">Share</button><button id="changes">Get changes</button></div>
      <div id="sync-result" class="result">Share and change events appear here.</div>
    </section>
  </main>
  <script>
    let currentFileId = "";
    const out = (id, value) => document.querySelector(id).textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
    async function json(path, options = {}) {
      const response = await fetch(path, {headers: {"content-type": "application/json", "X-User-Id": document.querySelector("#user").value}, ...options});
      const body = await response.json();
      if (!response.ok) throw body;
      return body;
    }
    document.querySelector("#upload").onclick = async () => {
      try {
        const text = document.querySelector("#content").value;
        const blob = new Blob([text], {type: "text/plain"});
        const upload = await json("/files/presigned-url", {method: "POST", body: JSON.stringify({file_metadata: {name: document.querySelector("#name").value, size: blob.size, mime_type: "text/plain", fingerprint: String(blob.size)}})});
        await fetch(upload.upload_url, {method: "PUT", body: blob});
        const done = await json("/storage/events/object-created", {method: "POST", body: JSON.stringify({object_key: upload.object_key, event_name: "ObjectCreated:Put"})});
        currentFileId = upload.file_id;
        out("#upload-result", {upload, storageEvent: done});
      } catch (error) { out("#upload-result", error); }
    };
    document.querySelector("#download").onclick = async () => {
      try {
        const file = await json(`/files/${currentFileId}`);
        const response = await fetch(file.downloadUrl);
        out("#upload-result", {file, downloadedText: await response.text()});
      } catch (error) { out("#upload-result", error); }
    };
    document.querySelector("#share").onclick = async () => {
      try { out("#sync-result", await json(`/files/${currentFileId}/share`, {method: "POST", body: JSON.stringify({users: [document.querySelector("#share-user").value]})})); }
      catch (error) { out("#sync-result", error); }
    };
    document.querySelector("#changes").onclick = async () => {
      try { out("#sync-result", await json(`/files/changes?since=${encodeURIComponent(document.querySelector("#since").value)}`)); }
      catch (error) { out("#sync-result", error); }
    };
  </script>
</body>
</html>
"""


def ui_response() -> HTMLResponse:
    return HTMLResponse(HTML)
