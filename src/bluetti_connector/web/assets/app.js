const state = {
  bootstrap: null,
  session: null,
  devices: [],
};

const elements = {
  sessionForm: document.querySelector('#session-form'),
  accessToken: document.querySelector('#access-token'),
  gatewayUrl: document.querySelector('#gateway-url'),
  ssoUrl: document.querySelector('#sso-url'),
  wssUrl: document.querySelector('#wss-url'),
  sessionSubmit: document.querySelector('#session-submit'),
  loadDevices: document.querySelector('#load-devices'),
  reloadDevices: document.querySelector('#reload-devices'),
  sessionFeedback: document.querySelector('#session-feedback'),
  devicesFeedback: document.querySelector('#devices-feedback'),
  devicesLoading: document.querySelector('#devices-loading'),
  devicesError: document.querySelector('#devices-error'),
  devicesEmpty: document.querySelector('#devices-empty'),
  deviceGrid: document.querySelector('#device-grid'),
  sessionStatusPill: document.querySelector('#session-status-pill'),
  deviceCount: document.querySelector('#device-count'),
  metaEnvironment: document.querySelector('#meta-environment'),
  metaServer: document.querySelector('#meta-server'),
  metaSessionSource: document.querySelector('#meta-session-source'),
  metaAccessToken: document.querySelector('#meta-access-token'),
};

init().catch((error) => {
  showFeedback(elements.devicesFeedback, formatError(error), 'error');
});

async function init() {
  bindEvents();
  await loadBootstrap();
  await loadSession();

  if (state.session?.configured) {
    await fetchDevices();
  } else {
    renderEmptyState('Configure a session and then load devices from the backend.');
  }
}

function bindEvents() {
  elements.sessionForm.addEventListener('submit', onSessionSubmit);
  elements.loadDevices.addEventListener('click', () => fetchDevices());
  elements.reloadDevices.addEventListener('click', () => fetchDevices());
  elements.deviceGrid.addEventListener('click', onDeviceGridClick);
}

async function onSessionSubmit(event) {
  event.preventDefault();
  clearFeedback(elements.sessionFeedback);

  setButtonBusy(elements.sessionSubmit, true, 'Saving…');
  try {
    const payload = {
      accessToken: elements.accessToken.value.trim(),
      gatewayUrl: emptyToNull(elements.gatewayUrl.value),
      ssoUrl: emptyToNull(elements.ssoUrl.value),
      wssUrl: emptyToNull(elements.wssUrl.value),
    };

    state.session = await requestJson('/api/session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    renderSession();
    showFeedback(elements.sessionFeedback, 'Session saved. Loading devices…', 'success');
    await fetchDevices();
  } catch (error) {
    showFeedback(elements.sessionFeedback, formatError(error), 'error');
  } finally {
    setButtonBusy(elements.sessionSubmit, false, 'Save session');
  }
}

async function onDeviceGridClick(event) {
  const actionButton = event.target.closest('[data-action]');
  if (!actionButton) {
    return;
  }

  const deviceSn = actionButton.dataset.deviceSn;
  const action = actionButton.dataset.action;
  const deviceCard = actionButton.closest('[data-device-card]');
  let feedbackNode = deviceCard?.querySelector('.device-feedback') || null;

  setButtonBusy(actionButton, true, actionButton.textContent);
  if (feedbackNode) {
    clearDeviceFeedback(feedbackNode);
  }

  try {
    if (action === 'refresh') {
      const payload = await requestJson(`/api/devices/${encodeURIComponent(deviceSn)}/refresh`, {
        method: 'POST',
      });
      upsertDevice(payload.item);
      renderDevices();
      feedbackNode = findDeviceFeedbackNode(deviceSn);
      setDeviceFeedback(feedbackNode, 'Device state refreshed.', 'success');
      showFeedback(elements.devicesFeedback, `Refreshed ${payload.item.name}.`, 'success');
      return;
    }

    if (action === 'toggle') {
      const payload = await requestJson(`/api/devices/${encodeURIComponent(deviceSn)}/commands`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fnCode: actionButton.dataset.fnCode,
          fnValue: actionButton.dataset.nextValue,
        }),
      });
      upsertDevice(payload.device);
      renderDevices();
      feedbackNode = findDeviceFeedbackNode(deviceSn);
      setDeviceFeedback(feedbackNode, `Command accepted for ${payload.device.name}.`, 'success');
      showFeedback(elements.devicesFeedback, `Command applied to ${payload.device.name}.`, 'success');
    }
  } catch (error) {
    const message = formatError(error);
    setDeviceFeedback(feedbackNode, message, 'error');
    showFeedback(elements.devicesFeedback, message, 'error');
  } finally {
    setButtonBusy(actionButton, false, actionButton.dataset.idleLabel || actionButton.textContent);
  }
}

