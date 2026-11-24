/* Human-observed drill outcomes with optional attachment to a workspace profile. */
const videoAssessment = (() => {
  const minimumAttempts = 5;
  const drills = {
    batting: { label: 'Batting contact', success: 'Bat contacts the ball' },
    bowling: { label: 'Bowling target accuracy', success: 'Delivery hits the marked target' },
    fielding: { label: 'Catching success', success: 'Fielder completes the catch' },
  };
  const timestamp = (seconds) => {
    const minutes = Math.floor(seconds / 60);
    return minutes + ':' + (seconds % 60).toFixed(2).padStart(5, '0');
  };

  function percent(part, whole) {
    return Number.isFinite(part) && whole > 0 ? Math.round(10000 * part / whole) / 100 : null;
  }

  function meterCard(label, value, detail, suffix) {
    return `<div class="vision-meter-card">
      <div class="vision-meter-label"><h4>${esc(label)}</h4>
      <strong>${value === null ? 'Insufficient evidence' : value + suffix}</strong></div>
      ${value === null ? '<div class="vision-meter-empty" aria-hidden="true"></div>' :
        `<meter class="vision-meter" min="0" max="100" value="${value}" aria-label="${esc(label)}">${value} out of 100</meter>`}
      <p class="helper">${esc(detail)}</p>
    </div>`;
  }

  function skillCards(review) {
    return Object.entries(drills).map(([key, drill]) => {
      const attempts = review?.attempts.filter(attempt => attempt.drill === key) ?? [];
      const successful = attempts.filter(attempt => attempt.success).length;
      const value = attempts.length >= minimumAttempts ? percent(successful, attempts.length) : null;
      const detail = value === null
        ? `${attempts.length} of ${minimumAttempts} reviewed attempts required. Success: ${drill.success.toLowerCase()}.`
        : `${successful} of ${attempts.length} attempts succeeded. Human-reviewed clip evidence.`;
      return meterCard(drill.label, value, detail, ' / 100');
    }).join('');
  }

  function panel(result, review) {
    const frames = result.frames;
    const detected = result.evidence?.frames_with_detection;
    const longest = result.evidence?.longest_track_frames;
    const subject = result.synthetic_fixture ? 'marker' : 'person';
    return `<section class="vision-assessment" aria-labelledby="skill-meter-title">
      <div class="eyebrow">${result.synthetic_fixture ? 'SYNTHETIC DEMONSTRATION' : 'CLIP REVIEW'}</div>
      <h3 class="panel-title" id="skill-meter-title">Skill meter</h3>
      <p class="panel-sub">${review ?
        'Review visible attempts by one player in the original clip. Each score is the percentage of attempts that succeeded in this clip.' :
        'Cricket skill ratings require reviewed sporting attempts from an uploaded clip.'}</p>
      <div class="vision-meter-grid" id="vision-skill-cards" aria-live="polite">${skillCards(review)}</div>
      ${review ? `<details class="vision-review">
        <summary>Review attempts and score skills</summary>
        <p class="helper">Pause at each attempt and mark its outcome. Skip obscured attempts. Use a visible target when reviewing bowling accuracy.</p>
        <video controls playsinline preload="metadata" id="vision-original" src="${esc(review.url)}" aria-label="Original uploaded video"></video>
        <div class="vision-review-actions">
          <label for="vision-drill">Skill
            <select class="select" id="vision-drill">
              ${Object.entries(drills).map(([key, drill]) => `<option value="${key}" ${key === review.drill ? 'selected' : ''}>${esc(drill.label)}</option>`).join('')}
            </select>
          </label>
          <button type="button" class="btn btn-sm" data-attempt="success" disabled>Mark success</button>
          <button type="button" class="btn btn-sm" data-attempt="miss" disabled>Mark miss</button>
        </div>
        <p class="helper" id="vision-review-status" role="status">Mark at least five attempts in a drill to save a review.</p>
        <div id="vision-attempts">${timeline(review)}</div>
        <form class="vision-review-actions review-save" id="vision-save-review">
          <label for="vision-save-player">Cricket profile<select class="select" id="vision-save-player" required>
            <option value="">Choose a profile</option>${state.players.filter(player => player.sport === 'cricket' && !player.demo).map(player =>
              `<option value="${esc(player.id)}" ${review.savedPlayer === player.id ? 'selected' : ''}>${esc(player.name)}</option>`).join('')}
          </select></label>
          <button type="submit" class="btn btn-primary btn-sm" disabled>${review.savedPlayer ? 'Update saved review' : 'Save to profile'}</button>
          ${state.players.some(player => player.sport === 'cricket' && !player.demo) ? '' : '<button class="btn btn-sm" type="button" data-nav="/import">Create a player profile</button>'}
        </form>
      </details>` : ''}
      <h3 class="panel-title vision-evidence-title">Tracking evidence</h3>
      <p class="helper">The detector measures visibility and track continuity in the sampled frames.</p>
      <div class="vision-meter-grid">
        ${meterCard('Detection coverage', percent(detected, frames),
          detected === undefined ? 'Frame visibility was not recorded for this result.' : `${detected} of ${frames} sampled frames contained a ${subject} detection.`, '%')}
        ${meterCard('Longest continuous track', percent(longest, frames),
          longest === undefined ? 'Track continuity was not recorded for this result.' : `${longest} consecutive sampled frames on one approximate ${subject} track, out of ${frames} sampled.`, '%')}
      </div>
    </section>`;
  }

  function timeline(review) {
    if (!review.attempts.length) return '';
    return `<ol class="vision-attempts" aria-label="Reviewed attempts">${review.attempts.map((attempt, index) => `
      <li><button type="button" class="btn btn-sm" data-review-seek="${index}" aria-label="Jump to ${timestamp(attempt.seconds)}">${timestamp(attempt.seconds)}</button>
        <span>${drills[attempt.drill].label} · ${attempt.success ? 'Success' : 'Miss'}</span>
        <button type="button" class="btn btn-sm" data-review-remove="${index}" aria-label="Remove attempt at ${timestamp(attempt.seconds)}">Remove</button></li>`).join('')}</ol>`;
  }

  function mount(review) {
    const player = document.getElementById('vision-original');
    if (!player || !review) return;
    const status = document.getElementById('vision-review-status');
    const drill = document.getElementById('vision-drill');
    const list = document.getElementById('vision-attempts');
    const controls = player.closest('details').querySelectorAll('[data-attempt]');
    const saveForm = document.getElementById('vision-save-review');
    const savePlayer = document.getElementById('vision-save-player');
    const saveButton = saveForm.querySelector('[type=submit]');
    if (review.savedPlayer) savePlayer.disabled = true;
    const updateSave = () => {
      const enough = Object.keys(drills).some(key => review.attempts.filter(attempt => attempt.drill === key).length >= minimumAttempts);
      saveButton.disabled = !enough || !savePlayer.value || !state.lastVideo.source_duration_s;
    };
    const update = () => {
      document.getElementById('vision-skill-cards').innerHTML = skillCards(review);
      list.innerHTML = timeline(review);
      updateSave();
    };
    const ready = () => controls.forEach(button => { button.disabled = player.readyState < 1; });
    player.addEventListener('loadedmetadata', ready);
    player.addEventListener('error', () => {
      controls.forEach(button => { button.disabled = true; });
      status.textContent = 'This browser could not play the original clip. Use a browser-compatible MP4 or WebM to review attempts.';
    });
    ready();
    drill.addEventListener('change', () => { review.drill = drill.value; });
    savePlayer.addEventListener('change', updateSave);
    saveForm.addEventListener('submit', async event => {
      event.preventDefault();
      const playerId = savePlayer.value;
      saveButton.disabled = true;
      try {
        await workspaceWrite('/players/' + encodeURIComponent(playerId) + '/video-reviews','POST',{
          video_id:state.lastVideo.id, attempts:review.attempts,
        });
        review.savedPlayer = playerId;
        savePlayer.disabled = true;
        saveButton.textContent = 'Update saved review';
        status.textContent = 'Review saved to the player’s media library.';
      } catch (error) {
        status.textContent = error.message;
      } finally {
        updateSave();
      }
    });
    updateSave();
    for (const button of controls) {
      button.addEventListener('click', () => {
        player.pause();
        const seconds = Math.floor(player.currentTime * 100) / 100;
        if (review.attempts.some(attempt => attempt.drill === review.drill && Math.abs(attempt.seconds - seconds) < 0.25)) {
          status.textContent = 'An attempt already exists at this point. Seek to a different attempt.';
          return;
        }
        review.attempts.push({ seconds, drill: review.drill, success: button.dataset.attempt === 'success' });
        review.attempts.sort((a, b) => a.seconds - b.seconds);
        update();
        status.textContent = `Attempt recorded at ${timestamp(seconds)}.`;
      });
    }
    list.addEventListener('click', (event) => {
      const button = event.target.closest('button');
      if (!button) return;
      if ('reviewSeek' in button.dataset) {
        player.currentTime = review.attempts[Number(button.dataset.reviewSeek)].seconds;
      }
      if ('reviewRemove' in button.dataset) {
        review.attempts.splice(Number(button.dataset.reviewRemove), 1);
        update();
        controls[0].focus();
        status.textContent = 'Attempt removed.';
      }
    });
  }

  return {panel, mount};
})();
