# Local Web Page

The local browser page is a small HTML/CSS/JavaScript control surface served by the Python backend from `src/bluetti_connector/web/`. Browser code talks only to the local backend. BLUETTI tokens and cloud calls stay server-side.

## Start The Page

Install and run the Python development runtime:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
cp .env.example .env
bluetti-connector-dev
```

Open `http://127.0.0.1:8080`.

The page supports:

- backend-owned browser OAuth through `Connect with BLUETTI`
- manual access-token and refresh-token session setup for local fallback use
- device discovery and per-device refresh
- safe switch-style and select-style controls when the backend can validate allowed values
- backend-owned live-update status and local SSE-driven refresh hints

## Fake-Gateway Verification

Use the fake gateway when you want deterministic local checks without a live BLUETTI account.

1. Start the fake gateway:

   ```bash
   .venv/bin/python tests/fake_bluetti_gateway.py --port 18081
   ```

2. In another terminal, start the app with loopback fake-gateway live updates enabled:

   ```bash
   BLUETTI_ENABLE_FAKE_GATEWAY_LIVE_UPDATES=true bluetti-connector-dev
   ```

3. Open `http://127.0.0.1:8080`.
4. Click `Load devices` before configuring a session and confirm the page shows the backend session error.
5. Fill the session form with these fake-gateway values:

   - Access token: `expired-access-token`
   - Refresh token: `test-refresh-token`
   - Gateway URL: `http://127.0.0.1:18081`
   - SSO URL: `http://127.0.0.1:18081/sso`
   - WebSocket URL: `ws://127.0.0.1:18081/api/edgeiotgw/ws-coordination`

6. Save the session and confirm the page renders `Workshop Battery`.
7. Confirm the runtime panel reports live updates as connected for the loopback fake gateway.
8. Trigger a fake disconnect and confirm the runtime panel falls back to degraded or manual-refresh messaging:

   ```bash
   curl -sS -X POST http://127.0.0.1:18081/api/test/live-updates/disconnect
   ```

9. Optionally publish a fake device-update hint:

   ```bash
   curl -sS -X POST http://127.0.0.1:18081/api/test/live-updates/device-update \
     -H 'Content-Type: application/json' \
     -d '{"deviceSn":"AC200L-TEST-001"}'
   ```

10. Refresh devices, toggle `AC Output`, and change `Working mode`; confirm success feedback and refreshed device state.

## Browser OAuth Verification

For a live account, start the backend and use `Connect with BLUETTI` on the local page. The backend owns `/api/session/oauth/start` and `/api/session/oauth/callback`; the browser never sends tokens directly to BLUETTI.

If BLUETTI rejects the callback or the local redirect URI is not accepted, use the manual token form as a fallback and record the exact sanitized failure before changing behavior.

## Live-Account Verification

Live-account verification is opt-in to avoid accidental cloud calls.

1. Start the app with a real-account session and `BLUETTI_ENABLE_LIVE_ACCOUNT_VERIFICATION=true`.
2. Invoke:

   ```bash
   curl -sS http://127.0.0.1:8080/api/verification/live-account | python -m json.tool
   ```

The staged response covers auth readiness, device discovery, and live-update readiness. Sanitized errors include `AUTHENTICATION_EXPIRED`, `BLUETTI_CONNECTIVITY_ERROR`, `BLUETTI_TIMEOUT`, `BLUETTI_CLOUD_ERROR`, `LIVE_UPDATES_DEGRADED`, and `LIVE_UPDATES_UNAVAILABLE`.

## JavaScript Checks

Run the browser-side checks from the repository root:

```bash
node --check src/bluetti_connector/web/assets/app.js
node --test tests/web/test_app_live_updates.mjs
```
