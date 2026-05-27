import AppKit
import AuthenticationServices
import BluettiKit
import Combine
import Foundation
import UserNotifications

@MainActor
final class BluettiMonitorViewModel: ObservableObject {
    @Published private(set) var devices: [BluettiDevice] = []
    @Published private(set) var selectedDeviceSerialNumber: String?
    @Published private(set) var isLoading = false
    @Published private(set) var isAuthenticating = false
    @Published private(set) var isAuthenticated = false
    @Published private(set) var errorMessage: String?
    @Published private(set) var lastUpdatedAt: Date?
    @Published private(set) var liveUpdateSnapshot = BluettiLiveUpdateSnapshot(configured: false, status: .disabled, lastError: nil)

    private let client: BluettiClient
    private let notificationCenter: UNUserNotificationCenter
    private let lowBatteryThreshold: Int
    private let refreshInterval: Duration

    private var pollingTask: Task<Void, Never>?
    private var liveUpdateSubscriptionTask: Task<Void, Never>?
    private var liveHintRefreshTask: Task<Void, Never>?
    private var hasSentLowBatteryNotification = false

    init(
        client: BluettiClient = BluettiClient(
            tokenStore: BluettiKeychainTokenStore(service: BluettiMonitorSampleConfig.keychainService)
        ),
        notificationCenter: UNUserNotificationCenter = .current(),
        lowBatteryThreshold: Int = BluettiMonitorSampleConfig.lowBatteryThreshold,
        refreshInterval: Duration = BluettiMonitorSampleConfig.refreshInterval
    ) {
        self.client = client
        self.notificationCenter = notificationCenter
        self.lowBatteryThreshold = lowBatteryThreshold
        self.refreshInterval = refreshInterval

        Task {
            await requestNotificationPermission()
            await restoreSessionIfPossible()
        }
    }

    deinit {
        pollingTask?.cancel()
        liveUpdateSubscriptionTask?.cancel()
        liveHintRefreshTask?.cancel()
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

    var hasMultipleDevices: Bool {
        devices.count > 1
    }

    var canRefresh: Bool {
        isAuthenticated && !isLoading && !isAuthenticating
    }

    var liveUpdateStatusLine: String? {
        guard isAuthenticated else {
            return nil
        }

        switch liveUpdateSnapshot.status {
        case .connected:
            return "Live updates connected."
        case .connecting:
            return "Connecting live updates..."
        case .degraded:
            if let lastError = liveUpdateSnapshot.lastError, !lastError.isEmpty {
                return "\(lastError) Polling fallback is active."
            }
            return "Live updates degraded. Polling fallback is active."
        case .disabled:
            return "Live updates unavailable. Polling fallback is active."
        }
    }

    var usesPollingFallback: Bool {
        isAuthenticated && liveUpdateSnapshot.status != .connected
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
            liveUpdateSubscriptionTask?.cancel()
            liveUpdateSubscriptionTask = nil
            liveHintRefreshTask?.cancel()
            liveHintRefreshTask = nil
            devices = []
            selectedDeviceSerialNumber = nil
            isAuthenticated = false
            isLoading = false
            isAuthenticating = false
            lastUpdatedAt = nil
            liveUpdateSnapshot = BluettiLiveUpdateSnapshot(configured: false, status: .disabled, lastError: nil)
            hasSentLowBatteryNotification = false
        }
    }

    func refreshNow() {
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
            } else {
                syncPollingStrategy()
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
            _ = try await authSession.authenticate(
                with: client,
                redirectURI: BluettiMonitorSampleConfig.redirectURI
            )

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
                    await ensureLiveUpdatesRunning()
                }
                syncPollingStrategy()
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
                await ensureLiveUpdatesRunning()
            }
            syncPollingStrategy()
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
            syncPollingStrategy()
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
            syncPollingStrategy()
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

    private func ensureLiveUpdatesRunning() async {
        guard isAuthenticated else {
            return
        }

        if liveUpdateSubscriptionTask == nil {
            liveUpdateSubscriptionTask = Task { @MainActor [client] in
                let stream = await client.liveUpdates()
                for await event in stream {
                    guard !Task.isCancelled else {
                        return
                    }
                    handleLiveUpdateEvent(event)
                }
            }
        }

        liveUpdateSnapshot = await client.liveUpdateSnapshot()
        await client.startLiveUpdates()
    }

    private func handleLiveUpdateEvent(_ event: BluettiLiveUpdateEvent) {
        switch event {
        case let .status(snapshot):
            liveUpdateSnapshot = snapshot
            syncPollingStrategy()
        case let .deviceUpdate(serialNumber):
            guard serialNumber == selectedDeviceSerialNumber else {
                return
            }
            guard !isLoading else {
                return
            }

            liveHintRefreshTask?.cancel()
            liveHintRefreshTask = Task { @MainActor [serialNumber] in
                await refreshSelectedDevice(serialNumber: serialNumber)
            }
        }
    }

    private func syncPollingStrategy() {
        guard isAuthenticated else {
            pollingTask?.cancel()
            pollingTask = nil
            return
        }

        if liveUpdateSnapshot.status == .connected {
            pollingTask?.cancel()
            pollingTask = nil
            return
        }

        ensurePollingTask()
    }

    private func requestNotificationPermission() async {
        do {
            _ = try await notificationCenter.requestAuthorization(options: [.alert, .sound])
        } catch {
            // Notification permission is optional for the sample.
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
        sendLowBatteryNotification(for: device, batteryLevel: batteryLevel)
    }

    private func sendLowBatteryNotification(for device: BluettiDevice, batteryLevel: Int) {
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
                liveUpdateSubscriptionTask?.cancel()
                liveUpdateSubscriptionTask = nil
                liveHintRefreshTask?.cancel()
                liveHintRefreshTask = nil
                liveUpdateSnapshot = BluettiLiveUpdateSnapshot(configured: false, status: .disabled, lastError: nil)
            default:
                break
            }
        }
    }
}