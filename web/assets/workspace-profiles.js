const workspaceProfiles = (() => {
  const formats = ['Test', 'ODI', 'IT20', 'T20', 'T10', 'MDM', 'ODM', 'Other'];
  const counts = {
    matches:'Matches', innings:'Batting innings', runs:'Runs', balls_faced:'Balls faced',
    dismissals:'Dismissals', highest_score:'Highest score', fours:'Fours', sixes:'Sixes',
    wickets:'Wickets', balls_bowled:'Legal balls bowled', overs:'Overs notation',
    runs_conceded:'Runs conceded', dot_balls:'Dot balls', catches:'Catches', stumpings:'Stumpings',
  };
  const rates = {
    batting_average:'Batting average', strike_rate:'Batting strike rate',
    bowling_average:'Bowling average', economy:'Bowling economy', bowling_strike_rate:'Bowling strike rate',
    boundary_run_percent:'Runs from boundaries (%)', dot_ball_percent:'Dot balls (%)',
  };
  const drills = {batting:'Batting contact', bowling:'Bowling target accuracy', fielding:'Catching success'};
  const metricNumber = new Intl.NumberFormat(undefined, {maximumFractionDigits:2});
  const display = (value) => value == null ? 'Unavailable' : metricNumber.format(value);
  const timestamp = (seconds) => {
    const minutes = Math.floor(seconds / 60);
    return minutes + ':' + (seconds % 60).toFixed(2).padStart(5, '0');
  };
  const field = (name, label, value = '', type = 'text', attributes = '') =>
    `<label class="field">${esc(label)}<input class="input" name="${name}" type="${type}" value="${esc(value)}" ${attributes}></label>`;

  function panel(player) {
    return `<section class="workspace-profile panel panel-pad" id="workspace-profile" aria-label="Workspace profile management">
      <div class="workspace-header"><div><h2 class="panel-title">Profile records</h2><p class="helper" id="profile-details"></p></div>
        <div class="actions"><button class="btn" type="button" id="profile-edit">Edit profile</button>
          <button class="btn" type="button" id="profile-archive">Archive profile</button>
          <button class="btn" type="button" id="profile-report">Download scouting report</button></div></div>
      ${player.sport === 'cricket' ? `<section class="workspace-section">
        <h3 class="panel-title">Cricket statistics</h3>
        <div id="profile-statistics" aria-live="polite">Loading cricket records…</div>
        <details><summary>Add or update a scorecard</summary>
          <form id="profile-stats-form">
            <div class="workspace-fields">
              <label class="field">Format<select class="select" name="format">${formats.map(format => `<option>${format}</option>`).join('')}</select></label>
              ${field('competition','Competition','','text','maxlength="120"')}
              ${field('season','Season','','text','maxlength="30"')}
              ${field('source','Scorecard or data source','','text','required maxlength="300"')}
              ${Object.entries(counts).map(([name,label]) => name === 'overs'
                ? field(name,label,'','text','placeholder="4.2" maxlength="12"')
                : field(name,label,'','number','min="0" max="10000000" step="1"')).join('')}
            </div>
            <p class="helper">Save one record per format, competition, and season. Leave unknown counts blank.</p>
            <button class="btn btn-primary" type="submit">Save statistics</button>
          </form>
        </details>
      </section>` : ''}
      <details class="workspace-section" id="profile-vector-details">
        <summary>Talent vector and evidence</summary><div id="profile-vector"></div>
      </details>
      <section class="workspace-section">
        <div class="workspace-header"><h3 class="panel-title">Media and clip reviews</h3>
          <button type="button" class="btn btn-sm" id="profile-load-media">Open media library</button></div>
        <div id="profile-media" aria-live="polite"></div>
        <details><summary>Add a licensed photograph or video link</summary>
          <form id="profile-media-form">
            <div class="workspace-fields">
              <label class="field">Media type<select name="kind" class="select"><option value="photo">Profile photograph</option><option value="video">Video link</option></select></label>
              ${field('title','Title','','text','required maxlength="160"')}
              ${field('url','HTTPS link','','url','required maxlength="2083"')}
              ${field('attribution','Creator and license or permission','','text','required maxlength="300"')}
            </div>
            <p><label><input type="checkbox" name="authorized" required> I have permission to use this media.</label></p>
            <button class="btn btn-primary" type="submit">Save media</button>
          </form>
        </details>
      </section>
      <dialog id="profile-edit-dialog" class="scout-dialog" aria-labelledby="profile-edit-title">
        <header><h2 class="panel-title" id="profile-edit-title">Edit profile</h2>
          <button class="btn" id="profile-edit-close" type="button">Close</button></header>
        <form id="profile-edit-form"></form>
      </dialog>
    </section>`;
  }

  function statsMarkup(records) {
    if (!records.length) return '<p class="helper">No scorecard statistics have been added.</p>';
    return records.map((record,index) => `<details class="workspace-record"><summary>${esc(
      [record.format,record.competition,record.season].filter(Boolean).join(' · '))}</summary>
      <p class="helper">User-entered scorecard · ${esc(record.source)}</p>
      <dl class="scout-metrics">${Object.entries({...counts,...rates}).filter(([key]) => key !== 'overs')
        .map(([key,label]) => `<div><dt>${label}</dt><dd>${display(record.counts[key] ?? record.rates[key])}</dd></div>`).join('')}</dl>
      <button type="button" class="btn btn-sm" data-stat-edit="${index}">Edit scorecard</button></details>`).join('');
  }

  function mediaMarkup(library) {
    const links = library.media.map(item => `<li>
      <a href="${esc(item.url)}" target="_blank" rel="noopener noreferrer">${esc(item.title)}</a>
      <span class="helper">${esc(item.attribution)} · ${esc(item.created_at)}</span>
      <button type="button" class="btn btn-sm" data-remove-media="${item.id}">Remove link</button>
    </li>`);
    const reviews = library.reviews.map(review => `<details class="workspace-record">
      <summary>${esc(review.filename)} · Human-reviewed clip</summary>
      <p class="helper">Updated ${esc(review.updated_at)}. Scores use marked attempts from the original clip.</p>
      <dl class="scout-metrics">${Object.entries(review.metrics).map(([key,metric]) =>
        `<div><dt>${drills[key]}</dt><dd>${display(metric.score)}${metric.score == null ? '' : ' / 100'}</dd>
        <span class="helper">${metric.successes} / ${metric.observations} successes</span></div>`).join('')}</dl>
      ${review.browser_video ? `<video class="workspace-video" controls playsinline preload="none" src="${esc(review.output)}" aria-label="Annotated analysis video"></video>` : ''}
      <a class="btn btn-sm" href="${esc(review.output)}" download>Download annotated clip</a>
      <ol class="vision-attempts" aria-label="Reviewed attempts">${review.attempts.map(attempt =>
        `<li>${review.browser_video && attempt.seconds < review.sample_duration_s
          ? `<button type="button" class="btn btn-sm" data-review-jump="${attempt.seconds}">${timestamp(attempt.seconds)}</button>`
          : `<time>${timestamp(attempt.seconds)}</time>`} ${drills[attempt.drill]} · ${attempt.success ? 'Success' : 'Miss'}</li>`).join('')}</ol>
      </details>`);
    return `${links.length ? '<ul class="workspace-media-list">' + links.join('') + '</ul>' : ''}${reviews.join('')}${!links.length && !reviews.length ? '<p class="helper">No media or videos are available for this player.</p>' : ''}`;
  }

  function mount(player) {
    const root = document.getElementById('workspace-profile');
    if (!root) return;
    const path = '/players/' + encodeURIComponent(player.id);
    const edit = root.querySelector('#profile-edit-form');
    const dialog = root.querySelector('#profile-edit-dialog');
    const statForm = root.querySelector('#profile-stats-form');
    const statList = root.querySelector('#profile-statistics');
    const mediaForm = root.querySelector('#profile-media-form');
    const mediaList = root.querySelector('#profile-media');
    let records = [];

    async function refreshDetails() {
      const profile = await request(path);
      if (root.isConnected) root.querySelector('#profile-details').textContent =
        [profile.team, profile.style, profile.source_note].filter(Boolean).join(' · ');
      return profile;
    }
    async function refreshStats() {
      if (!statList) return;
      records = (await request(path + '/statistics')).statistics;
      statList.innerHTML = statsMarkup(records);
    }
    async function refreshMedia() {
      const library = await request(path + '/media');
      mediaList.innerHTML = mediaMarkup(library);
      const photo = library.media.find(item => item.kind === 'photo');
      const visual = document.querySelector('.profile-photo');
      if (root.isConnected && visual) {
        if (photo) {
          visual.src = photo.url;
          visual.alt = player.name + ' · ' + photo.attribution;
        } else {
          visual.removeAttribute('src');
        }
        visual.hidden = !photo;
      }
    }
    const showError = error => toast(error.message,true);

    refreshDetails().catch(showError);
    refreshStats().catch(error => { if (statList) statList.textContent = error.message; });
    refreshMedia().catch(error => { mediaList.textContent = error.message; });
    const vectorDetails = root.querySelector('#profile-vector-details');
    vectorDetails.addEventListener('toggle', async () => {
      const output = root.querySelector('#profile-vector');
      if (!vectorDetails.open || output.childElementCount) return;
      try {
        const vector = await request(path + '/talent-vector');
        output.innerHTML = `<dl class="scout-metrics">${Object.values(vector.features).map(feature =>
          `<div><dt>${esc(feature.label)}</dt><dd>${display(feature.score)}${feature.score === null ? '' : ' / 100'}</dd>
          <span class="helper">${esc(feature.source_type.replaceAll('_',' '))}${feature.confidence ? ' · ' + esc(feature.confidence) : ''}</span>
          ${feature.method ? `<div class="helper">${esc(feature.method)}</div>` : ''}</div>`).join('')}</dl>`;
      } catch (error) { output.textContent = error.message; }
    });

    root.querySelector('#profile-edit').onclick = async () => {
      try {
        const current = await refreshDetails();
        const sport = current.sport;
        edit.innerHTML = `<div class="workspace-fields">
          ${field('name','Name',current.name,'text','required maxlength="100"')}
          ${field('country','Country code',current.country,'text','maxlength="5"')}
          ${field('age','Age',current.age,'number','min="13" max="100" step="1"')}
          <label class="field">Role<select class="select" name="role">${rolesOf(sport).map(role =>
            `<option ${current.role === role ? 'selected' : ''}>${esc(role)}</option>`).join('')}</select></label>
          ${field('team','Team',current.team,'text','maxlength="100"')}
          ${field('style','Playing style',current.style,'text','maxlength="100"')}
          ${field('source_note','Data source',current.source_note,'text','maxlength="500"')}
          </div><h3>Manual skill scores</h3><p class="helper">Leave unavailable scores blank.</p>
          <div class="workspace-fields">${featuresOf(sport).map(feature =>
            field('skill-' + feature.key,feature.label,current.features[feature.key],'number','min="0" max="100" step="any"')).join('')}</div>
          <button class="btn btn-primary" type="submit">Save changes</button>`;
        if (root.isConnected) dialog.showModal();
      } catch (error) { showError(error); }
    };
    root.querySelector('#profile-edit-close').onclick = () => dialog.close();
    edit.onsubmit = async event => {
      event.preventDefault();
      const fields = Object.fromEntries(new FormData(edit));
      const features = {};
      for (const [key,value] of Object.entries(fields)) {
        if (!key.startsWith('skill-')) continue;
        if (value !== '') features[key.slice(6)] = Number(value);
        delete fields[key];
      }
      try {
        await workspaceWrite(path,'PATCH',{...fields,age:fields.age ? Number(fields.age) : null,features});
        await refreshData();
        if (root.isConnected) render();
        toast('Profile updated.');
      } catch (error) { showError(error); }
    };
    root.querySelector('#profile-archive').onclick = async () => {
      if (!window.confirm('Archive ' + player.name + '? The player will be hidden from discovery and new recommendations. Existing scorecards, media and saved team records will be retained.')) return;
      try {
        await workspaceWrite(path,'DELETE');
        await refreshData();
        if (root.isConnected) navigate('/talent');
        toast('Profile archived.');
      } catch (error) { showError(error); }
    };

    if (statForm) {
      statForm.onsubmit = async event => {
        event.preventDefault();
        const fields = Object.fromEntries(new FormData(statForm));
        const {format,competition,season,source} = fields;
        const values = Object.fromEntries(Object.keys(counts).filter(key => fields[key] !== '')
          .map(key => [key,key === 'overs' ? fields[key] : Number(fields[key])]));
        try {
          await workspaceWrite(path + '/statistics','PUT',{format,competition,season,source,counts:values});
          await refreshStats();
          statForm.reset();
          toast('Statistics saved.');
        } catch (error) { showError(error); }
      };
      statList.onclick = event => {
        const button = event.target.closest('[data-stat-edit]');
        if (!button) return;
        const record = records[Number(button.dataset.statEdit)];
        const values = {...record,...record.counts};
        for (const input of statForm.elements) {
          if (input.name) input.value = values[input.name] ?? '';
        }
        statForm.closest('details').open = true;
        statForm.querySelector('[name=competition]').focus();
      };
    }

    root.querySelector('#profile-report').onclick = async () => {
      try {
        await withWorkspaceAccess(async () => {
          const [profile, vector, library, stats] = await Promise.all([
            request(path), request(path + '/talent-vector'), request(path + '/media'), request(path + '/statistics'),
          ]);
          downloadReport(profile, vector, library, stats.statistics);
        });
      } catch (error) { showError(error); }
    };

    root.querySelector('#profile-load-media').onclick = () =>
      withWorkspaceAccess(refreshMedia).catch(showError);
    mediaForm.onsubmit = async event => {
      event.preventDefault();
      const payload = Object.fromEntries(new FormData(mediaForm));
      try {
        await workspaceWrite(path + '/media','POST',{...payload,authorized:payload.authorized === 'on'});
        await refreshMedia();
        mediaForm.reset();
        toast('Media added.');
      } catch (error) { showError(error); }
    };
    mediaList.onclick = async event => {
      const remove = event.target.closest('[data-remove-media]');
      const jump = event.target.closest('[data-review-jump]');
      if (jump) {
        const video = jump.closest('details').querySelector('video');
        video.currentTime = Number(jump.dataset.reviewJump);
        return;
      }
      if (!remove || !window.confirm('Remove this linked media item from the player profile?')) return;
      try {
        await workspaceWrite(path + '/media/' + remove.dataset.removeMedia,'DELETE');
        await refreshMedia();
      } catch (error) { showError(error); }
    };
  }

  function archiveDialog() {
    return `<dialog class="scout-dialog" id="player-archive-dialog" aria-labelledby="archive-dialog-title">
      <header><h2 id="archive-dialog-title" class="panel-title">Archived profiles</h2>
      <button type="button" class="btn" id="close-player-archive">Close</button></header><div id="archive-dialog-list"></div></dialog>`;
  }

  function mountArchive() {
    const dialog = document.getElementById('player-archive-dialog');
    const list = document.getElementById('archive-dialog-list');
    document.getElementById('close-player-archive').onclick = () => dialog.close();
    document.getElementById('open-player-archive').onclick = async () => {
      dialog.showModal();
      list.textContent = 'Loading archived profiles…';
      try {
        const archived = await withWorkspaceAccess(() => request('/players/archive/list'));
        const players = archived.players.filter(player => player.sport === 'cricket');
        list.innerHTML = players.length ? `<ul class="workspace-media-list">${players.map(player =>
          `<li>${esc(player.name)} · ${esc(player.role)} <button class="btn btn-sm" type="button"
            data-restore-player="${esc(player.id)}">Restore</button></li>`).join('')}</ul>`
          : '<p>No archived cricket profiles.</p>';
      } catch (error) { list.textContent = error.message; }
    };
    list.onclick = async event => {
      const restore = event.target.closest('[data-restore-player]');
      if (!restore) return;
      try {
        await workspaceWrite('/players/' + encodeURIComponent(restore.dataset.restorePlayer) + '/restore','POST');
        await refreshData();
        if (dialog.isConnected) render();
        toast('Profile restored.');
      } catch (error) { toast(error.message,true); }
    };
  }

  function downloadReport(profile, vector, library, statistics) {
    const photo = library.media.find(item => item.kind === 'photo');
    const fit = state.fitResults?.results.find(result => result.player.id === profile.id);
    const item = (label, value) => `<li><strong>${esc(label)}</strong> · ${esc(value)}</li>`;
    const list = entries => `<ul>${entries.join('')}</ul>`;
    const html = `<!doctype html><html lang="en"><meta charset="utf-8"><title>${esc(profile.name)} | VIXISU scouting report</title>
      <meta name="viewport" content="width=device-width,initial-scale=1">
      <style>body{font:16px/1.5 system-ui,sans-serif;max-width:850px;margin:36px auto;padding:0 18px;color:#17251c}h1,h2{line-height:1.1}img{max-width:210px;max-height:230px;object-fit:contain}section{margin-block:24px}li{margin-block:5px}@media print{img,li{break-inside:avoid}}</style>
      <p>VIXISU scouting report</p><h1>${esc(profile.name)}</h1><p>${esc([profile.sport,profile.role,profile.country,profile.team].filter(Boolean).join(' · '))}</p>
      ${profile.demo ? '<p>Illustrative demo profile</p>' : ''}${photo ? `<figure><img src="${esc(photo.url)}" alt="${esc(profile.name)}" referrerpolicy="no-referrer"><figcaption>${esc(photo.attribution)}</figcaption></figure>` : ''}
      <section><h2>Cricket statistics</h2>${statistics.length ? statistics.map(record =>
        `<h3>${esc([record.format,record.competition,record.season].filter(Boolean).join(' · '))}</h3><p>User-entered scorecard · ${esc(record.source)}</p>
          ${list(Object.entries({...counts,...rates}).filter(([key]) => (record.counts[key] ?? record.rates[key]) != null)
            .map(([key,label]) => item(label,display(record.counts[key] ?? record.rates[key]))))}`).join('')
        : '<p>No scorecards in the profile.</p>'}</section>
      <section><h2>Talent vector</h2>${list(Object.values(vector.features).map(feature =>
        item(feature.label,[display(feature.score),feature.source_type.replaceAll('_',' '),feature.method,feature.source].filter(Boolean).join(' · '))))}</section>
      <section><h2>Human-reviewed clips</h2>${library.reviews.length ? library.reviews.map(review =>
        `<h3>${esc(review.filename)}</h3>${list(Object.entries(review.metrics).map(([key,metric]) =>
          item(drills[key], display(metric.score) + ' · ' + metric.successes + ' successes across ' + metric.observations + ' attempts')))}
          ${list(review.attempts.map(attempt => item(timestamp(attempt.seconds),drills[attempt.drill] + ' · ' + (attempt.success ? 'Success' : 'Miss'))))}`).join('')
        : '<p>No saved clip reviews.</p>'}</section>
      <section><h2>Latest team-fit result</h2>${fit ? `<p>${esc(state.fitResults.role)} · ${fit.score} / 100 · ${fit.coverage}% weighted evidence coverage</p>
        ${list(fit.reasons.map(reason => esc(reason)).map(reason => `<li>${reason}</li>`))}`
        : '<p>Generate a Team Fit ranking in this tab to include a result for this player.</p>'}</section>
      <section><h2>Media sources</h2>${list(library.media.map(media => item(media.title,media.attribution + ' · ' + media.url)))}</section></html>`;
    const url = URL.createObjectURL(new Blob([html],{type:'text/html;charset=utf-8'}));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'vixisu-' + profile.id.toLowerCase() + '-scouting-report.html';
    link.click();
    setTimeout(() => URL.revokeObjectURL(url),1000);
  }

  return {panel,mount,archiveDialog,mountArchive};
})();
