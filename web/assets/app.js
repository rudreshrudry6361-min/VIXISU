/* VIXISU — premium sports talent intelligence. Zero frontend build dependencies. */
const API = '/api';
const app = document.getElementById('app');
const state = {
  route: window.location.pathname, sport: 'cricket', players: [], config: null,
  overview: null, teams: [], videos: [], search: '', roleFilter: 'all',
  profileId: null, compareA: null, compareB: null,
  fitSport: 'cricket', fitRole: 'Opener', weights: null, roster: [], fitResults: null,
  lastVideo: null, videoReview: null, videoPending: false, mobileOpen: false, teamName: '',
};
const icons = {
  grid:'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  users:'<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
  target:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
  layers:'<path d="m12 2 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 17l9 5 9-5"/>',
  camera:'<rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="12" cy="12" r="4"/><path d="m8 5 1-2h6l1 2"/>',
  upload:'<path d="M12 16V3m-5 5 5-5 5 5"/><path d="M4 16v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4"/>',
  info:'<circle cx="12" cy="12" r="10"/><path d="M12 16v-4m0-4h.01"/>',
  arrow:'<path d="M5 12h14m-6-6 6 6-6 6"/>',
  up:'<path d="m7 14 5-5 5 5"/>',
  search:'<circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/>',
  plus:'<path d="M12 5v14M5 12h14"/>',
  check:'<path d="m4 12 5 5L20 6"/>',
  chart:'<path d="M3 3v18h18"/><path d="m7 15 4-4 3 2 5-7"/>',
  menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',
  close:'<path d="M5 5l14 14M19 5 5 19"/>',
  refresh:'<path d="M3 12a9 9 0 0 1 15-6l3 3M21 3v6h-6"/><path d="M21 12a9 9 0 0 1-15 6l-3-3M3 21v-6h6"/>',
  file:'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6M8 13h8M8 17h8"/>',
  play:'<path d="m8 5 11 7-11 7V5Z"/>',
  filter:'<path d="M4 7h16M7 12h10m-7 5h4"/>',
};
const icon = (name, size=18) => `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name]||icons.grid}</svg>`;
const esc = x => String(x ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const titleCase = s => String(s||'').replace(/\b\w/g,c=>c.toUpperCase());
const art = sport => `/assets/${sport==='cricket'?'cricket':'football'}.svg`;
const fmt = n => Number(n||0).toLocaleString('en-US');
const getPlayer = id => state.players.find(p=>p.id===id);
const featureLabels = sport => Object.fromEntries((state.config?.features[sport]||[]).map(f=>[f.key,f.label]));
const featuresOf = sport => state.config?.features[sport]||[];
const rolesOf = sport => Object.keys(state.config?.roles[sport]||{});
const routeName = () => ({'/':'Overview','/scout':'Scouting Room','/talent':'Talent Pool','/team-fit':'Team Fit','/compare':'Compare','/vision':'Vision Lab','/import':'Data Studio','/about':'The System','/profile':'Player Profile'})[state.route] || 'Overview';
const navItems = [
  ['/', 'Overview','grid'],['/scout','Scouting Room','search'],['/talent','Talent Pool','users'],['/team-fit','Team Fit','target'],
  ['/compare','Compare Players','layers'],['/vision','Vision Lab','camera'],['/import','Data Studio','upload'],['/about','The System','info']
];
async function request(path, opts={}){
  const res=await fetch(API+path,opts);
  const data=await res.json().catch(()=>({detail:'Unexpected response'}));
  if(!res.ok) {
    const error = new Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail||data));
    error.status = res.status;
    throw error;
  }
  return data;
}

