from fastapi.responses import HTMLResponse


HTML = """
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Google Docs Prototype</title><style>
body{font-family:Inter,system-ui,sans-serif;margin:0;background:#f7f9fc;color:#17202a}main{max-width:980px;margin:auto;padding:32px 20px}
section{background:white;border:1px solid #d8dee4;border-radius:8px;padding:18px;margin-top:18px}.row{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
label{display:block;font-weight:650;margin:12px 0 6px}input,textarea,select{box-sizing:border-box;width:100%;border:1px solid #b8c2cc;border-radius:6px;padding:10px;font:inherit}
button{min-height:38px;padding:0 14px;border-radius:6px;border:1px solid #1d4ed8;background:#2563eb;color:white;font-weight:650}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}
.result{background:#f8fafc;border:1px solid #d8dee4;border-radius:6px;padding:12px;margin-top:14px;white-space:pre-wrap;overflow-wrap:anywhere}@media(max-width:760px){.row{grid-template-columns:1fr}}
</style></head><body><main><h1>Google Docs</h1><p>Create a document, share it, append edit operations, and poll live document events.</p><section>
<div class="row"><div><label>User</label><input id="user" value="alice"></div><div><label>Title</label><input id="title" value="Design Notes"></div><div><label>Document id</label><input id="doc"></div><div><label>Version</label><input id="version" type="number" value="0"></div></div>
<label>Text</label><textarea id="text" rows="4">first edit</textarea><label>Share with</label><input id="shareUser" value="bob">
<div class="actions"><button id="create">Create</button><button id="share">Share</button><button id="append">Append</button><button id="load">Load</button><button id="events">Events</button></div><div id="result" class="result">Results appear here.</div>
</section></main><script>
const out=v=>result.textContent=JSON.stringify(v,null,2);
async function json(path,opt={},u=user.value){const r=await fetch(path,{headers:{"content-type":"application/json","X-User-Id":u},...opt});const b=await r.json();if(!r.ok)throw b;return b}
create.onclick=async()=>{try{const b=await json("/documents",{method:"POST",body:JSON.stringify({title:title.value})});doc.value=b.documentId;version.value=b.version;out(b)}catch(e){out(e)}};
share.onclick=async()=>{try{out(await json(`/documents/${doc.value}/share`,{method:"POST",body:JSON.stringify({userId:shareUser.value,permission:"write"})}))}catch(e){out(e)}};
append.onclick=async()=>{try{const b=await json(`/documents/${doc.value}/operations`,{method:"POST",body:JSON.stringify({baseVersion:Number(version.value),text:text.value})});version.value=b.version;out(b)}catch(e){out(e)}};
load.onclick=async()=>{try{const b=await json(`/documents/${doc.value}`);version.value=b.version;out(b)}catch(e){out(e)}};
events.onclick=async()=>{try{out(await json(`/documents/${doc.value}/events`))}catch(e){out(e)}};
</script></body></html>
"""


def ui_response() -> HTMLResponse:
    return HTMLResponse(HTML)
