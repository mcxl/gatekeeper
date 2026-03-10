function escapeHtml(str) {
  if (!str) return '';
  const d = document.createElement('div');
  d.textContent = String(str);
  return d.innerHTML;
}

/**
 * intake.js — Gatekeeper SWMS Generator frontend
 *
 * Sections:
 * 1. Init (populate dropdowns from window.GATEKEEPER)
 * 2. Mode switching (tab handlers)
 * 3. Form prefill (called by Modes 2 & 3)
 * 4. Document upload (drag-drop + file input -> POST /upload/extract)
 * 5. Plain description submit (textarea -> POST /upload/extract as JSON)
 * 6. Optional SWMS gap upload (POST /upload/swms-gap)
 * 7. Guided form submit (existing stream logic)
 * 8. Helpers (status, table, downloads)
 */

// ============================================================
// 1. INIT — populate dropdowns from injected data
// ============================================================

(function init() {
  const G = window.GATEKEEPER || {};

  // Task name autocomplete
  const dl = document.getElementById('task-suggestions');
  (G.taskNames || []).forEach(name => {
    const opt = document.createElement('option');
    opt.value = name;
    dl.appendChild(opt);
  });

  // Trade type dropdown
  const tradeSelect = document.getElementById('trade_type');
  tradeSelect.innerHTML = '<option value="">— Select —</option>';
  (G.tradeTypes || []).forEach(t => {
    const opt = document.createElement('option');
    opt.value = t;
    opt.textContent = t;
    tradeSelect.appendChild(opt);
  });

  // Principal contractor dropdown
  const pcSelect = document.getElementById('principal_contractor');
  pcSelect.innerHTML = '';
  (G.principalContractors || []).forEach((pc, i) => {
    const opt = document.createElement('option');
    opt.value = pc;
    opt.textContent = i === 0 ? `${pc} (no PC overlay)` : pc;
    pcSelect.appendChild(opt);
  });
})();


// ============================================================
// 2. MODE SWITCHING
// ============================================================

document.querySelectorAll('.mode-tab').forEach(tab => {
  tab.addEventListener('click', function() {
    // Deactivate all
    document.querySelectorAll('.mode-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.mode-panel').forEach(p => p.classList.remove('active'));
    // Activate clicked
    this.classList.add('active');
    const mode = this.dataset.mode;
    document.getElementById('panel-' + mode).classList.add('active');
  });
});

function switchToGuided() {
  document.querySelectorAll('.mode-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.mode-panel').forEach(p => p.classList.remove('active'));
  document.querySelector('[data-mode="guided"]').classList.add('active');
  document.getElementById('panel-guided').classList.add('active');
}


// ============================================================
// 3. FORM PREFILL — called by Modes 2 & 3
// ============================================================

function prefillGuidedForm(data) {
  if (data.description) {
    document.getElementById('task_name').value = data.description;
  }
  if (data.site_name) {
    document.getElementById('site_name').value = data.site_name;
  }
  if (data.principal_contractor) {
    const pcSelect = document.getElementById('principal_contractor');
    // Try exact match first, then partial
    const pcLower = data.principal_contractor.toLowerCase();
    let matched = false;
    for (const opt of pcSelect.options) {
      if (opt.value.toLowerCase() === pcLower) {
        pcSelect.value = opt.value;
        matched = true;
        break;
      }
    }
    if (!matched) {
      for (const opt of pcSelect.options) {
        if (pcLower.includes(opt.value.toLowerCase()) || opt.value.toLowerCase().includes(pcLower)) {
          pcSelect.value = opt.value;
          break;
        }
      }
    }
  }
  if (data.trade_type) {
    const tradeSelect = document.getElementById('trade_type');
    const tradeLower = data.trade_type.toLowerCase();
    for (const opt of tradeSelect.options) {
      if (opt.value.toLowerCase() === tradeLower) {
        tradeSelect.value = opt.value;
        break;
      }
    }
  }
  if (data.plant_equipment) {
    document.getElementById('plant_equipment').value = data.plant_equipment;
  }
  if (data.permits) {
    document.getElementById('permits').value = data.permits;
  }
}


