/* The Cricsheet workspace uses a common cohort for evidence and its Decision Lab. */
const cricketScout = (() => {
  const fields = ["team_type", "gender", "format", "competition", "season"];
  const fieldLabels = {
    team_type: "Circuit", gender: "Category", format: "Format",
    competition: "Competition", season: "Season",
  };
  const metricLabels = {
    batting: "Batting average", strike: "Runs per 100 legal balls", finishing: "Runs per 100 late-over balls",
    bowling: "Wickets per 120 legal balls", economy: "Runs per six legal balls",
  };
  const pretty = (value) => ({club:"Domestic and franchise", international:"International", female:"Women's cricket", male:"Men's cricket"}[value] || value);
  const number = new Intl.NumberFormat(undefined, {maximumFractionDigits: 2});
  const value = (raw) => raw === null || raw === undefined ? "Unavailable" : number.format(raw);
  const pageSize = 20;
  const selected = new Map();
  const roster = new Map();
  const cohort = Object.fromEntries(fields.map(key => [key, ""]));
  let archive;
  let search = "";
  let criterion = "matches";
  let role = "Opener";
  let weights;
  let offset = 0;
  let renderId = 0;
  let searchTimer;
  let currentPage;
  const id = (key) => document.getElementById(key);
  const scope = () => new URLSearchParams(Object.entries(cohort).filter(([,filter]) => filter));
  const comparable = () => fields.every(key => cohort[key]);
  const complete = () => comparable() && cohort.format === "T20";
  let pendingProfile = new URLSearchParams(location.search).get("player");

  function page() {
    return `<div class="page-head"><div><div class="kicker">CRICSHEET MATCH EVIDENCE</div>
      <h1 class="page-title">SCOUTING <span class="accent">ROOM.</span></h1>
      <p class="intro">Find players across domestic and international cricket, then rank candidates against your team’s priorities.</p></div></div>
      <section id="cricket-scout" class="panel panel-pad" aria-label="Cricket archive"><p role="status">Loading cricket evidence…</p></section>
      <dialog id="scout-detail" class="scout-dialog" aria-labelledby="scout-title">
        <header><h2 id="scout-title" class="panel-title"></h2><button class="btn" id="scout-close" type="button">Close</button></header>
        <div id="scout-detail-body"></div>
      </dialog>`;
  }

  async function mount() {
    const root = id("cricket-scout");
    if (!root) return;
    currentPage = root;
    try {
      archive ||= await request("/cricket/coverage");
      if (root !== currentPage || !root.isConnected) return;
      renderControls();
      await refresh();
      if (pendingProfile && root === currentPage && root.isConnected) {
        const playerId = pendingProfile;
        pendingProfile = null;
        await showProfile(playerId);
      }
    } catch (error) {
      if (root.isConnected) root.textContent = error.message;
    }
  }

  function options(key) {
    const prior = fields.slice(0, fields.indexOf(key));
    const possible = archive.cohorts.filter(item => prior.every(field => !cohort[field] || item[field] === cohort[field]));
    return [...new Set(possible.map(item => item[key]).filter(Boolean))]
      .sort((a,b) => key === "season" ? b.localeCompare(a, undefined, {numeric:true}) : a.localeCompare(b));
  }

  function renderControls() {
    currentPage.innerHTML = `<p class="helper">${value(archive.players)} players · ${value(archive.matches)} matches · ${esc(archive.first_match)} to ${esc(archive.latest_match)} · <a href="https://cricsheet.org/downloads/">Cricsheet</a></p>
      <div class="scout-controls">${fields.map(key => `<label>${fieldLabels[key]}<select class="select" data-cohort="${key}">
        <option value="">All</option>${options(key).map(item => `<option value="${esc(item)}" ${cohort[key] === item ? "selected" : ""}>${esc(pretty(item))}</option>`).join("")}</select></label>`).join("")}</div>
      <div class="scout-controls secondary"><label>Player or team<input type="search" class="input" id="scout-search" placeholder="Search the selected coverage" value="${esc(search)}"></label>
        <label>Sort by<select class="select" id="scout-sort">${Object.entries({matches:"Appearances",runs:"Runs",wickets:"Wickets",name:"Name"}).map(([key,label]) => `<option value="${key}" ${criterion===key?"selected":""}>${label}</option>`).join("")}</select></label>
      </div>
      <details class="scout-copilot">
        <summary>Scouting copilot</summary>
        <form id="scout-question">
          <label class="field">Question<input class="input" name="question" maxlength="300" required placeholder="Find aggressive T20 openers"></label>
          <p class="helper">Uses the filters above. Rank one role, enter “find player NAME”, or compare the selected players.</p>
          <button class="btn" type="submit">Run scouting query</button>
        </form>
        <div id="scout-answer" aria-live="polite"></div>
      </details>
      <div id="scout-list" aria-live="polite"></div><div id="scout-fit"></div>`;
    currentPage.onchange = (event) => {
      const key = event.target.dataset.cohort;
      if (key) {
        cohort[key] = event.target.value;
        for (const dependent of fields.slice(fields.indexOf(key) + 1)) {
          if (!options(dependent).includes(cohort[dependent])) cohort[dependent] = "";
        }
        resetSelection();
        renderControls();
        id("cricket-scout").querySelector(`[data-cohort="${key}"]`).focus();
        refresh();
      } else if (event.target.id === "scout-sort") {
        criterion = event.target.value;
        offset = 0;
        refresh();
      }
    };
    id("scout-search").addEventListener("input", (event) => {
      search = event.target.value;
      offset = 0;
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => { if (currentPage.isConnected) refresh(); }, 250);
    });
    id("scout-close").onclick = () => id("scout-detail").close();
    id("scout-question").onsubmit = askCopilot;
    renderFit();
  }

  async function askCopilot(event) {
    event.preventDefault();
    const output = id("scout-answer");
    output.textContent = "Checking the selected cricket evidence…";
    try {
      const question = new FormData(event.currentTarget).get("question");
      const result = await request("/scouting/query",{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({question,cohort,player_ids:[...selected.keys()],roster_ids:[...roster.keys()]})});
      if (!output.isConnected) return;
      if (result.action === "compare") {
        output.textContent = "Comparison ready for " + contextLabel();
        showComparison(result.players);
        return;
      }
      if (result.action === "rank") {
        output.innerHTML = `<p>${esc(result.role)} · ${esc(contextLabel())} · ${value(result.ranked)} ranked</p>
          <p class="helper">Weights · ${Object.entries(result.weights).map(([key,weight]) => metricLabels[key] + " " + value(weight)).join(" · ")}</p>
          ${result.results.length ? `<ol>${result.results.slice(0,5).map(row => `<li><button type="button" class="section-link" data-ask-profile="${esc(row.player.id)}">${esc(row.player.name)}</button>
            · ${value(row.score)} / 100 · ${row.coverage}% evidence coverage<p class="helper">${esc(row.reasons.join(" · "))}</p></li>`).join("")}</ol>` : "<p>No candidates have sufficient evidence.</p>"}`;
      } else {
        output.innerHTML = `<p>${value(result.total)} matching records · ${esc(contextLabel())}</p><ul>${result.players.map(row =>
          `<li><button type="button" class="section-link" data-ask-profile="${esc(row.player_id)}">${esc(row.name)}</button> · ${value(row.matches)} appearances</li>`).join("")}</ul>`;
      }
      output.querySelectorAll("[data-ask-profile]").forEach(button => {
        button.onclick = () => showProfile(button.dataset.askProfile);
      });
    } catch (error) {
      if (output.isConnected) output.textContent = error.message;
    }
  }

  function resetSelection() {
    selected.clear();
    roster.clear();
    offset = 0;
  }

  async function refresh() {
    const list = id("scout-list");
    const ticket = ++renderId;
    list.innerHTML = '<p role="status">Searching match records…</p>';
    const params = scope();
    params.set("q", search.trim());
    params.set("criterion", criterion);
    params.set("offset", offset);
    params.set("limit", pageSize);
    try {
      const response = await request("/cricket/players?" + params);
      if (ticket !== renderId || !list.isConnected) return;
      const rows = response.players;
      list.innerHTML = `<div class="scout-results-head"><p>${rows.length ? `${value(offset+1)}–${value(offset+rows.length)} of ${value(response.total)} players` : "No players match these filters."}</p>
        <button class="btn btn-sm" id="scout-compare" ${selected.size < 2 || !comparable() ? "disabled" : ""}>Compare (${selected.size})</button></div>
        ${!comparable() ? '<p class="helper">Choose a circuit, category, format, competition, and season to compare players in the same cohort.</p>' : ""}
        ${rows.length ? `<div class="scout-table-wrap"><table class="scout-table">
          <thead><tr><th>Player</th><th>Matches</th><th>Runs</th><th>Wickets</th><th>Compare</th>${complete() ? "<th>Squad</th>" : ""}</tr></thead>
          <tbody>${rows.map(row => `<tr><th scope="row"><button class="section-link" data-scout-player="${esc(row.player_id)}">${esc(row.name)}</button>
            <div class="helper">${esc(row.teams?.split(",").slice(0, 2).join(", ") || "")}</div></th>
            <td>${value(row.matches)}</td><td>${value(row.runs)}</td><td>${value(row.wickets)}</td>
            <td><input type="checkbox" aria-label="Compare ${esc(row.name)}" data-scout-select="${esc(row.player_id)}" ${selected.has(row.player_id) ? "checked" : ""} ${!comparable() || (selected.size >= 3 && !selected.has(row.player_id)) ? "disabled" : ""}></td>
            ${complete() ? `<td><input type="checkbox" aria-label="Add ${esc(row.name)} to current squad" data-scout-roster="${esc(row.player_id)}" ${roster.has(row.player_id) ? "checked" : ""} ${roster.size >= 30 && !roster.has(row.player_id) ? "disabled" : ""}></td>` : ""}</tr>`).join("")}</tbody></table></div>` : ""}
        <div class="scout-results-head"><button class="btn btn-sm" id="scout-prev" ${!offset ? "disabled" : ""}>Previous</button>
        <button class="btn btn-sm" id="scout-next" ${offset + pageSize >= response.total ? "disabled" : ""}>Next</button></div>`;
      const byId = new Map(rows.map(row => [row.player_id, row]));
      list.querySelectorAll("[data-scout-player]").forEach(button => {button.onclick = () => showProfile(button.dataset.scoutPlayer);});
      list.querySelectorAll("[data-scout-select],[data-scout-roster]").forEach(input => {
        input.onchange = () => {
          const selection = input.dataset.scoutSelect ? selected : roster;
          const playerId = input.dataset.scoutSelect || input.dataset.scoutRoster;
          if (input.checked) selection.set(playerId, byId.get(playerId).name);
          else selection.delete(playerId);
          id("scout-compare").textContent = `Compare (${selected.size})`;
          id("scout-compare").disabled = selected.size < 2 || !comparable();
          list.querySelectorAll("[data-scout-select]").forEach(item => {item.disabled = !comparable() || (selected.size >= 3 && !item.checked);});
          list.querySelectorAll("[data-scout-roster]").forEach(item => {item.disabled = roster.size >= 30 && !item.checked;});
          if (selection === roster) renderFit();
        };
      });
      id("scout-compare").onclick = compare;
      id("scout-prev").onclick = () => { offset -= pageSize; refresh(); };
      id("scout-next").onclick = () => { offset += pageSize; refresh(); };
    } catch (error) {
      if (ticket === renderId && list.isConnected) list.textContent = error.message;
    }
  }

  function open(title, html) {
    const dialog = id("scout-detail");
    if (!dialog) return;
    id("scout-title").textContent = title;
    id("scout-detail-body").innerHTML = html;
    if (!dialog.open) dialog.showModal();
  }

  const rateRows = [
    ["Appearances", "matches"], ["Runs", "runs"], ["Wickets", "wickets"],
    ["Batting average", "batting_average"], ["Runs per 100 legal balls", "strike_rate"],
    ["Economy per six balls", "economy"], ["Highest innings score", "highest_score"],
    ["Runs from boundaries (%)", "boundary_run_percent"], ["Dot balls (%)", "dot_ball_percent"],
    ["Recorded catches", "catches"], ["Recorded stumpings", "stumpings"],
  ];
  const readMetric = (profile, key) => profile[key] ?? profile.rates?.[key];

  async function showProfile(playerId) {
    const root = currentPage;
    try {
      const params = scope().toString();
      const player = await request(`/cricket/players/${encodeURIComponent(playerId)}?${params}`);
      if (!root.isConnected || root !== currentPage || scope().toString() !== params) return;
      open(player.name, `${player.photo ? `<figure class="scout-photo"><img src="${esc(player.photo)}" alt="${esc(player.name)}"><figcaption><a href="/home#credits">Photography credits</a></figcaption></figure>` : ""}<p>${esc(player.description)}</p>
        <p class="helper">${esc(player.first_match)} to ${esc(player.latest_match)} · ${esc(contextLabel())} · <a href="https://cricsheet.org/downloads/">Cricsheet</a></p>
        <dl class="scout-metrics">${rateRows.map(([label,key]) => `<div><dt>${label}</dt><dd>${value(readMetric(player,key))}</dd></div>`).join("")}</dl>
        <p class="helper">Sample size · ${value(player.legal_balls_faced)} legal balls faced · ${value(player.dismissals)} dismissals · ${value(player.legal_balls_bowled)} legal balls bowled</p>
        <h3>Recent match evidence</h3><div class="scout-table-wrap"><table class="scout-table"><thead><tr><th>Date</th><th>Competition and season</th><th>Team</th><th>Runs</th><th>Wickets</th></tr></thead>
        <tbody>${player.recent_matches.map(match => `<tr><td>${esc(match.date)}</td><td>${esc(match.competition || match.format)} · ${esc(match.season)}</td>
          <td>${esc(match.team || "Unavailable")}</td><td>${value(match.runs)}</td><td>${value(match.wickets)}</td></tr>`).join("")}</tbody></table></div>`);
    } catch (error) { if (root.isConnected) toast(error.message, true); }
  }

  function contextLabel() {
    return fields.map(key => cohort[key] && pretty(cohort[key])).filter(Boolean).join(" · ") || "Full archive";
  }

  async function compare() {
    const root = currentPage;
    const params = scope().toString();
    try {
      const players = await Promise.all([...selected.keys()].map(key => request(`/cricket/players/${key}?${params}`)));
      if (!root.isConnected || scope().toString() !== params) return;
      showComparison(players);
    } catch (error) { if (root.isConnected) toast(error.message, true); }
  }

  function showComparison(players) {
      open("Compare players", `<p>${esc(contextLabel())}</p><div class="scout-table-wrap"><table class="scout-table">
        <thead><tr><th>Metric</th>${players.map(p => `<th>${esc(p.name)}</th>`).join("")}</tr></thead>
        <tbody>${rateRows.map(([label,key]) => {
          const entries = players.map(profile => readMetric(profile,key));
          const max = Math.max(0, ...entries.filter(Number.isFinite));
          return `<tr><th scope="row">${label}</th>${entries.map(entry => `<td>${value(entry)}${
            Number.isFinite(entry) && max > 0 ? `<div class="scout-bar" aria-hidden="true"><i style="width:${entry/max*100}%"></i></div>` : ""}</td>`).join("")}</tr>`;
        }).join("")}</tbody></table></div>`);
  }

  function renderFit() {
    const box = id("scout-fit");
    if (!complete()) {
      box.innerHTML = '<div class="divider"></div><h2 class="panel-title">Decision Lab</h2><p>Choose a circuit, category, named competition, T20 format, and season to rank candidates.</p><button class="btn" id="scout-example">Try IPL 2024</button>';
      id("scout-example").onclick = () => {
        Object.assign(cohort,{team_type:"club",gender:"male",format:"T20",competition:"Indian Premier League",season:"2024"});
        search = "";
        resetSelection();
        renderControls();
        refresh();
      };
      return;
    }
    weights ||= {...archive.role_weights[role]};
    box.innerHTML = `<div class="divider"></div><h2 class="panel-title">Decision Lab</h2><p>${esc(contextLabel())}</p>
      <p class="helper">Role eligibility uses observed match activity. Scores use this cohort’s metric ranges and the existing team-fit engine. Five-over finishing evidence uses full scheduled T20 innings.</p>
      <label class="field">Required role<select class="select" id="scout-role">${Object.keys(archive.role_weights).map(key => `<option ${key===role?"selected":""}>${esc(key)}</option>`).join("")}</select></label>
      <div class="scout-controls secondary">${Object.entries(weights).map(([key,weight]) => `<label>${metricLabels[key]}<input type="number" min="0" max="100" class="input" data-scout-weight="${key}" value="${weight}"></label>`).join("")}</div>
      <p class="helper">Current squad (${roster.size})${roster.size ? " · " + esc([...roster.values()].join(", ")) : " · Optional. Select existing players in the table."}</p>
      <button class="btn btn-primary" id="scout-rank">Rank candidates</button><div id="scout-rankings" aria-live="polite"></div>`;
    id("scout-role").onchange = (event) => {
      role = event.target.value;
      weights = {...archive.role_weights[role]};
      renderFit();
      id("scout-role").focus();
    };
    box.querySelectorAll("[data-scout-weight]").forEach(control => {
      control.oninput = () => {
        weights[control.dataset.scoutWeight] = Number(control.value);
        id("scout-rankings").replaceChildren();
      };
    });
    id("scout-rank").onclick = rank;
  }

  async function rank() {
    const results = id("scout-rankings");
    const button = id("scout-rank");
    const rankingWeights = JSON.stringify(weights);
    button.disabled = true;
    results.textContent = "Ranking candidates…";
    try {
      const result = await request("/cricket/decision-lab", {
        method:"POST", headers:{"Content-Type":"application/json"},
        body:JSON.stringify({cohort,role,weights,roster_ids:[...roster.keys()]}),
      });
      if (!results.isConnected || rankingWeights !== JSON.stringify(weights)) return;
      results.innerHTML = `<p>${value(result.ranked)} ranked of ${value(result.eligible)} eligible candidates${result.margin===null?"":` · Leader margin ${value(result.margin)} points`}</p>
        ${result.results.length ? '<button class="btn btn-sm" id="scout-report">Download scouting brief</button>' : ""}
        <p class="helper">Skill contributions are score points. Role eligibility contributes 15 points, and a selected squad can produce a bounded gap bonus.</p>
        <ol class="scout-ranking">${result.results.map(item => `<li><button class="section-link" data-result-player="${esc(item.player.id)}">${esc(item.player.name)}</button>
          <strong>${value(item.score)} / 100</strong><div class="helper">${value(item.player.matches)} appearances · ${item.coverage}% feature coverage${item.gap_bonus ? ` · +${value(item.gap_bonus)} squad gap points` : ""}</div>
          <ul>${Object.entries(item.contributions).map(([key,points]) => `<li>${metricLabels[key]} · ${value(item.player.measurements[key])} observed · ${value(item.player.features[key])}/100 normalized · +${value(points)} points</li>`).join("")}
          ${Object.keys(result.weights).filter(key => !(key in item.contributions)).map(key => `<li>${metricLabels[key]} · Insufficient evidence or unavailable cohort range</li>`).join("")}</ul></li>`).join("")}</ol>
        ${result.results.length ? `<h3>Ranking sensitivity</h3><ul>${result.scenarios.map(item => `<li>${metricLabels[item.metric]} +50% · ${esc(item.leader || "No rankable leader")}${item.same_leader ? " (same leader)" : ""}</li>`).join("")}</ul>` : '<p>No candidate meets the required weighted evidence coverage.</p>'}`;
      const report = id("scout-report");
      if (report) report.onclick = () => downloadBrief(result);
      results.querySelectorAll("[data-result-player]").forEach(item => {item.onclick = () => showProfile(item.dataset.resultPlayer);});
    } catch (error) { if (results.isConnected) results.textContent = error.message; }
    finally { button.disabled = false; }
  }

  function downloadBrief(result) {
    const leaders = result.results.map((entry, index) => {
      const metrics = Object.entries(entry.contributions).map(([key, points]) =>
        `  ${metricLabels[key]} · ${value(entry.player.measurements[key])} observed · ${value(points)} score points`);
      const missing = Object.keys(result.weights).filter(key => !(key in entry.contributions))
        .map(key => `  ${metricLabels[key]} · Insufficient evidence or unavailable cohort range`);
      return [`${index+1}. ${entry.player.name} · ${value(entry.score)} / 100 · ${entry.coverage}% coverage · ${entry.player.matches} appearances`,
        ...metrics, ...missing].join("\n");
    });
    const text = [
      "VIXISU SCOUTING BRIEF", contextLabel(), `Role · ${role}`,
      `Ranked · ${result.ranked} of ${result.eligible} eligible candidates`,
      `Leader margin · ${value(result.margin)} points`,
      `Weights · ${Object.entries(result.weights).map(([key,weight]) => metricLabels[key] + " " + weight).join(" · ")}`,
      `Squad · ${[...roster.values()].join(", ") || "No squad selected"}`, "",
      ...leaders, "", "SENSITIVITY", ...result.scenarios.map(entry =>
        `${metricLabels[entry.metric]} +50% · ${entry.leader || "Unavailable"}`),
      "", "These cohort-specific scores support scouting decisions.", "Source · " + result.source,
    ].join("\n");
    const url = URL.createObjectURL(new Blob([text],{type:"text/plain;charset=utf-8"}));
    const link = document.createElement("a");
    link.href = url;
    link.download = "vixisu-scouting-brief.txt";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return {page,mount};
})();
