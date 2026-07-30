const $ = (id) => document.getElementById(id);

let state = null;
let dirty = false;

const providerLabels = {
  local_openai_compatible: 'Local OpenAI-compatible server',
  openai: 'OpenAI / GPT',
  anthropic: 'Anthropic / Claude',
  google: 'Google / Gemini',
  custom_openai_compatible: 'Custom OpenAI-compatible API'
};

function setStatus(message, tone = 'normal') {
  const element = $('footerStatus');
  element.textContent = message;
  element.style.color = tone === 'error' ? 'var(--danger)' : tone === 'good' ? 'var(--good)' : 'var(--muted)';
}

function markDirty() {
  dirty = true;
  setStatus('Unsaved changes');
}

function setRange(id, value) {
  const input = $(id);
  input.value = value;
  updateRangeOutput(input);
}

function updateRangeOutput(input) {
  const output = document.querySelector(`output[for="${input.id}"]`);
  if (!output) return;
  const numeric = Number(input.value);
  output.textContent = input.step && Number(input.step) < 1 ? numeric.toFixed(2) : String(Math.round(numeric));
}

function fillProviderSelect(select, providers) {
  select.textContent = '';
  for (const provider of providers) {
    const option = document.createElement('option');
    option.value = provider;
    option.textContent = providerLabels[provider] || provider;
    select.appendChild(option);
  }
}

function activeProfile() {
  return state.config.profiles[state.config.activeProfileId];
}

function renderState(nextState) {
  state = nextState;
  const profile = activeProfile();
  const { llm, voice, behavior, motion, memory, permissions } = profile;

  $('activeProfileMetric').textContent = profile.name;
  $('primaryModelMetric').textContent = llm.primary.model || providerLabels[llm.primary.provider] || llm.primary.provider;
  $('connectedOrbsMetric').textContent = String(state.connectedOrbs?.length || 0);

  $('profileName').value = profile.name;
  $('applyScope').value = state.config.applyScope.mode;
  $('orbIds').value = (state.config.applyScope.orbIds || []).join('\n');
  updateScopeVisibility();

  setRange('warmth', behavior.warmth);
  setRange('enthusiasm', behavior.enthusiasm);
  setRange('salesmanship', behavior.salesmanship);
  setRange('humor', behavior.humor);
  setRange('directness', behavior.directness);
  setRange('patience', behavior.patience);
  setRange('initiative', behavior.initiative);
  setRange('verbosity', behavior.verbosity);

  $('voiceEnabled').checked = voice.enabled;
  $('voiceProvider').value = voice.provider;
  $('voiceId').value = voice.voiceId;
  $('voiceStyle').value = voice.styleDirection;
  setRange('volume', voice.volume);
  setRange('rate', voice.rate);
  setRange('pitch', voice.pitch);
  setRange('voiceWarmth', voice.warmth);
  setRange('voiceEnergy', voice.energy);
  $('greetOnArrival').checked = behavior.greetOnArrival;
  $('speakFirst').checked = behavior.speakFirst;
  $('autoListen').checked = behavior.autoListen;

  fillProviderSelect($('primaryProvider'), state.providers);
  fillProviderSelect($('fallbackProvider'), state.providers);
  $('routingMode').value = llm.routingMode;
  $('primaryProvider').value = llm.primary.provider;
  $('primaryModel').value = llm.primary.model;
  $('primaryBaseUrl').value = llm.primary.baseUrl;
  $('primaryTimeout').value = llm.primary.timeoutMs;
  $('fallbackEnabled').checked = llm.fallback.enabled;
  $('fallbackProvider').value = llm.fallback.provider;
  $('fallbackModel').value = llm.fallback.model;
  $('fallbackBaseUrl').value = llm.fallback.baseUrl;
  $('fallbackTimeout').value = llm.fallback.timeoutMs;
  $('primaryApiKey').value = '';
  $('fallbackApiKey').value = '';
  setCredentialStatus('primary', llm.primary.apiKeyStored);
  setCredentialStatus('fallback', llm.fallback.apiKeyStored);

  $('motionEnabled').checked = motion.enabled;
  setRange('motionSpeed', motion.speed);
  $('expressiveMotion').checked = motion.expressive;
  $('avoidHeaderBand').checked = motion.avoidHeaderBand;
  $('sleepEnabled').checked = motion.sleepEnabled;

  $('memoryEnabled').checked = memory.enabled;
  $('rememberAcrossSessions').checked = memory.rememberAcrossSessions;
  $('permissionVoice').checked = permissions.voice;
  $('permissionMicrophone').checked = permissions.microphone;
  $('permissionPointer').checked = permissions.pointerGuidance;
  $('permissionActions').checked = permissions.browserActions;

  $('encryptionNotice').hidden = state.encryptionAvailable;
  $('encryptionBadge').className = `badge ${state.encryptionAvailable ? 'good' : 'warn'}`;
  $('encryptionBadge').innerHTML = `<span class="dot"></span><span>${state.encryptionAvailable ? 'API keys protected' : 'Key protection unavailable'}</span>`;

  const control = state.controlPlane;
  $('controlPlaneAddress').textContent = control ? `http://${control.host}:${control.port}` : 'Unavailable';
  renderOrbs(state.connectedOrbs || []);

  dirty = false;
  setStatus(`Profile revision ${state.config.revision} loaded`, 'good');
}

