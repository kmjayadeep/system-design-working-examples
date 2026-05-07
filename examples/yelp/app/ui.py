from fastapi.responses import HTMLResponse


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Yelp Prototype</title>
  <style>
    :root { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f6f7f9; color: #1f2933; }
    main { max-width: 980px; margin: 0 auto; padding: 32px 20px 56px; }
    section { background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 18px; margin-top: 18px; }
    label { display: block; font-weight: 650; margin: 12px 0 6px; }
    input, textarea { width: 100%; box-sizing: border-box; border: 1px solid #bcccdc; border-radius: 6px; padding: 10px 12px; font: inherit; }
    button { min-height: 38px; padding: 0 14px; border-radius: 6px; border: 1px solid #a61e4d; background: #c2255c; color: white; font-weight: 650; cursor: pointer; }
    .row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }
    .result { background: #f8fafc; border: 1px solid #d9e2ec; border-radius: 6px; padding: 12px; margin-top: 14px; white-space: pre-wrap; overflow-wrap: anywhere; }
    @media (max-width: 720px) { .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <h1>Yelp Business Search</h1>
    <p>Search by keyword, category, and location, view business details, and submit one review per user.</p>
    <section>
      <div class="row">
        <div><label>Search</label><input id="q" value="tacos"></div>
        <div><label>Category</label><input id="category" value="restaurants"></div>
        <div><label>Radius km</label><input id="radius" type="number" value="5"></div>
      </div>
      <div class="row">
        <div><label>Latitude</label><input id="lat" value="37.7749"></div>
        <div><label>Longitude</label><input id="lon" value="-122.4194"></div>
        <div><label>Business id</label><input id="business" value="biz-1"></div>
      </div>
      <div class="actions"><button id="search">Search</button><button id="details">Load details</button></div>
      <div id="search-result" class="result">Search results appear here.</div>
    </section>
    <section>
      <h2>Review</h2>
      <div class="row">
        <div><label>User</label><input id="user" value="dave"></div>
        <div><label>Rating</label><input id="rating" type="number" min="1" max="5" value="5"></div>
      </div>
      <label>Text</label><textarea id="text" rows="3">Great local demo.</textarea>
      <div class="actions"><button id="review">Submit review</button></div>
      <div id="review-result" class="result">Review result appears here.</div>
    </section>
  </main>
  <script>
    const out = (id, value) => document.querySelector(id).textContent = JSON.stringify(value, null, 2);
    async function json(path, options = {}) {
      const response = await fetch(path, {headers: {"content-type": "application/json", "X-User-Id": document.querySelector("#user").value}, ...options});
      const body = await response.json();
      if (!response.ok) throw body;
      return body;
    }
    document.querySelector("#search").onclick = async () => {
      try {
        const query = new URLSearchParams({q: document.querySelector("#q").value, category: document.querySelector("#category").value, latitude: document.querySelector("#lat").value, longitude: document.querySelector("#lon").value, radius_km: document.querySelector("#radius").value});
        const result = await json(`/businesses/search?${query}`);
        if (result.businesses.length) document.querySelector("#business").value = result.businesses[0].id;
        out("#search-result", result);
      } catch (error) { out("#search-result", error); }
    };
    document.querySelector("#details").onclick = async () => { try { out("#search-result", await json(`/businesses/${document.querySelector("#business").value}`)); } catch (error) { out("#search-result", error); } };
    document.querySelector("#review").onclick = async () => {
      try { out("#review-result", await json(`/businesses/${document.querySelector("#business").value}/reviews`, {method: "POST", body: JSON.stringify({rating: Number(document.querySelector("#rating").value), text: document.querySelector("#text").value})})); }
      catch (error) { out("#review-result", error); }
    };
  </script>
</body>
</html>
"""


def ui_response() -> HTMLResponse:
    return HTMLResponse(HTML)
