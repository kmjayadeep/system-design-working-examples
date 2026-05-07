from fastapi.responses import HTMLResponse


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FB News Feed Prototype</title>
  <style>
    :root { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f6f7f9; color: #1f2933; }
    main { max-width: 960px; margin: 0 auto; padding: 32px 20px 56px; }
    section { background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 18px; margin-top: 18px; }
    label { display: block; font-weight: 650; margin: 12px 0 6px; }
    input, textarea { width: 100%; box-sizing: border-box; border: 1px solid #bcccdc; border-radius: 6px; padding: 10px 12px; font: inherit; }
    button { min-height: 38px; padding: 0 14px; border-radius: 6px; border: 1px solid #364fc7; background: #4263eb; color: white; font-weight: 650; cursor: pointer; }
    .row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }
    .result { background: #f8fafc; border: 1px solid #d9e2ec; border-radius: 6px; padding: 12px; margin-top: 14px; white-space: pre-wrap; overflow-wrap: anywhere; }
    @media (max-width: 720px) { .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <h1>FB News Feed</h1>
    <p>Create posts, follow users, run fanout workers, and page through a precomputed feed.</p>
    <section>
      <div class="row">
        <div><label>Actor user</label><input id="user" value="alice"></div>
        <div><label>Follow user</label><input id="followed" value="bob"></div>
        <div><label>Page size</label><input id="page-size" type="number" value="5"></div>
      </div>
      <label>Post text</label><textarea id="text" rows="3">Hello from a fanout-on-write prototype.</textarea>
      <div class="actions"><button id="follow">Follow</button><button id="post">Create post</button><button id="fanout">Run fanout</button><button id="feed">Load feed</button></div>
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
    document.querySelector("#follow").onclick = async () => { try { out(await json(`/users/${document.querySelector("#followed").value}/follow`, {method: "PUT"}, document.querySelector("#user").value)); } catch (error) { out(error); } };
    document.querySelector("#post").onclick = async () => { try { out(await json("/posts", {method: "POST", body: JSON.stringify({content: {text: document.querySelector("#text").value}})}, document.querySelector("#user").value)); } catch (error) { out(error); } };
    document.querySelector("#fanout").onclick = async () => { try { out(await json("/workers/fanout/tick?limit=100", {method: "POST"})); } catch (error) { out(error); } };
    document.querySelector("#feed").onclick = async () => { try { out(await json(`/feed?page_size=${document.querySelector("#page-size").value}`, {}, document.querySelector("#user").value)); } catch (error) { out(error); } };
  </script>
</body>
</html>
"""


def ui_response() -> HTMLResponse:
    return HTMLResponse(HTML)
