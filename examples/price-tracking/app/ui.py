from fastapi.responses import HTMLResponse


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Price Tracking Prototype</title>
  <style>
    :root { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f6f7f9; color: #1f2933; }
    main { max-width: 980px; margin: 0 auto; padding: 32px 20px 56px; }
    section { background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 18px; margin-top: 18px; }
    label { display: block; font-weight: 650; margin: 12px 0 6px; }
    input { width: 100%; box-sizing: border-box; border: 1px solid #bcccdc; border-radius: 6px; padding: 10px 12px; font: inherit; }
    button { min-height: 38px; padding: 0 14px; border-radius: 6px; border: 1px solid #2b8a3e; background: #37b24d; color: white; font-weight: 650; cursor: pointer; }
    .row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }
    .result { background: #f8fafc; border: 1px solid #d9e2ec; border-radius: 6px; padding: 12px; margin-top: 14px; white-space: pre-wrap; overflow-wrap: anywhere; }
    @media (max-width: 720px) { .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <h1>Price Tracking Service</h1>
    <p>Ingest product prices, query price history, subscribe to a threshold, and process notification ticks.</p>
    <section>
      <div class="row">
        <div><label>ASIN</label><input id="asin" value="B000DEMO"></div>
        <div><label>Title</label><input id="title" value="Demo headphones"></div>
        <div><label>Price</label><input id="price" type="number" value="129.99"></div>
      </div>
      <div class="actions"><button id="ingest">Ingest price</button><button id="history">Price history</button></div>
      <div id="price-result" class="result">Price data appears here.</div>
    </section>
    <section>
      <div class="row">
        <div><label>User</label><input id="user" value="alice"></div>
        <div><label>Threshold</label><input id="threshold" type="number" value="100"></div>
      </div>
      <div class="actions"><button id="subscribe">Subscribe</button><button id="tick">Process notifications</button><button id="notifications">My notifications</button></div>
      <div id="notification-result" class="result">Subscription and notifications appear here.</div>
    </section>
  </main>
  <script>
    const out = (id, value) => document.querySelector(id).textContent = JSON.stringify(value, null, 2);
    async function json(path, options = {}, user = "alice") {
      const response = await fetch(path, {headers: {"content-type": "application/json", "X-User-Id": user}, ...options});
      const body = await response.json();
      if (!response.ok) throw body;
      return body;
    }
    document.querySelector("#ingest").onclick = async () => { try { out("#price-result", await json("/prices", {method: "POST", body: JSON.stringify({asin: document.querySelector("#asin").value, title: document.querySelector("#title").value, price: document.querySelector("#price").value, source: "manual"})})); } catch (error) { out("#price-result", error); } };
    document.querySelector("#history").onclick = async () => { try { out("#price-result", await json(`/products/${document.querySelector("#asin").value}/prices`)); } catch (error) { out("#price-result", error); } };
    document.querySelector("#subscribe").onclick = async () => { try { out("#notification-result", await json("/subscriptions", {method: "POST", body: JSON.stringify({asin: document.querySelector("#asin").value, threshold_price: document.querySelector("#threshold").value})}, document.querySelector("#user").value)); } catch (error) { out("#notification-result", error); } };
    document.querySelector("#tick").onclick = async () => { try { out("#notification-result", await json("/notifications/tick", {method: "POST"})); } catch (error) { out("#notification-result", error); } };
    document.querySelector("#notifications").onclick = async () => { try { out("#notification-result", await json("/notifications", {}, document.querySelector("#user").value)); } catch (error) { out("#notification-result", error); } };
  </script>
</body>
</html>
"""


def ui_response() -> HTMLResponse:
    return HTMLResponse(HTML)
