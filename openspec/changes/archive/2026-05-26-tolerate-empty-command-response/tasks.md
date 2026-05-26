## 1. Change Artifacts

- [x] 1.1 Add OpenSpec proposal, design, and spec deltas for the empty fulfillment response bugfix

## 2. Swift Command Handling

- [x] 2.1 Accept successful BLUETTI fulfillment responses without payload data in `BluettiClient`
- [x] 2.2 Add a regression test for a successful AC/DC command response that omits payload data

## 3. Validation

- [x] 3.1 Run focused `swift test` validation for `swift/BluettiKit`
- [x] 3.2 Run `DO_NOT_TRACK=1 rtk openspec validate --all --no-interactive 2>/dev/null`