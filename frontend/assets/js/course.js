(function () {
  const { identity, apiJson, escapeHtml } = WeOUCRuntime;
  const weekdayLabels = { 1: '周一', 2: '周二', 3: '周三', 4: '周四', 5: '周五', 6: '周六', 7: '周日' };
  const historyLabels = {
    assumed_passed: '历史课表中推定已通过',
    passed: '历史记录中已通过',
    failed: '历史记录中未通过',
    withdrawn: '历史记录中已退课',
    retaking: '历史记录中重修中',
    unknown: '历史状态待确认',
  };

  function formatSchedule(schedules) {
    if (!schedules?.length) return '时间待公布';
    return schedules.map((slot) => {
      const periods = slot.periods?.length ? `${slot.periods.join('、')}节` : '节次待定';
      return `${weekdayLabels[slot.weekday] || `星期${slot.weekday}`} ${periods}`;
    }).join('；');
  }

  function formatLocations(schedules) {
    const locations = [...new Set((schedules || []).map((slot) => slot.location).filter(Boolean))];
    return locations.join('；') || '地点待公布';
  }

  function showError(title, detail) {
    document.querySelector('#courseLoading').classList.add('hidden');
    const target = document.querySelector('#courseError');
    target.classList.remove('hidden');
    target.innerHTML = `
      <div class="card empty-state">
        <div class="empty-icon" data-icon="course"></div>
        <h2>${escapeHtml(title)}</h2>
        <p class="muted">${escapeHtml(detail)}</p>
        <a class="btn btn-primary" href="index.html">返回选课咨询</a>
      </div>`;
    target.querySelector('[data-icon]').innerHTML = icon('course');
  }

  function render(detail) {
    document.querySelector('#courseLoading').classList.add('hidden');
    document.querySelector('#courseDetail').classList.remove('hidden');
    document.querySelector('#courseName').textContent = detail.course_name;
    document.querySelector('#courseCode').textContent = `${detail.course_code} · ${detail.course_category || '类别待定'} · ${detail.department || '开课单位待定'}`;
    document.querySelector('#courseCredits').textContent = detail.credits ?? '—';
    document.querySelector('#courseTeacher').textContent = detail.teacher_name || '待公布';
    document.querySelector('#courseCampus').textContent = detail.campus || '待公布';
    document.querySelector('#courseSchedule').textContent = formatSchedule(detail.schedules);
    document.querySelector('#sectionName').textContent = detail.extra?.section_name || detail.external_offering_id;
    document.querySelector('#courseLocation').textContent = formatLocations(detail.schedules);
    document.querySelector('#courseCapacity').textContent = detail.capacity ?? '未提供';
    document.querySelector('#courseRemaining').textContent = detail.remaining_capacity ?? '未提供';
    document.querySelector('#courseSemester').textContent = detail.snapshot.semester;
    document.querySelector('#courseUpdatedAt').textContent = detail.source_updated_at
      ? new Date(detail.source_updated_at).toLocaleString('zh-CN')
      : '未提供';
    document.querySelector('#relationshipLabel').textContent = detail.programme_relationship.label;
    document.querySelector('#programmeDescription').textContent = detail.programme
      ? `${detail.programme.programme_name} · ${detail.programme.version_code}${detail.programme_relationship.matched_rule ? ` · 规则 ${detail.programme_relationship.matched_rule}` : ''}`
      : '当前学生尚未绑定培养方案。';
    document.querySelector('#snapshotId').textContent = detail.snapshot.snapshot_id;
    document.querySelector('#snapshotGeneratedAt').textContent = new Date(detail.snapshot.generated_at).toLocaleString('zh-CN');
    document.querySelector('#demoBadge').classList.toggle('hidden', detail.extra?.demo_only !== true);

    const historyTarget = document.querySelector('#historyState');
    historyTarget.innerHTML = detail.history
      ? `<span class="badge ${['assumed_passed', 'passed'].includes(detail.history.completion_status) ? 'risk' : 'neutral'}">${escapeHtml(historyLabels[detail.history.completion_status] || detail.history.completion_status)}</span>`
      : '<span class="badge success">未在历史课表中发现</span>';

    document.querySelector('#continueQuestion').onclick = () => {
      sessionStorage.setItem('weoucPendingQuestion', `请继续说明 ${detail.course_name} 的选课信息`);
      location.href = 'index.html';
    };
  }

  async function loadCourse() {
    const offeringId = new URLSearchParams(location.search).get('offering_id');
    if (!offeringId) {
      showError('请选择一门具体课程', '请先在选课推荐结果中点击“查看详情”。');
      return;
    }
    const query = new URLSearchParams({ tenant_id: identity.tenantId, user_id: identity.userId });
    try {
      const detail = await apiJson(`/api/v1/catalog/offerings/${encodeURIComponent(offeringId)}?${query.toString()}`);
      render(detail);
    } catch (error) {
      showError('课程详情加载失败', error.message);
    }
  }

  document.addEventListener('DOMContentLoaded', loadCourse);
})();