// ============================================================
// 4. DOCUMENT UPLOAD — drag-drop + file input
// ============================================================

(function setupUpload() {
  const zone = document.getElementById('upload-drop-zone');
  const fileInput = document.getElementById('upload-file');
  const statusEl = document.getElementById('upload-status');

  zone.addEventListener('click', () => fileInput.click());

  zone.addEventListener('dragover', e => {
    e.preventDefault();
    zone.classList.add('drag-over');
  });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    if (e.dataTransfer.files.length > 0) {
      processUploadFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      processUploadFile(fileInput.files[0]);
    }
  });

  async function processUploadFile(file) {
    statusEl.style.display = 'block';
    statusEl.textContent = 'Extracting fields from ' + file.name + '...';
    statusEl.style.color = '#1a3a5c';

    const formData = new FormData();
    formData.append('file', file);

    try {
      const resp = await fetch('/upload/extract', {
        method: 'POST',
        body: formData,
      });
      const data = await resp.json();
      if (data.error) {
        statusEl.textContent = 'Error: ' + data.error;
        statusEl.style.color = '#8b0000';
        return;
      }
      statusEl.textContent = 'Fields extracted. Review the pre-filled form below.';
      statusEl.style.color = '#2e7d32';
      prefillGuidedForm(data);
      switchToGuided();
    } catch (err) {
      statusEl.textContent = 'Upload failed: ' + err.message;
      statusEl.style.color = '#8b0000';
    }
  }
})();


// ============================================================
// 5. PLAIN DESCRIPTION SUBMIT
// ============================================================

document.getElementById('describe-btn').addEventListener('click', async function() {
  const text = document.getElementById('describe-text').value.trim();
  if (!text) return;

  const btn = this;
  const statusEl = document.getElementById('describe-status');
  btn.disabled = true;
  btn.textContent = 'Extracting...';
  statusEl.style.display = 'block';
  statusEl.textContent = 'Sending to Claude for field extraction...';
  statusEl.style.color = '#1a3a5c';

  try {
    const resp = await fetch('/upload/extract', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    const data = await resp.json();
    if (data.error) {
      statusEl.textContent = 'Error: ' + data.error;
      statusEl.style.color = '#8b0000';
      return;
    }
    statusEl.textContent = 'Fields extracted. Review the pre-filled form.';
    statusEl.style.color = '#2e7d32';
    prefillGuidedForm(data);
    switchToGuided();
  } catch (err) {
    statusEl.textContent = 'Extraction failed: ' + err.message;
    statusEl.style.color = '#8b0000';
  } finally {
    btn.disabled = false;
    btn.textContent = 'Extract & Pre-fill';
  }
});


// ============================================================
// 6. SWMS GAP ANALYSIS UPLOAD
// ============================================================

document.getElementById('gap-upload-btn').addEventListener('click', async function() {
  const fileInput = document.getElementById('gap-file');
  if (!fileInput.files.length) return;

  const btn = this;
  const resultsDiv = document.getElementById('gap-results');
  btn.disabled = true;
  btn.textContent = 'Analysing...';
  resultsDiv.style.display = 'none';

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);

  try {
    const resp = await fetch('/upload/swms-gap', {
      method: 'POST',
      body: formData,
    });
    const data = await resp.json();
    if (data.error) {
      resultsDiv.style.display = 'block';
      resultsDiv.innerHTML = '<div style="color:#8b0000;">Error: ' + escapeHtml(data.error) + '</div>';
      return;
    }

    let html = '<strong>Gap Analysis Results</strong> (confidence: ' +
      Math.round((data.confidence || 0) * 100) + '%)<br><br>';

    if (data.gaps && data.gaps.length > 0) {
      html += '<strong style="color:#c62828;">Gaps Found:</strong><br>';
      data.gaps.forEach(g => { html += '<div class="gap-item">&#x2717; ' + escapeHtml(g) + '</div>'; });
      html += '<br>';
    }
    if (data.matched && data.matched.length > 0) {
      html += '<strong style="color:#2e7d32;">Requirements Met:</strong><br>';
      data.matched.forEach(m => { html += '<div class="match-item">&#x2713; ' + escapeHtml(m) + '</div>'; });
    }

    resultsDiv.style.display = 'block';
    resultsDiv.innerHTML = html;
  } catch (err) {
    resultsDiv.style.display = 'block';
    resultsDiv.innerHTML = '<div style="color:#8b0000;">Error: ' + escapeHtml(err.message) + '</div>';
  } finally {
    btn.disabled = false;
    btn.textContent = 'Analyse Gaps';
  }
});


