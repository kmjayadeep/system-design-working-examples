from fastapi.responses import HTMLResponse


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Rate Limiter Prototype</title>
  <style>
    :root { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f6f7f9; color: #1f2933; }
    main { max-width: 920px; margin: 0 auto; padding: 32px 20px 56px; }
    section { background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 18px; margin-top: 18px; }
    label { display: block; font-weight: 650; margin: 12px 0 6px; }
    input { width: 100%; box-sizing: border-box; border: 1px solid #bcccdc; border-radius: 6px; padding: 10px 12px; font: inherit; }
    button { min-height: 38px; padding: 0 14px; border-radius: 6px; border: 1px solid #5f3dc4; background: #7048e8; color: white; font-weight: 650; cursor: pointer; }
    .row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }
    .result { background: #f8fafc; border: 1px solid #d9e2ec; border-radius: 6px; padding: 12px; margin-top: 14px; white-space: pre-wrap; overflow-wrap: anywhere; }
    @media (max-width: 720px) { .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <h1>Distributed Rate Limiter</h1>
    <p>Create token bucket rules and check requests through multiple API replicas sharing Redis state.</p>
    <section>
      <div class="row">
        <div><label>Rule id</label><input id="rule" value="search"></div>
        <div><label>Capacity</label><input id="capacity" type="number" value="3"></div>
        <div><label>Refill / second</label><input id="refill" type="number" value="1"></div>
      </div>
      <div class="row">
        <div><label>Client id</label><input id="client" value="alice"></div>
      </div>
      <div class="actions"><button id="save">Save rule</button><button id="check">Check request</button><button id="burst">Burst 5</button><button id="reset">Reset buckets</button></div>
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
    const rule = () => document.querySelector("#rule").value;
    const client = () => document.querySelector("#client").value;
    document.querySelector("#save").onclick = async () => { try { out(await json("/rules", {method: "POST", body: JSON.stringify({rule_id: rule(), capacity: Number(document.querySelector("#capacity").value), refill_per_second: Number(document.querySelector("#refill").value)})})); } catch (error) { out(error); } };
    document.querySelector("#check").onclick = async () => { try { out(await json(`/check?client_id=${encodeURIComponent(client())}&rule_id=${encodeURIComponent(rule())}`, {method: "POST"})); } catch (error) { out(error); } };
    document.querySelector("#burst").onclick = async () => { try { const results = []; for (let i = 0; i < 5; i++) results.push(await json(`/check?client_id=${encodeURIComponent(client())}&rule_id=${encodeURIComponent(rule())}`, {method: "POST"})); out(results); } catch (error) { out(error); } };
    document.querySelector("#reset").onclick = async () => { try { out(await json("/reset", {method: "POST"})); } catch (error) { out(error); } };
  </script>
</body>
</html>
"""


def ui_response() -> HTMLResponse:
    return HTMLResponse(HTML)
