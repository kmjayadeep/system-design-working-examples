from fastapi.responses import HTMLResponse


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>YouTube Top K Prototype</title>
  <style>
    :root { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f7f7f5; color: #1f2933; }
    main { max-width: 920px; margin: 0 auto; padding: 32px 20px 56px; }
    section { background: white; border: 1px solid #d8dee4; border-radius: 8px; padding: 18px; margin-top: 18px; }
    label { display: block; font-weight: 650; margin: 12px 0 6px; }
    input, select { width: 100%; box-sizing: border-box; border: 1px solid #b8c2cc; border-radius: 6px; padding: 10px 12px; font: inherit; }
    button { min-height: 38px; padding: 0 14px; border-radius: 6px; border: 1px solid #b91c1c; background: #dc2626; color: white; font-weight: 650; cursor: pointer; }
    .row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }
    .result { background: #f8fafc; border: 1px solid #d8dee4; border-radius: 6px; padding: 12px; margin-top: 14px; white-space: pre-wrap; overflow-wrap: anywhere; }
    @media (max-width: 760px) { .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <h1>YouTube Top K</h1>
    <p>Ingest view events and query exact top videos for all-time or tumbling hour, day, and month windows.</p>
    <section>
      <div class="row">
        <div><label>Video id</label><input id="video" value="video-a"></div>
        <div><label>Count</label><input id="count" type="number" min="1" value="1"></div>
        <div><label>Window</label><select id="window"><option value="all">All time</option><option value="hour">Hour</option><option value="day">Day</option><option value="month">Month</option></select></div>
        <div><label>K</label><input id="k" type="number" min="1" max="1000" value="10"></div>
      </div>
      <label>Timestamp</label><input id="at" value="2026-05-07T13:45:00Z">
      <div class="actions"><button id="view">Record view</button><button id="top">Top K</button><button id="reset">Reset</button></div>
      <div id="result" class="result">Results appear here.</div>
    </section>
  </main>
  <script>
    const out = (value) => document.querySelector("#result").textContent = JSON.stringify(value, null, 2);
    async function json(path, options = {}) {
      const response = await fetch(path, {headers: {"content-type": "application/json"}, ...options});
      const body = await response.json();
      if (!response.ok) throw body;
      return body;
    }
    document.querySelector("#view").onclick = async () => {
      try {
        out(await json("/views", {method: "POST", body: JSON.stringify({videoId: document.querySelector("#video").value, count: Number(document.querySelector("#count").value), viewedAt: document.querySelector("#at").value})}));
      } catch (error) { out(error); }
    };
    document.querySelector("#top").onclick = async () => {
      try {
        const windowName = encodeURIComponent(document.querySelector("#window").value);
        const k = encodeURIComponent(document.querySelector("#k").value);
        const at = encodeURIComponent(document.querySelector("#at").value);
        out(await json(`/views/top-k?window=${windowName}&k=${k}&at=${at}`));
      } catch (error) { out(error); }
    };
    document.querySelector("#reset").onclick = async () => { try { out(await json("/reset", {method: "POST"})); } catch (error) { out(error); } };
  </script>
</body>
</html>
"""


def ui_response() -> HTMLResponse:
    return HTMLResponse(HTML)
