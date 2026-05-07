from fastapi.responses import HTMLResponse


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>WhatsApp Prototype</title>
  <style>
    :root { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f6f7f9; color: #1f2933; }
    main { max-width: 980px; margin: 0 auto; padding: 32px 20px 56px; }
    section { background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 18px; margin-top: 18px; }
    label { display: block; font-weight: 650; margin: 12px 0 6px; }
    input, textarea { width: 100%; box-sizing: border-box; border: 1px solid #bcccdc; border-radius: 6px; padding: 10px 12px; font: inherit; }
    button { min-height: 38px; padding: 0 14px; border-radius: 6px; border: 1px solid #2b8a3e; background: #37b24d; color: white; font-weight: 650; cursor: pointer; }
    .row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }
    .result { background: #f8fafc; border: 1px solid #d9e2ec; border-radius: 6px; padding: 12px; margin-top: 14px; white-space: pre-wrap; overflow-wrap: anywhere; }
    @media (max-width: 720px) { .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <h1>WhatsApp Messaging</h1>
    <p>Create group chats, send messages, upload media, inspect offline inboxes, and ack delivery.</p>
    <section>
      <div class="row">
        <div><label>User</label><input id="user" value="alice"></div>
        <div><label>Participants</label><input id="participants" value="bob,charlie"></div>
        <div><label>Chat id</label><input id="chat"></div>
      </div>
      <div class="actions"><button id="create">Create chat</button></div>
      <div id="chat-result" class="result">Chat result appears here.</div>
    </section>
    <section>
      <label>Message body</label><textarea id="body" rows="3">hello from a durable inbox prototype</textarea>
      <div class="row">
        <div><label>Attachment filename</label><input id="filename" value="note.txt"></div>
        <div><label>Attachment text</label><input id="filetext" value="media bytes"></div>
        <div><label>Attachment id</label><input id="attachment"></div>
      </div>
      <div class="actions"><button id="attachment-button">Create/upload attachment</button><button id="send">Send message</button><button id="inbox">Load inbox</button><button id="ack">Ack first</button></div>
      <div id="message-result" class="result">Message results appear here.</div>
    </section>
  </main>
  <script>
    let lastMessageId = "";
    const out = (id, value) => document.querySelector(id).textContent = JSON.stringify(value, null, 2);
    async function json(path, options = {}, user = "alice") {
      const response = await fetch(path, {headers: {"content-type": "application/json", "X-User-Id": user}, ...options});
      const body = await response.json();
      if (!response.ok) throw body;
      return body;
    }
    document.querySelector("#create").onclick = async () => {
      try {
        const body = await json("/chats", {method: "POST", body: JSON.stringify({participants: document.querySelector("#participants").value.split(",").map((x) => x.trim()).filter(Boolean), name: "Demo chat"})}, document.querySelector("#user").value);
        document.querySelector("#chat").value = body.chatId;
        out("#chat-result", body);
      } catch (error) { out("#chat-result", error); }
    };
    document.querySelector("#attachment-button").onclick = async () => {
      try {
        const body = await json("/attachments", {method: "POST", body: JSON.stringify({filename: document.querySelector("#filename").value, mime_type: "text/plain"})}, document.querySelector("#user").value);
        await fetch(body.uploadUrl, {method: "PUT", body: new Blob([document.querySelector("#filetext").value], {type: "text/plain"})});
        document.querySelector("#attachment").value = body.attachmentId;
        out("#message-result", body);
      } catch (error) { out("#message-result", error); }
    };
    document.querySelector("#send").onclick = async () => {
      try {
        const attachment = document.querySelector("#attachment").value;
        const body = await json(`/chats/${document.querySelector("#chat").value}/messages`, {method: "POST", body: JSON.stringify({body: document.querySelector("#body").value, attachment_ids: attachment ? [attachment] : []})}, document.querySelector("#user").value);
        lastMessageId = body.messageId;
        out("#message-result", body);
      } catch (error) { out("#message-result", error); }
    };
    document.querySelector("#inbox").onclick = async () => { try { const body = await json("/inbox", {}, document.querySelector("#user").value); if (body.messages.length) lastMessageId = body.messages[0].messageId; out("#message-result", body); } catch (error) { out("#message-result", error); } };
    document.querySelector("#ack").onclick = async () => { try { out("#message-result", await json("/acks", {method: "POST", body: JSON.stringify({message_id: lastMessageId})}, document.querySelector("#user").value)); } catch (error) { out("#message-result", error); } };
  </script>
</body>
</html>
"""


def ui_response() -> HTMLResponse:
    return HTMLResponse(HTML)
