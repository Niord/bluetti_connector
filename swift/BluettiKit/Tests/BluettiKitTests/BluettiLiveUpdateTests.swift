import Foundation
import XCTest
@testable import BluettiKit

final class BluettiLiveUpdateTests: XCTestCase {
    func testStartLiveUpdatesSendsHandshakeAndPublishesDeviceUpdateHints() async throws {
        let socketTask = MockWebSocketTask()
        let client = makeClient(socketTask: socketTask)
        let collectedEventsTask = Task {
            let stream = await client.liveUpdates()
            var iterator = stream.makeAsyncIterator()
            var events: [BluettiLiveUpdateEvent] = []

            while events.count < 4, let event = await iterator.next() {
                events.append(event)
            }
            return events
        }
        addTeardownBlock {
            collectedEventsTask.cancel()
            await client.stopLiveUpdates()
        }

        await client.startLiveUpdates()
        await socketTask.enqueue(text: connectedFrame(userName: "swift-user"))
        await socketTask.enqueue(text: deviceUpdateFrame(serialNumber: "AC200L-TEST-001"))

        let events = try await valueWithTimeout(of: collectedEventsTask, timeout: .seconds(1))
        let sentFrames = await socketTask.sentTextFrames()
        let isResumed = await socketTask.resumed()

        XCTAssertEqual(
            events,
            [
                .status(BluettiLiveUpdateSnapshot(configured: false, status: .disabled, lastError: nil)),
                .status(BluettiLiveUpdateSnapshot(configured: true, status: .connecting, lastError: nil)),
                .status(BluettiLiveUpdateSnapshot(configured: true, status: .connected, lastError: nil)),
                .deviceUpdate(serialNumber: "AC200L-TEST-001"),
            ]
        )
        XCTAssertEqual(isResumed, true)
        XCTAssertTrue(sentFrames.contains(where: { $0.hasPrefix("CONNECT\n") }))
        XCTAssertTrue(sentFrames.contains(where: { $0.hasPrefix("SUBSCRIBE\n") && $0.contains("/ws-subscribe/user/swift-user/notify") }))
    }

    func testLiveUpdatesDegradeOnDisconnect() async throws {
        let socketTask = MockWebSocketTask()
        let client = makeClient(socketTask: socketTask)
        let collectedEventsTask = Task {
            let stream = await client.liveUpdates()
            var iterator = stream.makeAsyncIterator()
            var events: [BluettiLiveUpdateEvent] = []

            while events.count < 4, let event = await iterator.next() {
                events.append(event)
            }
            return events
        }
        addTeardownBlock {
            collectedEventsTask.cancel()
            await client.stopLiveUpdates()
        }

        await client.startLiveUpdates()
        await socketTask.enqueue(text: connectedFrame(userName: "swift-user"))
        await socketTask.fail(TestLiveUpdateError.disconnected)

        let events = try await valueWithTimeout(of: collectedEventsTask, timeout: .seconds(1))

        XCTAssertEqual(
            events,
            [
                .status(BluettiLiveUpdateSnapshot(configured: false, status: .disabled, lastError: nil)),
                .status(BluettiLiveUpdateSnapshot(configured: true, status: .connecting, lastError: nil)),
                .status(BluettiLiveUpdateSnapshot(configured: true, status: .connected, lastError: nil)),
                .status(BluettiLiveUpdateSnapshot(configured: true, status: .degraded, lastError: "Live updates disconnected.")),
            ]
        )
        let snapshot = await client.liveUpdateSnapshot()
        XCTAssertEqual(snapshot, BluettiLiveUpdateSnapshot(configured: true, status: .degraded, lastError: "Live updates disconnected."))
    }

    func testLiveUpdatesDegradeOnAuthenticationFailure() async throws {
        let socketTask = MockWebSocketTask()
        let client = makeClient(socketTask: socketTask)
        let collectedEventsTask = Task {
            let stream = await client.liveUpdates()
            var iterator = stream.makeAsyncIterator()
            var events: [BluettiLiveUpdateEvent] = []

            while events.count < 4, let event = await iterator.next() {
                events.append(event)
            }
            return events
        }
        addTeardownBlock {
            collectedEventsTask.cancel()
            await client.stopLiveUpdates()
        }

        await client.startLiveUpdates()
        await socketTask.enqueue(text: connectedFrame(userName: "swift-user"))
        await socketTask.enqueue(text: authenticationExpiredErrorFrame())

        let events = try await valueWithTimeout(of: collectedEventsTask, timeout: .seconds(1))

        XCTAssertEqual(
            events,
            [
                .status(BluettiLiveUpdateSnapshot(configured: false, status: .disabled, lastError: nil)),
                .status(BluettiLiveUpdateSnapshot(configured: true, status: .connecting, lastError: nil)),
                .status(BluettiLiveUpdateSnapshot(configured: true, status: .connected, lastError: nil)),
                .status(BluettiLiveUpdateSnapshot(configured: true, status: .degraded, lastError: "Live updates authentication expired.")),
            ]
        )
        let snapshot = await client.liveUpdateSnapshot()
        XCTAssertEqual(snapshot, BluettiLiveUpdateSnapshot(configured: true, status: .degraded, lastError: "Live updates authentication expired."))
    }

