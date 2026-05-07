from fastapi.responses import HTMLResponse


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Tinder Prototype</title>
  <style>
    :root { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f6f7f9; color: #1f2933; }
    main { max-width: 980px; margin: 0 auto; padding: 32px 20px 56px; }
    section { background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 18px; margin-top: 18px; }
    label { display: block; font-weight: 650; margin: 12px 0 6px; }
    input, select { width: 100%; box-sizing: border-box; border: 1px solid #bcccdc; border-radius: 6px; padding: 10px 12px; font: inherit; }
    button { min-height: 38px; padding: 0 14px; border-radius: 6px; border: 1px solid #c2255c; background: #e64980; color: white; font-weight: 650; cursor: pointer; }
    .row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }
    .result { background: #f8fafc; border: 1px solid #d9e2ec; border-radius: 6px; padding: 12px; margin-top: 14px; white-space: pre-wrap; overflow-wrap: anywhere; }
    @media (max-width: 720px) { .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <h1>Tinder Matching</h1>
    <p>Create profiles, load nearby recommendations, swipe yes/no, and check mutual matches.</p>
    <section>
      <h2>Profile</h2>
      <div class="row">
        <div><label>User</label><input id="user" value="alice"></div>
        <div><label>Name</label><input id="name" value="Alice"></div>
        <div><label>Age</label><input id="age" type="number" value="29"></div>
      </div>
      <div class="row">
        <div><label>Gender</label><select id="gender"><option>female</option><option>male</option><option>nonbinary</option></select></div>
        <div><label>Interested in</label><select id="interested"><option>male</option><option>female</option><option>both</option><option>any</option></select></div>
        <div><label>Max distance km</label><input id="distance" type="number" value="15"></div>
      </div>
      <div class="row">
        <div><label>Latitude</label><input id="lat" value="37.7749"></div>
        <div><label>Longitude</label><input id="lon" value="-122.4194"></div>
      </div>
      <div class="actions"><button id="save">Save profile</button><button id="feed">Load feed</button></div>
      <div id="profile-result" class="result">Profile and feed results appear here.</div>
    </section>
    <section>
      <h2>Swipe</h2>
      <div class="row">
        <div><label>Target user</label><input id="target" value="bob"></div>
        <div><label>Decision</label><select id="decision"><option>yes</option><option>no</option></select></div>
      </div>
      <div class="actions"><button id="swipe">Swipe</button><button id="matches">Matches</button></div>
      <div id="swipe-result" class="result">Swipe and match results appear here.</div>
    </section>
  </main>
  <script>
    const out = (id, value) => document.querySelector(id).textContent = JSON.stringify(value, null, 2);
    async function json(path, options = {}, user = "alice") {
      const response = await fetch(path, {headers: {"content-type": "application/json", "X-User-Id": user}, ...options});
      const body = await response.json();
      if (!response.ok) throw body;
      return body;
    }
    document.querySelector("#save").onclick = async () => {
      try { out("#profile-result", await json("/profile", {method: "POST", body: JSON.stringify({name: document.querySelector("#name").value, age: Number(document.querySelector("#age").value), gender: document.querySelector("#gender").value, interested_in: document.querySelector("#interested").value, min_age: 18, max_age: 45, max_distance_km: Number(document.querySelector("#distance").value), latitude: Number(document.querySelector("#lat").value), longitude: Number(document.querySelector("#lon").value)})}, document.querySelector("#user").value)); }
      catch (error) { out("#profile-result", error); }
    };
    document.querySelector("#feed").onclick = async () => { try { out("#profile-result", await json(`/feed?latitude=${document.querySelector("#lat").value}&longitude=${document.querySelector("#lon").value}`, {}, document.querySelector("#user").value)); } catch (error) { out("#profile-result", error); } };
    document.querySelector("#swipe").onclick = async () => { try { out("#swipe-result", await json(`/swipe/${document.querySelector("#target").value}`, {method: "POST", body: JSON.stringify({decision: document.querySelector("#decision").value})}, document.querySelector("#user").value)); } catch (error) { out("#swipe-result", error); } };
    document.querySelector("#matches").onclick = async () => { try { out("#swipe-result", await json("/matches", {}, document.querySelector("#user").value)); } catch (error) { out("#swipe-result", error); } };
  </script>
</body>
</html>
"""


def ui_response() -> HTMLResponse:
    return HTMLResponse(HTML)