function setCredentialStatus(slot, stored) {
  const element = $(`${slot}CredentialStatus`);
  element.textContent = stored ? 'Encrypted key stored' : 'No key stored';
  element.classList.toggle('stored', stored);
}

function updateScopeVisibility() {
  $('orbIdsField').hidden = $('applyScope').value !== 'selected_orbs';
}

function collectConfig() {
  const next = structuredClone(state.config);
  const profile = next.profiles[next.activeProfileId];

  profile.name = $('profileName').value.trim();
  next.applyScope.mode = $('applyScope').value;
  next.applyScope.orbIds = $('orbIds').value.split(/\r?\n|,/).map((value) => value.trim()).filter(Boolean);

  profile.behavior.warmth = Number($('warmth').value);
  profile.behavior.enthusiasm = Number($('enthusiasm').value);
  profile.behavior.salesmanship = Number($('salesmanship').value);
  profile.behavior.humor = Number($('humor').value);
  profile.behavior.directness = Number($('directness').value);
  profile.behavior.patience = Number($('patience').value);
  profile.behavior.initiative = Number($('initiative').value);
  profile.behavior.verbosity = Number($('verbosity').value);
  profile.behavior.greetOnArrival = $('greetOnArrival').checked;
  profile.behavior.speakFirst = $('speakFirst').checked;
  profile.behavior.autoListen = $('autoListen').checked;

  profile.voice.enabled = $('voiceEnabled').checked;
  profile.voice.provider = $('voiceProvider').value.trim();
  profile.voice.voiceId = $('voiceId').value.trim();
  profile.voice.styleDirection = $('voiceStyle').value.trim();
  profile.voice.volume = Number($('volume').value);
  profile.voice.rate = Number($('rate').value);
  profile.voice.pitch = Number($('pitch').value);
  profile.voice.warmth = Number($('voiceWarmth').value);
  profile.voice.energy = Number($('voiceEnergy').value);

  profile.llm.routingMode = $('routingMode').value;
  profile.llm.primary.provider = $('primaryProvider').value;
  profile.llm.primary.model = $('primaryModel').value.trim();
  profile.llm.primary.baseUrl = $('primaryBaseUrl').value.trim();
  profile.llm.primary.timeoutMs = Number($('primaryTimeout').value);
  profile.llm.fallback.enabled = $('fallbackEnabled').checked;
  profile.llm.fallback.provider = $('fallbackProvider').value;
  profile.llm.fallback.model = $('fallbackModel').value.trim();
  profile.llm.fallback.baseUrl = $('fallbackBaseUrl').value.trim();
  profile.llm.fallback.timeoutMs = Number($('fallbackTimeout').value);

  profile.motion.enabled = $('motionEnabled').checked;
  profile.motion.speed = Number($('motionSpeed').value);
  profile.motion.expressive = $('expressiveMotion').checked;
  profile.motion.avoidHeaderBand = $('avoidHeaderBand').checked;
  profile.motion.sleepEnabled = $('sleepEnabled').checked;

  profile.memory.enabled = $('memoryEnabled').checked;
  profile.memory.rememberAcrossSessions = $('rememberAcrossSessions').checked;
  profile.permissions.voice = $('permissionVoice').checked;
  profile.permissions.microphone = $('permissionMicrophone').checked;
  profile.permissions.pointerGuidance = $('permissionPointer').checked;
  profile.permissions.browserActions = $('permissionActions').checked;

  return next;
}

async function saveConfig() {
  $('saveButton').disabled = true;
  setStatus('Saving and applying profile…');
  try {
    const result = await window.orbDock.saveConfig(collectConfig());
    if (!result?.ok) throw new Error(result?.error || 'Save failed');
    renderState(result.state);
    setStatus('Profile saved and published to assigned ORBs', 'good');
  } catch (error) {
    setStatus(error.message || 'Unable to save profile', 'error');
  } finally {
    $('saveButton').disabled = false;
  }
}

