## Context

The current Swift client uses one generic gateway-envelope path for both read requests and command fulfillment requests. That is correct for device-list and device-state endpoints, where `data` must exist, but it is too strict for BLUETTI command responses because the gateway can acknowledge success with `msgCode == 0` and no payload body.

The closest control point is `sendCommand` in `BluettiClient`. The sample app already clears the previous error and merges the returned device state on success, so the user-visible false failure comes from the package throwing before that optimistic state update can complete.

## Goals / Non-Goals

**Goals:**
- accept successful BLUETTI fulfillment responses that omit the `data` field or set it to `null`
- keep strict `data` requirements for read-style gateway endpoints that actually need decoded payloads
- add regression coverage for the successful empty-response command case

**Non-Goals:**
- changing how unsupported commands or failed BLUETTI responses are validated
- adding new UI error strings or new menu bar controls
- reworking the broader request pipeline beyond the command-acceptance path

## Decisions

### 1. Add a command-specific envelope path instead of weakening all gateway requests
The client will keep the existing payload-required path for typed read requests and add a dedicated fulfillment acceptance path for commands.

Why: only the fulfillment endpoint is currently known to acknowledge success without returning useful payload data. Narrowing the tolerance to the command path fixes the false error without making device reads more permissive.

Alternative considered: remove the `data` requirement from all gateway responses. Rejected because that would hide malformed responses from endpoints that should always return device payloads.

### 2. Keep optimistic local state updates after accepted commands
After the fulfillment request is accepted, the client will continue returning `device.updatingState(...)` instead of forcing an extra refresh round-trip.

Why: the existing package and sample already rely on this optimistic merge for responsive UI updates, and the bug is only that the acceptance step fails too early.

Alternative considered: re-fetch the device after every command. Rejected because it adds latency and unnecessary network traffic without solving the gateway-response inconsistency directly.

## Risks / Trade-offs

- [A malformed fulfillment response with `msgCode == 0` and no payload will now be treated as accepted] -> Limit the relaxed behavior to fulfillment requests only and continue rejecting non-zero `msgCode`, HTTP failures, and authentication-expiry responses.
- [The package still does not verify any optional `accepted` flag in the payload] -> Preserve the current contract because the gateway already communicates success through `msgCode`, and this change is scoped to false-negative handling.

## Migration Plan

1. Add OpenSpec artifacts for the fulfillment empty-response bugfix.
2. Patch `BluettiClient` so commands use a success-without-payload acceptance path.
3. Add a regression test for an empty successful fulfillment response and run focused Swift tests.
4. Sync the delta specs into the main specs, validate OpenSpec, and archive the change.

Rollback strategy: restore the previous shared envelope path for commands and remove the regression artifacts if the gateway contract turns out to require payload data after all.

## Open Questions

- Whether other BLUETTI write endpoints besides `fulfillment` also need the same empty-success tolerance in future native client work.