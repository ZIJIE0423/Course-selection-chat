(function () {
  const { identity, apiJson, escapeHtml } = WeOUCRuntime;

  function historyHeaders() {
    return { 'X-Tenant-Id': identity.tenantId, 'X-User-Id': identity.userId };
  }

  async function loadProfile() {
    const query = new URLSearchParams({ tenant_id: identity.tenantId, user_id: identity.userId });
    const content = document.querySelector('#profileContent');
    try {
      const profile = await apiJson(`/api/v1/student/profile?${query.toString()}`);
      document.querySelector('#identityState').textContent = '学生资料已确认';
      document.querySelector('#identityState').className = 'badge success';
      document.querySelector('#profileTitle').textContent = profile.major;
      document.querySelector('#profileSummary').textContent = `${profile.grade} · ${profile.department}`;
      content.innerHTML = `
        <span class="badge rule">培养方案已确认</span>
        <h3 style="font-size:16px;margin:14px 0 6px">${escapeHtml(profile.programme_name)}</h3>
        <p class="muted small">${escapeHtml(profile.programme_version_code)} · ${escapeHtml(profile.department)}</p>
        <div class="meta-list">
          <div class="meta-item"><span>年级</span><strong>${escapeHtml(profile.grade)}</strong></div>
          <div class="meta-item"><span>专业</span><strong>${escapeHtml(profile.major)}</strong></div>
        </div>
        <div class="privacy-note">确认时间：${profile.programme_confirmed_at ? new Date(profile.programme_confirmed_at).toLocaleString('zh-CN') : '未记录'}</div>`;
    } catch (error) {
      document.querySelector('#identityState').textContent = '资料待完善';
      document.querySelector('#identityState').className = 'badge risk';
      document.querySelector('#profileSummary').textContent = '尚未完成学生资料和培养方案绑定';
      content.innerHTML = `
        <div class="empty-state" style="padding:22px 10px">
          <h3>还没有后端学生档案</h3>
          <p class="muted small">请先填写年级、学院、专业并确认培养方案。</p>
          <a class="btn btn-primary btn-sm" href="onboarding.html">立即完善</a>
        </div>`;
    }
  }

  async function loadHistorySummary() {
    const target = document.querySelector('#historySummary');
    try {
      const payload = await apiJson('/api/v1/academic-history/records', { headers: historyHeaders() });
      const completed = payload.records.filter((record) => ['assumed_passed', 'passed'].includes(record.completion_status)).length;
      const exceptions = payload.record_count - completed;
      target.innerHTML = `
        <div class="meta-list">
          <div class="meta-item"><span>已保存课程</span><strong>${payload.record_count} 门</strong></div>
          <div class="meta-item"><span>规划时排除</span><strong>${completed} 门</strong></div>
        </div>
        <div class="privacy-note">${exceptions ? `${exceptions} 门课程标记为未通过、退课或重修，不会作为已完成课程排除。` : '所有历史课程当前均按已通过处理。'}</div>`;
    } catch (error) {
      target.innerHTML = `<div class="danger" style="padding:12px;border-radius:10px">${escapeHtml(error.message)}</div>`;
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelector('#tenantId').textContent = identity.tenantId;
    document.querySelector('#userId').textContent = identity.userId;
    loadProfile();
    loadHistorySummary();
  });
})();
