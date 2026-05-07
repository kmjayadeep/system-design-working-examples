from fastapi.responses import HTMLResponse


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>YouTube Prototype</title>
  <style>
    :root { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f6f7f9; color: #1f2933; }
    main { max-width: 980px; margin: 0 auto; padding: 32px 20px 56px; }
    section { background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 18px; margin-top: 18px; }
    label { display: block; font-weight: 650; margin: 12px 0 6px; }
    input, textarea { width: 100%; box-sizing: border-box; border: 1px solid #bcccdc; border-radius: 6px; padding: 10px 12px; font: inherit; }
    button { min-height: 38px; padding: 0 14px; border-radius: 6px; border: 1px solid #c92a2a; background: #e03131; color: white; font-weight: 650; cursor: pointer; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }
    .result { background: #f8fafc; border: 1px solid #d9e2ec; border-radius: 6px; padding: 12px; margin-top: 14px; white-space: pre-wrap; overflow-wrap: anywhere; }
    @media (max-width: 720px) { .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <h1>YouTube Video Streaming</h1>
    <p>Upload bytes through a presigned URL, complete processing, then fetch the manifest and adaptive segment URLs.</p>
    <section>
      <div class="row">
        <div><label>User</label><input id="user" value="alice"></div>
        <div><label>Title</label><input id="title" value="System Design Walkthrough"></div>
      </div>
      <label>Description</label><input id="description" value="A local demo video">
      <label>Video bytes</label><textarea id="content" rows="4">fake video bytes for adaptive streaming demo</textarea>
      <div class="actions"><button id="upload">Upload and process</button><button id="load">Load playback metadata</button></div>
      <div id="result" class="result">No video uploaded yet.</div>
    </section>
  </main>
  <script>
    let currentVideoId = "";
    const out = (value) => document.querySelector("#result").textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
    async function json(path, options = {}) {
      const response = await fetch(path, {headers: {"content-type": "application/json", "X-User-Id": document.querySelector("#user").value}, ...options});
      const body = await response.json();
      if (!response.ok) throw body;
      return body;
    }
    document.querySelector("#upload").onclick = async () => {
      try {
        const blob = new Blob([document.querySelector("#content").value.repeat(64)], {type: "application/octet-stream"});
        const upload = await json("/videos/presigned-url", {method: "POST", body: JSON.stringify({video_metadata: {title: document.querySelector("#title").value, description: document.querySelector("#description").value, size: blob.size}})});
        await fetch(upload.uploadUrl, {method: "PUT", body: blob});
        const completed = await json(`/videos/${upload.videoId}/complete`, {method: "POST"});
        currentVideoId = upload.videoId;
        out({upload, completed});
      } catch (error) { out(error); }
    };
    document.querySelector("#load").onclick = async () => {
      try { out(await json(`/videos/${currentVideoId}`)); }
      catch (error) { out(error); }
    };
  </script>
</body>
</html>
"""


def ui_response() -> HTMLResponse:
    return HTMLResponse(HTML)