// ============================================================
// 7. GUIDED FORM SUBMIT — streaming generation
// ============================================================

document.getElementById('swms-form').addEventListener('submit', async function(e) {
  e.preventDefault();

  const btn = document.getElementById('generate-btn');
  const meta = document.getElementById('result-meta');
  const downloads = document.getElementById('downloads');

  btn.disabled = true;
  btn.textContent = 'Generating...';
  setStatus('info', 'Analysing work description...');
  downloads.style.display = 'none';
  downloads.innerHTML = '';
  meta.textContent = '';

  const fd = new FormData(this);
  const description = fd.get('task_name');
  const plantEquipment = fd.get('plant_equipment') || '';
  const permits = fd.get('permits') || '';

  // Build a richer description if extra fields are filled
  let fullDescription = description;
  if (plantEquipment) fullDescription += '. Plant/equipment: ' + plantEquipment;
  if (permits) fullDescription += '. Permits: ' + permits;

  const payload = {
    description: fullDescription,
    project_meta: {
      project_name: fd.get('site_name') || '',
      site_address: fd.get('site_name') || '',
      principal_contractor: fd.get('principal_contractor') || 'General',
      trade_type: fd.get('trade_type') || '',
    },
  };

  let tbody = null;
  let allTasks = [];
  let lastInference = null;
  let taskTotal = 0;
  let tasksDone = 0;

  try {
    const resp = await fetch('/generate/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!resp.ok) {
      setStatus('error', 'Server error: ' + resp.status);
      return;
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        let event;
        try { event = JSON.parse(line.slice(6)); }
        catch { continue; }

        if (event.type === 'route') {
          lastInference = event.inference;
          const route = event.route;
          const hrcw = event.inference?.hrcw ? ' — HRCW' : '';
          setStatus('info', 'Pipeline: ' + route + hrcw + ' — waiting for tasks...');
        }

        else if (event.type === 'task_count') {
          taskTotal = event.count;
          setStatus('info', 'Generating ' + taskTotal + ' tasks...');
          tbody = initTable();
        }

        else if (event.type === 'task') {
          tasksDone++;
          allTasks.push(event.task);
          if (!tbody) tbody = initTable();
          appendTaskRow(tbody, event.task, event.index);
          setStatus('info', 'Generated ' + tasksDone + ' of ' + taskTotal + ' tasks...');
        }

        else if (event.type === 'done') {
          setStatus('ok', 'Generated — pipeline: ' + (event.route || 'full') + ' — ' + event.task_count + ' tasks');
          if (allTasks.length > 0) {
            addWordDownload(allTasks, payload.project_meta);
            if (lastInference) addJsonDownload(allTasks, lastInference);
          }
          if (lastInference) {
            const inf = lastInference;
            let parts = [];
            if (inf.hrcw) parts.push('HRCW: ' + (inf.hrcw_category || 'Yes'));
            if (inf.safework_notification_required) parts.push('SafeWork notification required');
            meta.textContent = parts.length > 0 ? parts.join(' | ') : 'Standard work — no HRCW triggers';
          }
        }

        else if (event.type === 'error') {
          setStatus('error', 'Error: ' + event.message);
        }
      }
    }

  } catch(err) {
    setStatus('error', 'Network error: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Generate SWMS';
  }
});


