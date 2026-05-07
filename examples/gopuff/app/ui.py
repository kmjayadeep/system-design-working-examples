from fastapi.responses import HTMLResponse


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GoPuff Prototype</title>
  <style>
    :root { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f6f7f9; color: #1f2933; }
    main { max-width: 920px; margin: 0 auto; padding: 32px 20px 56px; }
    section { background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 18px; margin-top: 18px; }
    label { display: block; font-weight: 650; margin: 12px 0 6px; }
    input, select { width: 100%; box-sizing: border-box; border: 1px solid #bcccdc; border-radius: 6px; padding: 10px 12px; font: inherit; }
    button { min-height: 38px; padding: 0 14px; border-radius: 6px; border: 1px solid #2f9e44; background: #37b24d; color: white; font-weight: 650; cursor: pointer; }
    .row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }
    .result { background: #f8fafc; border: 1px solid #d9e2ec; border-radius: 6px; padding: 12px; margin-top: 14px; white-space: pre-wrap; overflow-wrap: anywhere; }
    @media (max-width: 720px) { .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <h1>GoPuff Local Delivery</h1>
    <p>Check nearby inventory, place an order, and see cache invalidation after inventory changes.</p>
    <section>
      <div class="row">
        <div><label>User</label><input id="user" value="alice"></div>
        <div><label>Latitude</label><input id="lat" value="37.7749"></div>
        <div><label>Longitude</label><input id="lon" value="-122.4194"></div>
      </div>
      <div class="row">
        <div><label>Item</label><select id="item"><option>cheetos</option><option>sparkling-water</option><option>battery-aa</option></select></div>
        <div><label>Quantity</label><input id="qty" type="number" min="1" value="1"></div>
      </div>
      <div class="actions"><button id="availability">Check availability</button><button id="order">Place order</button></div>
      <div id="result" class="result">Results appear here.</div>
    </section>
  </main>
  <script>
    const out = (value) => document.querySelector("#result").textContent = JSON.stringify(value, null, 2);
    const params = () => `latitude=${encodeURIComponent(document.querySelector("#lat").value)}&longitude=${encodeURIComponent(document.querySelector("#lon").value)}&item_id=${encodeURIComponent(document.querySelector("#item").value)}`;
    async function json(path, options = {}) {
      const response = await fetch(path, {headers: {"content-type": "application/json", "X-User-Id": document.querySelector("#user").value}, ...options});
      const body = await response.json();
      if (!response.ok) throw body;
      return body;
    }
    document.querySelector("#availability").onclick = async () => { try { out(await json(`/availability?${params()}`)); } catch (error) { out(error); } };
    document.querySelector("#order").onclick = async () => {
      try {
        out(await json("/orders", {method: "POST", body: JSON.stringify({latitude: Number(document.querySelector("#lat").value), longitude: Number(document.querySelector("#lon").value), items: [{item_id: document.querySelector("#item").value, quantity: Number(document.querySelector("#qty").value)}]})}));
      } catch (error) { out(error); }
    };
  </script>
</body>
</html>
"""


def ui_response() -> HTMLResponse:
    return HTMLResponse(HTML)
