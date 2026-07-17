(function () {
  const { identity, apiJson, escapeHtml } = WeOUCRuntime;
  const panels = [...document.querySelectorAll('.setup-panel')];
  const steps = [...document.querySelectorAll('.step')];
  let programmes = [];
  let selectedProgramme = null;

  function show(index) {
    panels.forEach((panel, panelIndex) => panel.classList.toggle('active', panelIndex === index));
    steps.forEach((step, stepIndex) => step.classList.toggle('active', stepIndex === index));
  }

  function formValue(name) {
    return document.querySelector(`[name="${name}"]`).value.trim();
  }

  function setMessage(selector, type, text) {
    const target = document.querySelector(selector);
    target.innerHTML = text
      ? `<div class="${type}" style="padding:12px;border-radius:10px;margin-top:12px">${escapeHtml(text)}</div>`
      : '';
  }

  function renderProgramme(programme) {
    selectedProgramme = programme;
    document.querySelector('#programmeName').textContent = programme.programme_name;
    document.querySelector('#programmeIssuer').textContent = programme.issuing_unit
      ? `${programme.issuing_unit}发布`
      : '发布单位未提供';
    document.querySelector('#programmeMajor').textContent = formValue('major');
    document.querySelector('#programmeGrade').textContent = formValue('grade');
    document.querySelector('#programmeVersion').textContent = programme.version_code;
    document.querySelector('#programmeDate').textContent = programme.published_at
      ? new Date(programme.published_at).toLocaleDateString('zh-CN')
      : '未提供';
  }

  async function matchProgramme() {
    const required = ['grade', 'college', 'major'];
    for (const name of required) {
      if (!formValue(name)) {
        toast('请先完成年级、学院和专业信息');
        return;
      }
    }
    const button = document.querySelector('#matchBtn');
    button.disabled = true;
    button.textContent = '正在查询培养方案…';
    setMessage('#profileLoadMessage', '', '');
    try {
      const query = new URLSearchParams({
        tenant_id: identity.tenantId,
        grade: formValue('grade'),
        major: formValue('major'),
      });
      programmes = await apiJson(`/api/v1/student/programmes?${query.toString()}`);
      if (!programmes.length) throw new Error('没有找到适用于当前年级和专业的活动培养方案');
      const choiceWrap = document.querySelector('#programmeChoiceWrap');
      const choice = document.querySelector('#programmeChoice');
      choice.innerHTML = programmes.map((programme) => (
        `<option value="${programme.id}">${escapeHtml(programme.programme_name)} · ${escapeHtml(programme.version_code)}</option>`
      )).join('');
      choiceWrap.classList.toggle('hidden', programmes.length < 2);
      renderProgramme(programmes[0]);
      show(1);
    } catch (error) {
      setMessage('#profileLoadMessage', 'danger', error.message);
    } finally {
      button.disabled = false;
      button.innerHTML = `匹配培养方案 ${icon('arrow')}`;
    }
  }

  async function saveProfile() {
    if (!selectedProgramme) return;
    const button = document.querySelector('#confirmPlan');
    button.disabled = true;
    setMessage('#saveProfileMessage', 'official', '正在保存学生资料…');
    try {
      await apiJson('/api/v1/student/profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tenant_id: identity.tenantId,
          user_id: identity.userId,
          grade: formValue('grade'),
          department: formValue('college'),
          major: formValue('major'),
          programme_version_id: selectedProgramme.id,
        }),
      });
      setMessage('#saveProfileMessage', 'success', '学生资料和培养方案已保存');
      location.href = 'history.html?welcome=1';
    } catch (error) {
      setMessage('#saveProfileMessage', 'danger', error.message);
    } finally {
      button.disabled = false;
    }
  }

  async function loadExistingProfile() {
    const query = new URLSearchParams({ tenant_id: identity.tenantId, user_id: identity.userId });
    try {
      const profile = await apiJson(`/api/v1/student/profile?${query.toString()}`);
      document.querySelector('#grade').value = profile.grade;
      document.querySelector('#college').value = profile.department;
      document.querySelector('#major').value = profile.major;
      setMessage('#profileLoadMessage', 'success', '已从后端读取现有学生资料');
    } catch (error) {
      if (error.status !== 404) setMessage('#profileLoadMessage', 'danger', error.message);
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelector('#matchBtn').onclick = matchProgramme;
    document.querySelector('#confirmPlan').onclick = saveProfile;
    document.querySelectorAll('[data-back-setup]').forEach((button) => {
      button.onclick = () => show(0);
    });
    document.querySelector('#programmeChoice').onchange = (event) => {
      renderProgramme(programmes.find((programme) => programme.id === Number(event.target.value)));
    };
    loadExistingProfile();
  });
})();