// ============================================================
// 8. HELPERS — status, table, downloads
// ============================================================

function setStatus(cls, text) {
  const s = document.getElementById('status');
  s.className = cls;
  s.style.display = 'block';
  s.textContent = text;
}

function initTable() {
  const downloads = document.getElementById('downloads');
  downloads.innerHTML = '';
  downloads.style.display = 'block';
  const table = document.createElement('table');
  table.id = 'task-table';
  table.style.cssText = 'width:100%;border-collapse:collapse;font-size:12px;margin-top:12px;';
  table.innerHTML =
    '<thead><tr style="background:#1a3a5c;color:#fff;">' +
    '<th style="padding:6px 8px;text-align:left;">#</th>' +
    '<th style="padding:6px 8px;text-align:left;">Task</th>' +
    '<th style="padding:6px 8px;">Risk</th>' +
    '<th style="padding:6px 8px;">CCVS</th>' +
    '<th style="padding:6px 8px;">Controls</th>' +
    '</tr></thead><tbody id="task-tbody"></tbody>';
  downloads.appendChild(table);
  return document.getElementById('task-tbody');
}

function appendTaskRow(tbody, t, index) {
  const bg = index % 2 === 0 ? '#f8f9fa' : '#fff';
  const ccvs = t.ccvs_code || 'N/A';
  const ccvsColor = ccvs !== 'N/A' ? '#c62828' : '#666';
  const riskPre = t.risk_pre || '?';
  const riskPost = t.risk_post || '?';
  const ctrlCount = (t.controls || []).length;
  const tr = document.createElement('tr');
  tr.style.cssText = 'background:' + bg + ';border-bottom:1px solid #e0e0e0;';
  tr.innerHTML =
    '<td style="padding:5px 8px;color:#999;">' + (index + 1) + '</td>' +
    '<td style="padding:5px 8px;">' + escapeHtml(t.task || '?') + '</td>' +
    '<td style="padding:5px 8px;text-align:center;">' + riskPre + ' &rarr; ' + riskPost + '</td>' +
    '<td style="padding:5px 8px;text-align:center;color:' + ccvsColor + ';font-weight:700;">' + ccvs + '</td>' +
    '<td style="padding:5px 8px;text-align:center;">' + ctrlCount + '</td>';
  tbody.appendChild(tr);
}

function addJsonDownload(allTasks, inference) {
  const downloads = document.getElementById('downloads');
  const payload = { tasks: allTasks, inference: inference };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'swms_tasks.json';
  a.textContent = 'Download JSON';
  a.className = 'dl-btn';
  a.style.cssText = 'display:inline-block;margin-bottom:10px;padding:8px 16px;background:#2e7d32;color:#fff;border-radius:4px;text-decoration:none;font-size:13px;font-weight:700;';
  downloads.insertBefore(a, downloads.firstChild);
}

function addWordDownload(allTasks, projectMeta) {
  const downloads = document.getElementById('downloads');
  const btn = document.createElement('button');
  btn.textContent = 'Download Word';
  btn.className = 'dl-btn';
  btn.style.cssText = 'display:inline-block;margin-bottom:10px;margin-right:12px;padding:8px 16px;background:#1a3a5c;color:#fff;border:none;border-radius:4px;font-size:13px;font-weight:700;cursor:pointer;';
  btn.addEventListener('click', async function() {
    btn.disabled = true;
    btn.textContent = 'Rendering...';
    try {
      const resp = await fetch('/render/docx', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tasks: allTasks, project_meta: projectMeta, filename: 'SWMS_Output.docx' }),
      });
      if (!resp.ok) { alert('Render failed: ' + resp.status); return; }
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'SWMS_Output.docx';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch(err) { alert('Download error: ' + err.message); }
    finally { btn.disabled = false; btn.textContent = 'Download Word'; }
  });
  downloads.insertBefore(btn, downloads.firstChild);
}
