from fastapi.responses import HTMLResponse


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ticketmaster Prototype</title>
  <style>
    :root { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f6f7f9; color: #1f2933; }
    main { max-width: 980px; margin: 0 auto; padding: 32px 20px 56px; }
    section { background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 18px; margin-top: 18px; }
    label { display: block; font-weight: 650; margin: 12px 0 6px; }
    input { width: 100%; box-sizing: border-box; border: 1px solid #bcccdc; border-radius: 6px; padding: 10px 12px; font: inherit; }
    button { min-height: 38px; padding: 0 14px; border-radius: 6px; border: 1px solid #1864ab; background: #1971c2; color: white; font-weight: 650; cursor: pointer; }
    .row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }
    .result { background: #f8fafc; border: 1px solid #d9e2ec; border-radius: 6px; padding: 12px; margin-top: 14px; white-space: pre-wrap; overflow-wrap: anywhere; }
    @media (max-width: 720px) { .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <h1>Ticketmaster Booking</h1>
    <p>Search events, view seats, reserve tickets with a hold, and confirm a booking.</p>
    <section>
      <div class="row">
        <div><label>Search</label><input id="q" value="jazz"></div>
        <div><label>City</label><input id="city" value="San Francisco"></div>
        <div><label>Event id</label><input id="event" value="evt-jazz"></div>
      </div>
      <div class="actions"><button id="search">Search</button><button id="view">View event</button></div>
      <div id="event-result" class="result">Events and seats appear here.</div>
    </section>
    <section>
      <div class="row">
        <div><label>User</label><input id="user" value="alice"></div>
        <div><label>Ticket ids, comma separated</label><input id="tickets" value="t-jazz-a1,t-jazz-a2"></div>
        <div><label>Reservation id</label><input id="reservation"></div>
      </div>
      <div class="actions"><button id="reserve">Reserve</button><button id="confirm">Confirm booking</button></div>
      <div id="booking-result" class="result">Reservation and booking results appear here.</div>
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
    document.querySelector("#search").onclick = async () => { try { out("#event-result", await json(`/events/search?q=${encodeURIComponent(document.querySelector("#q").value)}&city=${encodeURIComponent(document.querySelector("#city").value)}`)); } catch (error) { out("#event-result", error); } };
    document.querySelector("#view").onclick = async () => { try { out("#event-result", await json(`/events/${document.querySelector("#event").value}`)); } catch (error) { out("#event-result", error); } };
    document.querySelector("#reserve").onclick = async () => {
      try {
        const body = await json(`/events/${document.querySelector("#event").value}/reservations`, {method: "POST", body: JSON.stringify({ticket_ids: document.querySelector("#tickets").value.split(",").map((item) => item.trim()).filter(Boolean)})}, document.querySelector("#user").value);
        document.querySelector("#reservation").value = body.reservationId;
        out("#booking-result", body);
      } catch (error) { out("#booking-result", error); }
    };
    document.querySelector("#confirm").onclick = async () => { try { out("#booking-result", await json("/bookings", {method: "POST", body: JSON.stringify({reservation_id: document.querySelector("#reservation").value})}, document.querySelector("#user").value)); } catch (error) { out("#booking-result", error); } };
  </script>
</body>
</html>
"""


def ui_response() -> HTMLResponse:
    return HTMLResponse(HTML)
