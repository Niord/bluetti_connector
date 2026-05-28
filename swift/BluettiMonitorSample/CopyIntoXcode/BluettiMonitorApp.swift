import AppKit
import AuthenticationServices
import BluettiKit
import Combine
import SwiftUI
import UserNotifications

@main
struct BluettiMonitorApp: App {
    @StateObject private var viewModel = BluettiManager()

    var body: some Scene {
        MenuBarExtra {
            VStack(alignment: .leading, spacing: 12) {
                Text("Bluetti Status")
                    .font(.headline)

                Text(viewModel.statusLine)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)

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

                    statusRow("Battery", "\(viewModel.batteryLevel)%")
                    statusRow("Charging", viewModel.isCharging ? "Yes" : "No")

                    if let pv = selectedDevice.powerMetrics.pvInputWatts {
                        statusRow("PV Input", "\(Int(pv)) W")
                    }

                    if let grid = selectedDevice.powerMetrics.gridInputWatts {
                        statusRow("Grid Input", "\(Int(grid)) W")
                    }

                    if let acLoad = selectedDevice.powerMetrics.acLoadWatts {
                        statusRow("AC Load", "\(Int(acLoad)) W")
                    }

                    if let dcLoad = selectedDevice.powerMetrics.dcLoadWatts {
                        statusRow("DC Load", "\(Int(dcLoad)) W")
                    }

                    Divider()

                    if viewModel.acOutputAvailable {
                        controlRow(
                            title: "AC Output",
                            stateLabel: viewModel.acOutputEnabled ? "On" : "Off",
                            buttonTitle: viewModel.acOutputEnabled ? "Turn Off" : "Turn On"
                        ) {
                            viewModel.setACOutput(!viewModel.acOutputEnabled)
                        }
                        .disabled(viewModel.isLoading)
                    }

                    if viewModel.dcOutputAvailable {
                        controlRow(
                            title: "DC Output",
                            stateLabel: viewModel.dcOutputEnabled ? "On" : "Off",
                            buttonTitle: viewModel.dcOutputEnabled ? "Turn Off" : "Turn On"
                        ) {
                            viewModel.setDCOutput(!viewModel.dcOutputEnabled)
                        }
                        .disabled(viewModel.isLoading)
                    }

                    Divider()

                    HStack {
                        Button("Refresh now") {
                            viewModel.fetchData()
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
                        Button("Refresh now") {
                            viewModel.fetchData()
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
        } label: {
            HStack(spacing: 4) {
                Text(viewModel.menuBarTitle)
                    .monospacedDigit()
                Image(systemName: viewModel.batteryIcon)
            }
        }
        .menuBarExtraStyle(.window)
    }

    private func statusRow(_ title: String, _ value: String) -> some View {
        HStack {
            Text(title)
                .foregroundStyle(.secondary)
            Spacer()
            Text(value)
        }
    }

    private func controlRow(title: String, stateLabel: String, buttonTitle: String, action: @escaping () -> Void) -> some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                Text(stateLabel)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Button(buttonTitle, action: action)
        }
    }
}

@MainActor
final class BluettiManager: ObservableObject {
    @Published private(set) var devices: [BluettiDevice] = []
    @Published private(set) var selectedDeviceSerialNumber: String?
    @Published private(set) var isLoading = false
    @Published private(set) var isAuthenticating = false
    @Published private(set) var isAuthenticated = false
    @Published private(set) var errorMessage: String?
    @Published private(set) var lastUpdatedAt: Date?

    private let client = BluettiClient(
        tokenStore: BluettiKeychainTokenStore(service: "com.example.BluettiMonitor")
    )
    private let notificationCenter = UNUserNotificationCenter.current()
    private let lowBatteryThreshold = 20
    private let refreshInterval: Duration = .seconds(60)
    private let redirectURI = URL(string: "bluetti-monitor://oauth/callback")!

    private var pollingTask: Task<Void, Never>?
    private var hasSentLowBatteryNotification = false

    init() {
        Task {
            await Self.requestNotificationPermission()
            await restoreSessionIfPossible()
        }
    }

    deinit {
        pollingTask?.cancel()
    }

    var selectedDevice: BluettiDevice? {
        guard let selectedDeviceSerialNumber else {
            return nil
        }
        return devices.first(where: { $0.serialNumber == selectedDeviceSerialNumber })
    }

    var batteryLevel: Int {
        selectedDevice?.batteryLevel ?? 0
    }

