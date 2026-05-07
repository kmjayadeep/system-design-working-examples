from fastapi.responses import HTMLResponse


HTML = """
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Robinhood Prototype</title><style>
body{font-family:Inter,system-ui,sans-serif;margin:0;background:#f6f8f7;color:#17202a}main{max-width:980px;margin:auto;padding:32px 20px}
section{background:white;border:1px solid #d8dee4;border-radius:8px;padding:18px;margin-top:18px}.row{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
label{display:block;font-weight:650;margin:12px 0 6px}input,select{box-sizing:border-box;width:100%;border:1px solid #b8c2cc;border-radius:6px;padding:10px;font:inherit}
button{min-height:38px;padding:0 14px;border-radius:6px;border:1px solid #087f5b;background:#099268;color:white;font-weight:650}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}
.result{background:#f8fafc;border:1px solid #d8dee4;border-radius:6px;padding:12px;margin-top:14px;white-space:pre-wrap;overflow-wrap:anywhere}@media(max-width:760px){.row{grid-template-columns:1fr}}
</style></head><body><main><h1>Robinhood</h1><p>Update market prices, place buy/sell orders, and inspect a portfolio.</p><section>
<div class="row"><div><label>User</label><input id="user" value="alice"></div><div><label>Symbol</label><input id="symbol" value="AAPL"></div><div><label>Price cents</label><input id="price" type="number" value="18000"></div><div><label>Quantity</label><input id="qty" type="number" value="1"></div></div>
<label>Side</label><select id="side"><option value="buy">Buy</option><option value="sell">Sell</option></select>
<div class="actions"><button id="setPrice">Set price</button><button id="order">Place order</button><button id="portfolio">Portfolio</button></div><div id="result" class="result">Results appear here.</div>
</section></main><script>
const out=v=>document.querySelector("#result").textContent=JSON.stringify(v,null,2);
async function json(path,opt={}){const r=await fetch(path,{headers:{"content-type":"application/json"},...opt});const b=await r.json();if(!r.ok)throw b;return b}
setPrice.onclick=async()=>{try{out(await json("/market/prices",{method:"POST",body:JSON.stringify({symbol:symbol.value,priceCents:Number(price.value)})}))}catch(e){out(e)}};
order.onclick=async()=>{try{out(await json("/orders",{method:"POST",body:JSON.stringify({userId:user.value,symbol:symbol.value,side:side.value,quantity:Number(qty.value)})}))}catch(e){out(e)}};
portfolio.onclick=async()=>{try{out(await json(`/portfolio/${encodeURIComponent(user.value)}`))}catch(e){out(e)}};
</script></body></html>
"""


def ui_response() -> HTMLResponse:
    return HTMLResponse(HTML)