    private func makeClient(socketTask: MockWebSocketTask) -> BluettiClient {
        let configuration = BluettiCloudConfiguration(
            ssoBaseURL: URL(string: "https://sso.example")!,
            gatewayBaseURL: URL(string: "https://gw.example")!,
            liveUpdatesBaseURL: URL(string: "wss://gw.example/api/edgeiotgw/ws-coordination")!
        )

        return BluettiClient(
            configuration: configuration,
            tokenStore: InMemoryTokenStore(
                initialTokens: BluettiTokenState(accessToken: "active-access", refreshToken: "refresh-token")
            ),
            session: URLSession(configuration: .ephemeral),
            webSocketTaskFactory: { _ in socketTask }
        )
    }

    private func connectedFrame(userName: String) -> String {
        """
        CONNECTED
        version:1.2
        heart-beat:10000,10000
        user-name:\(userName)

        \0
        """
    }

    private func deviceUpdateFrame(serialNumber: String) -> String {
        let body = #"{"data":{"deviceSn":"\#(serialNumber)"}}"#
        return """
        MESSAGE
        subscription:clientUniqueId
        destination:/ws-subscribe/user/swift-user/notify
        content-type:application/json

        \(body)\0
        """
    }

    private func authenticationExpiredErrorFrame() -> String {
        let body = #"{"msgCode":805,"message":"Token expired"}"#
        return """
        ERROR

        \(body)\0
        """
    }

    private func valueWithTimeout<T>(of task: Task<T, Never>, timeout: Duration) async throws -> T {
        try await withThrowingTaskGroup(of: T.self) { group in
            group.addTask {
                await task.value
            }
            group.addTask {
                try await Task.sleep(for: timeout)
                throw TimeoutError.timedOut
            }

            guard let value = try await group.next() else {
                throw TimeoutError.timedOut
            }
            group.cancelAll()
            return value
        }
    }
}

private actor MockWebSocketTask: BluettiWebSocketTaskProtocol {
    private var queuedResults: [Result<URLSessionWebSocketTask.Message, Error>] = []
    private var waiters: [CheckedContinuation<URLSessionWebSocketTask.Message, Error>] = []
    private var sentMessages: [URLSessionWebSocketTask.Message] = []

    private(set) var isResumed = false

    func resume() async {
        isResumed = true
    }

    func send(_ message: URLSessionWebSocketTask.Message) async throws {
        sentMessages.append(message)
    }

    func receive() async throws -> URLSessionWebSocketTask.Message {
        try await withCheckedThrowingContinuation { continuation in
            if !queuedResults.isEmpty {
                let result = queuedResults.removeFirst()
                continuation.resume(with: result)
                return
            }

            waiters.append(continuation)
        }
    }

    func cancel(with closeCode: URLSessionWebSocketTask.CloseCode, reason: Data?) async {
        let pendingWaiters = waiters
        waiters.removeAll()

        for waiter in pendingWaiters {
            waiter.resume(throwing: CancellationError())
        }
    }

    func enqueue(text: String) {
        resolve(.success(.string(text)))
    }

    func fail(_ error: Error) {
        resolve(.failure(error))
    }

    func resumed() -> Bool {
        isResumed
    }

    func sentTextFrames() -> [String] {
        sentMessages.compactMap {
            if case let .string(value) = $0 {
                return value
            }
            return nil
        }
    }

    private func resolve(_ result: Result<URLSessionWebSocketTask.Message, Error>) {
        if !waiters.isEmpty {
            let waiter = waiters.removeFirst()
            waiter.resume(with: result)
            return
        }

        queuedResults.append(result)
    }
}

private enum TestLiveUpdateError: Error {
    case disconnected
}

private enum TimeoutError: Error {
    case timedOut
}