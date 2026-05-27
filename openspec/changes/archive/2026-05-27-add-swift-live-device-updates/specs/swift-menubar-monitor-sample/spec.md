## MODIFIED Requirements

### Requirement: Menu Bar Sample Polls And Displays Device Status
The menu bar sample SHALL subscribe to `BluettiKit` live updates for the active BLUETTI session when that live path is available, SHALL refresh the selected device on relevant live-update hints, SHALL fall back to explicit refresh or polling when live updates are degraded or unavailable, SHALL let the user choose the visible device when multiple devices exist, SHALL show the current battery and power summary in menu bar content, and SHALL mirror the selected device battery percentage in the visible menu bar status item whenever device state is available.

#### Scenario: Selected device status is refreshed from a live-update hint
- **WHEN** the sample app has an authenticated BLUETTI session, live updates are connected, and the selected device receives a live-update hint
- **THEN** the sample refreshes that selected device through `BluettiKit` and updates the displayed battery percentage and power readings without waiting for the fallback poll interval

#### Scenario: Live updates are unavailable for the selected device
- **WHEN** the sample app cannot keep the BLUETTI live-update session connected for the current selection
- **THEN** it shows that live updates are unavailable or degraded and continues to keep device status fresh through explicit refresh or fallback polling

#### Scenario: Selected device battery is shown in the menu bar item
- **WHEN** the sample app has an authenticated BLUETTI session and a selected device with battery state
- **THEN** the visible menu bar status item shows that battery percentage without requiring the user to open the menu

#### Scenario: Multiple devices are available
- **WHEN** the BLUETTI account exposes more than one device
- **THEN** the sample app allows the user to change the active device shown in the menu bar content