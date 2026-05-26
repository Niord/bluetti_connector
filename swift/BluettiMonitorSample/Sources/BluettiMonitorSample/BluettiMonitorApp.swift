import SwiftUI

@main
struct BluettiMonitorApp: App {
    @StateObject private var viewModel = BluettiMonitorViewModel()

    var body: some Scene {
        MenuBarExtra {
            BluettiMonitorMenuContent(viewModel: viewModel)
        } label: {
            HStack(spacing: 4) {
                Text(viewModel.menuBarTitle)
                    .monospacedDigit()
                Image(systemName: viewModel.batteryIcon)
            }
        }
        .menuBarExtraStyle(.window)
    }
}

enum BluettiMonitorSampleConfig {
    static let redirectURI = URL(string: "bluetti-monitor://oauth/callback")!
    static let keychainService = "com.example.BluettiMonitor"
    static let lowBatteryThreshold = 20
    static let refreshInterval: Duration = .seconds(60)
}