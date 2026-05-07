from fastapi.responses import HTMLResponse


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FB Post Search Prototype</title>
  <style>
    :root { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f5f7fb; color: #1f2933; }
    main { max-width: 980px; margin: 0 auto; padding: 32px 20px 56px; }
    section { background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 18px; margin-top: 18px; }
    label { display: block; font-weight: 650; margin: 12px 0 6px; }
    input, textarea, select { width: 100%; box-sizing: border-box; border: 1px solid #bcccdc; border-radius: 6px; padding: 10px 12px; font: inherit; }
    button { min-height: 38px; padding: 0 14px; border-radius: 6px; border: 1px solid #1864ab; background: #1971c2; color: white; font-weight: 650; cursor: pointer; }
    .row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }
    .result { background: #f8fafc; border: 1px solid #d9e2ec; border-radius: 6px; padding: 12px; margin-top: 14px; white-space: pre-wrap; overflow-wrap: anywhere; }
    @media (max-width: 720px) { .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <h1>FB Post Search</h1>
    <p>Create posts, like them, and query a simple inverted index sorted by recency or like count.</p>
    <section>
      <div class="row">
        <div><label>User</label><input id="user" value="alice"></div>
        <div><label>Search query</label><input id="query" value="coffee"></div>
        <div><label>Sort</label><select id="sort"><option value="recency">Recency</option><option value="likes">Likes</option></select></div>
      </div>
      <label>Post content</label><textarea id="content" rows="3">coffee and distributed systems</textarea>
      <label>Post id to like</label><input id="postId" placeholder="created post id">
      <div class="actions"><button id="create">Create post</button><button id="like">Like post</button><button id="search">Search</button></div>
      <div id="result" class="result">Results appear here.</div>
    </section>
  </main>
  <script>
    const out = (value) => document.querySelector("#result").textContent = JSON.stringify(value, null, 2);
    async function json(path, options = {}, user = "alice") {
      const response = await fetch(path, {headers: {"content-type": "application/json", "X-User-Id": user}, ...options});
      const body = await response.json();
      if (!response.ok) throw body;
      return body;
    }
    document.querySelector("#create").onclick = async () => {
      try {
        const body = await json("/posts", {method: "POST", body: JSON.stringify({content: document.querySelector("#content").value})}, document.querySelector("#user").value);
        document.querySelector("#postId").value = body.postId;
        out(body);
      } catch (error) { out(error); }
    };
    document.querySelector("#like").onclick = async () => { try { out(await json("/likes", {method: "POST", body: JSON.stringify({postId: document.querySelector("#postId").value})}, document.querySelector("#user").value)); } catch (error) { out(error); } };
    document.querySelector("#search").onclick = async () => {
      try {
        const q = encodeURIComponent(document.querySelector("#query").value);
        const sort = encodeURIComponent(document.querySelector("#sort").value);
        out(await json(`/search?q=${q}&sort=${sort}`));
      } catch (error) { out(error); }
    };
  </script>
</body>
</html>
"""


def ui_response() -> HTMLResponse:
    return HTMLResponse(HTML)
