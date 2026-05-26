## 1. Browser OAuth Callback Fix

- [x] 1.1 Main-actor isolate the native `ASWebAuthenticationSession` callback flow in `swift/BluettiKit`
- [x] 1.2 Update the sample integration only if the fixed package path requires a small actor-bridging adjustment

## 2. Validation

- [x] 2.1 Rebuild the Swift sample package after the callback-threading fix
- [x] 2.2 Run `DO_NOT_TRACK=1 rtk openspec validate --all --no-interactive 2>/dev/null` after the fix is in place