    var isCharging: Bool {
        let powerMetrics = selectedDevice?.powerMetrics
        return (powerMetrics?.pvInputWatts ?? 0) > 0 || (powerMetrics?.gridInputWatts ?? 0) > 0
    }

    var batteryIcon: String {
        if isCharging {
            return "battery.100.bolt"
        }

        switch batteryLevel {
        case 81...:
            return "battery.100"
        case 51...80:
            return "battery.75"
        case 21...50:
            return "battery.25"
        default:
            return selectedDevice == nil ? "bolt.horizontal.circle" : "battery.0"
        }
    }

    var menuBarTitle: String {
        if let batteryLevel = selectedDevice?.batteryLevel {
            return "\(batteryLevel)%"
        }
        if isAuthenticating {
            return "Auth"
        }
        if isLoading {
            return "..."
        }
        return "BLU"
    }

    var statusLine: String {
        if isAuthenticating {
            return "Connecting to BLUETTI..."
        }
        if isLoading {
            return "Refreshing device status..."
        }
        if !isAuthenticated {
            return "Sign in to start monitoring your BLUETTI devices."
        }
        if let selectedDevice {
            return selectedDevice.isOnline ? "\(selectedDevice.displayName) is online" : "\(selectedDevice.displayName) is offline"
        }
        return "No BLUETTI devices are currently visible for this account."
    }

    var hasMultipleDevices: Bool {
        devices.count > 1
    }

    var canRefresh: Bool {
        isAuthenticated && !isLoading && !isAuthenticating
    }

    var acOutputAvailable: Bool {
        selectedDevice?.state(matching: BluettiKnownStateCodes.acOutput) != nil
    }

    var dcOutputAvailable: Bool {
        selectedDevice?.state(matching: BluettiKnownStateCodes.dcOutput) != nil
    }

    var acOutputEnabled: Bool {
        selectedDevice?.acOutputEnabled ?? false
    }

    var dcOutputEnabled: Bool {
        selectedDevice?.dcOutputEnabled ?? false
    }

    func connect() {
        guard !isAuthenticating else {
            return
        }

        let presentationAnchor = NSApp.keyWindow ?? NSApp.windows.first ?? NSWindow()
        Task {
            await authenticate(presentationAnchor: presentationAnchor)
        }
    }

    func disconnect() {
        Task {
            do {
                try await client.clearSession()
            } catch {
                errorMessage = error.localizedDescription
            }

            pollingTask?.cancel()
            pollingTask = nil
            devices = []
            selectedDeviceSerialNumber = nil
            isAuthenticated = false
            isLoading = false
            isAuthenticating = false
            lastUpdatedAt = nil
            hasSentLowBatteryNotification = false
        }
    }

    func fetchData() {
        Task {
            await refreshData(startPollingIfNeeded: false)
        }
    }

    func selectDevice(serialNumber: String) {
        guard selectedDeviceSerialNumber != serialNumber else {
            return
        }

        selectedDeviceSerialNumber = serialNumber
        Task {
            await refreshSelectedDevice(serialNumber: serialNumber)
        }
    }

    func setACOutput(_ isOn: Bool) {
        guard let serialNumber = selectedDevice?.serialNumber else {
            return
        }

        Task {
            await sendSwitchCommand(
                operation: { try await self.client.setACOutput(serialNumber: serialNumber, isOn: isOn) }
            )
        }
    }

    func setDCOutput(_ isOn: Bool) {
        guard let serialNumber = selectedDevice?.serialNumber else {
            return
        }

        Task {
            await sendSwitchCommand(
                operation: { try await self.client.setDCOutput(serialNumber: serialNumber, isOn: isOn) }
            )
        }
    }

    private func restoreSessionIfPossible() async {
        do {
            let tokens = try await client.loadPersistedTokens()
            isAuthenticated = tokens?.hasAnyToken == true
            if isAuthenticated {
                await refreshData(startPollingIfNeeded: true)
            }
        } catch {
            handle(error: error)
        }
    }

    private func authenticate(presentationAnchor: ASPresentationAnchor) async {
        isAuthenticating = true
        errorMessage = nil

        do {
            let authSession = BluettiBrowserOAuthSession(presentationAnchor: presentationAnchor)
            _ = try await authSession.authenticate(with: client, redirectURI: redirectURI)
            isAuthenticated = true
            await refreshData(startPollingIfNeeded: true)
        } catch {
            handle(error: error)
        }

        isAuthenticating = false
    }

