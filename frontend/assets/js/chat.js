(function () {
  let activeController = null;
  let contextPromise = null;
  const browserSession = localStorage.getItem('weoucSession') || crypto.randomUUID();
  const compare = [];
  const identity = {
    tenantId: localStorage.getItem('weoucTenantId') || 'weouc',
    userId: localStorage.getItem('weoucUserId') || 'student-1',
  };

  localStorage.setItem('weoucSession', browserSession);
  localStorage.setItem('weoucTenantId', identity.tenantId);
  localStorage.setItem('weoucUserId', identity.userId);

  const $ = (selector) => document.querySelector(selector);
  const messages = () => $('#messages');

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }

  function bubble(role, html) {
    const element = document.createElement('div');
    element.className = `message ${role}`;
    element.innerHTML = role === 'assistant'
      ? `<div class="assistant-avatar">W</div><div class="bubble">${html}</div>`
      : '<div class="bubble"></div>';
    if (role === 'user') element.querySelector('.bubble').textContent = html;
    messages().append(element);
    messages().scrollTop = messages().scrollHeight;
    return element.querySelector('.bubble');
  }

  function setBusy(busy, stoppable = false) {
    const button = $('#sendBtn');
    if (!button) return;
    button.disabled = busy && !stoppable;
    button.classList.toggle('stop', busy && stoppable);
    button.innerHTML = busy && stoppable
      ? '<span style="width:12px;height:12px;background:#fff;border-radius:2px"></span>'
      : icon('send');
  }

  async function requestJson(url, options = {}) {
    const response = await fetch(url, options);
    if (!response.ok) {
      let detail = `服务返回 ${response.status}`;
      try {
        const payload = await response.json();
        detail = payload.detail || detail;
      } catch (_) {
        // Keep the HTTP status fallback when the response is not JSON.
      }
      throw new Error(detail);
    }
    return response.json();
  }

  function updateContextHeader(context) {
    const contextMain = document.querySelector('.context-main');
    const programmeName = $('#planningProgrammeName') || contextMain?.querySelector('strong');
    const programmeMeta = $('#planningProgrammeMeta') || contextMain?.querySelector('.muted.small');
    if (programmeName && context.programme) {
      programmeName.textContent = context.programme.programme_name;
    }
    if (programmeMeta && context.snapshot && context.programme) {
      const confirmation = context.programme.confirmed ? '' : ' · 待学生确认';
      programmeMeta.textContent = `${context.snapshot.semester} · ${context.programme.version_code}${confirmation}`;
    }
  }

  function getPlanningContext(force = false) {
    if (!contextPromise || force) {
      const query = new URLSearchParams({
        tenant_id: identity.tenantId,
        user_id: identity.userId,
      });
      contextPromise = requestJson(`/api/v1/planning/context?${query.toString()}`)
        .then((context) => {
          updateContextHeader(context);
          return context;
        })
        .catch((error) => {
          contextPromise = null;
          throw error;
        });
    }
    return contextPromise;
  }

  function looksLikePlanningQuery(text) {
    return /推荐|筛选|选什么|可选课程|选课要求|适合我的课/.test(text);
  }

  const weekdayLabels = {
    1: '周一',
    2: '周二',
    3: '周三',
    4: '周四',
    5: '周五',
    6: '周六',
    7: '周日',
  };
  const requirementLabels = {
    campus: '校区',
    weekday: '上课时间',
    course_category: '课程类别',
    teacher_name: '教师',
    credits: '学分',
    avoid_period: '避开节次',
    course_code: '课程号',
  };
  const unsupportedLabels = {
    workload: '作业量',
    assessment_method: '考核方式',
  };

  function requirementText(item) {
    let value = item.value;
    if (item.type === 'weekday') value = weekdayLabels[value] || value;
    if (item.type === 'avoid_period') value = `第 ${value} 节`;
    if (item.type === 'credits' && item.operator === 'lte') value = `不超过 ${value} 学分`;
    if (item.type === 'credits' && item.operator === 'gte') value = `至少 ${value} 学分`;
    return `${requirementLabels[item.type] || item.type}：${value}`;
  }

  function requirementTags(items, emptyText) {
    if (!items.length) return `<span class="muted small">${escapeHtml(emptyText)}</span>`;
    return items.map((item) => `<span class="tag">${escapeHtml(requirementText(item))}</span>`).join('');
  }

  function renderPlanningUnavailable(answer, context) {
    const missingLabels = {
      course_offering_snapshot: '当前学期可选课程快照',
      programme_version: '适用培养方案',
    };
    const missing = (context.missing || []).map((item) => missingLabels[item] || item).join('、');
    answer.innerHTML = `
      <div class="danger" style="padding:14px;border-radius:12px">
        <strong>暂时无法开始真实选课规划</strong>
        <div class="small" style="margin-top:6px">缺少：${escapeHtml(missing || '规划上下文')}。请先由数据提供方导入后再重试。</div>
      </div>`;
  }

  function renderRequirementConfirmation(answer, planning, originalQuery) {
    const requirements = planning.requirements;
    const unsupported = requirements.unsupported_preferences || [];
    const unsupportedHtml = unsupported.length
      ? `<div class="privacy-note" style="margin-top:12px">${unsupported.map((item) => escapeHtml(unsupportedLabels[item] || item)).join('、')}数据尚未启用，本次不会据此筛选或排序。</div>`
      : '';
    const programmeNotice = planning.context?.programme && !planning.context.programme.confirmed
      ? '<div class="privacy-note" style="margin-top:12px">当前使用最新活动培养方案进行演示，但该方案尚未由当前学生确认。正式使用前需要完成培养方案绑定。</div>'
      : '';

    answer.innerHTML = `
      <div class="requirement">
        <h4>请确认我理解的选课要求</h4>
        <div class="req-row">
          <span class="req-label">必须满足</span>
          <div class="actions">${requirementTags(requirements.constraints || [], '没有识别到硬性约束')}</div>
        </div>
        <div class="req-row">
          <span class="req-label">优先考虑</span>
          <div class="actions">${requirementTags(requirements.preferences || [], '没有识别到可用偏好')}</div>
        </div>
        ${unsupportedHtml}
        ${programmeNotice}
        <div class="actions" style="margin-top:14px">
          <button class="btn btn-primary btn-sm" data-confirm-plan>确认并查找</button>
          <button class="btn btn-ghost btn-sm" data-edit-plan>修改原问题</button>
        </div>
      </div>`;

    const confirmButton = answer.querySelector('[data-confirm-plan]');
    const editButton = answer.querySelector('[data-edit-plan]');
    confirmButton.addEventListener('click', () => confirmRecommendations(answer, planning));
    editButton.addEventListener('click', () => {
      $('#question').value = originalQuery;
      $('#question').focus();
      toast('请修改后重新发送，系统会重新识别条件');
    });
  }

  function formatSchedule(schedules) {
    if (!schedules || !schedules.length) return '时间待公布';
    return schedules.map((slot) => {
      const weekday = weekdayLabels[slot.weekday] || `星期 ${slot.weekday}`;
      const periods = slot.periods?.length ? `第 ${slot.periods.join('、')} 节` : '节次待定';
      const weeks = slot.weeks ? ` · ${slot.weeks}周` : '';
      const location = slot.location ? ` · ${slot.location}` : '';
      return `${weekday} ${periods}${weeks}${location}`;
    }).join('；');
  }

  function renderWarnings(warnings) {
    if (!warnings?.length) return '';
    return `<div class="privacy-note" style="margin-top:12px">${warnings.map(escapeHtml).join('<br>')}</div>`;
  }

  function recommendationCards(payload) {
    if (!payload.recommendations.length) {
      return `
        <div class="empty-state" style="padding:28px 12px">
          <div class="empty-icon">0</div>
          <h3>没有课程同时满足当前条件</h3>
          <p class="muted small">可以放宽校区、星期、学分或课程类别后重新提问。</p>
        </div>${renderWarnings(payload.warnings)}`;
    }

    const cards = payload.recommendations.map((course) => {
      const reasons = (course.match_reasons || [])
        .map((reason) => `<span class="tag">${escapeHtml(reason)}</span>`)
        .join('');
      const evidence = course.evidence?.[0] || {};
      const snapshotText = evidence.snapshot_id
        ? `依据课程快照 ${escapeHtml(evidence.snapshot_id)} · ${escapeHtml(evidence.semester || '')}`
        : '依据当前活动课程快照';
      return `
        <div class="course-card">
          <div class="course-top">
            <div>
              <h3>${escapeHtml(course.course_name)}</h3>
              <div class="course-meta">
                <span>${escapeHtml(course.course_code)}</span>
                <span>${course.credits == null ? '学分待定' : `${escapeHtml(course.credits)} 学分`}</span>
                <span>${escapeHtml(course.course_category || '类别待定')}</span>
              </div>
            </div>
            <span class="badge success">符合已确认条件</span>
          </div>
          <div class="fact-grid" style="margin-top:14px">
            <div class="fact"><span>教师与校区</span>${escapeHtml(course.teacher_name || '教师待定')} · ${escapeHtml(course.campus || '校区待定')}</div>
            <div class="fact"><span>上课安排</span>${escapeHtml(formatSchedule(course.schedules))}</div>
            <div class="fact"><span>排序得分</span>${escapeHtml(course.score)}</div>
          </div>
          <div class="match-row">${reasons}</div>
          ${renderWarnings(course.warnings)}
          <div class="privacy-note" style="margin-top:12px">${snapshotText}</div>
          <div class="actions" style="margin-top:14px">
            <a class="btn btn-primary btn-sm" href="course.html?offering_id=${encodeURIComponent(course.offering_id)}">查看详情</a>
            <button class="btn btn-ghost btn-sm" data-ask="${escapeHtml(course.course_name)}">继续问这门课</button>
            <button class="btn btn-ghost btn-sm" data-compare="${escapeHtml(course.offering_id)}">加入对比</button>
          </div>
        </div>`;
    }).join('');

    return `
      <div style="margin:12px 0">
        <p><strong>找到 ${payload.total_candidates} 门符合条件的课程。</strong>以下结果已经排除已修课程、无余量课程和不符合培养方案范围的课程。</p>
        ${renderWarnings(payload.warnings)}
        <div style="margin-top:12px">${cards}</div>
      </div>`;
  }

  async function confirmRecommendations(answer, planning) {
    const button = answer.querySelector('[data-confirm-plan]');
    if (button) button.disabled = true;
    answer.innerHTML = '<div class="status-line"><span class="spinner"></span>正在根据培养方案、历史课程和当前课程快照筛选…</div>';
    try {
      const payload = await requestJson(
        `/api/v1/planning/sessions/${encodeURIComponent(planning.session_id)}/requirements/confirm`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            constraints: planning.requirements.constraints || [],
            preferences: planning.requirements.preferences || [],
          }),
        },
      );
      answer.innerHTML = recommendationCards(payload);
      wireDynamic(answer);
    } catch (error) {
      answer.innerHTML = `
        <div class="danger" style="padding:14px;border-radius:12px">
          <strong>课程筛选失败</strong>
          <div class="small" style="margin-top:6px">${escapeHtml(error.message)}</div>
        </div>`;
    }
    messages().scrollTop = messages().scrollHeight;
  }

  const historyStatusLabels = {
    assumed_passed: '默认已通过',
    passed: '已通过',
    failed: '未通过',
    withdrawn: '已退课',
    retaking: '重修中',
    unknown: '待确认',
  };

  function renderHistoryConfirmation(answer, planning, originalQuery) {
    const candidates = planning.requirements.history_correction_candidates || [];
    if (!candidates.length) {
      answer.innerHTML = '<div class="privacy-note">没有找到可以修改的历史课程，请先上传并确认历史课表。</div>';
      return;
    }
    answer.innerHTML = `
      <div class="requirement">
        <h4>请确认历史课程状态修改</h4>
        <p class="muted small">系统不会根据一句话直接修改记录，只有你确认后才会保存。</p>
        ${candidates.map((candidate) => `
          <div class="course-card" style="margin-top:10px" data-history-candidate>
            <strong>${escapeHtml(candidate.course_name)}</strong>
            <div class="course-meta" style="margin:6px 0 12px">
              <span>当前：${escapeHtml(historyStatusLabels[candidate.current_status] || candidate.current_status)}</span>
              <span>修改为：${escapeHtml(historyStatusLabels[candidate.proposed_status] || candidate.proposed_status)}</span>
            </div>
            <button class="btn btn-primary btn-sm" data-confirm-history
              data-record-id="${escapeHtml(candidate.record_id)}"
              data-status="${escapeHtml(candidate.proposed_status)}">确认修改</button>
          </div>`).join('')}
        <button class="btn btn-ghost btn-sm" style="margin-top:12px" data-cancel-history>暂不修改</button>
      </div>`;

    answer.querySelectorAll('[data-confirm-history]').forEach((button) => {
      button.addEventListener('click', () => confirmHistoryCorrection(button));
    });
    answer.querySelector('[data-cancel-history]').addEventListener('click', () => {
      $('#question').value = originalQuery;
      $('#question').focus();
      toast('历史课程状态未修改');
    });
  }

  async function confirmHistoryCorrection(button) {
    const card = button.closest('[data-history-candidate]');
    button.disabled = true;
    try {
      const result = await requestJson('/api/v1/planning/history-corrections/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tenant_id: identity.tenantId,
          user_id: identity.userId,
          record_id: Number(button.dataset.recordId),
          status: button.dataset.status,
        }),
      });
      card.innerHTML = `
        <span class="badge success">已确认</span>
        <strong style="display:block;margin-top:10px">${escapeHtml(result.course_name)}</strong>
        <p class="muted small">课程状态已更新为“${escapeHtml(historyStatusLabels[result.completion_status] || result.completion_status)}”。</p>`;
    } catch (error) {
      button.disabled = false;
      toast(`修改失败：${error.message}`);
    }
  }

  async function createPlanningSession(text, answer) {
    const context = await getPlanningContext();
    if (!context.available) {
      if (looksLikePlanningQuery(text)) {
        renderPlanningUnavailable(answer, context);
        return true;
      }
      return false;
    }

    const planning = await requestJson('/api/v1/planning/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: activeController.signal,
      body: JSON.stringify({
        tenant_id: identity.tenantId,
        user_id: identity.userId,
        snapshot_id: context.snapshot.id,
        programme_version_id: context.programme?.id || null,
        query: text,
      }),
    });
    planning.context = context;

    if (planning.requirements.intent === 'course_recommendation') {
      renderRequirementConfirmation(answer, planning, text);
      return true;
    }
    if (planning.requirements.intent === 'history_correction') {
      renderHistoryConfirmation(answer, planning, text);
      return true;
    }
    return false;
  }

  async function streamLegacyChat(text, answer) {
    answer.innerHTML = '<div class="status-line"><span class="spinner"></span><span>正在查询课程知识…</span></div>';
    const response = await fetch('/api/v1/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: text, session_id: browserSession }),
      signal: activeController.signal,
    });
    if (!response.ok) throw new Error('问答服务返回异常');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let full = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop();
      for (const part of parts) {
        const raw = part.split('\n').find((line) => line.startsWith('data:'));
        if (!raw) continue;
        const event = JSON.parse(raw.slice(5));
        if (event.type === 'status') {
          answer.innerHTML = `<div class="status-line"><span class="spinner"></span><span>${escapeHtml(event.content)}</span></div>${full ? `<div style="margin-top:10px;white-space:pre-wrap">${escapeHtml(full)}</div>` : ''}`;
        } else if (['answer', 'answer_delta'].includes(event.type)) {
          full += event.content || '';
          answer.innerHTML = `<div style="white-space:pre-wrap">${escapeHtml(full)}</div>`;
        }
      }
    }
  }

  function wireDynamic(root = document) {
    root.querySelectorAll('[data-source]').forEach((element) => {
      element.onclick = () => openDrawer(Number(element.dataset.source));
    });
    root.querySelectorAll('[data-ask]').forEach((element) => {
      element.onclick = () => {
        $('#question').value = `${element.dataset.ask}的上课安排和选课限制是什么？`;
        $('#question').focus();
      };
    });
    root.querySelectorAll('[data-compare]').forEach((element) => {
      element.onclick = () => {
        if (compare.includes(element.dataset.compare)) return toast('这门课已在对比栏');
        if (compare.length >= 3) return toast('最多同时对比 3 门课程');
        compare.push(element.dataset.compare);
        renderCompare();
      };
    });
  }

  function renderCompare() {
    const bar = $('#compareBar');
    bar.classList.toggle('show', compare.length > 0);
    bar.querySelector('span').textContent = `已选 ${compare.length}/3 门课程`;
    bar.querySelector('button').onclick = () => toast('已记录当前选择，课程对比页将在后续模块开放');
  }

  async function send() {
    const question = $('#question');
    const text = question.value.trim();
    if (!text || activeController) return;

    question.value = '';
    bubble('user', text);
    const answer = bubble('assistant', '<div class="status-line"><span class="spinner"></span><span>正在理解你的需求…</span></div>');
    activeController = new AbortController();
    setBusy(true, true);

    try {
      let handledByPlanning = false;
      try {
        handledByPlanning = await createPlanningSession(text, answer);
      } catch (planningError) {
        if (looksLikePlanningQuery(text)) throw planningError;
      }
      if (!handledByPlanning) await streamLegacyChat(text, answer);
    } catch (error) {
      if (error.name === 'AbortError') {
        answer.insertAdjacentHTML('beforeend', '<p class="muted small">已停止本次请求。</p>');
      } else {
        answer.innerHTML = `
          <div class="danger" style="padding:14px;border-radius:12px">
            <strong>请求未完成</strong>
            <div class="small" style="margin-top:6px">${escapeHtml(error.message)}</div>
          </div>
          <button class="btn btn-ghost btn-sm" style="margin-top:10px" data-retry>重新发送</button>`;
        answer.querySelector('[data-retry]').onclick = () => {
          $('#question').value = text;
          $('#question').focus();
        };
      }
    } finally {
      activeController = null;
      setBusy(false);
      messages().scrollTop = messages().scrollHeight;
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    $('#sendBtn').onclick = () => activeController ? activeController.abort() : send();
    $('#question').onkeydown = (event) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        send();
      }
    };
    document.querySelectorAll('[data-prompt]').forEach((button) => {
      button.onclick = () => {
        $('#question').value = button.dataset.prompt;
        $('#question').focus();
      };
    });
    $('#saveConditions').onclick = () => {
      closeOverlays();
      toast('请在输入框确认修改后的自然语言要求');
    };
    wireDynamic();
    const pendingQuestion = sessionStorage.getItem('weoucPendingQuestion');
    if (pendingQuestion) {
      sessionStorage.removeItem('weoucPendingQuestion');
      $('#question').value = pendingQuestion;
      $('#question').focus();
    }
    getPlanningContext().catch(() => {
      // The page remains usable for the legacy Q&A path when planning data is unavailable.
    });
  });
})();