async function loadBootstrap() {
  state.bootstrap = await requestJson('/api/bootstrap');
  elements.metaEnvironment.textContent = state.bootstrap.environment;
  elements.metaServer.textContent = `${state.bootstrap.server.host}:${state.bootstrap.server.port}`;
  applyBootstrapDefaults(state.bootstrap);
}

async function loadSession() {
  state.session = await requestJson('/api/session');
  renderSession();
}

async function fetchDevices() {
  clearFeedback(elements.devicesFeedback);
  setLoading(true);
  clearDeviceError();

  try {
    const payload = await requestJson('/api/devices');
    state.devices = payload.items;
    renderDevices();
    if (payload.count > 0) {
      showFeedback(elements.devicesFeedback, `Loaded ${payload.count} device${payload.count === 1 ? '' : 's'}.`, 'success');
    }
  } catch (error) {
    state.devices = [];
    renderDevices();
    showDeviceError(formatError(error));
  } finally {
    setLoading(false);
  }
}

function renderSession() {
  const configured = Boolean(state.session?.configured);
  elements.sessionStatusPill.textContent = configured ? 'Configured' : 'Not configured';
  elements.sessionStatusPill.className = configured ? 'status-pill status-pill--success' : 'status-pill status-pill--muted';
  elements.metaSessionSource.textContent = state.session?.source || 'None';
  elements.metaAccessToken.textContent = state.session?.hasAccessToken ? 'Present' : 'Missing';

  const cloud = state.session?.cloud || state.bootstrap?.cloud;
  if (cloud) {
    if (!elements.gatewayUrl.value) {
      elements.gatewayUrl.value = cloud.gatewayUrl || '';
    }
    if (!elements.ssoUrl.value) {
      elements.ssoUrl.value = cloud.ssoUrl || '';
    }
    if (!elements.wssUrl.value) {
      elements.wssUrl.value = cloud.wssUrl || '';
    }
  }
}

function renderDevices() {
  const count = state.devices.length;
  elements.deviceCount.textContent = `${count} device${count === 1 ? '' : 's'}`;
  elements.deviceGrid.innerHTML = '';

  if (count === 0) {
    if (!elements.devicesError.textContent) {
      renderEmptyState('No BLUETTI devices are currently available from the configured session.');
    }
    return;
  }

  hideState(elements.devicesEmpty);
  for (const device of state.devices) {
    elements.deviceGrid.appendChild(buildDeviceCard(device));
  }
}

function buildDeviceCard(device) {
  const card = document.createElement('article');
  card.className = 'device-card';
  card.dataset.deviceCard = device.sn;

  const switchStates = device.states.filter((stateItem) => {
    return typeof stateItem.fnType === 'string' && stateItem.fnType.toLowerCase().includes('switch');
  });

  const stateRows = device.states.slice(0, 6).map((stateItem) => {
    return `
      <div class="state-row">
        <span class="state-row__name">${escapeHtml(stateItem.fnName || stateItem.fnCode)}</span>
        <span class="state-row__value">${escapeHtml(formatStateValue(stateItem))}</span>
      </div>
    `;
  }).join('');

  const actionButtons = switchStates.length === 0
    ? '<span class="summary-chip">No switch actions exposed yet</span>'
    : switchStates.map((stateItem, index) => {
        const isOn = stateItem.fnValue === '1';
        const nextValue = isOn ? '0' : '1';
        const idleLabel = `${isOn ? 'Turn off' : 'Turn on'} ${stateItem.fnName || stateItem.fnCode}`;
        return `
          <button
            type="button"
            class="button ${isOn ? 'button--danger' : 'button--action'}"
            data-action="toggle"
            data-device-sn="${escapeHtml(device.sn)}"
            data-fn-code="${escapeHtml(stateItem.fnCode)}"
            data-next-value="${nextValue}"
            data-idle-label="${escapeHtml(idleLabel)}"
            data-testid="device-command-${index}"
          >${escapeHtml(idleLabel)}</button>
        `;
      }).join('');

  card.innerHTML = `
    <div class="device-card__header">
      <div>
        <h3 class="device-card__title">${escapeHtml(device.name)}</h3>
        <p class="device-card__meta">${escapeHtml(device.model || 'Unknown model')} · ${escapeHtml(device.sn)}</p>
      </div>
      <span class="status-pill ${device.online ? 'status-pill--success' : 'status-pill--danger'}">${device.online ? 'Online' : 'Offline'}</span>
    </div>
    <div class="device-card__body">
      <div class="device-summary">
        <span class="summary-chip">Battery ${device.batteryLevel}%</span>
        <span class="summary-chip">${escapeHtml(device.manufacturer)}</span>
      </div>
      <div class="state-list">${stateRows}</div>
      <div class="device-actions">${actionButtons}</div>
      <div class="device-footer">
        <div class="device-feedback" aria-live="polite"></div>
        <button type="button" class="button button--ghost" data-action="refresh" data-device-sn="${escapeHtml(device.sn)}" data-idle-label="Refresh device">Refresh device</button>
      </div>
    </div>
  `;

  return card;
}

