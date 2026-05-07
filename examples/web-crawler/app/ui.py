from fastapi.responses import HTMLResponse


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Web Crawler Prototype</title>
  <style>
    :root { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f6f7f9; color: #1f2933; }
    main { max-width: 920px; margin: 0 auto; padding: 32px 20px 56px; }
    section { background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 18px; margin-top: 18px; }
    label { display: block; font-weight: 650; margin: 12px 0 6px; }
    input, textarea { width: 100%; box-sizing: border-box; border: 1px solid #bcccdc; border-radius: 6px; padding: 10px 12px; font: inherit; }
    button { min-height: 38px; padding: 0 14px; border-radius: 6px; border: 1px solid #5f3dc4; background: #7048e8; color: white; font-weight: 650; cursor: pointer; }
    .row { display: grid; grid-template-columns: 2fr 1fr; gap: 14px; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }
    .result { background: #f8fafc; border: 1px solid #d9e2ec; border-radius: 6px; padding: 12px; margin-top: 14px; white-space: pre-wrap; overflow-wrap: anywhere; }
    @media (max-width: 720px) { .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <h1>Web Crawler</h1>
    <p>Create a crawl job from fixture URLs, tick the workers, and inspect discovered pages.</p>
    <section>
      <div class="row">
        <div><label>Seed URLs, one per line</label><textarea id="seeds" rows="4">https://example.test/</textarea></div>
        <div><label>Max pages</label><input id="max" type="number" value="4" min="1"></div>
      </div>
      <div class="actions"><button id="create">Create job</button><button id="tick">Tick crawler</button><button id="load">Load job</button></div>
      <div id="result" class="result">No crawl job yet.</div>
    </section>
  </main>
  <script>
    let jobId = "";
    const out = (value) => document.querySelector("#result").textContent = JSON.stringify(value, null, 2);
    async function json(path, options = {}) {
      const response = await fetch(path, {headers: {"content-type": "application/json"}, ...options});
      const body = await response.json();
      if (!response.ok) throw body;
      return body;
    }
    document.querySelector("#create").onclick = async () => {
      try {
        const seeds = document.querySelector("#seeds").value.split("\\n").map((line) => line.trim()).filter(Boolean);
        const body = await json("/crawl-jobs", {method: "POST", body: JSON.stringify({seeds, max_pages: Number(document.querySelector("#max").value)})});
        jobId = body.jobId;
        out(body);
      } catch (error) { out(error); }
    };
    document.querySelector("#tick").onclick = async () => { try { out(await json(`/crawl-jobs/${jobId}/tick?limit=4`, {method: "POST"})); } catch (error) { out(error); } };
    document.querySelector("#load").onclick = async () => { try { out(await json(`/crawl-jobs/${jobId}`)); } catch (error) { out(error); } };
  </script>
</body>
</html>
"""


def ui_response() -> HTMLResponse:
    return HTMLResponse(HTML)