let workspaceUnlock;
async function withWorkspaceAccess(action){
  try {
    return await action();
  } catch (error) {
    if (error.status !== 401) throw error;
    workspaceUnlock ||= Promise.resolve().then(() => {
      const token = window.prompt('Enter the VIXISU workspace owner token.');
      if (!token) throw error;
      return request('/workspace/unlock',{method:'POST',headers:{Authorization:'Bearer ' + token}});
    }).finally(() => { workspaceUnlock = undefined; });
    await workspaceUnlock;
    return action();
  }
}
function workspaceWrite(path, method, values){
  return withWorkspaceAccess(() => request(path, {method, headers:{'Content-Type':'application/json'},
    body:values === undefined ? undefined : JSON.stringify(values)}));
}
function toast(msg,error=false){
  let stack=document.querySelector('.toast-stack'); if(!stack){stack=document.createElement('div');stack.className='toast-stack';document.body.appendChild(stack)}
  const el=document.createElement('div');el.className='toast'+(error?' error':'');el.textContent=msg;stack.appendChild(el);setTimeout(()=>el.remove(),4500);
}
function navigate(route,query={}){
  state.route=route;
  if(query.sport) state.sport=query.sport;
  if(query.id) state.profileId=query.id;
  history.pushState({route},'',route+(query.id?'?id='+encodeURIComponent(query.id):''));
  state.mobileOpen=false;render();window.scrollTo({top:0,behavior:'smooth'});
}
function shell(){
  return `<div class="mobile-shade ${state.mobileOpen?'open':''}" data-close-menu></div><div class="app-shell">
  <aside class="sidebar ${state.mobileOpen?'open':''}" aria-label="Primary navigation">
    <a class="logo" href="/home" aria-label="VIXISU home"><span class="logo-mark">V</span><span><span class="logo-word">VIXISU<span class="accent">.</span></span><span class="logo-sub">TALENT INTELLIGENCE</span></span></a>
    <div><div class="side-label">WORKSPACE / 01</div><nav class="side-nav">${navItems.map(([path,label,ic])=>`<button class="nav-item ${state.route===path||(state.route==='/profile'&&path==='/talent')?'active':''}" data-nav="${path}">${icon(ic)}<span>${label}</span></button>`).join('')}</nav></div>
    <div class="side-spacer"></div>
    <div class="side-note"><div class="mini-icon">✳</div><strong>Intelligence in motion.</strong><p>Discover the player your team actually needs.</p><button data-nav="/team-fit">OPEN TEAM-FIT ENGINE &nbsp;↗</button></div>
    <div class="side-footer">VIXISU / BUILD 001<br/>EXPERIMENTAL SCOUTING LAB</div>
  </aside>
  <main class="main"><header class="topbar"><div class="top-left"><button class="menu-toggle" data-toggle-menu aria-label="Open menu">${icon('menu',21)}</button><span class="breadcrumb">VIXISU &nbsp; / &nbsp; <b>${esc(routeName().toUpperCase())}</b></span><span class="tiny-split"></span><span class="page-number">001 — 026</span></div><div class="top-right"><span class="status"><i class="status-dot"></i> SYSTEM OPERATIONAL</span><span class="tag neutral">MVP / BETA</span><span class="top-avatar">AI</span></div></header><div id="page" class="page"></div></main></div>`;
}
function metric(label,value,foot){return `<div class="metric-card"><div class="metric-label">${label}</div><div class="metric-value">${value}</div><div class="metric-foot">${foot}</div></div>`}
function section(kicker,title,sub,link='',path=''){return `<div class="section-head"><div><div class="kicker">${kicker}</div><h2>${title}</h2>${sub?`<p>${sub}</p>`:''}</div>${link?`<button class="section-link" data-nav="${path}">${link} &nbsp; ↗</button>`:''}</div>`}
function sportSwitch(){return `<div class="sport-switch"><span class="tag">CRICKET / T20</span></div>`;}
function topPlayers(sport,limit=3){return state.players.filter(p=>p.sport===sport).sort((a,b)=>avg(b.features)-avg(a.features)).slice(0,limit)}
function avg(obj){const v=Object.values(obj||{});return v.length?v.reduce((a,b)=>a+b,0)/v.length:0}
function overviewPage(){
 const o=state.overview||{cricket:0,teams:0,videos:0};
 return `<section class="hero" aria-labelledby="hero-title"><div class="hero-orbit"></div><div class="hero-art"><img src="/assets/cricket.svg" alt="Original illustration of a cricketer"/></div><div class="hero-content"><div class="hero-top"><span class="hero-index">01 / CRICKET</span><span>THE FUTURE OF SCOUTING</span></div><h1 id="hero-title">TALENT.<br/><span class="outline">REDEFINED.</span><br/><em>FIT FIRST.</em></h1><p>Discover overlooked cricket talent. Turn performance signals into clear, explainable recruitment decisions.</p><div class="hero-cta"><button class="btn btn-primary" data-nav="/team-fit">FIND THE RIGHT PLAYER ${icon('arrow')}</button><button class="btn btn-ghost" data-nav="/talent">EXPLORE TALENT ${icon('arrow')}</button></div></div><div class="hero-bottom"><span class="hero-scroll">SCROLL TO EXPLORE <span>↓</span></span><span class="hero-coord">VIXISU / T20 INTELLIGENCE</span></div></section>
 <div class="metric-grid">${metric('Cricket profiles',fmt(o.cricket),'ILLUSTRATIVE TALENT POOL')}${metric('Role templates',rolesOf('cricket').length,'CUSTOMIZABLE REQUIREMENTS')}${metric('Saved teams',fmt(o.teams),'TEAM COMPOSITION')}${metric('Vision analyses',fmt(o.videos),'VIDEO PROCESSING')}</div>
 ${section('01 / SCOUTING','THE CRICKET INDEX.','Explore the talent vectors of our illustrative candidates.','ALL PLAYERS','/talent')}
 <div class="player-grid">${topPlayers('cricket',3).map(playerCard).join('')}</div>
 ${section('02 / DECISION INTELLIGENCE','THE SCIENCE OF FIT.','Change your team requirements and watch the candidate ranking change.','OPEN ENGINE','/team-fit')}
 <div class="story-panel"><div><div class="kicker">THE DIFFERENCE MAKER</div><h2>NOT THE BEST PLAYER.<br/><span class="accent">THE RIGHT PLAYER.</span></h2><p>Define an opener, finisher or bowler. Our transparent scoring engine considers the team's priorities, role and skill gaps rather than ranking everyone by a single number.</p><button class="btn btn-primary" data-nav="/team-fit">RUN TEAM-FIT ANALYSIS ${icon('arrow')}</button></div><div class="story-symbol">V.</div></div>
 <div class="notice" style="margin-top:18px"><strong>Demo edition:</strong> fictional cricket profiles and illustrative normalized scores. Computer-vision processing is real; the demo scores are not measured player abilities.</div>`;
}
function playerCard(p){
  const entries=Object.entries(p.features).sort((a,b)=>b[1]-a[1]).slice(0,2);
  const labels=featureLabels(p.sport);
  return `<article class="player-card" data-player-card="${esc(p.id)}"><div class="player-visual ${p.sport}"><span class="big-initials">${esc(p.initials)}</span><img src="${art(p.sport)}" alt=""/><span class="number">${esc(p.id)} / VIXISU</span><span class="country">${esc(p.country)}</span></div><div class="player-info"><span class="tag small ${p.sport==='cricket'?'orange':''}">${p.sport.toUpperCase()}</span><h3>${esc(p.name)}</h3><div class="player-role">${esc(p.role)} &nbsp; • &nbsp; AGE ${p.age||'—'}</div><div class="stats">${entries.map(([k,v])=>`<div><span>${esc(labels[k]||titleCase(k))}</span><strong>${v}<span style="display:inline;font-size:10px"> /100</span></strong></div>`).join('')}</div><div class="card-actions"><button class="btn btn-sm btn-primary" data-player="${esc(p.id)}">VIEW PROFILE ${icon('arrow',13)}</button><button class="btn btn-sm" data-compare-add="${esc(p.id)}" title="Compare this player">${icon('layers',14)}</button></div></div></article>`;
}
function talentPage(){
  const pool=state.players.filter(p=>p.sport===state.sport && (state.roleFilter==='all'||p.role===state.roleFilter) && p.name.toLowerCase().includes(state.search.toLowerCase()));
  return `<div class="page-head"><div><div class="kicker">THE SCOUTING DATABASE</div><h1 class="page-title">TALENT <span class="accent">POOL.</span></h1><p class="intro">Every profile is a set of signals. Filter, inspect and compare player capabilities in cricket.</p></div><div class="actions"><button class="btn" id="open-player-archive">Archived profiles</button><button class="btn" data-nav="/import">${icon('plus')} ADD TALENT</button><button class="btn btn-primary" data-nav="/team-fit">BUILD YOUR TEAM ${icon('arrow')}</button></div></div>
  <div class="toolbar">${sportSwitch(state.sport)}<div style="display:flex;gap:10px;flex-wrap:wrap"><div class="search">${icon('search')}<input id="talent-search" placeholder="Search talent..." value="${esc(state.search)}" aria-label="Search players"/></div><select class="select" id="role-filter" aria-label="Filter by role"><option value="all">All positions</option>${rolesOf(state.sport).map(r=>`<option ${state.roleFilter===r?'selected':''}>${esc(r)}</option>`).join('')}</select></div></div>
  <div style="display:flex;justify-content:space-between;align-items:center;margin:14px 0 18px"><div class="eyebrow">${pool.length} PROFILES / ${state.sport.toUpperCase()}</div><span class="tag neutral">SCORES 0–100</span></div>
  <div class="player-grid" id="talent-grid">${pool.length?pool.map(playerCard).join(''):`<div class="empty" style="grid-column:1/-1"><strong>No matching players.</strong>Try another filter or import new talent.</div>`}</div>
  <div class="notice" style="margin-top:22px">Seed profiles are fictional. Scores represent illustrative normalized skills, not measurements from actual matches.</div>${workspaceProfiles.archiveDialog()}`;
}
function radarSvg(p, size=310){
  const keys=featuresOf(p.sport).map(f=>f.key).filter(k=>p.features[k]!==undefined);
  const labels=featureLabels(p.sport);const cx=size/2,cy=size/2,r=size*.31;
  const pt=(i,value)=>{const a=(Math.PI*2*i/keys.length)-Math.PI/2;return [cx+Math.cos(a)*r*value,cy+Math.sin(a)*r*value]};
  const polygons=[.25,.5,.75,1].map(fr=>`<polygon class="radar-grid" points="${keys.map((k,i)=>pt(i,fr).join(',')).join(' ')}"/>`).join('');
  const spokes=keys.map((k,i)=>{const [x,y]=pt(i,1);return `<line x1="${cx}" y1="${cy}" x2="${x}" y2="${y}" class="radar-grid"/>`}).join('');
  const poly=keys.map((k,i)=>pt(i,(p.features[k]||0)/100).join(',')).join(' ');
  const points=keys.map((k,i)=>{const [x,y]=pt(i,(p.features[k]||0)/100);return `<circle class="radar-point" cx="${x}" cy="${y}" r="3"/>`}).join('');
  const texts=keys.map((k,i)=>{const [x,y]=pt(i,1.25);return `<text class="radar-label" x="${x}" y="${y}" text-anchor="middle" dominant-baseline="middle">${esc(labels[k]||k)}</text>`}).join('');
  return `<svg class="radar" viewBox="0 0 ${size} ${size}" role="img" aria-label="Radar chart showing ${esc(p.name)} skill scores">${polygons}${spokes}<polygon class="radar-polygon" points="${poly}"/>${points}${texts}</svg>`;
}
function profilePage(){
  const p=getPlayer(state.profileId);if(!p)return `<div class="empty"><strong>Player not found.</strong><button class="btn" data-nav="/talent">Back to talent pool</button></div>`;
  const labels=featureLabels(p.sport);
  const entries=Object.entries(p.features).sort((a,b)=>b[1]-a[1]);
  return `<div class="page-head"><div><div class="kicker">PLAYER INTELLIGENCE / ${esc(p.id)}</div><h1 class="page-title">TALENT <span class="accent">PROFILE.</span></h1><p class="intro">A structured view of skills, role and evidence for one candidate.</p></div><div class="actions"><button class="btn" data-nav="/talent">← ALL PLAYERS</button><button class="btn btn-primary" data-compare-add="${esc(p.id)}">COMPARE PLAYER ${icon('arrow')}</button></div></div>
  <div class="profile-hero ${p.sport}"><img src="${art(p.sport)}" alt=""/>
  <img class="profile-photo" alt="" referrerpolicy="no-referrer" hidden><div class="profile-text"><span class="tag ${p.sport==='cricket'?'orange':''}">${p.sport.toUpperCase()} / ${esc(p.id)}</span><h2>${esc(p.name.toUpperCase())}</h2><p>${esc(p.role)} &nbsp; / &nbsp; ${esc(p.country)} &nbsp; / &nbsp; AGE ${p.age||'—'}</p><span class="tag neutral">${p.demo?'ILLUSTRATIVE DEMO':'USER-SUPPLIED DATA'}</span></div></div>
  <div class="profile-layout" style="margin-top:18px"><div class="panel panel-pad"><div class="eyebrow">PERFORMANCE MATRIX</div><h2 class="panel-title">Skill breakdown</h2><p class="panel-sub">Normalized performance indicators / 100</p><div class="divider"></div><div class="skill-list">${entries.map(([k,v])=>`<div class="skill-row"><div class="skill-row-top"><span>${esc(labels[k]||k)}</span><b>${v} / 100</b></div><div class="skill-track"><div class="skill-fill" style="width:${v}%"></div></div></div>`).join('')}</div></div>
  <div class="panel panel-pad"><div class="eyebrow">TALENT DNA</div><h2 class="panel-title">Capability signature</h2>${radarSvg(p)}<p class="helper">Sport-specific normalized indicators. Radar area is illustrative and not a cross-sport comparison.</p></div></div>
  <div class="notice" style="margin-top:18px"><strong>Data provenance:</strong> ${esc(p.source)}. Do not use fictional demo profiles to make real recruitment decisions.</div>${workspaceProfiles.panel(p)}`;
}
function fitPage(){
  const sport=state.fitSport,roles=rolesOf(sport);
  if(!roles.includes(state.fitRole))state.fitRole=roles[0];
  if(!state.weights)state.weights={...state.config.roles[sport][state.fitRole]};
  const labels=featureLabels(sport),pool=state.players.filter(p=>p.sport===sport);
  return `<div class="page-head"><div><div class="kicker">THE DECISION ENGINE / 03</div><h1 class="page-title">TEAM-FIT <span class="accent">INTELLIGENCE.</span></h1><p class="intro">Define the role. Set your priorities. Discover which player adds the most value to your team.</p></div><span class="tag">EXPLAINABLE MATCHING</span></div>
  <div class="fit-layout"><div class="fit-config panel panel-pad"><div class="eyebrow">01 / DEFINE YOUR REQUIREMENTS</div><h2 class="panel-title">Build your ideal profile.</h2><p class="panel-sub">Change the criteria to see different candidates emerge.</p><div class="divider"></div>
  <div class="field"><label>SELECT SPORT</label>${sportSwitch(sport,'fit')}</div><div class="field" style="margin-top:18px"><label>REQUIRED POSITION</label><select id="fit-role" class="select" style="width:100%">${roles.map(r=>`<option ${r===state.fitRole?'selected':''}>${esc(r)}</option>`).join('')}</select></div>
  <div class="divider"></div><div class="eyebrow">02 / SKILL PRIORITIES</div><div class="weight-list">${Object.entries(state.weights).map(([key,value])=>`<div><div class="weight-line"><label for="weight-${key}">${esc(labels[key]||key)}</label><output id="out-${key}">${value}%</output></div><input class="range" type="range" id="weight-${key}" data-weight="${key}" min="0" max="100" value="${value}" aria-label="Weight for ${esc(labels[key]||key)}"/></div>`).join('')}</div>
  <p class="helper" style="margin-top:10px">Weights are normalized automatically. They do not need to total 100.</p><div class="divider"></div><div class="eyebrow">03 / EXISTING TEAM (OPTIONAL)</div><p class="panel-sub" style="margin:8px 0 12px">Select existing players to identify complementary skill gaps.</p><div class="roster-list">${pool.map(p=>`<button class="roster-chip ${state.roster.includes(p.id)?'selected':''}" data-roster="${esc(p.id)}">${state.roster.includes(p.id)?'✓ ': '+ '}${esc(p.name)}</button>`).join('')}</div><div class="divider"></div><div class="eyebrow">04 / SAVE YOUR TEAM</div><div class="field" style="margin:10px 0"><label for="team-name">TEAM NAME</label><input class="input" id="team-name" placeholder="e.g. City Eleven" value="${esc(state.teamName)}" maxlength="100"/></div><button class="btn" id="save-team" style="width:100%;margin-bottom:12px">SAVE TEAM CONFIGURATION ${icon('plus')}</button>${state.teams.length?`<div class="field"><label for="saved-team">LOAD SAVED TEAM</label><select class="select" id="saved-team" style="width:100%"><option value="">Choose saved team...</option>${state.teams.map(t=>`<option value="${t.id}">${esc(t.name)} — ${esc(t.sport)}</option>`).join('')}</select></div><div class="divider"></div>`:''}<button id="generate-fit" class="btn btn-primary" style="width:100%">GENERATE RECOMMENDATIONS ${icon('arrow')}</button></div>
  <div><div class="result-header"><div><div class="eyebrow">RANKED INTELLIGENCE</div><h2 class="panel-title" style="font-size:26px">Recommended candidates</h2></div><span class="tag neutral">${sport.toUpperCase()}</span></div><div id="fit-results">${renderFitResults()}</div></div></div>`;
}
function renderFitResults(){
  if(!state.fitResults)return `<div class="panel panel-pad" style="min-height:330px;display:grid;place-content:center;text-align:center"><div style="font-size:44px;color:var(--lime)">◎</div><h3 class="panel-title">Ready to discover fit.</h3><p class="panel-sub">Configure a role and generate your first ranking.</p></div>`;
  const results=state.fitResults.results;
  return `<div class="notice" style="margin-bottom:15px"><strong>${results.length} candidates evaluated.</strong> Rankings combine skill weights, role compatibility and optional roster gap bonuses. Scores are decision-support estimates.</div>${results.length?results.map((r,i)=>`<article class="result-card"><div class="rank">${String(i+1).padStart(2,'0')}</div><div class="result-main"><h3>${esc(r.player.name)}</h3><p>${esc(r.player.role)} &nbsp; • &nbsp; ${esc(r.player.country)} &nbsp; • &nbsp; ${r.coverage}% FEATURE COVERAGE</p>${r.reasons.slice(0,3).map(s=>`<div class="reason">${esc(s)}</div>`).join('')}<details class="fit-explanation"><summary>Why this fit score?</summary><p class="helper">${esc(r.player.source)}</p><ul>${Object.entries(r.contributions||{}).map(([key,points])=>`<li>${esc(featureLabels(r.player.sport)[key]||key)} · ${points} points</li>`).join('')}<li>Role compatibility · ${r.role_points} points</li>${r.gap_bonus?`<li>Squad gap bonus · ${r.gap_bonus} points</li>`:''}</ul>${r.missing_features?.length?`<p class="helper">Unavailable · ${esc(r.missing_features.map(key=>featureLabels(r.player.sport)[key]||key).join(', '))}</p>`:''}</details><button type="button" class="btn btn-sm" data-simulate-player="${esc(r.player.id)}">Simulate addition</button>
      <div class="team-simulation" id="simulate-${esc(r.player.id)}" aria-live="polite"></div><button class="section-link" style="padding:10px 0 0" data-player="${esc(r.player.id)}">VIEW PROFILE ↗</button></div><div><div class="score-num">${r.score}<small>FIT SCORE / 100</small></div><div class="score-mini">ROLE ${r.role_match} /100</div>${r.gap_bonus?`<div class="score-mini accent">+${r.gap_bonus} GAP BONUS</div>`:''}</div></article>`).join(''):`<div class="empty">No candidates have sufficient evidence for these criteria.</div>`}`;
}
async function generateFit(){
  const btn=document.getElementById('generate-fit');if(btn){btn.disabled=true;btn.textContent='ANALYZING PLAYER FIT...'}
  try{
    state.fitResults=await request('/recommendations',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sport:state.fitSport,role:state.fitRole,weights:state.weights,roster_ids:state.roster})});
    document.getElementById('fit-results').innerHTML=renderFitResults();
  }catch(e){toast(e.message,true)}finally{if(btn){btn.disabled=false;btn.innerHTML=`GENERATE RECOMMENDATIONS ${icon('arrow')}`}}
}
async function simulateAddition(playerId){
  const output = document.getElementById('simulate-' + playerId);
  const ranked = state.fitResults;
  if (!output || !ranked) return;
  output.textContent = 'Running squad simulation…';
  try {
    const result = await request('/teams/simulate',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({sport:ranked.sport,role:ranked.role,weights:ranked.weights,
        roster_ids:ranked.roster_ids,proposed_roster_ids:[...ranked.roster_ids,playerId]})});
    if (!output.isConnected) return;
    const labels = featureLabels(ranked.sport);
    const lead = setup => setup.recommendations[0]?.player.name ?? 'Unavailable';
    output.innerHTML = `<p><strong>Squad simulation</strong> · ${esc(result.role)}</p>
      <p class="helper">Exact-role members ${result.before.exact_role} → ${result.after.exact_role}. Next recommendation ${esc(lead(result.before))} → ${esc(lead(result.after))}.</p>
      <ul>${Object.entries(result.before.skills).map(([key,before]) => {
        const after = result.after.skills[key];
        return `<li>${esc(labels[key] || key)} · ${before.mean ?? 'Unavailable'} → ${after.mean ?? 'Unavailable'} · ${before.observed} → ${after.observed} contributing profiles</li>`;
      }).join('')}</ul>`;
  } catch (error) { if (output.isConnected) output.textContent = error.message; }
}