function findDeviceFeedbackNode(deviceSn) {
  return document.querySelector(`[data-device-card="${cssEscape(deviceSn)}"] .device-feedback`);
}

function applyBootstrapDefaults(bootstrap) {
  const session = bootstrap.session || {};
  const cloud = session.cloud || bootstrap.cloud || {};
  elements.gatewayUrl.value = cloud.gatewayUrl || '';
  elements.ssoUrl.value = cloud.ssoUrl || '';
  elements.wssUrl.value = cloud.wssUrl || '';
}

function upsertDevice(device) {
  const index = state.devices.findIndex((item) => item.sn === device.sn);
  if (index === -1) {
    state.devices.push(device);
    return;
  }
  state.devices[index] = device;
}

function renderEmptyState(message) {
  elements.devicesEmpty.textContent = message;
  showState(elements.devicesEmpty);
  elements.deviceGrid.innerHTML = '';
}

function showDeviceError(message) {
  elements.devicesError.textContent = message;
  showState(elements.devicesError);
  hideState(elements.devicesEmpty);
}

function clearDeviceError() {
  elements.devicesError.textContent = '';
  hideState(elements.devicesError);
}

function setLoading(loading) {
  if (loading) {
    showState(elements.devicesLoading);
    return;
  }
  hideState(elements.devicesLoading);
}

function setDeviceFeedback(node, message, tone) {
  if (!node) {
    return;
  }
  node.textContent = message;
  node.className = `device-feedback device-feedback--${tone}`;
}

function clearDeviceFeedback(node) {
  if (!node) {
    return;
  }
  node.textContent = '';
  node.className = 'device-feedback';
}

function showFeedback(node, message, tone) {
  node.textContent = message;
  node.className = `feedback feedback--${tone}`;
  node.hidden = false;
}

function clearFeedback(node) {
  node.textContent = '';
  node.className = 'feedback feedback--hidden';
  node.hidden = true;
}

function showState(node) {
  node.classList.remove('state-banner--hidden');
  node.hidden = false;
}

function hideState(node) {
  node.classList.add('state-banner--hidden');
  node.hidden = true;
}

function setButtonBusy(button, busy, busyLabel) {
  if (!button.dataset.idleLabel) {
    button.dataset.idleLabel = button.textContent;
  }
  button.disabled = busy;
  button.textContent = busy ? busyLabel : button.dataset.idleLabel;
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const text = await response.text();
  const payload = text ? JSON.parse(text) : {};

  if (!response.ok) {
    const error = payload?.error || {};
    const details = error.details;
    throw new Error(error.message || `Request failed with status ${response.status}`, { cause: details });
  }

  return payload;
}

function emptyToNull(value) {
  const trimmed = value.trim();
  return trimmed.length === 0 ? null : trimmed;
}

function formatStateValue(stateItem) {
  if (typeof stateItem.fnType === 'string' && stateItem.fnType.toLowerCase().includes('switch')) {
    return stateItem.fnValue === '1' ? 'On' : 'Off';
  }
  if (stateItem.fnValue !== null && stateItem.fnValue !== undefined && stateItem.fnValue !== '') {
    return String(stateItem.fnValue);
  }
  return stateItem.displayValue || 'Unknown';
}

function formatError(error) {
  if (error instanceof Error) {
    return error.message;
  }
  return 'An unexpected UI error occurred.';
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function cssEscape(value) {
  return String(value).replaceAll('\\', '\\\\').replaceAll('"', '\\"');
}