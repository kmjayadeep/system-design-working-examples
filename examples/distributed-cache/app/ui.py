from fastapi.responses import HTMLResponse


HTML = """
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Distributed Cache Prototype</title>
<style>body{font-family:Inter,system-ui,sans-serif;margin:0;background:#f6f7f8;color:#17202a}main{max-width:920px;margin:auto;padding:32px 20px}section{background:white;border:1px solid #d8dee4;border-radius:8px;padding:18px}.row{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}label{display:block;font-weight:650;margin:12px 0 6px}input{box-sizing:border-box;width:100%;border:1px solid #b8c2cc;border-radius:6px;padding:10px;font:inherit}button{min-height:38px;padding:0 14px;border-radius:6px;border:1px solid #374151;background:#4b5563;color:white;font-weight:650}.actions{display:flex;gap:10px;margin-top:14px}.result{background:#f8fafc;border:1px solid #d8dee4;border-radius:6px;padding:12px;margin-top:14px;white-space:pre-wrap;overflow-wrap:anywhere}@media(max-width:720px){.row{grid-template-columns:1fr}}</style></head>
<body><main><h1>Distributed Cache</h1><p>Store, read, delete, and inspect owner routing for cache keys.</p><section><div class="row"><div><label>Key</label><input id="key" value="user:1"></div><div><label>Value</label><input id="value" value="cached profile"></div><div><label>TTL seconds</label><input id="ttl" type="number" value="60"></div></div><div class="actions"><button id="put">Put</button><button id="get">Get</button><button id="del">Delete</button><button id="ring">Owner</button></div><div id="result" class="result">Results appear here.</div></section></main>
<script>const out=v=>result.textContent=JSON.stringify(v,null,2);async function json(path,opt={}){const r=await fetch(path,{headers:{"content-type":"application/json"},...opt});const b=await r.json();if(!r.ok)throw b;return b}put.onclick=async()=>{try{out(await json(`/cache/${encodeURIComponent(key.value)}`,{method:"PUT",body:JSON.stringify({value:value.value,ttlSeconds:Number(ttl.value)})}))}catch(e){out(e)}};get.onclick=async()=>{try{out(await json(`/cache/${encodeURIComponent(key.value)}`))}catch(e){out(e)}};del.onclick=async()=>{try{out(await json(`/cache/${encodeURIComponent(key.value)}`,{method:"DELETE"}))}catch(e){out(e)}};ring.onclick=async()=>{try{out(await json(`/ring/${encodeURIComponent(key.value)}`))}catch(e){out(e)}};</script></body></html>
"""


def ui_response() -> HTMLResponse:
    return HTMLResponse(HTML)