    private func refreshData(startPollingIfNeeded: Bool) async {
        isLoading = true
        errorMessage = nil

        do {
            let listedDevices = try await client.listDevices()
            guard !listedDevices.isEmpty else {
                devices = []
                selectedDeviceSerialNumber = nil
                isAuthenticated = true
                lastUpdatedAt = Date()
                isLoading = false
                if startPollingIfNeeded {
                    ensurePollingTask()
                }
                return
            }

            let nextSerialNumber = resolveSelectedSerialNumber(from: listedDevices)
            let refreshedDevice = try await client.refreshDevice(serialNumber: nextSerialNumber)

            devices = listedDevices.map { device in
                if device.serialNumber == refreshedDevice.serialNumber {
                    return device.merged(with: refreshedDevice)
                }
                return device
            }

            selectedDeviceSerialNumber = nextSerialNumber
            lastUpdatedAt = Date()
            isAuthenticated = true
            handleLowBatteryState(for: refreshedDevice)

            if startPollingIfNeeded {
                ensurePollingTask()
            }
        } catch {
            handle(error: error)
        }

        isLoading = false
    }

    private func refreshSelectedDevice(serialNumber: String) async {
        isLoading = true
        errorMessage = nil

        do {
            let refreshedDevice = try await client.refreshDevice(serialNumber: serialNumber)
            merge(refreshedDevice)
            selectedDeviceSerialNumber = serialNumber
            lastUpdatedAt = Date()
            isAuthenticated = true
            handleLowBatteryState(for: refreshedDevice)
        } catch {
            handle(error: error)
        }

        isLoading = false
    }

    private func sendSwitchCommand(operation: @escaping @Sendable () async throws -> BluettiDevice) async {
        isLoading = true
        errorMessage = nil

        do {
            let refreshedDevice = try await operation()
            merge(refreshedDevice)
            lastUpdatedAt = Date()
            isAuthenticated = true
            handleLowBatteryState(for: refreshedDevice)
        } catch {
            handle(error: error)
        }

        isLoading = false
    }

    private func ensurePollingTask() {
        if pollingTask != nil {
            return
        }

        pollingTask = Task { [refreshInterval] in
            while !Task.isCancelled {
                try? await Task.sleep(for: refreshInterval)
                guard !Task.isCancelled else {
                    return
                }
                await refreshData(startPollingIfNeeded: false)
            }
        }
    }

    private nonisolated static func requestNotificationPermission() async {
        let notificationCenter = UNUserNotificationCenter.current()

        do {
            _ = try await notificationCenter.requestAuthorization(options: [.alert, .sound])
        } catch {
            // Notification permission is optional for this sample.
        }
    }

    private func handleLowBatteryState(for device: BluettiDevice) {
        guard let batteryLevel = device.batteryLevel else {
            return
        }

        if batteryLevel >= lowBatteryThreshold {
            hasSentLowBatteryNotification = false
            return
        }

        guard !hasSentLowBatteryNotification else {
            return
        }

        hasSentLowBatteryNotification = true
        sendNotification(for: device, batteryLevel: batteryLevel)
    }

    private func sendNotification(for device: BluettiDevice, batteryLevel: Int) {
        let content = UNMutableNotificationContent()
        content.title = "Low BLUETTI battery"
        content.body = "\(device.displayName) dropped to \(batteryLevel)%"
        content.sound = .default

        let request = UNNotificationRequest(
            identifier: "bluetti-low-battery-\(device.serialNumber)",
            content: content,
            trigger: nil
        )

        notificationCenter.add(request) { _ in }
    }

    private func resolveSelectedSerialNumber(from listedDevices: [BluettiDevice]) -> String {
        if let selectedDeviceSerialNumber,
           listedDevices.contains(where: { $0.serialNumber == selectedDeviceSerialNumber }) {
            return selectedDeviceSerialNumber
        }

        return listedDevices[0].serialNumber
    }

    private func merge(_ refreshedDevice: BluettiDevice) {
        if let index = devices.firstIndex(where: { $0.serialNumber == refreshedDevice.serialNumber }) {
            devices[index] = devices[index].merged(with: refreshedDevice)
        } else {
            devices.append(refreshedDevice)
        }
    }

    private func handle(error: Error) {
        errorMessage = error.localizedDescription

        if let bluettiError = error as? BluettiError {
            switch bluettiError {
            case .sessionNotConfigured, .authenticationExpired:
                isAuthenticated = false
                devices = []
                selectedDeviceSerialNumber = nil
                pollingTask?.cancel()
                pollingTask = nil
            default:
                break
            }
        }
    }
}