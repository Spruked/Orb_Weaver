"""Admin-only pointer authority overlay injected into the customer-site proxy."""

import json
from typing import Any, Dict


def build_pointer_admin_overlay(config: Dict[str, Any]) -> str:
    """Return a self-contained overlay script.

    The script owns no authority state. It resolves DOM geometry for display,
    and sends every requested color change to the existing authority route.
    """
    safe_config = json.dumps(config, separators=(",", ":")).replace("<", "\\u003c")
    return f"""(() => {{
  const CONFIG = {safe_config};
  const records = Array.isArray(CONFIG.authority_records) ? CONFIG.authority_records : [];
  const root = document.createElement('div');
  root.id = 'orb-pointer-admin-overlay';
  root.innerHTML = `
    <style>
      #orb-pointer-admin-overlay {{ all: initial; position: fixed; inset: 0; z-index: 2147483646; pointer-events: none; font-family: Inter, ui-sans-serif, system-ui, sans-serif; color: #e5eef5; }}
      #orb-pointer-admin-overlay * {{ box-sizing: border-box; font-family: inherit; }}
      .opa-dot {{ position: fixed; width: 22px; height: 22px; margin: -11px 0 0 -11px; border: 2px solid #fff; border-radius: 50%; display: grid; place-items: center; color: #071018; font: 800 11px/1 system-ui; cursor: pointer; pointer-events: auto; box-shadow: 0 2px 12px #0008; transition: transform .12s ease; }}
      .opa-dot:hover {{ transform: scale(1.25); }} .opa-dot.green {{ background:#48e08c; }} .opa-dot.blue {{ background:#55b9ff; }} .opa-dot.red {{ background:#ff6574; }}
      .opa-dot.offscreen {{ opacity:.9; right: 12px; left:auto; margin:0; }}
      .opa-panel {{ position: fixed; top: 14px; right: 14px; width: 330px; max-height: calc(100vh - 28px); overflow:auto; padding: 14px; border:1px solid #355268; border-radius:14px; background:#071522ee; color:#e5eef5; box-shadow:0 18px 55px #0008; pointer-events:auto; }}
      .opa-panel h1 {{ margin:0 0 5px; font-size:15px; letter-spacing:.08em; text-transform:uppercase; }} .opa-panel p {{ margin:0 0 10px; color:#a9c0d0; font-size:12px; line-height:1.4; }}
      .opa-counts {{ display:grid; grid-template-columns:repeat(3,1fr); gap:5px; margin:10px 0; }} .opa-count {{ padding:7px; border-radius:8px; background:#102536; text-align:center; font-size:11px; }} .opa-count strong {{ display:block; color:#fff; font-size:16px; }}
      .opa-list {{ margin-top:12px; border-top:1px solid #294052; padding-top:10px; }} .opa-list h2 {{ margin:0 0 6px; font-size:11px; text-transform:uppercase; color:#8fd6ff; letter-spacing:.08em; }}
      .opa-list button {{ display:block; width:100%; padding:7px 0; border:0; border-bottom:1px solid #20394a; background:transparent; color:#d7e8f2; text-align:left; cursor:pointer; font-size:11px; }}
      .opa-card {{ position:fixed; left:18px; bottom:18px; width:min(390px,calc(100vw - 36px)); padding:14px; border:1px solid #47657b; border-radius:14px; background:#081723f5; box-shadow:0 18px 55px #0009; pointer-events:auto; }}
      .opa-card h2 {{ margin:0 0 4px; font-size:16px; }} .opa-card .meta {{ color:#9fb8c8; font-size:11px; line-height:1.5; }} .opa-card .reason {{ margin:10px 0; color:#e6f4fb; font-size:12px; line-height:1.45; }}
      .opa-actions {{ display:flex; gap:6px; }} .opa-actions button {{ flex:1; border:0; border-radius:7px; padding:8px 5px; color:#061019; font-weight:800; cursor:pointer; }} .opa-actions button:disabled {{ opacity:.45; cursor:wait; }} .opa-green {{ background:#48e08c; }} .opa-blue {{ background:#55b9ff; }} .opa-red {{ background:#ff6574; }} .opa-error {{ color:#ff9da8; font-size:11px; margin-top:8px; }}
    </style>
    <div class="opa-panel" aria-label="Pointer authority admin overlay">
      <h1>Pointer authority</h1><p>Admin review only. Dots are live DOM geometry when rendered; authority changes are signed by the existing decision route.</p>
      <div class="opa-counts"><div class="opa-count"><strong data-total>0</strong>Total</div><div class="opa-count"><strong data-rendered>0</strong>Rendered</div><div class="opa-count"><strong data-missing>0</strong>Missing</div></div>
      <div class="opa-list" data-unrendered></div>
    </div><div data-card></div>`;
  document.documentElement.appendChild(root);
  const dots = new Map();
  const card = root.querySelector('[data-card]');
  const normalize = value => String(value || '').replace(/\\s+/g, ' ').trim().toLowerCase();
  const route = () => String(CONFIG.site_route || location.pathname).replace(/\\/+$/, '') || '/';
  const recordRoute = record => {{ try {{ return new URL(record.page_route, location.origin).pathname.replace(/\\/+$/, '') || '/'; }} catch {{ return record.page_route || '/'; }} }};
  const fragments = record => [(record.meaning || '').replace(/^[^:]+:\\s*/, ''), ...(record.direct_aliases || record.intent_aliases || [])].map(normalize).filter(Boolean);
  const reason = record => record.finding_subreason || record.owner_authority?.notes || record.runtime_policy?.reason || record.finding_class || 'No disposition reason recorded.';
  const disposition = record => {{
    const health = String(record.pointer_health || '').toUpperCase(); const finding = String(record.finding_class || '').toUpperCase();
    if (health === 'OWNER_VERIFIED' || record.confidence_class === 'VERIFIED') return ['VERIFIED', 'green', 'G'];
    const raw = (finding + ' ' + String(record.finding_subreason || '')).toUpperCase();
    const named = ['NOT_FOUND','NOT_INTERACTABLE','PROTECTED'].find(name => raw.includes(name));
    if (named || finding === 'CONFLICT' || finding === 'BLOCKED' || ['OWNER_REJECTED','DEPRECATED','REMOVED'].includes(health)) return [named || finding || 'PROTECTED', 'red', 'R'];
    if (finding === 'TRANSIENT' || finding === 'DYNAMIC') return ['UNSTABLE', 'blue', 'U'];
    return ['REQUIRES_RUNTIME_CHECK', 'blue', 'C'];
  }};
  const visible = element => {{ const r=element.getBoundingClientRect(), s=getComputedStyle(element); return document.body.contains(element) && r.width>0 && r.height>0 && s.display!=='none' && s.visibility!=='hidden' && Number(s.opacity||1)>0; }};
  const matches = (element, record) => {{ const tag=String(record.structural_context?.tag||'').toLowerCase(); if(tag && element.tagName.toLowerCase()!==tag)return false; const text=normalize(['INPUT','TEXTAREA','SELECT'].includes(element.tagName)?[element.getAttribute('aria-label'),element.getAttribute('placeholder'),element.getAttribute('name'),element.textContent].join(' '):element.textContent); return fragments(record).some(fragment => text===fragment || (text.length>=5 && fragment.length>=5 && (text.includes(fragment)||fragment.includes(text)) && Math.min(text.length,fragment.length)/Math.max(text.length,fragment.length)>=.65)); }};
  const resolve = record => {{ if(recordRoute(record)!==route()) return {{ ok:false, reason:'route_mismatch' }}; const parent=String(record.structural_context?.parent_locator||'').trim(); const selector=(parent?parent+' ':'')+String(record.semantic_locator||'').replaceAll('\\\\',''); let found=[]; try {{ found=Array.from(document.querySelectorAll(selector)).filter(element=>matches(element,record)); }} catch {{ return {{ok:false,reason:'invalid_locator'}}; }} if(found.length!==1)return {{ok:false,reason:found.length?'ambiguous':'not_rendered',count:found.length,selector}}; const element=found[0]; if(!visible(element))return {{ok:false,reason:'hidden',selector}}; const rect=element.getBoundingClientRect(); return {{ok:true,element,selector,route:route(),tag:element.tagName.toLowerCase(),text:normalize(element.textContent),rect:{{x:rect.x,y:rect.y,width:rect.width,height:rect.height}}}}; }};
  const authHeaders = () => {{ const token=sessionStorage.getItem('orb_weaver_customer_session_token'); return token ? {{Authorization:'Bearer '+token,'Content-Type':'application/json'}} : {{'Content-Type':'application/json'}}; }};
  const createDot = record => {{ const dot=document.createElement('button'); dot.className='opa-dot'; dot.type='button'; dot.title=record.meaning||record.target_id; dot.addEventListener('click',()=>showCard(record)); root.appendChild(dot); dots.set(record.target_id,dot); return dot; }};
  const position = (record, dot, resolved, index) => {{ const [label, color, letter]=disposition(record); dot.className='opa-dot '+color+(resolved.ok?'':' offscreen'); dot.textContent=letter; dot.dataset.disposition=label; if(resolved.ok){{ dot.style.left=(resolved.rect.x+resolved.rect.width/2)+'px'; dot.style.top=(resolved.rect.y+resolved.rect.height/2)+'px'; dot.style.right='auto'; }} else {{ dot.style.top=(86+index*25)+'px'; }} }};
  const render = () => {{ let rendered=0, missing=0; const unrendered=[]; records.forEach((record,index)=>{{ const dot=dots.get(record.target_id)||createDot(record); const resolved=resolve(record); if(resolved.ok)rendered++; if(!resolved.ok){{ missing++; unrendered.push({{record,resolved}}); }} position(record,dot,resolved,index); }}); root.querySelector('[data-total]').textContent=records.length; root.querySelector('[data-rendered]').textContent=rendered; root.querySelector('[data-missing]').textContent=missing; const list=root.querySelector('[data-unrendered]'); list.innerHTML='<h2>Not found / not rendered</h2>'; unrendered.slice(0,80).forEach(item=>{{ const button=document.createElement('button'); button.textContent=(item.record.meaning||item.record.target_id)+' · '+recordRoute(item.record)+' · '+item.resolved.reason; button.addEventListener('click',()=>showCard(item.record)); list.appendChild(button); }}); }};
  const showCard = record => {{ const [label,color]=disposition(record); card.innerHTML=`<div class="opa-card"><h2>${{record.meaning||record.target_id}}</h2><div class="meta">${{record.target_id}} · route ${{recordRoute(record)}} · disposition ${{label}}</div><div class="reason">${{reason(record)}}</div><div class="opa-actions"><button class="opa-green" data-decision="green">Make Green</button><button class="opa-blue" data-decision="blue">Make Blue</button><button class="opa-red" data-decision="red">Make Red</button></div><div class="opa-error" data-error></div></div>`; card.querySelectorAll('[data-decision]').forEach(button=>button.addEventListener('click',()=>decide(record,button.dataset.decision))); }};
  const decide = async (record, decision) => {{ const error=card.querySelector('[data-error]'); const buttons=Array.from(card.querySelectorAll('button')); buttons.forEach(button=>button.disabled=true); let livePayload=null; if(decision==='green'){{ const live=resolve(record); if(!live.ok){{ error.textContent='Make Green refused: '+live.reason+'. The target must resolve uniquely and visibly at click time.'; buttons.forEach(button=>button.disabled=false); return; }} livePayload={{ok:true,route:live.route,selector:live.selector,tag:live.tag,text:live.text,rect:live.rect}}; }} try {{ const response=await fetch(CONFIG.decision_url.replace('__TARGET_ID__',encodeURIComponent(record.target_id)),{{method:'POST',headers:authHeaders(),body:JSON.stringify({{decision,notes:'Admin pointer overlay decision',live_resolution:livePayload}})}}); const body=await response.json().catch(()=>({{}})); if(!response.ok)throw new Error(body.detail||'Authority decision refused'); const index=records.findIndex(item=>item.target_id===record.target_id); if(index>=0)records[index]=body.pointer; render(); showCard(records[index]); }} catch(err) {{ error.textContent=err.message||'Authority decision failed'; }} finally {{ buttons.forEach(button=>button.disabled=false); }} }};
  document.addEventListener('click', event => {{ const anchor=event.target.closest && event.target.closest('a[href]'); if(!anchor || event.defaultPrevented)return; try {{ const next=new URL(anchor.href); const source=new URL(CONFIG.target_origin || next.origin); if(next.origin===source.origin && next.hash===''){{ event.preventDefault(); location.href=CONFIG.proxy_url.replace(/\\/$/,'')+next.pathname+(next.search||''); }} }} catch {{ /* Leave malformed or external links to the customer page. */ }} }});
  window.addEventListener('scroll',render,true); window.addEventListener('resize',render); if(document.body) new MutationObserver(render).observe(document.body,{{subtree:true,childList:true}}); render();
}})();"""
