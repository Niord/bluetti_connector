# swift-menubar-monitor-sample Specification

## MODIFIED Requirements

### Requirement: Menu Bar Sample Polls And Displays Device Status
The menu bar sample SHALL periodically refresh BLUETTI device state, SHALL let the user choose the visible device when multiple devices exist, SHALL show the current battery and power summary in menu bar content, and SHALL mirror the selected device battery percentage in the visible menu bar status item whenever device state is available.

#### Scenario: Selected device status is refreshed
- **WHEN** the sample app has an authenticated BLUETTI session and a selected device
- **THEN** it refreshes that device on demand and on the configured poll interval, then updates the displayed battery percentage and power readings

#### Scenario: Selected device battery is shown in the menu bar item
- **WHEN** the sample app has an authenticated BLUETTI session and a selected device with battery state
- **THEN** the visible menu bar status item shows that battery percentage without requiring the user to open the menu

#### Scenario: Multiple devices are available
- **WHEN** the BLUETTI account exposes more than one device
- **THEN** the sample app allows the user to change the active device shown in the menu bar content