async function saveCredential(slot) {
  const input = $(`${slot}ApiKey`);
  const apiKey = input.value.trim();
  if (!apiKey) {
    setStatus('Enter an API key before saving it', 'error');
    return;
  }
  try {
    if (dirty) await saveConfig();
    const result = await window.orbDock.saveCredential({
      profileId: state.config.activeProfileId,
      slot,
      apiKey
    });
    input.value = '';
    renderState(result.state);
    setStatus(`${slot === 'primary' ? 'Primary' : 'Fallback'} API key encrypted and saved`, 'good');
  } catch (error) {
    setStatus(error.message || 'Unable to save API key', 'error');
  }
}

async function clearCredential(slot) {
  try {
    const result = await window.orbDock.clearCredential({
      profileId: state.config.activeProfileId,
      slot
    });
    renderState(result.state);
    setStatus(`${slot === 'primary' ? 'Primary' : 'Fallback'} API key removed`, 'good');
  } catch (error) {
    setStatus(error.message || 'Unable to remove API key', 'error');
  }
}

function renderOrbs(orbs) {
  $('connectedOrbsMetric').textContent = String(orbs.length);
  const container = $('orbTableContainer');
  container.textContent = '';
  container.className = '';
  if (!orbs.length) {
    container.className = 'empty';
    container.textContent = 'No ORBs are currently connected.';
    return;
  }

  const table = document.createElement('table');
  table.className = 'orb-list';
  const head = document.createElement('thead');
  const headRow = document.createElement('tr');
  for (const label of ['ORB', 'Type', 'Website', 'Status', 'Last seen']) {
    const th = document.createElement('th');
    th.textContent = label;
    headRow.appendChild(th);
  }
  head.appendChild(headRow);
  table.appendChild(head);

  const body = document.createElement('tbody');
  for (const orb of orbs) {
    const row = document.createElement('tr');
    const values = [orb.name || orb.id, orb.kind, orb.site || '—', orb.status, new Date(orb.lastSeenAt).toLocaleTimeString()];
    for (const value of values) {
      const td = document.createElement('td');
      td.textContent = value || '—';
      row.appendChild(td);
    }
    body.appendChild(row);
  }
  table.appendChild(body);
  container.appendChild(table);
}

async function refreshOrbs() {
  try {
    const result = await window.orbDock.refreshOrbs();
    state.connectedOrbs = result.orbs || [];
    renderOrbs(state.connectedOrbs);
    setStatus('Connected ORB list refreshed', 'good');
  } catch (error) {
    setStatus(error.message || 'Unable to refresh ORBs', 'error');
  }
}

function installListeners() {
  for (const button of document.querySelectorAll('.nav-button')) {
    button.addEventListener('click', () => {
      document.querySelectorAll('.nav-button').forEach((item) => item.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach((item) => item.classList.remove('active'));
      button.classList.add('active');
      $(button.dataset.tab).classList.add('active');
    });
  }

  document.querySelectorAll('input, select, textarea').forEach((control) => {
    control.addEventListener('input', () => {
      if (control.type === 'range') updateRangeOutput(control);
      markDirty();
    });
    control.addEventListener('change', () => {
      if (control.id === 'applyScope') updateScopeVisibility();
      markDirty();
    });
  });

  $('saveButton').addEventListener('click', saveConfig);
  $('hideButton').addEventListener('click', () => window.orbDock.hide());
  $('savePrimaryKey').addEventListener('click', () => saveCredential('primary'));
  $('saveFallbackKey').addEventListener('click', () => saveCredential('fallback'));
  $('clearPrimaryKey').addEventListener('click', () => clearCredential('primary'));
  $('clearFallbackKey').addEventListener('click', () => clearCredential('fallback'));
  $('refreshOrbs').addEventListener('click', refreshOrbs);

  window.addEventListener('beforeunload', (event) => {
    if (!dirty) return;
    event.preventDefault();
    event.returnValue = '';
  });
}

async function start() {
  installListeners();
  try {
    const initial = await window.orbDock.getState();
    renderState(initial);
    window.orbDock.onConfigChanged((profile) => {
      if (!dirty) setStatus(`Runtime profile revision ${profile.revision} is active`, 'good');
    });
  } catch (error) {
    setStatus(error.message || 'Dock Station failed to load', 'error');
    $('runtimeBadge').className = 'badge warn';
    $('runtimeBadge').innerHTML = '<span class="dot"></span><span>Runtime unavailable</span>';
  }
}

start();
