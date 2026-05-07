from fastapi.responses import HTMLResponse


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Uber Prototype</title>
  <style>
    :root { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f5f6f7; color: #1f2933; }
    main { max-width: 1020px; margin: 0 auto; padding: 32px 20px 56px; }
    section { background: white; border: 1px solid #d8dee4; border-radius: 8px; padding: 18px; margin-top: 18px; }
    label { display: block; font-weight: 650; margin: 12px 0 6px; }
    input { width: 100%; box-sizing: border-box; border: 1px solid #b8c2cc; border-radius: 6px; padding: 10px 12px; font: inherit; }
    button { min-height: 38px; padding: 0 14px; border-radius: 6px; border: 1px solid #111827; background: #111827; color: white; font-weight: 650; cursor: pointer; }
    .row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }
    .result { background: #f8fafc; border: 1px solid #d8dee4; border-radius: 6px; padding: 12px; margin-top: 14px; white-space: pre-wrap; overflow-wrap: anywhere; }
    @media (max-width: 760px) { .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <h1>Uber</h1>
    <p>Update driver availability, estimate fares, request nearby rides, and accept or complete a ride.</p>
    <section>
      <div class="row">
        <div><label>Driver id</label><input id="driver" value="driver-1"></div>
        <div><label>Rider id</label><input id="rider" value="rider-1"></div>
        <div><label>Start lat</label><input id="startLat" value="37.7749"></div>
        <div><label>Start lng</label><input id="startLng" value="-122.4194"></div>
      </div>
      <div class="row">
        <div><label>Dest lat</label><input id="destLat" value="37.8044"></div>
        <div><label>Dest lng</label><input id="destLng" value="-122.2712"></div>
        <div><label>Ride id</label><input id="rideId" placeholder="created ride id"></div>
        <div><label>Driver lat/lng</label><input id="driverPoint" value="37.7750,-122.4195"></div>
      </div>
      <div class="actions"><button id="driverAvailable">Set driver available</button><button id="estimate">Estimate</button><button id="request">Request ride</button><button id="accept">Accept</button><button id="complete">Complete</button></div>
      <div id="result" class="result">Results appear here.</div>
    </section>
  </main>
  <script>
    const out = (value) => document.querySelector("#result").textContent = JSON.stringify(value, null, 2);
    async function json(path, options = {}) {
      const response = await fetch(path, {headers: {"content-type": "application/json"}, ...options});
      const body = await response.json();
      if (!response.ok) throw body;
      return body;
    }
    const n = (id) => Number(document.querySelector(id).value);
    document.querySelector("#driverAvailable").onclick = async () => {
      try {
        const [lat, lng] = document.querySelector("#driverPoint").value.split(",").map(Number);
        out(await json(`/drivers/${encodeURIComponent(document.querySelector("#driver").value)}/location`, {method: "POST", body: JSON.stringify({lat, lng, available: true})}));
      } catch (error) { out(error); }
    };
    document.querySelector("#estimate").onclick = async () => { try { out(await json(`/fare-estimate?startLat=${n("#startLat")}&startLng=${n("#startLng")}&destLat=${n("#destLat")}&destLng=${n("#destLng")}`)); } catch (error) { out(error); } };
    document.querySelector("#request").onclick = async () => {
      try {
        const body = await json("/rides", {method: "POST", body: JSON.stringify({riderId: document.querySelector("#rider").value, startLat: n("#startLat"), startLng: n("#startLng"), destLat: n("#destLat"), destLng: n("#destLng")})});
        document.querySelector("#rideId").value = body.rideId;
        document.querySelector("#driver").value = body.driverId;
        out(body);
      } catch (error) { out(error); }
    };
    document.querySelector("#accept").onclick = async () => { try { out(await json(`/rides/${document.querySelector("#rideId").value}/respond`, {method: "POST", body: JSON.stringify({driverId: document.querySelector("#driver").value, accept: true})})); } catch (error) { out(error); } };
    document.querySelector("#complete").onclick = async () => { try { out(await json(`/rides/${document.querySelector("#rideId").value}/complete`, {method: "POST"})); } catch (error) { out(error); } };
  </script>
</body>
</html>
"""


def ui_response() -> HTMLResponse:
    return HTMLResponse(HTML)
