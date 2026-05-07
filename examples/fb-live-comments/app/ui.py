from fastapi.responses import HTMLResponse


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FB Live Comments Prototype</title>
  <style>
    :root { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f6f7f9; color: #1f2933; }
    main { max-width: 920px; margin: 0 auto; padding: 32px 20px 56px; }
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
    <h1>FB Live Comments</h1>
    <p>Post comments, load historical comments with cursors, and poll the Redis-backed live stream.</p>
    <section>
      <div class="row">
        <div><label>User</label><input id="user" value="alice"></div>
        <div><label>Live video id</label><input id="video" value="live-1"></div>
        <div><label>After stream id</label><input id="after" value="0-0"></div>
      </div>
      <label>Message</label><textarea id="message" rows="3">great live video</textarea>
      <div class="actions"><button id="post">Post</button><button id="history">History</button><button id="stream">Stream poll</button></div>
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
    const video = () => document.querySelector("#video").value;
    document.querySelector("#post").onclick = async () => { try { out(await json(`/comments/${video()}`, {method: "POST", body: JSON.stringify({message: document.querySelector("#message").value})}, document.querySelector("#user").value)); } catch (error) { out(error); } };
    document.querySelector("#history").onclick = async () => { try { out(await json(`/comments/${video()}?page_size=10`)); } catch (error) { out(error); } };
    document.querySelector("#stream").onclick = async () => { try { const body = await json(`/comments/${video()}/stream?after=${encodeURIComponent(document.querySelector("#after").value)}`); if (body.events.length) document.querySelector("#after").value = body.events[body.events.length - 1].streamId; out(body); } catch (error) { out(error); } };
  </script>
</body>
</html>
"""


def ui_response() -> HTMLResponse:
    return HTMLResponse(HTML)
