import assert from 'node:assert/strict';
import test from 'node:test';


const DEVICE_SN = 'AC3002306000478165';
const APP_URL = new URL('../../src/bluetti_connector/web/assets/app.js', import.meta.url);
const ELEMENT_IDS = [
  'session-form',
  'access-token',
  'refresh-token',
  'gateway-url',
  'sso-url',
  'wss-url',
  'session-submit',
  'load-devices',
  'reload-devices',
  'session-feedback',
  'devices-feedback',
  'devices-loading',
  'devices-error',
  'devices-empty',
  'device-grid',
  'session-status-pill',
  'device-count',
  'meta-environment',
  'meta-server',
  'meta-session-source',
  'meta-auth-mode',
  'meta-access-token',
  'meta-refresh-token',
  'meta-stored-session',
  'meta-live-updates',
  'meta-live-updates-detail',
  'live-updates-banner',
];

const INITIAL_DEVICE = {
  deviceId: 'device-1',
  sn: DEVICE_SN,
  name: 'AC300',
  model: 'AC300',
  manufacturer: 'BLUETTI',
  online: true,
  batteryLevel: 81,
  states: [
    {
      fnCode: 'SetCtrlWorkMode',
      fnName: 'Working mode',
      fnValue: '1',
      fnType: 'enum',
      displayValue: 'Standard UPS',
      sensorInfo: {},
      control: {
        kind: 'select',
        allowedValues: [
          { value: '1', label: 'Standard UPS' },
          { value: '2', label: 'PV Priority' },
        ],
      },
    },
    {
      fnCode: 'SOC',
      fnName: 'Battery',
      fnValue: '81',
      fnType: 'number',
      displayValue: '81%',
      sensorInfo: {},
      control: null,
    },
  ],
};

const REFRESHED_DEVICE = {
  ...INITIAL_DEVICE,
  states: [
    {
      ...INITIAL_DEVICE.states[0],
      fnValue: '2',
      displayValue: 'PV Priority',
    },
    INITIAL_DEVICE.states[1],
  ],
};


class FakeClassList {
  constructor(element) {
    this.element = element;
  }

  add(...tokens) {
    const values = new Set(this.element.className.split(/\s+/).filter(Boolean));
    for (const token of tokens) {
      values.add(token);
    }
    this.element.className = [...values].join(' ');
  }

  remove(...tokens) {
    const values = new Set(this.element.className.split(/\s+/).filter(Boolean));
    for (const token of tokens) {
      values.delete(token);
    }
    this.element.className = [...values].join(' ');
  }
}


class FakeElement {
  constructor(id = null) {
    this.id = id;
    this.value = '';
    this.textContent = '';
    this.className = '';
    this.hidden = false;
    this.dataset = {};
    this.disabled = false;
    this.children = [];
    this._innerHTML = '';
    this._listeners = new Map();
    this.classList = new FakeClassList(this);
  }

  addEventListener(type, handler) {
    const handlers = this._listeners.get(type) || [];
    handlers.push(handler);
    this._listeners.set(type, handlers);
  }

  async trigger(type, eventOverrides = {}) {
    const handlers = this._listeners.get(type) || [];
    for (const handler of handlers) {
      await handler({
        preventDefault() {},
        target: this,
        currentTarget: this,
        ...eventOverrides,
      });
    }
  }

  appendChild(child) {
    this.children.push(child);
    return child;
  }

  closest() {
    return null;
  }

  querySelector() {
    return null;
  }

  set innerHTML(value) {
    this._innerHTML = value;
    if (value === '') {
      this.children = [];
    }
  }

  get innerHTML() {
    return this._innerHTML;
  }
}


class FakeDocument {
  constructor() {
    this.title = 'BLUETTI Connector';
    this._nodes = new Map();
    for (const id of ELEMENT_IDS) {
      this._nodes.set(`#${id}`, new FakeElement(id));
    }
  }

  querySelector(selector) {
    return this._nodes.get(selector) || null;
  }

  createElement(tagName) {
    return new FakeElement(tagName);
  }

  getById(id) {
    return this._nodes.get(`#${id}`);
  }
}


class FakeEventSource {
  static instances = [];

  constructor(url) {
    this.url = url;
    this._listeners = new Map();
    FakeEventSource.instances.push(this);
  }

  addEventListener(type, handler) {
    const handlers = this._listeners.get(type) || [];
    handlers.push(handler);
    this._listeners.set(type, handlers);
  }

  emit(type, payload) {
    const handlers = this._listeners.get(type) || [];
    for (const handler of handlers) {
      handler({ data: JSON.stringify(payload) });
    }
  }

  close() {}

  static latest() {
    return FakeEventSource.instances.at(-1) || null;
  }

  static reset() {
    FakeEventSource.instances = [];
  }
}


function createJsonResponse(payload, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    async text() {
      return payload === null ? '' : JSON.stringify(payload);
    },
  };
}

