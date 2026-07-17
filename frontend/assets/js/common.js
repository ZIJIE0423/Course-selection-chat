(function () {
  const icons = {
    chat: '<path d="M21 12a8 8 0 0 1-8 8H5l-3 2 1-6a8 8 0 1 1 18-4Z"/>',
    course: '<path d="m4 19 8 3 8-3V5l-8-3-8 3v14Z"/><path d="m4 5 8 3 8-3M12 8v14"/>',
    history: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/>',
    feedback: '<path d="M4 4h16v14H7l-3 3V4Z"/><path d="M8 9h8M8 13h5"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 22a8 8 0 0 1 16 0"/>',
    menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
    send: '<path d="m22 2-7 20-4-9-9-4 20-7Z"/><path d="M22 2 11 13"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    close: '<path d="m6 6 12 12M18 6 6 18"/>',
    arrow: '<path d="m9 18 6-6-6-6"/>',
    shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
    search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    upload: '<path d="M12 3v12M7 8l5-5 5 5"/><path d="M5 13v6h14v-6"/>',
  };

  let capabilitiesPromise = null;
  const identity = {
    tenantId: localStorage.getItem('weoucTenantId') || 'weouc',
    userId: localStorage.getItem('weoucUserId') || 'student-1',
  };
  localStorage.setItem('weoucTenantId', identity.tenantId);
  localStorage.setItem('weoucUserId', identity.userId);

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }

  async function apiJson(url, options = {}) {
    const response = await fetch(url, options);
    if (!response.ok) {
      let detail = `服务返回 ${response.status}`;
      try {
        const payload = await response.json();
        detail = payload.detail || detail;
      } catch (_) {
        // Keep status-based fallback for non-JSON errors.
      }
      const error = new Error(detail);
      error.status = response.status;
      throw error;
    }
    return response.json();
  }

  function getCapabilities() {
    if (!capabilitiesPromise) {
      capabilitiesPromise = apiJson('/api/v1/capabilities').catch(() => ({
        modules: {
          course_planning: true,
          academic_history_import: true,
          course_feedback: false,
          student_review_rag: false,
        },
      }));
    }
    return capabilitiesPromise;
  }

  window.icon = (name) => `<svg viewBox="0 0 24 24" aria-hidden="true">${icons[name] || icons.arrow}</svg>`;
  window.toast = (text) => {
    let element = document.querySelector('.toast');
    if (!element) {
      element = document.createElement('div');
      element.className = 'toast';
      document.body.append(element);
    }
    element.textContent = text;
    element.classList.add('show');
    clearTimeout(element._timer);
    element._timer = setTimeout(() => element.classList.remove('show'), 2600);
  };
  window.closeOverlays = () => {
    document.querySelectorAll('.drawer-backdrop,.modal-backdrop').forEach((element) => {
      element.classList.remove('open');
    });
  };
  window.openDrawer = (index = 0) => {
    const drawer = document.querySelector('#sourceDrawer');
    if (!drawer) return;
    const sources = window.WeOUCData?.sources || [];
    const source = sources[index];
    const target = drawer.querySelector('[data-source-content]');
    if (!source) {
      target.innerHTML = '<div class="privacy-note">当前页面的来源信息由实时接口直接展示。</div>';
    } else {
      target.innerHTML = `
        <span class="badge ${source.level === '官方' ? 'official' : 'experience'}">${escapeHtml(source.type)}</span>
        <h3 style="margin:16px 0 6px">${escapeHtml(source.name)}</h3>
        <p class="muted small">${escapeHtml(source.level)}来源 · 数据所属 ${escapeHtml(source.term)}</p>
        <div class="divider"></div>
        <div class="meta-list">
          <div class="meta-item"><span>更新时间 / 抓取时间</span><strong>${escapeHtml(source.updated)}</strong></div>
          <div class="meta-item"><span>来源属性</span><strong>${escapeHtml(source.level)}</strong></div>
        </div>
        <p style="line-height:1.75">${escapeHtml(source.summary)}</p>`;
    }
    drawer.classList.add('open');
  };

  window.WeOUCRuntime = {
    identity,
    apiJson,
    escapeHtml,
    getCapabilities,
  };

  function addHistoryNavigation() {
    document.querySelectorAll('.nav,.mobile-nav').forEach((navigation) => {
      if (navigation.querySelector('a[href^="history.html"]')) return;
      const link = document.createElement('a');
      link.href = 'history.html';
      link.dataset.feature = 'academic_history_import';
      const mobile = navigation.classList.contains('mobile-nav');
      link.innerHTML = `<span data-icon="history"></span>${mobile ? '历史' : '历史课表'}`;
      if (location.pathname.endsWith('/history.html')) link.classList.add('active');
      const profileLink = navigation.querySelector('a[href^="profile.html"]');
      navigation.insertBefore(link, profileLink || null);
    });
  }

  function applyCapabilities(capabilities) {
    const modules = capabilities.modules || {};
    document.querySelectorAll('[data-feature]').forEach((element) => {
      if (modules[element.dataset.feature] !== true) element.classList.add('hidden');
    });
    if (modules.course_feedback !== true) {
      document.querySelectorAll('a[href^="feedback.html"],#submissions,[data-feature="course_feedback"]').forEach((element) => {
        element.classList.add('hidden');
      });
      if (location.pathname.endsWith('/feedback.html')) location.replace('index.html');
    }
    if (modules.student_review_rag !== true) {
      document.querySelectorAll('button[data-prompt*="评价"],.badge.experience[data-source]').forEach((element) => {
        element.classList.add('hidden');
      });
    }
    if (modules.schedule_conflict !== true) {
      document.querySelectorAll('button[data-prompt*="课表冲突"],button[onclick*="authModal"],#authModal').forEach((element) => {
        element.classList.add('hidden');
      });
      document.querySelectorAll('.side-card').forEach((element) => {
        if (element.querySelector('h3')?.textContent.includes('课表冲突')) element.classList.add('hidden');
      });
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    addHistoryNavigation();
    document.querySelectorAll('[data-icon]').forEach((element) => {
      element.innerHTML = icon(element.dataset.icon);
    });
    document.querySelectorAll('[data-source]').forEach((element) => {
      element.addEventListener('click', () => openDrawer(Number(element.dataset.source || 0)));
    });
    document.querySelectorAll('[data-close]').forEach((element) => {
      element.addEventListener('click', closeOverlays);
    });
    document.querySelectorAll('.drawer-backdrop,.modal-backdrop').forEach((element) => {
      element.addEventListener('click', (event) => {
        if (event.target === element) closeOverlays();
      });
    });
    const menu = document.querySelector('.menu-btn');
    const sidebar = document.querySelector('.sidebar');
    if (menu && sidebar) menu.onclick = () => sidebar.classList.toggle('open');
    getCapabilities().then(applyCapabilities);
  });
})();