function comparePage(){
  const sport=state.sport;const pool=state.players.filter(p=>p.sport===sport);
  if(!pool.find(p=>p.id===state.compareA))state.compareA=pool[0]?.id;
  if(!pool.find(p=>p.id===state.compareB))state.compareB=pool[1]?.id;
  const a=getPlayer(state.compareA),b=getPlayer(state.compareB);
  return `<div class="page-head"><div><div class="kicker">HEAD TO HEAD / 04</div><h1 class="page-title">PLAYER <span class="accent">COMPARISON.</span></h1><p class="intro">See strengths and gaps side by side. Only players from the same sport are comparable.</p></div></div>
  <div class="toolbar">${sportSwitch(sport)}<span class="tag neutral">NORMALIZED METRICS</span></div><div class="compare-columns">${[['compare-a',a],['compare-b',b]].map(([id,p])=>`<div class="compare-player"><div class="eyebrow">${id==='compare-a'?'CANDIDATE / 01':'CANDIDATE / 02'}</div><select class="select" id="${id}" style="width:100%;margin:13px 0">${pool.map(q=>`<option value="${esc(q.id)}" ${q.id===p?.id?'selected':''}>${esc(q.name)} — ${esc(q.role)}</option>`).join('')}</select>${p?`<h3>${esc(p.name)}</h3><p class="panel-sub">${esc(p.role)} • ${esc(p.country)}</p>${radarSvg(p,300)}`:''}</div>`).join('')}</div>
  ${a&&b?`<div class="panel panel-pad" style="margin-top:17px"><div class="eyebrow">CAPABILITY DIFFERENTIAL</div><h2 class="panel-title">Skill-by-skill comparison</h2><div class="compare-table">${featuresOf(sport).map(f=>`<div><div class="compare-numbers"><span>${a.features[f.key]??'—'}</span><span>${b.features[f.key]??'—'}</span></div><div class="compare-metric"><div class="left"><i style="width:${a.features[f.key]||0}%"></i></div><div class="label">${esc(f.label)}</div><div class="right"><i style="width:${b.features[f.key]||0}%"></i></div></div></div>`).join('')}</div></div>`:''}<div class="notice" style="margin-top:17px">Comparison values are illustrative for seed profiles. These charts do not imply that higher scores alone determine team suitability.</div>`;
}
function visionPage(){
  return `<div class="page-head"><div><div class="kicker">COMPUTER VISION / 05</div><h1 class="page-title">VISION <span class="accent">LAB.</span></h1><p class="intro">From raw footage to visual signals. Upload a short clip to run person detection and approximate visual tracking.</p></div><span class="tag">OPENCV PIPELINE</span></div>
  <div class="panel panel-pad"><div class="eyebrow">01 / INPUT SOURCE</div><h2 class="panel-title">Analyze match footage.</h2><p class="panel-sub">MP4, MOV, AVI, MKV or WEBM • up to 25 MB • first 15 seconds sampled</p><div class="upload-zone" id="video-zone" style="margin-top:20px"><input id="video-file" type="file" accept="video/mp4,video/quicktime,video/x-msvideo,video/x-matroska,video/webm,.mp4,.mov,.avi,.mkv,.webm" aria-label="Choose a sports video"/><div class="upload-icon">${icon('upload',40)}</div><h3>DROP FOOTAGE HERE.</h3><p id="video-file-name">or click to choose a video from your device</p><span class="tag neutral">VIDEO INPUT / SECURE LOCAL PROCESSING</span></div><div style="display:flex;justify-content:space-between;align-items:center;gap:15px;margin-top:17px;flex-wrap:wrap"><span class="helper">Uses an optional local YOLO model when configured; otherwise OpenCV HOG person detection. No fictional detections are generated.</span><button class="btn btn-primary" id="analyze-video" ${state.videoPending ? 'disabled' : ''}>RUN VISION ANALYSIS ${icon('arrow')}</button></div></div>
  <div class="panel panel-pad" style="margin-top:18px"><div class="eyebrow">DEMO &amp; LIVE INPUT</div><h2 class="panel-title">Try the analysis pipeline</h2><p class="panel-sub">The built-in synthetic pitch clip tracks a colored marker and measures its pixel path; it is not real athlete or cricket-ball detection. For real detections, choose authorized cricket footage or capture a webcam clip.</p><div class="actions" style="display:flex;gap:10px;flex-wrap:wrap;margin-top:14px"><button class="btn" id="sample-video" ${state.videoPending ? 'disabled' : ''}>ANALYZE SAMPLE CLIP ${icon('play')}</button><button class="btn" id="webcam-record" ${state.videoPending ? 'disabled' : ''}>RECORD 5-SECOND CAMERA CLIP ${icon('camera')}</button></div><video id="camera-preview" autoplay muted playsinline hidden style="width:min(100%,420px);margin-top:14px"></video><p class="helper" id="camera-status">Camera access requires permission; footage is processed locally. Recording is not continuous live tracking.</p></div><div id="vision-results" style="margin-top:20px">${visionResult()}</div>
  <div class="section-head"><div><div class="kicker">MODEL TRANSPARENCY</div><h2>WHAT THE MODEL CAN SEE.</h2></div></div><div class="steps"><div class="step"><span class="step-num">01</span><h3>DECODE.</h3><p>Extract and sample frames from the uploaded video with OpenCV.</p></div><div class="step"><span class="step-num">02</span><h3>DETECT.</h3><p>Use YOLO when installed, otherwise OpenCV HOG. A simple centroid tracker links nearby detections.</p></div><div class="step"><span class="step-num">03</span><h3>ANNOTATE.</h3><p>Save a labeled preview, annotated video and tracking metadata. Review visible drill attempts to calculate clip-specific skill scores.</p></div></div>`;
}
function visionResult(){
  if(state.videoPending)return '<p class="notice" role="status">Analyzing video. Results will appear here.</p>';
  const v=state.lastVideo;if(!v)return `<div class="notice">Upload a clip to begin. The output will contain actual model detections, an annotated preview, and an explicit detector label.</div>`;
  return `<div class="panel panel-pad"><div class="eyebrow">02 / ANALYSIS COMPLETE</div><h2 class="panel-title">${esc(v.filename)}</h2><div class="video-result" style="margin-top:18px"><div>${v.preview?`<img src="${esc(v.preview)}" alt="Last analyzed video frame with model detection boxes"/>${v.browser_video?`<video controls playsinline preload="metadata" src="${esc(v.output)}" style="width:100%;margin-top:10px;border-radius:10px"></video>`:""}`:''}</div><div><div class="video-stat"><span>STATUS</span><strong class="accent">COMPLETE</strong></div><div class="video-stat"><span>DETECTOR</span><strong>${esc(v.detector)}</strong></div><div class="video-stat"><span>FRAMES SAMPLED</span><strong>${v.frames}</strong></div><div class="video-stat"><span>FRAME DETECTIONS</span><strong>${v.detections}</strong></div><div class="video-stat"><span>TRACKS (2+ OBSERVATIONS)</span><strong>${v.tracks??0}</strong></div><div class="video-stat"><span>SAMPLED DURATION</span><strong>${v.sample_duration_s??"—"} s</strong></div>${v.synthetic_fixture?`<div class="video-stat"><span>MARKER PATH / IMAGE PLANE</span><strong>${v.marker_path_px} px</strong></div>`:""}<p class="helper" style="margin:17px 0">${esc(v.note)}</p>${v.output?`<a class="btn btn-primary" href="${esc(v.output)}" download>DOWNLOAD ANNOTATED VIDEO ${icon('arrow')}</a>`:''}</div></div>${videoAssessment.panel(v, state.videoReview)}</div>`;
}
function importPage(){
  const sport=state.sport;
  return `<div class="page-head"><div><div class="kicker">DATA OPERATIONS / 06</div><h1 class="page-title">DATA <span class="accent">STUDIO.</span></h1><p class="intro">Bring your own talent. Import pre-normalized scouting data or create an individual player profile.</p></div><div class="actions"><a class="btn" href="/assets/sample_import.csv" download>${icon('file')} NORMALIZED TEMPLATE</a><a class="btn" href="/assets/sample_raw_import.csv" download>${icon('file')} RAW STATS TEMPLATE</a></div></div>
  <div class="fit-layout"><div class="panel panel-pad"><div class="eyebrow">01 / BATCH IMPORT</div><h2 class="panel-title">Import player profiles.</h2><p class="panel-sub">Import normalized feature scores or aggregated raw match statistics.</p><div class="field" style="margin-top:18px"><label for="csv-mode">DATA FORMAT</label><select class="select" id="csv-mode" style="width:100%"><option value="normalized">Normalized skill scores (0–100)</option><option value="raw">Raw aggregated match statistics</option></select></div><div class="upload-zone" style="margin:20px 0"><input type="file" id="csv-file" accept=".csv,text/csv" aria-label="Choose CSV file"/><div class="upload-icon">${icon('file',38)}</div><h3>YOUR DATA. OUR ENGINE.</h3><p id="csv-file-name">Choose a CSV file • up to 2 MB</p></div><button class="btn btn-primary" id="import-csv" style="width:100%">IMPORT PLAYER DATA ${icon('arrow')}</button><div class="notice orange" style="margin-top:18px"><strong>Important:</strong> Normalized CSV values must be 0–100. Raw statistics are converted using disclosed illustrative reference ranges; unmeasured skills remain missing.</div></div>
  <div class="panel panel-pad"><div class="eyebrow">02 / MANUAL ENTRY</div><h2 class="panel-title">Create a new player.</h2><div class="form-grid" style="margin:20px 0"><div class="field"><label for="new-name">PLAYER NAME</label><input class="input" id="new-name" placeholder="e.g. Alex Morgan" maxlength="100"/></div><div class="field"><label for="new-country">COUNTRY CODE</label><input class="input" id="new-country" placeholder="e.g. IN" maxlength="5"/></div><div class="field"><label for="new-sport">SPORT</label><select class="select" id="new-sport"><option value="cricket" ${sport==='cricket'?'selected':''}>Cricket</option></select></div><div class="field"><label for="new-role">ROLE</label><select class="select" id="new-role">${rolesOf(sport).map(r=>`<option>${esc(r)}</option>`).join('')}</select></div></div><div class="eyebrow">SKILL SCORES / 100</div><div id="new-features" class="form-grid" style="margin:14px 0">${manualFeatureInputs(sport)}</div><button class="btn btn-primary" id="create-player" style="width:100%">SAVE PLAYER PROFILE ${icon('plus')}</button></div></div>
  <div class="section-head"><div><div class="kicker">DATA SCHEMA</div><h2>IMPORT REFERENCE.</h2><p>Use supported feature keys exactly as listed.</p></div></div><div class="panel panel-pad"><div class="table-wrap"><table class="data-table"><thead><tr><th>SPORT</th><th>REQUIRED COLUMNS</th><th>SUPPORTED FEATURE COLUMNS</th></tr></thead><tbody><tr><td>Cricket</td><td>name, sport, role</td><td>batting, strike, consistency, fielding, bowling, economy, finishing</td></tr></tbody></table></div></div>`;
}
function manualFeatureInputs(sport){return featuresOf(sport).map(f=>`<div class="field"><label for="f-${f.key}">${esc(f.label)}</label><input class="input" id="f-${f.key}" type="number" min="0" max="100" placeholder="Not measured" data-new-feature="${f.key}"/></div>`).join('')}
function aboutPage(){
  return `<div class="page-head"><div><div class="kicker">THE VIXISU METHOD</div><h1 class="page-title">INTELLIGENCE <span class="accent">WITH INTENT.</span></h1><p class="intro">A transparent approach to performance signals, team requirements and explainable recommendations.</p></div></div><div class="story-panel"><div><div class="kicker">OUR NORTH STAR</div><h2>TALENT IS EVERYWHERE.<br/><span class="accent">FIT IS EVERYTHING.</span></h2><p>We don't just find the highest-rated player. We help teams understand what they're missing, what each player contributes and why a candidate fits.</p></div><div class="story-symbol" aria-hidden="true">V·</div></div>
  ${section('HOW IT WORKS','THREE LAYERS. ONE MISSION.','Cricket performance indicators feed a transparent, reusable role-matching engine.')}
  <div class="steps"><div class="step"><div class="step-num">01</div><h3>DOMAIN SIGNALS.</h3><p>This cricket edition uses cricket-specific statistics and role definitions. Other sports can be added separately.</p></div><div class="step"><div class="step-num">02</div><h3>TALENT VECTOR.</h3><p>Normalized sport-specific indicators are stored with their definitions, provenance and data coverage.</p></div><div class="step"><div class="step-num">03</div><h3>TEAM-FIT ENGINE.</h3><p>Weighted skill fit, role compatibility and bounded roster-gap bonuses produce an interpretable candidate ranking.</p></div></div>
  ${section('ENGINE TRANSPARENCY','WHAT THE SCORE MEANS.','A score is a structured decision-support estimate, not a prediction of future success.')}
  <div class="panel panel-pad"><div class="eyebrow">SCORING MODEL</div><h2 class="panel-title">FIT = 0.85 × SKILL MATCH + 0.15 × ROLE MATCH + ROSTER GAP BONUS</h2><p class="panel-sub">The gap bonus is capped at eight points. Weights are normalized across available features, and candidates need at least 50% weighted feature coverage. Candidates already on the selected roster are excluded from recruitment results.</p><div class="divider"></div><div class="eyebrow">KNOWN LIMITATIONS</div><p class="small muted">Seed player profiles are fictional. Video analysis identifies people in sampled frames but does not establish identity, speed, shot accuracy, cricket technique or player potential. The prototype is not validated for professional recruitment, and real use requires sourced datasets, role-appropriate calibration, expert evaluation, privacy safeguards and bias testing.</p></div>`;
}
function render(){
  if(!state.config)return;
  app.innerHTML=shell();
  const page=document.getElementById('page');
  page.innerHTML=({'/':overviewPage,'/scout':cricketScout.page,'/talent':talentPage,'/profile':profilePage,'/team-fit':fitPage,'/compare':comparePage,'/vision':visionPage,'/import':importPage,'/about':aboutPage}[state.route]||overviewPage)();
  if(state.route==='/scout') cricketScout.mount();
  if(state.route==='/vision') videoAssessment.mount(state.videoReview);
  if(state.route==='/profile' && getPlayer(state.profileId)) workspaceProfiles.mount(getPlayer(state.profileId));
  if(state.route==='/talent') workspaceProfiles.mountArchive();
}
async function refreshData(){
  const [players,overview,teams]=await Promise.all([request('/players?sport=cricket'),request('/overview'),request('/teams')]);
  state.players=players.players;state.overview=overview;state.teams=teams.teams.filter(t=>t.sport==='cricket');
  state.roster=state.roster.filter(id=>getPlayer(id));
}
async function initialize(){
  try{
    state.config=await request('/config');
    await refreshData();
    state.profileId=new URLSearchParams(location.search).get('id')||state.profileId;
    if(!['/','/scout','/talent','/profile','/team-fit','/compare','/vision','/import','/about'].includes(state.route))state.route='/';
    render();
  }catch(e){app.innerHTML=`<div class="loading-screen"><div class="brand-glyph">V·</div><h2>CONNECTION UNAVAILABLE</h2><p>${esc(e.message)}</p><p>Start the FastAPI server with <code>python run.py</code> and refresh.</p></div>`}
}
// Central event delegation keeps pages lightweight and avoids unnecessary listeners.
document.addEventListener('click',async e=>{
  const n=e.target.closest('[data-nav]');if(n){e.preventDefault();navigate(n.dataset.nav);return}
  const sw=e.target.closest('[data-switch]');if(sw){const [kind,sport]=sw.dataset.switch.split(':');if(kind==='fit'){state.fitSport=sport;state.fitRole=rolesOf(sport)[0];state.weights={...state.config.roles[sport][state.fitRole]};state.roster=[];state.fitResults=null}else{state.sport=sport;state.roleFilter='all';state.search='';state.compareA=null;state.compareB=null}render();return}
  const domain=e.target.closest('[data-domain]');if(domain){state.sport=domain.dataset.domain;state.roleFilter='all';state.search='';navigate('/talent');return}
  const player=e.target.closest('[data-player]');if(player){navigate('/profile',{id:player.dataset.player});return}
  const cmp=e.target.closest('[data-compare-add]');if(cmp){const p=getPlayer(cmp.dataset.compareAdd);state.sport=p.sport;state.compareA=p.id;state.compareB=state.players.find(q=>q.sport===p.sport&&q.id!==p.id)?.id; navigate('/compare');return}
  if(e.target.closest('[data-toggle-menu]')){state.mobileOpen=!state.mobileOpen;render();return}
  if(e.target.closest('[data-close-menu]')){state.mobileOpen=false;render();return}
  const roster=e.target.closest('[data-roster]');if(roster){const id=roster.dataset.roster;state.roster=state.roster.includes(id)?state.roster.filter(x=>x!==id):[...state.roster,id];roster.classList.toggle('selected');roster.textContent=(state.roster.includes(id)?'✓ ':'+ ')+getPlayer(id).name;return}
  const simulation=e.target.closest('[data-simulate-player]');
  if(simulation){await simulateAddition(simulation.dataset.simulatePlayer);return}
  if(e.target.closest('#generate-fit')){await generateFit();return}
  if(e.target.closest('#save-team')){await saveTeam();return}
  if(e.target.closest('#analyze-video')){await uploadVideo();return}
  if(e.target.closest('#sample-video')){await runSampleVideo();return}
  if(e.target.closest('#webcam-record')){await recordWebcam();return}
  if(e.target.closest('#import-csv')){await uploadCsv();return}
  if(e.target.closest('#create-player')){await createPlayer();return}
});
document.addEventListener('input',e=>{
  if(e.target.id==='talent-search'){
    state.search=e.target.value;
    const cards=document.querySelectorAll('[data-player-card]');
    let shown=0;cards.forEach(c=>{const p=getPlayer(c.dataset.playerCard);const visible=p.name.toLowerCase().includes(state.search.toLowerCase());c.style.display=visible?'':'none';if(visible)shown++});
    return;
  }
  if(e.target.matches('[data-weight]')){
    const k=e.target.dataset.weight;state.weights[k]=Number(e.target.value);
    const out=document.getElementById('out-'+k);if(out)out.textContent=e.target.value+'%';return;
  }
});
document.addEventListener('change',e=>{
  if(e.target.id==='role-filter'){state.roleFilter=e.target.value;render();return}
  if(e.target.id==='fit-role'){state.fitRole=e.target.value;state.weights={...state.config.roles[state.fitSport][state.fitRole]};state.fitResults=null;render();return}
  if(e.target.id==='saved-team'&&e.target.value){const t=state.teams.find(x=>String(x.id)===e.target.value);if(t){state.fitSport=t.sport;state.fitRole=t.role;state.weights={...t.weights};state.roster=t.roster_ids.filter(id=>getPlayer(id));state.teamName=t.name;state.fitResults=null;render();toast('Loaded saved team configuration.')}return}
  if(e.target.id==='compare-a'){state.compareA=e.target.value;render();return}
  if(e.target.id==='compare-b'){state.compareB=e.target.value;render();return}
  if(e.target.id==='new-sport'){
    const sport=e.target.value;document.getElementById('new-role').innerHTML=rolesOf(sport).map(r=>`<option>${esc(r)}</option>`).join('');
    document.getElementById('new-features').innerHTML=manualFeatureInputs(sport);return;
  }
  if(e.target.id==='video-file'){document.getElementById('video-file-name').textContent=e.target.files?.[0]?.name||'Choose a sports video';return}
  if(e.target.id==='csv-file'){document.getElementById('csv-file-name').textContent=e.target.files?.[0]?.name||'Choose a CSV file';return}
});
window.addEventListener('popstate',()=>{state.route=location.pathname;state.profileId=new URLSearchParams(location.search).get('id');render()});
async function saveTeam(){
  const name=document.getElementById('team-name')?.value.trim();
  if(!name||name.length<2){toast('Enter a team name.',true);return}
  state.teamName=name;
  try{await workspaceWrite('/teams','POST',{name,sport:state.fitSport,role:state.fitRole,weights:state.weights,roster_ids:state.roster});state.teams=(await request('/teams')).teams.filter(t=>t.sport==='cricket');render();toast('Team configuration saved.')}catch(e){toast(e.message,true)}
}
function updateVisionResult() {
  const results = document.getElementById('vision-results');
  if (results) {
    results.innerHTML = visionResult();
    videoAssessment.mount(state.videoReview);
  }
  for (const id of ['analyze-video', 'sample-video']) {
    const button = document.getElementById(id);
    if (button) button.disabled = state.videoPending;
  }
  return results;
}

