import AppKit
import SwiftUI

struct BluettiMonitorMenuContent: View {
    @ObservedObject var viewModel: BluettiMonitorViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Bluetti Status")
                .font(.headline)

            Text(viewModel.statusLine)
                .font(.subheadline)
                .foregroundStyle(.secondary)

            if let liveUpdateStatusLine = viewModel.liveUpdateStatusLine {
                Text(liveUpdateStatusLine)
                    .font(.caption)
                    .foregroundStyle(viewModel.usesPollingFallback ? .orange : .secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            if !viewModel.isAuthenticated {
                Button(viewModel.isAuthenticating ? "Connecting..." : "Connect with BLUETTI") {
                    viewModel.connect()
                }
                .disabled(viewModel.isAuthenticating)
            } else if let selectedDevice = viewModel.selectedDevice {
                if viewModel.hasMultipleDevices {
                    Picker(
                        "Device",
                        selection: Binding(
                            get: { viewModel.selectedDeviceSerialNumber ?? selectedDevice.serialNumber },
                            set: { viewModel.selectDevice(serialNumber: $0) }
                        )
                    ) {
                        ForEach(viewModel.devices) { device in
                            Text(device.displayName)
                                .tag(device.serialNumber)
                        }
                    }
                    .pickerStyle(.menu)
                }

                Divider()

                MetricRow(title: "Battery", value: "\(selectedDevice.batteryLevel ?? 0)%")
                MetricRow(title: "Charging", value: viewModel.isCharging ? "Yes" : "No")

                if let pvInputWatts = selectedDevice.powerMetrics.pvInputWatts {
                    MetricRow(title: "PV Input", value: powerText(pvInputWatts))
                }

                if let gridInputWatts = selectedDevice.powerMetrics.gridInputWatts {
                    MetricRow(title: "Grid Input", value: powerText(gridInputWatts))
                }

                if let acLoadWatts = selectedDevice.powerMetrics.acLoadWatts {
                    MetricRow(title: "AC Load", value: powerText(acLoadWatts))
                }

                if let dcLoadWatts = selectedDevice.powerMetrics.dcLoadWatts {
                    MetricRow(title: "DC Load", value: powerText(dcLoadWatts))
                }

                Divider()

                if viewModel.acOutputAvailable {
                    ControlRow(
                        title: "AC Output",
                        stateLabel: viewModel.acOutputEnabled ? "On" : "Off",
                        actionTitle: viewModel.acOutputEnabled ? "Turn Off" : "Turn On"
                    ) {
                        viewModel.setACOutput(!viewModel.acOutputEnabled)
                    }
                    .disabled(viewModel.isLoading)
                }

                if viewModel.dcOutputAvailable {
                    ControlRow(
                        title: "DC Output",
                        stateLabel: viewModel.dcOutputEnabled ? "On" : "Off",
                        actionTitle: viewModel.dcOutputEnabled ? "Turn Off" : "Turn On"
                    ) {
                        viewModel.setDCOutput(!viewModel.dcOutputEnabled)
                    }
                    .disabled(viewModel.isLoading)
                }

                Divider()

                HStack {
                    Button("Refresh") {
                        viewModel.refreshNow()
                    }
                    .disabled(!viewModel.canRefresh)

                    Button("Disconnect") {
                        viewModel.disconnect()
                    }
                    .disabled(viewModel.isLoading || viewModel.isAuthenticating)
                }

                if let lastUpdatedAt = viewModel.lastUpdatedAt {
                    Text("Updated \(lastUpdatedAt.formatted(date: .omitted, time: .shortened))")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            } else {
                Text("No BLUETTI devices are currently visible for this account.")
                    .foregroundStyle(.secondary)

                HStack {
                    Button("Refresh") {
                        viewModel.refreshNow()
                    }
                    .disabled(!viewModel.canRefresh)

                    Button("Disconnect") {
                        viewModel.disconnect()
                    }
                }
            }

            if let errorMessage = viewModel.errorMessage {
                Divider()

                Text(errorMessage)
                    .font(.caption)
                    .foregroundStyle(.red)
                    .fixedSize(horizontal: false, vertical: true)
            }

            Divider()

            Button("Quit BluettiMonitor") {
                NSApplication.shared.terminate(nil)
            }
            .keyboardShortcut("q")
        }
        .padding()
        .frame(minWidth: 320)
    }

    private func powerText(_ watts: Double) -> String {
        "\(Int(watts)) W"
    }
}

private struct MetricRow: View {
    let title: String
    let value: String

    var body: some View {
        HStack {
            Text(title)
                .foregroundStyle(.secondary)
            Spacer()
            Text(value)
        }
    }
}

private struct ControlRow: View {
    let title: String
    let stateLabel: String
    let actionTitle: String
    let action: () -> Void

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                Text(stateLabel)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Button(actionTitle, action: action)
        }
    }
}