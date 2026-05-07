from fastapi.responses import HTMLResponse


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Bitly Prototype</title>
  <style>
    :root { color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f6f7f9; color: #1f2933; }
    main { max-width: 920px; margin: 0 auto; padding: 32px 20px 56px; }
    h1 { margin: 0 0 6px; font-size: 28px; }
    p { color: #52606d; line-height: 1.5; }
    section { background: #fff; border: 1px solid #d9e2ec; border-radius: 8px; padding: 20px; margin-top: 18px; }
    label { display: block; font-weight: 650; margin: 14px 0 6px; }
    input { width: 100%; box-sizing: border-box; border: 1px solid #bcccdc; border-radius: 6px; padding: 10px 12px; font: inherit; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    button, a.button { display: inline-flex; align-items: center; justify-content: center; min-height: 38px; padding: 0 14px; border-radius: 6px; border: 1px solid #1864ab; background: #1971c2; color: white; font-weight: 650; text-decoration: none; cursor: pointer; }
    button.secondary, a.secondary { background: white; color: #1864ab; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 16px; }
    .result { background: #f8fafc; border: 1px solid #d9e2ec; border-radius: 6px; padding: 12px; margin-top: 16px; white-space: pre-wrap; overflow-wrap: anywhere; }
    .error { color: #b42318; }
    table { width: 100%; border-collapse: collapse; margin-top: 12px; }
    th, td { text-align: left; border-bottom: 1px solid #e4e7eb; padding: 10px; vertical-align: top; }
    code { background: #edf2f7; border-radius: 4px; padding: 2px 4px; }
    @media (max-width: 720px) { .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <h1>Bitly URL Shortener</h1>
    <p>Create generated or custom short links, optionally set an expiration time, and open the shortened URL to exercise the redirect path through the proxy.</p>

    <section>
      <h2>Create Short URL</h2>
      <form id="shorten-form">
        <label for="long_url">Long URL</label>
        <input id="long_url" name="long_url" value="https://www.hellointerview.com/learn/system-design/problem-breakdowns/bitly" required>
        <div class="row">
          <div>
            <label for="custom_alias">Custom alias</label>
            <input id="custom_alias" name="custom_alias" placeholder="optional, e.g. system-design">
          </div>
          <div>
            <label for="expiration_date">Expiration</label>
            <input id="expiration_date" name="expiration_date" type="datetime-local">
          </div>
        </div>
        <div class="actions">
          <button type="submit">Shorten</button>
          <button class="secondary" type="button" id="fill-expiry">Set 2 minute expiry</button>
        </div>
      </form>
      <div id="result" class="result">No short URL created yet.</div>
    </section>

    <section>
      <h2>Created Links</h2>
      <table>
        <thead><tr><th>Short URL</th><th>Original URL</th><th>Actions</th></tr></thead>
        <tbody id="links"><tr><td colspan="3">Created links will appear here.</td></tr></tbody>
      </table>
    </section>
  </main>

  <script>
    const form = document.querySelector("#shorten-form");
    const result = document.querySelector("#result");
    const links = document.querySelector("#links");
    const created = [];

    function renderLinks() {
      if (created.length === 0) {
        links.innerHTML = '<tr><td colspan="3">Created links will appear here.</td></tr>';
        return;
      }
      links.innerHTML = created.map((item) => `
        <tr>
          <td><code>${item.short_url}</code></td>
          <td>${item.long_url}</td>
          <td><a class="button secondary" href="${item.short_url}" target="_blank" rel="noreferrer">Open</a></td>
        </tr>
      `).join("");
    }

    document.querySelector("#fill-expiry").addEventListener("click", () => {
      const date = new Date(Date.now() + 2 * 60 * 1000);
      date.setSeconds(0, 0);
      document.querySelector("#expiration_date").value = date.toISOString().slice(0, 16);
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      result.className = "result";
      result.textContent = "Creating...";
      const data = new FormData(form);
      const expiration = data.get("expiration_date");
      const payload = {
        long_url: data.get("long_url"),
        custom_alias: data.get("custom_alias") || null,
        expiration_date: expiration ? new Date(expiration).toISOString() : null
      };
      try {
        const response = await fetch("/shorten", {
          method: "POST",
          headers: {"content-type": "application/json"},
          body: JSON.stringify(payload)
        });
        const body = await response.json();
        if (!response.ok) {
          throw new Error(body.detail || JSON.stringify(body));
        }
        result.innerHTML = `Created <a href="${body.short_url}" target="_blank" rel="noreferrer">${body.short_url}</a>\\nShort code: ${body.short_code}\\nExpires: ${body.expires_at || "never"}`;
        created.unshift({...body, long_url: payload.long_url});
        renderLinks();
      } catch (error) {
        result.className = "result error";
        result.textContent = error.message;
      }
    });
  </script>
</body>
</html>
"""


def ui_response() -> HTMLResponse:
    return HTMLResponse(HTML)