async function analyzeClip(path, file) {
  if (state.videoPending) return false;
  state.videoPending = true;
  updateVisionResult();
  let completed = false;
  try {
    const body = file ? new FormData() : undefined;
    if (body) body.append('file', file);
    const result = await withWorkspaceAccess(() => request(path, {method:'POST', body}));
    if (state.videoReview) URL.revokeObjectURL(state.videoReview.url);
    state.lastVideo = result;
    state.videoReview = file ? {url:URL.createObjectURL(file), drill:'batting', attempts:[], savedPlayer:null} : null;
    completed = true;
    toast(file ? 'Video analysis completed.' : 'Sample tracking completed.');
  } catch (error) {
    toast(error.message, true);
  } finally {
    state.videoPending = false;
    const results = updateVisionResult();
    if (completed) results?.scrollIntoView({block:'start'});
  }
  if (completed) {
    try { state.overview = await request('/overview'); } catch { /* The clip result is already available. */ }
  }
  return completed;
}

async function uploadVideo(provided){
  const file = provided || document.getElementById('video-file')?.files?.[0];
  if (!file) {
    toast('Choose a video first.', true);
    return false;
  }
  return analyzeClip('/videos/analyze', file);
}
async function uploadCsv(){
  const file=document.getElementById('csv-file')?.files?.[0];if(!file){toast('Choose a CSV file first.',true);return}
  const btn=document.getElementById('import-csv');btn.disabled=true;btn.textContent='IMPORTING...';
  const form=new FormData();form.append('file',file);
  const mode=document.getElementById('csv-mode')?.value||'normalized';
  try{const result=await withWorkspaceAccess(() => request(mode==='raw'?'/players/import-raw':'/players/import',{method:'POST',body:form}));await refreshData();toast(`Imported ${result.imported} player profiles.`);state.search='';state.roleFilter='all';navigate('/talent')}catch(e){toast(e.message,true)}finally{btn.disabled=false;btn.innerHTML=`IMPORT PLAYER DATA ${icon('arrow')}`}
}
async function createPlayer(){
  const name=document.getElementById('new-name')?.value.trim();
  const country=document.getElementById('new-country')?.value.trim();
  const sport=document.getElementById('new-sport')?.value;
  const role=document.getElementById('new-role')?.value;
  const features={};document.querySelectorAll('[data-new-feature]').forEach(el=>{if(el.value!=='')features[el.dataset.newFeature]=Number(el.value)});
  if(!name||name.length<2){toast('Enter a player name with at least two characters.',true);return}
  try{const p=await workspaceWrite('/players','POST',{name,country,sport,role,features});await refreshData();toast('Player profile created.');navigate('/profile',{id:p.id})}catch(e){toast(e.message,true)}
}
async function runSampleVideo(){
  return analyzeClip('/videos/sample');
}
async function recordWebcam(){
 const b=document.getElementById('webcam-record'),v=document.getElementById('camera-preview'),msg=document.getElementById('camera-status');let stream;
 if(state.videoPending)return;
 b.disabled=true;
 try{if(!navigator.mediaDevices?.getUserMedia||!window.MediaRecorder)throw Error('Camera recording is not supported in this browser. Use Chrome or Edge on localhost.');
 stream=await navigator.mediaDevices.getUserMedia({video:true,audio:false});v.srcObject=stream;v.hidden=false;
 const recorder=new MediaRecorder(stream);const chunks=[];recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};
 const stopped=new Promise((resolve,reject)=>{recorder.onstop=resolve;recorder.onerror=reject});recorder.start();msg.textContent='Recording a 5-second clip…';await new Promise(r=>setTimeout(r,5000));recorder.stop();await stopped;stream.getTracks().forEach(t=>t.stop());v.hidden=true;
 const type=recorder.mimeType||'video/webm';const ext=type.includes('mp4')?'mp4':'webm';msg.textContent='Recording finished. Processing the clip locally…';const completed=await uploadVideo(new File(chunks,'camera_clip.'+ext,{type}));msg.textContent=completed?'Camera session ended.':'Camera clip analysis did not complete.';
 }catch(e){toast(e.message||'Camera recording failed',true);msg.textContent='Camera unavailable. Use the upload or sample option.'}finally{if(stream)stream.getTracks().forEach(t=>t.stop());v.hidden=true;b.disabled=false}
}
initialize();