function createSession(liveUpdates = { configured: true, status: 'connected', lastError: null }) {
  return {
    configured: true,
    source: 'manual',
    authMode: 'token',
    usesStoredSession: false,
    hasAccessToken: true,
    hasRefreshToken: true,
    cloud: {
      gatewayUrl: 'https://gw.bluettipower.com',
      ssoUrl: 'https://sso.bluettipower.com',
      wssUrl: 'wss://gw.bluettipower.com/api/edgeiotgw/ws-coordination/',
    },
    liveUpdates,
  };
}

function createBootstrap() {
  return {
    environment: 'development',
    server: { host: '127.0.0.1', port: 8080 },
    cloud: createSession().cloud,
    session: { cloud: createSession().cloud },
  };
}

function createFetchStub() {
  const calls = [];

  return {
    calls,
    fetch: async (url, options = {}) => {
      calls.push({ url, method: options.method || 'GET' });

      if (url === '/api/bootstrap') {
        return createJsonResponse(createBootstrap());
      }
      if (url === '/api/session') {
        return createJsonResponse(createSession());
      }
      if (url === '/api/devices') {
        return createJsonResponse({ count: 1, items: [INITIAL_DEVICE] });
      }
      if (url === `/api/devices/${encodeURIComponent(DEVICE_SN)}/refresh`) {
        return createJsonResponse({ item: REFRESHED_DEVICE });
      }

      throw new Error(`Unexpected fetch call: ${url}`);
    },
  };
}

async function flushAsyncWork(rounds = 4) {
  for (let index = 0; index < rounds; index += 1) {
    await Promise.resolve();
    await new Promise((resolve) => setTimeout(resolve, 0));
  }
}

async function waitFor(predicate, message, attempts = 20) {
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    if (predicate()) {
      return;
    }
    await flushAsyncWork();
  }

  throw new Error(message);
}

async function loadApp() {
  const document = new FakeDocument();
  const fetchStub = createFetchStub();

  FakeEventSource.reset();
  globalThis.document = document;
  globalThis.window = {
    location: {
      search: '',
      pathname: '/',
      hash: '',
    },
    history: {
      replaceState() {},
    },
  };
  globalThis.fetch = fetchStub.fetch;
  globalThis.EventSource = FakeEventSource;

  const appUrl = new URL(APP_URL.href);
  appUrl.search = `?test=${Date.now()}-${Math.random()}`;
  await import(appUrl.href);
  await flushAsyncWork();

  return {
    document,
    fetchCalls: fetchStub.calls,
    eventSource: FakeEventSource.latest(),
  };
}

function cleanupGlobals() {
  delete globalThis.document;
  delete globalThis.window;
  delete globalThis.fetch;
  delete globalThis.EventSource;
}


test('live update events refresh visible devices and update runtime status feedback', { concurrency: false }, async () => {
  try {
    const harness = await loadApp();
    const deviceGrid = harness.document.getById('device-grid');
    const loadDevicesButton = harness.document.getById('load-devices');

    assert.equal(harness.document.getById('meta-live-updates').textContent, 'Connected');
    assert.match(harness.document.getById('live-updates-banner').textContent, /Live updates are active/);

    await loadDevicesButton.trigger('click');
    await waitFor(
      () => harness.fetchCalls.some((call) => call.url === '/api/devices' && call.method === 'GET'),
      'Expected the UI to request the device list through the backend.'
    );
    await waitFor(() => deviceGrid.children.length === 1, 'Expected the initial device card to render.');
    assert.equal(deviceGrid.children.length, 1);
    assert.match(deviceGrid.children[0].innerHTML, /Standard UPS/);

    harness.eventSource.emit('device-update', {
      eventType: 'device-update',
      deviceSn: DEVICE_SN,
    });
    await waitFor(
      () => harness.fetchCalls.some((call) => call.url === `/api/devices/${encodeURIComponent(DEVICE_SN)}/refresh`),
      'Expected the UI to call the backend refresh endpoint after a live device update.'
    );
    await waitFor(() => /PV Priority/.test(deviceGrid.children[0]?.innerHTML || ''), 'Expected the device card to refresh after a live update.');

    assert.ok(
      harness.fetchCalls.some(
        (call) => call.url === `/api/devices/${encodeURIComponent(DEVICE_SN)}/refresh` && call.method === 'POST'
      )
    );
    assert.equal(
      harness.fetchCalls.filter(
        (call) => call.url === `/api/devices/${encodeURIComponent(DEVICE_SN)}/refresh` && call.method === 'POST'
      ).length,
      1
    );
    assert.equal(deviceGrid.children.length, 1);
    assert.match(deviceGrid.children[0].innerHTML, /PV Priority/);

    harness.eventSource.emit('status', {
      eventType: 'status',
      status: 'degraded',
      lastError: 'Live updates disconnected.',
    });
    await flushAsyncWork();

    assert.equal(harness.document.getById('meta-live-updates').textContent, 'Degraded');
    assert.match(harness.document.getById('meta-live-updates-detail').textContent, /Live updates disconnected/);
    assert.match(harness.document.getById('live-updates-banner').textContent, /Manual refresh remains available/);
    assert.match(harness.document.getById('live-updates-banner').className, /state-banner--error/);
  } finally {
    cleanupGlobals();
  }
});