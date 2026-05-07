from fastapi.responses import HTMLResponse


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Instagram Prototype</title>
  <style>
    :root { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #fafafa; color: #1f2933; }
    main { max-width: 980px; margin: 0 auto; padding: 32px 20px 56px; }
    section { background: white; border: 1px solid #d8dee4; border-radius: 8px; padding: 18px; margin-top: 18px; }
    label { display: block; font-weight: 650; margin: 12px 0 6px; }
    input, select, textarea { width: 100%; box-sizing: border-box; border: 1px solid #b8c2cc; border-radius: 6px; padding: 10px 12px; font: inherit; }
    button { min-height: 38px; padding: 0 14px; border-radius: 6px; border: 1px solid #be185d; background: #db2777; color: white; font-weight: 650; cursor: pointer; }
    .row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }
    .result { background: #f8fafc; border: 1px solid #d8dee4; border-radius: 6px; padding: 12px; margin-top: 14px; white-space: pre-wrap; overflow-wrap: anywhere; }
    @media (max-width: 760px) { .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <h1>Instagram</h1>
    <p>Create media upload slots, publish posts with captions, follow users, and read a chronological feed.</p>
    <section>
      <div class="row">
        <div><label>User</label><input id="user" value="alice"></div>
        <div><label>Media type</label><select id="mediaType"><option value="photo">Photo</option><option value="video">Video</option></select></div>
        <div><label>Post id</label><input id="postId" placeholder="created post id"></div>
        <div><label>Follow user</label><input id="followee" value="alice"></div>
      </div>
      <label>Caption</label><textarea id="caption" rows="3">first post from a local prototype</textarea>
      <div class="actions"><button id="upload">Create upload URL</button><button id="publish">Publish post</button><button id="follow">Follow</button><button id="feed">Feed</button></div>
      <div id="result" class="result">Results appear here. Upload the media bytes with the returned PUT URL, then publish.</div>
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
    document.querySelector("#upload").onclick = async () => {
      try {
        const body = await json("/media/uploads", {method: "POST", body: JSON.stringify({mediaType: document.querySelector("#mediaType").value})}, document.querySelector("#user").value);
        document.querySelector("#postId").value = body.postId;
        out(body);
      } catch (error) { out(error); }
    };
    document.querySelector("#publish").onclick = async () => { try { out(await json("/posts", {method: "POST", body: JSON.stringify({postId: document.querySelector("#postId").value, caption: document.querySelector("#caption").value})}, document.querySelector("#user").value)); } catch (error) { out(error); } };
    document.querySelector("#follow").onclick = async () => { try { out(await json("/follows", {method: "POST", body: JSON.stringify({userId: document.querySelector("#followee").value})}, document.querySelector("#user").value)); } catch (error) { out(error); } };
    document.querySelector("#feed").onclick = async () => { try { out(await json("/feed", {}, document.querySelector("#user").value)); } catch (error) { out(error); } };
  </script>
</body>
</html>
"""


def ui_response() -> HTMLResponse:
    return HTMLResponse(HTML)
