from fastapi.responses import HTMLResponse


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>News Aggregator Prototype</title>
  <style>
    :root { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f6f7f9; color: #1f2933; }
    main { max-width: 980px; margin: 0 auto; padding: 32px 20px 56px; }
    section { background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 18px; margin-top: 18px; }
    label { display: block; font-weight: 650; margin: 12px 0 6px; }
    input, textarea, select { width: 100%; box-sizing: border-box; border: 1px solid #bcccdc; border-radius: 6px; padding: 10px 12px; font: inherit; }
    button { min-height: 38px; padding: 0 14px; border-radius: 6px; border: 1px solid #364fc7; background: #4263eb; color: white; font-weight: 650; cursor: pointer; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }
    .result { background: #f8fafc; border: 1px solid #d9e2ec; border-radius: 6px; padding: 12px; margin-top: 14px; white-space: pre-wrap; overflow-wrap: anywhere; }
    @media (max-width: 720px) { .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <h1>News Aggregator</h1>
    <p>Ingest articles, read a cached feed, filter by category, and open publisher redirects.</p>
    <section>
      <h2>Feed</h2>
      <div class="row">
        <div><label>Category</label><input id="feed-category" placeholder="optional, e.g. tech"></div>
        <div><label>Limit</label><input id="limit" type="number" min="1" value="2"></div>
      </div>
      <div class="actions"><button id="feed">Load feed</button><button id="open-first">Open first article</button></div>
      <div id="feed-result" class="result">Feed appears here.</div>
    </section>
    <section>
      <h2>Ingest Article</h2>
      <div class="row">
        <div><label>Publisher</label><select id="publisher"><option>daily-planet</option><option>tech-wire</option></select></div>
        <div><label>Category</label><input id="category" value="tech"></div>
      </div>
      <label>Title</label><input id="title" value="Local prototype ships UI">
      <label>Summary</label><textarea id="summary" rows="3">Manual testing is now available through the proxy.</textarea>
      <label>Publisher URL</label><input id="url" value="https://www.hellointerview.com/learn/system-design/problem-breakdowns/news-aggregator">
      <div class="actions"><button id="ingest">Ingest</button></div>
      <div id="ingest-result" class="result">Ingest result appears here.</div>
    </section>
  </main>
  <script>
    let lastFeed = null;
    const out = (id, value) => document.querySelector(id).textContent = JSON.stringify(value, null, 2);
    async function json(path, options = {}) {
      const response = await fetch(path, {headers: {"content-type": "application/json"}, ...options});
      const body = await response.json();
      if (!response.ok) throw body;
      return body;
    }
    document.querySelector("#feed").onclick = async () => {
      try {
        const category = document.querySelector("#feed-category").value;
        lastFeed = await json(`/feed?limit=${encodeURIComponent(document.querySelector("#limit").value)}${category ? `&category=${encodeURIComponent(category)}` : ""}`);
        out("#feed-result", lastFeed);
      } catch (error) { out("#feed-result", error); }
    };
    document.querySelector("#open-first").onclick = () => {
      if (lastFeed && lastFeed.articles.length) window.open(`/articles/${lastFeed.articles[0].id}/redirect`, "_blank", "noreferrer");
    };
    document.querySelector("#ingest").onclick = async () => {
      try {
        out("#ingest-result", await json("/ingest/articles", {method: "POST", body: JSON.stringify({publisher_id: document.querySelector("#publisher").value, title: document.querySelector("#title").value, summary: document.querySelector("#summary").value, category: document.querySelector("#category").value, publisher_url: document.querySelector("#url").value})}));
      } catch (error) { out("#ingest-result", error); }
    };
  </script>
</body>
</html>
"""


def ui_response() -> HTMLResponse:
    return HTMLResponse(HTML)
