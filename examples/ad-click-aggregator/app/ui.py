from fastapi.responses import HTMLResponse


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ad Click Aggregator Prototype</title>
  <style>
    :root { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f6f7f9; color: #1f2933; }
    main { max-width: 920px; margin: 0 auto; padding: 32px 20px 56px; }
    section { background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 18px; margin-top: 18px; }
    label { display: block; font-weight: 650; margin: 12px 0 6px; }
    input, select { width: 100%; box-sizing: border-box; border: 1px solid #bcccdc; border-radius: 6px; padding: 10px 12px; font: inherit; }
    button, a.button { display: inline-flex; align-items: center; justify-content: center; min-height: 38px; padding: 0 14px; border-radius: 6px; border: 1px solid #d9480f; background: #f76707; color: white; font-weight: 650; text-decoration: none; cursor: pointer; }
    .row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }
    .result { background: #f8fafc; border: 1px solid #d9e2ec; border-radius: 6px; padding: 12px; margin-top: 14px; white-space: pre-wrap; overflow-wrap: anywhere; }
    @media (max-width: 720px) { .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <h1>Ad Click Aggregator</h1>
    <p>Queue click redirects, process events into minute buckets, and query aggregated metrics.</p>
    <section>
      <div class="row">
        <div><label>Ad</label><select id="ad"><option>ad-1</option><option>ad-2</option></select></div>
        <div><label>User</label><input id="user" value="alice"></div>
        <div><label>Click id</label><input id="click" value="manual-1"></div>
      </div>
      <div class="actions"><a id="click-link" class="button" target="_blank" rel="noreferrer">Open tracked click</a><button id="process">Process queue</button><button id="metrics">Get metrics</button></div>
      <div id="result" class="result">Metrics appear here.</div>
    </section>
  </main>
  <script>
    const out = (value) => document.querySelector("#result").textContent = JSON.stringify(value, null, 2);
    const link = document.querySelector("#click-link");
    function updateLink() { link.href = `/click/${encodeURIComponent(document.querySelector("#ad").value)}?click_id=${encodeURIComponent(document.querySelector("#click").value)}&user_id=${encodeURIComponent(document.querySelector("#user").value)}`; }
    document.querySelectorAll("input,select").forEach((element) => element.addEventListener("input", updateLink));
    updateLink();
    async function json(path, options = {}) {
      const response = await fetch(path, options);
      const body = await response.json();
      if (!response.ok) throw body;
      return body;
    }
    document.querySelector("#process").onclick = async () => { try { out(await json("/processor/tick?limit=100", {method: "POST"})); } catch (error) { out(error); } };
    document.querySelector("#metrics").onclick = async () => { try { out(await json(`/metrics?ad_id=${encodeURIComponent(document.querySelector("#ad").value)}`)); } catch (error) { out(error); } };
  </script>
</body>
</html>
"""


def ui_response() -> HTMLResponse:
    return HTMLResponse(HTML)
