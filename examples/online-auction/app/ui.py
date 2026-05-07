from fastapi.responses import HTMLResponse


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Online Auction Prototype</title>
  <style>
    :root { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f6f7f9; color: #1f2933; }
    main { max-width: 960px; margin: 0 auto; padding: 32px 20px 56px; }
    section { background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 18px; margin-top: 18px; }
    label { display: block; font-weight: 650; margin: 12px 0 6px; }
    input, textarea { width: 100%; box-sizing: border-box; border: 1px solid #bcccdc; border-radius: 6px; padding: 10px 12px; font: inherit; }
    button { min-height: 38px; padding: 0 14px; border-radius: 6px; border: 1px solid #1864ab; background: #1971c2; color: white; font-weight: 650; cursor: pointer; }
    .row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }
    .result { background: #f8fafc; border: 1px solid #d9e2ec; border-radius: 6px; padding: 12px; margin-top: 14px; white-space: pre-wrap; overflow-wrap: anywhere; }
    @media (max-width: 720px) { .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <h1>Online Auction</h1>
    <p>Create an auction, place higher bids, reject stale bids, and view the current winner and bid stream.</p>
    <section>
      <h2>Create Auction</h2>
      <div class="row">
        <div><label>Seller</label><input id="seller" value="alice"></div>
        <div><label>Title</label><input id="title" value="Vintage keyboard"></div>
        <div><label>Starting price</label><input id="start-price" type="number" value="50"></div>
      </div>
      <label>Description</label><textarea id="description" rows="3">A local system-design auction item.</textarea>
      <label>Ends at</label><input id="ends-at" type="datetime-local">
      <div class="actions"><button id="create">Create</button></div>
      <div id="create-result" class="result">No auction yet.</div>
    </section>
    <section>
      <h2>Bid and View</h2>
      <div class="row">
        <div><label>Auction id</label><input id="auction"></div>
        <div><label>Bidder</label><input id="bidder" value="bob"></div>
        <div><label>Amount</label><input id="amount" type="number" value="75"></div>
      </div>
      <div class="actions"><button id="bid">Place bid</button><button id="view">View auction</button></div>
      <div id="bid-result" class="result">Bids and auction state appear here.</div>
    </section>
  </main>
  <script>
    const out = (id, value) => document.querySelector(id).textContent = JSON.stringify(value, null, 2);
    const defaultEnd = new Date(Date.now() + 60 * 60 * 1000);
    document.querySelector("#ends-at").value = defaultEnd.toISOString().slice(0, 16);
    async function json(path, options = {}, user = "alice") {
      const response = await fetch(path, {headers: {"content-type": "application/json", "X-User-Id": user}, ...options});
      const body = await response.json();
      if (!response.ok) throw body;
      return body;
    }
    document.querySelector("#create").onclick = async () => {
      try {
        const body = await json("/auctions", {method: "POST", body: JSON.stringify({title: document.querySelector("#title").value, description: document.querySelector("#description").value, starting_price: Number(document.querySelector("#start-price").value), ends_at: new Date(document.querySelector("#ends-at").value).toISOString()})}, document.querySelector("#seller").value);
        document.querySelector("#auction").value = body.auctionId;
        out("#create-result", body);
      } catch (error) { out("#create-result", error); }
    };
    document.querySelector("#bid").onclick = async () => {
      try { out("#bid-result", await json(`/auctions/${document.querySelector("#auction").value}/bids`, {method: "POST", body: JSON.stringify({amount: Number(document.querySelector("#amount").value)})}, document.querySelector("#bidder").value)); }
      catch (error) { out("#bid-result", error); }
    };
    document.querySelector("#view").onclick = async () => {
      try { out("#bid-result", await json(`/auctions/${document.querySelector("#auction").value}`)); }
      catch (error) { out("#bid-result", error); }
    };
  </script>
</body>
</html>
"""


def ui_response() -> HTMLResponse:
    return HTMLResponse(HTML)
