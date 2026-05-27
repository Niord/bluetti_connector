import Foundation

public enum BluettiLiveUpdateStatus: String, Equatable, Sendable {
    case disabled
    case connecting
    case connected
    case degraded
}

public struct BluettiLiveUpdateSnapshot: Equatable, Sendable {
    public var configured: Bool
    public var status: BluettiLiveUpdateStatus
    public var lastError: String?

    public init(configured: Bool, status: BluettiLiveUpdateStatus, lastError: String? = nil) {
        self.configured = configured
        self.status = status
        self.lastError = lastError
    }
}

public enum BluettiLiveUpdateEvent: Equatable, Sendable {
    case status(BluettiLiveUpdateSnapshot)
    case deviceUpdate(serialNumber: String)
}

internal typealias BluettiWebSocketTaskFactory = @Sendable (URL) -> any BluettiWebSocketTaskProtocol

internal protocol BluettiWebSocketTaskProtocol: AnyObject, Sendable {
    func resume() async
    func send(_ message: URLSessionWebSocketTask.Message) async throws
    func receive() async throws -> URLSessionWebSocketTask.Message
    func cancel(with closeCode: URLSessionWebSocketTask.CloseCode, reason: Data?) async
}

internal final class URLSessionBluettiWebSocketTask: BluettiWebSocketTaskProtocol, @unchecked Sendable {
    private let task: URLSessionWebSocketTask

    init(task: URLSessionWebSocketTask) {
        self.task = task
    }

    func resume() async {
        task.resume()
    }

    func send(_ message: URLSessionWebSocketTask.Message) async throws {
        try await task.send(message)
    }

    func receive() async throws -> URLSessionWebSocketTask.Message {
        try await task.receive()
    }

    func cancel(with closeCode: URLSessionWebSocketTask.CloseCode, reason: Data?) async {
        task.cancel(with: closeCode, reason: reason)
    }
}

internal enum BluettiLiveUpdateTransportError: Error, LocalizedError, Equatable {
    case authenticationExpired
    case disconnected
    case invalidPayload
    case invalidResponse(String)
    case cloudError(code: Int, description: String)

    var errorDescription: String? {
        switch self {
        case .authenticationExpired:
            return "Live updates authentication expired."
        case .disconnected:
            return "Live updates disconnected."
        case .invalidPayload:
            return "Live updates returned an invalid payload."
        case let .invalidResponse(description):
            return description
        case let .cloudError(code, description):
            return "Live updates failed with BLUETTI code \(code): \(description)"
        }
    }
}

internal struct BluettiStompFrame: Equatable {
    let command: String
    let headers: [String: String]
    let body: String

    init(text: String) throws {
        let normalized = text
            .replacingOccurrences(of: "\r\n", with: "\n")
            .replacingOccurrences(of: "\0", with: "")

        let parts = normalized.components(separatedBy: "\n\n")
        guard let headerBlock = parts.first else {
            throw BluettiLiveUpdateTransportError.invalidPayload
        }

        let lines = headerBlock.components(separatedBy: "\n")
        guard let firstLine = lines.first?.trimmingCharacters(in: .whitespacesAndNewlines), !firstLine.isEmpty else {
            throw BluettiLiveUpdateTransportError.invalidPayload
        }

        command = firstLine
        var parsedHeaders: [String: String] = [:]
        for line in lines.dropFirst() where !line.isEmpty {
            let components = line.split(separator: ":", maxSplits: 1, omittingEmptySubsequences: false)
            guard components.count == 2 else {
                continue
            }
            parsedHeaders[String(components[0])] = String(components[1]).trimmingCharacters(in: .whitespaces)
        }
        headers = parsedHeaders
        body = parts.dropFirst().joined(separator: "\n\n").trimmingCharacters(in: .newlines)
    }

    static func connectFrame(host: String, accessToken: String) -> String {
        """
        CONNECT
        accept-version:1.0,1.1,2.0
        Host:\(host)
        Authorization: \(accessToken)
        heart-beat:10000,10000

        \0
        """
    }

    static func subscribeFrame(destination: String) -> String {
        """
        SUBSCRIBE
        id:clientUniqueId
        destination:\(destination)
        ack:auto

        \0
        """
    }
}

internal struct BluettiLiveUpdateMessagePayload: Decodable {
    let data: DevicePayload?

    struct DevicePayload: Decodable {
        let deviceSn: String?
    }
}