from fastapi.responses import HTMLResponse


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Strava Prototype</title>
  <style>
    :root { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f6f7f9; color: #1f2933; }
    main { max-width: 980px; margin: 0 auto; padding: 32px 20px 56px; }
    section { background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 18px; margin-top: 18px; }
    label { display: block; font-weight: 650; margin: 12px 0 6px; }
    input, select, textarea { width: 100%; box-sizing: border-box; border: 1px solid #bcccdc; border-radius: 6px; padding: 10px 12px; font: inherit; }
    button { min-height: 38px; padding: 0 14px; border-radius: 6px; border: 1px solid #d9480f; background: #f76707; color: white; font-weight: 650; cursor: pointer; }
    .row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }
    .result { background: #f8fafc; border: 1px solid #d9e2ec; border-radius: 6px; padding: 12px; margin-top: 14px; white-space: pre-wrap; overflow-wrap: anywhere; }
    @media (max-width: 720px) { .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <h1>Strava Activity Tracking</h1>
    <p>Start an activity, upload route points, pause/resume/stop it, save the completed activity, and view your friends' activities.</p>
    <section>
      <div class="row">
        <div><label>User</label><input id="user" value="alice"></div>
        <div><label>Type</label><select id="type"><option>run</option><option>ride</option></select></div>
        <div><label>Activity id</label><input id="activity" placeholder="created by Start"></div>
      </div>
      <label>Route points JSON</label>
      <textarea id="points" rows="5">[{"latitude":37.7749,"longitude":-122.4194,"recorded_at":"2026-05-07T10:00:00Z"},{"latitude":37.7759,"longitude":-122.4184,"recorded_at":"2026-05-07T10:02:00Z"},{"latitude":37.7769,"longitude":-122.4174,"recorded_at":"2026-05-07T10:04:00Z"}]</textarea>
      <div class="actions"><button id="start">Start</button><button id="points-button">Upload points</button><button id="pause">Pause</button><button id="resume">Resume</button><button id="stop">Stop</button><button id="save">Save</button></div>
      <div id="activity-result" class="result">No activity yet.</div>
    </section>
    <section>
      <h2>Read Paths</h2>
      <div class="actions"><button id="live">Live stats</button><button id="details">Activity details</button><button id="feed">Friend feed</button></div>
      <div id="read-result" class="result">Live stats, details, and feed appear here.</div>
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
    function id() { return document.querySelector("#activity").value; }
    document.querySelector("#start").onclick = async () => {
      try {
        const body = await json("/activities", {method: "POST", body: JSON.stringify({activity_type: document.querySelector("#type").value})});
        document.querySelector("#activity").value = body.activityId;
        out("#activity-result", body);
      } catch (error) { out("#activity-result", error); }
    };
    document.querySelector("#points-button").onclick = async () => { try { out("#activity-result", await json(`/activities/${id()}/points`, {method: "POST", body: JSON.stringify({points: JSON.parse(document.querySelector("#points").value)})})); } catch (error) { out("#activity-result", error); } };
    document.querySelector("#pause").onclick = async () => { try { out("#activity-result", await json(`/activities/${id()}/pause`, {method: "POST"})); } catch (error) { out("#activity-result", error); } };
    document.querySelector("#resume").onclick = async () => { try { out("#activity-result", await json(`/activities/${id()}/resume`, {method: "POST"})); } catch (error) { out("#activity-result", error); } };
    document.querySelector("#stop").onclick = async () => { try { out("#activity-result", await json(`/activities/${id()}/stop`, {method: "POST"})); } catch (error) { out("#activity-result", error); } };
    document.querySelector("#save").onclick = async () => { try { out("#activity-result", await json(`/activities/${id()}/save`, {method: "POST"})); } catch (error) { out("#activity-result", error); } };
    document.querySelector("#live").onclick = async () => { try { out("#read-result", await json(`/activities/${id()}/live`)); } catch (error) { out("#read-result", error); } };
    document.querySelector("#details").onclick = async () => { try { out("#read-result", await json(`/activities/${id()}`)); } catch (error) { out("#read-result", error); } };
    document.querySelector("#feed").onclick = async () => { try { out("#read-result", await json("/activities/feed")); } catch (error) { out("#read-result", error); } };
  </script>
</body>
</html>
"""


def ui_response() -> HTMLResponse:
    return HTMLResponse(HTML)
