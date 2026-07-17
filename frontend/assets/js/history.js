(function () {
  let selectedFile = null;
  let currentImport = null;
  const { identity, apiJson, escapeHtml } = WeOUCRuntime;

  const statusLabels = {
    assumed_passed: '推定已通过',
    passed: '已通过',
    failed: '未通过',
    withdrawn: '已退课',
    retaking: '重修中',
    unknown: '待确认',
  };

  function historyHeaders() {
    return {
      'X-Tenant-Id': identity.tenantId,
      'X-User-Id': identity.userId,
    };
  }

  function formatBytes(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }

  function setFile(file) {
    selectedFile = file || null;
    const summary = document.querySelector('#fileSummary');
    const button = document.querySelector('#uploadButton');
    if (!selectedFile) {
      summary.classList.add('hidden');
      button.disabled = true;
      document.querySelector('#historyFile').value = '';
      return;
    }
    document.querySelector('#fileName').textContent = selectedFile.name;
    document.querySelector('#fileSize').textContent = formatBytes(selectedFile.size);
    summary.classList.remove('hidden');
    button.disabled = false;
  }

  function setUploadMessage(type, title, detail = '') {
    const target = document.querySelector('#uploadMessage');
    if (!title) {
      target.innerHTML = '';
      return;
    }
    target.innerHTML = `<div class="${type}" style="padding:12px;border-radius:10px;margin-top:14px"><strong>${escapeHtml(title)}</strong>${detail ? `<div class="small" style="margin-top:4px">${escapeHtml(detail)}</div>` : ''}</div>`;
  }

  function statusOptions(selected) {
    return Object.entries(statusLabels).map(([value, label]) => (
      `<option value="${value}" ${value === selected ? 'selected' : ''}>${label}</option>`
    )).join('');
  }

  function renderPreview(payload) {
    currentImport = payload;
    document.querySelector('#previewCount').textContent = `${payload.record_count} 门课程待确认`;
    const warningTarget = document.querySelector('#parseWarnings');
    warningTarget.innerHTML = payload.warnings?.length
      ? `<div class="privacy-note" style="margin-bottom:14px">${payload.warnings.map(escapeHtml).join('<br>')}</div>`
      : '';
    document.querySelector('#previewTable').innerHTML = `
      <table class="data-table">
        <thead><tr><th>课程号</th><th>课程名称</th><th>学期</th><th>学分</th><th>状态</th><th>匹配</th></tr></thead>
        <tbody>${payload.records.map((record) => `
          <tr data-record-id="${record.id}">
            <td><input data-field="course_code" value="${escapeHtml(record.course_code || '')}" placeholder="可空"></td>
            <td><input data-field="course_name" value="${escapeHtml(record.course_name)}" required></td>
            <td><input data-field="semester" value="${escapeHtml(record.semester || '')}" placeholder="如 2025-2026-1"></td>
            <td><input data-field="credits" type="number" min="0" step="0.5" value="${record.credits ?? ''}"></td>
            <td><select data-field="completion_status">${statusOptions(record.completion_status)}</select></td>
            <td><span class="badge ${record.match_confidence >= 0.9 ? 'success' : 'risk'}">${Math.round(record.match_confidence * 100)}%</span></td>
          </tr>`).join('')}</tbody>
      </table>`;
    document.querySelector('#previewCard').classList.remove('hidden');
    document.querySelector('#previewCard').focus({ preventScroll: true });
  }

  async function uploadHistory() {
    if (!selectedFile) return;
    const button = document.querySelector('#uploadButton');
    const state = document.querySelector('#uploadState');
    button.disabled = true;
    state.textContent = '解析中';
    state.className = 'badge official';
    setUploadMessage('', '');
    const form = new FormData();
    form.append('file', selectedFile);
    try {
      const response = await fetch('/api/v1/academic-history/imports', {
        method: 'POST',
        headers: historyHeaders(),
        body: form,
      });
      if (!response.ok) {
        const errorPayload = await response.json().catch(() => ({}));
        throw new Error(errorPayload.detail || `解析失败（${response.status}）`);
      }
      const payload = await response.json();
      state.textContent = '待确认';
      state.className = 'badge risk';
      renderPreview(payload);
      setUploadMessage('success', '文件解析完成', `识别到 ${payload.record_count} 门课程，请继续校对。`);
    } catch (error) {
      state.textContent = '解析失败';
      state.className = 'badge danger';
      setUploadMessage('danger', '无法解析这个文件', error.message);
    } finally {
      button.disabled = false;
    }
  }

  function collectCorrections() {
    return [...document.querySelectorAll('#previewTable tbody tr')].map((row) => {
      const value = (field) => row.querySelector(`[data-field="${field}"]`).value.trim();
      const credits = value('credits');
      return {
        record_id: Number(row.dataset.recordId),
        course_code: value('course_code') || null,
        course_name: value('course_name'),
        semester: value('semester') || null,
        credits: credits === '' ? null : Number(credits),
        completion_status: value('completion_status'),
      };
    });
  }

  async function confirmImport() {
    if (!currentImport) return;
    const button = document.querySelector('#confirmImport');
    button.disabled = true;
    document.querySelector('#confirmMessage').innerHTML = '<div class="status-line"><span class="spinner"></span>正在保存确认结果…</div>';
    try {
      const payload = await apiJson(`/api/v1/academic-history/imports/${encodeURIComponent(currentImport.import_id)}/confirm`, {
        method: 'POST',
        headers: { ...historyHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ corrections: collectCorrections() }),
      });
      currentImport = null;
      document.querySelector('#previewCard').classList.add('hidden');
      document.querySelector('#uploadState').textContent = '已确认';
      document.querySelector('#uploadState').className = 'badge success';
      setUploadMessage('success', '历史课表已保存', `${payload.record_count} 门课程已可用于选课排除。`);
      await loadSavedRecords();
    } catch (error) {
      document.querySelector('#confirmMessage').innerHTML = `<div class="danger" style="padding:12px;border-radius:10px;margin-top:12px">${escapeHtml(error.message)}</div>`;
    } finally {
      button.disabled = false;
    }
  }

  function renderSavedRecords(payload) {
    const target = document.querySelector('#savedRecords');
    if (!payload.records.length) {
      target.innerHTML = '<div class="empty-state" style="padding:26px 12px"><div class="empty-icon" data-icon="history"></div><h3>还没有历史课程</h3><p class="muted small">上传以前的课表后，系统会在推荐时自动排除已修课程。</p></div>';
      target.querySelectorAll('[data-icon]').forEach((element) => { element.innerHTML = icon(element.dataset.icon); });
      return;
    }
    target.innerHTML = `
      <div class="record-list">${payload.records.map((record) => `
        <div class="record-item">
          <div>
            <strong>${escapeHtml(record.course_name)}</strong>
            <div class="muted small">${escapeHtml(record.course_code || '无课程号')} · ${escapeHtml(record.semester || '学期未填写')} · ${record.credits ?? '—'} 学分</div>
          </div>
          <span class="badge ${['assumed_passed', 'passed'].includes(record.completion_status) ? 'success' : 'risk'}">${escapeHtml(statusLabels[record.completion_status] || record.completion_status)}</span>
        </div>`).join('')}</div>`;
  }

  async function loadSavedRecords() {
    const target = document.querySelector('#savedRecords');
    target.innerHTML = '<div class="status-line"><span class="spinner"></span>正在读取历史课程…</div>';
    try {
      const payload = await apiJson('/api/v1/academic-history/records', { headers: historyHeaders() });
      renderSavedRecords(payload);
    } catch (error) {
      target.innerHTML = `<div class="danger" style="padding:12px;border-radius:10px">${escapeHtml(error.message)}</div>`;
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.querySelector('#historyFile');
    const zone = document.querySelector('#uploadZone');
    fileInput.addEventListener('change', () => setFile(fileInput.files[0]));
    zone.addEventListener('dragover', (event) => {
      event.preventDefault();
      zone.classList.add('dragging');
    });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragging'));
    zone.addEventListener('drop', (event) => {
      event.preventDefault();
      zone.classList.remove('dragging');
      setFile(event.dataTransfer.files[0]);
    });
    document.querySelector('#clearFile').onclick = () => setFile(null);
    document.querySelector('#uploadButton').onclick = uploadHistory;
    document.querySelector('#confirmImport').onclick = confirmImport;
    document.querySelector('#cancelImport').onclick = () => {
      currentImport = null;
      document.querySelector('#previewCard').classList.add('hidden');
      toast('已放弃本次确认，解析记录不会用于确定性结论');
    };
    document.querySelector('#refreshRecords').onclick = loadSavedRecords;
    loadSavedRecords();
  });
})();
