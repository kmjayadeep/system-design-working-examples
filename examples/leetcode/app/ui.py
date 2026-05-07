from fastapi.responses import HTMLResponse


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LeetCode Prototype</title>
  <style>
    :root { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f6f7f9; color: #1f2933; }
    main { max-width: 1040px; margin: 0 auto; padding: 32px 20px 56px; }
    section { background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 18px; margin-top: 18px; }
    label { display: block; font-weight: 650; margin: 12px 0 6px; }
    input, textarea { width: 100%; box-sizing: border-box; border: 1px solid #bcccdc; border-radius: 6px; padding: 10px 12px; font: inherit; }
    textarea { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
    button { min-height: 38px; padding: 0 14px; border-radius: 6px; border: 1px solid #d9480f; background: #f76707; color: white; font-weight: 650; cursor: pointer; }
    .row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }
    .result { background: #f8fafc; border: 1px solid #d9e2ec; border-radius: 6px; padding: 12px; margin-top: 14px; white-space: pre-wrap; overflow-wrap: anywhere; }
    @media (max-width: 720px) { .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <h1>LeetCode Judge</h1>
    <p>Browse problems, submit code, tick the judge worker, poll results, and view a competition leaderboard.</p>
    <section>
      <div class="row">
        <div><label>User</label><input id="user" value="alice"></div>
        <div><label>Problem id</label><input id="problem" value="two-sum"></div>
        <div><label>Competition id</label><input id="competition" value="weekly-1"></div>
      </div>
      <label>Code</label><textarea id="code" rows="8">def solve(nums, target):
    seen = {}
    for i, n in enumerate(nums):
        if target - n in seen:
            return [seen[target - n], i]
        seen[n] = i</textarea>
      <div class="actions"><button id="list">Problems</button><button id="view">View problem</button><button id="submit">Submit</button><button id="judge">Run judge</button><button id="result">Result</button><button id="leaderboard">Leaderboard</button></div>
      <div id="output" class="result">Results appear here.</div>
    </section>
  </main>
  <script>
    let submissionId = "";
    const out = (value) => document.querySelector("#output").textContent = JSON.stringify(value, null, 2);
    async function json(path, options = {}, user = "alice") {
      const response = await fetch(path, {headers: {"content-type": "application/json", "X-User-Id": user}, ...options});
      const body = await response.json();
      if (!response.ok) throw body;
      return body;
    }
    document.querySelector("#list").onclick = async () => { try { out(await json("/problems")); } catch (error) { out(error); } };
    document.querySelector("#view").onclick = async () => { try { out(await json(`/problems/${document.querySelector("#problem").value}`)); } catch (error) { out(error); } };
    document.querySelector("#submit").onclick = async () => {
      try {
        const body = await json(`/problems/${document.querySelector("#problem").value}/submit`, {method: "POST", body: JSON.stringify({language: "python", code: document.querySelector("#code").value, competition_id: document.querySelector("#competition").value})}, document.querySelector("#user").value);
        submissionId = body.submissionId;
        out(body);
      } catch (error) { out(error); }
    };
    document.querySelector("#judge").onclick = async () => { try { out(await json("/workers/judge/tick?limit=10", {method: "POST"})); } catch (error) { out(error); } };
    document.querySelector("#result").onclick = async () => { try { out(await json(`/submissions/${submissionId}`)); } catch (error) { out(error); } };
    document.querySelector("#leaderboard").onclick = async () => { try { out(await json(`/leaderboard/${document.querySelector("#competition").value}`)); } catch (error) { out(error); } };
  </script>
</body>
</html>
"""


def ui_response() -> HTMLResponse:
    return HTMLResponse(HTML)
