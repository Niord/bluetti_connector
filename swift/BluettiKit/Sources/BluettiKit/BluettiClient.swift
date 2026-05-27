import Foundation

public actor BluettiClient {
    private let configuration: BluettiCloudConfiguration
    private let tokenStore: any BluettiTokenStore
    private let session: URLSession
    private let webSocketTaskFactory: BluettiWebSocketTaskFactory
    private let jsonDecoder = JSONDecoder()
    private let jsonEncoder = JSONEncoder()

    private var cachedTokens: BluettiTokenState?
    private var liveUpdateSnapshotValue = BluettiLiveUpdateSnapshot(configured: false, status: .disabled, lastError: nil)
    private var liveUpdateSubscribers: [UUID: AsyncStream<BluettiLiveUpdateEvent>.Continuation] = [:]
    private var liveUpdateWebSocketTask: (any BluettiWebSocketTaskProtocol)?
    private var liveUpdateReceiveTask: Task<Void, Never>?
    private var liveUpdateHeartbeatTask: Task<Void, Never>?
    private var liveUpdateAccessToken: String?
    private var currentLiveUpdateSocketURL: URL?

    public init(
        configuration: BluettiCloudConfiguration = .production,
        tokenStore: (any BluettiTokenStore)? = nil,
        session: URLSession = .shared
    ) {
        self.configuration = configuration
        self.tokenStore = tokenStore ?? InMemoryTokenStore()
        self.session = session
        self.webSocketTaskFactory = { url in
            URLSessionBluettiWebSocketTask(task: session.webSocketTask(with: url))
        }
    }

    internal init(
        configuration: BluettiCloudConfiguration = .production,
        tokenStore: (any BluettiTokenStore)? = nil,
        session: URLSession = .shared,
        webSocketTaskFactory: @escaping BluettiWebSocketTaskFactory
    ) {
        self.configuration = configuration
        self.tokenStore = tokenStore ?? InMemoryTokenStore()
        self.session = session
        self.webSocketTaskFactory = webSocketTaskFactory
    }

    public nonisolated func authorizeURL(redirectURI: URL, state: String) throws -> URL {
        var components = URLComponents(
            url: configuration.ssoBaseURL
                .appendingPathComponent("oauth2")
                .appendingPathComponent("grant"),
            resolvingAgainstBaseURL: false
        )
        components?.queryItems = [
            URLQueryItem(name: "response_type", value: "code"),
            URLQueryItem(name: "client_id", value: configuration.oauthClientID),
            URLQueryItem(name: "redirect_uri", value: redirectURI.absoluteString),
            URLQueryItem(name: "state", value: state),
        ]
        guard let url = components?.url else {
            throw BluettiError.invalidResponse("Failed to build the BLUETTI authorize URL.")
        }
        return url
    }

    public func loadPersistedTokens() async throws -> BluettiTokenState? {
        try await currentTokens()
    }

    public func liveUpdateSnapshot() -> BluettiLiveUpdateSnapshot {
        liveUpdateSnapshotValue
    }

    public func liveUpdates() -> AsyncStream<BluettiLiveUpdateEvent> {
        AsyncStream { continuation in
            let subscriberID = UUID()
            liveUpdateSubscribers[subscriberID] = continuation
            continuation.yield(.status(liveUpdateSnapshotValue))
            continuation.onTermination = { @Sendable _ in
                Task {
                    await self.removeLiveUpdateSubscriber(subscriberID)
                }
            }
        }
    }

    public func startLiveUpdates() async {
        guard let socketURL = liveUpdateSocketURL() else {
            updateLiveUpdateSnapshot(
                BluettiLiveUpdateSnapshot(configured: false, status: .disabled, lastError: nil)
            )
            return
        }

        let accessToken: String
        do {
            accessToken = try await requireAccessToken()
        } catch {
            updateLiveUpdateSnapshot(
                BluettiLiveUpdateSnapshot(configured: false, status: .disabled, lastError: nil)
            )
            return
        }

        if liveUpdateSnapshotValue.status == .connecting || liveUpdateSnapshotValue.status == .connected {
            if liveUpdateAccessToken == accessToken, currentLiveUpdateSocketURL == socketURL {
                return
            }
        }

        await stopLiveUpdatesInternal(resetToDisabled: false)

        liveUpdateAccessToken = accessToken
        currentLiveUpdateSocketURL = socketURL
        liveUpdateWebSocketTask = webSocketTaskFactory(socketURL)
        await liveUpdateWebSocketTask?.resume()
        updateLiveUpdateSnapshot(
            BluettiLiveUpdateSnapshot(configured: true, status: .connecting, lastError: nil)
        )

        liveUpdateReceiveTask = Task {
            await self.runLiveUpdateReceiveLoop()
        }
        liveUpdateHeartbeatTask = Task {
            await self.runLiveUpdateHeartbeatLoop()
        }

        do {
            try await sendLiveUpdateFrame(
                BluettiStompFrame.connectFrame(
                    host: socketURL.host ?? "",
                    accessToken: accessToken
                )
            )
        } catch {
            await degradeLiveUpdates(with: error)
        }
    }

    public func stopLiveUpdates() async {
        await stopLiveUpdatesInternal(resetToDisabled: true)
    }

    public func setTokenState(_ tokens: BluettiTokenState) async throws {
        if !tokens.hasAnyToken {
            try await clearSession()
            return
        }

        cachedTokens = tokens
        try await tokenStore.saveTokens(tokens)
    }

    public func clearSession() async throws {
        await stopLiveUpdatesInternal(resetToDisabled: true)
        cachedTokens = nil
        try await tokenStore.clearTokens()
    }

    public func exchangeAuthorizationCode(_ code: String, redirectURI: URL) async throws -> BluettiTokenState {
        let tokenState = try await requestOAuthToken(
            form: [
                "grant_type": "authorization_code",
                "client_id": configuration.oauthClientID,
                "client_secret": configuration.oauthClientSecret,
                "code": code,
                "redirect_uri": redirectURI.absoluteString,
            ]
        )
        try await setTokenState(tokenState)
        return tokenState
    }

    public func refreshAccessToken() async throws -> BluettiTokenState {
        guard let refreshToken = try await currentTokens()?.refreshToken else {
            try await clearSession()
            throw BluettiError.authenticationExpired
        }

        do {
            let refreshed = try await requestOAuthToken(
                form: [
                    "grant_type": "refresh_token",
                    "client_id": configuration.oauthClientID,
                    "client_secret": configuration.oauthClientSecret,
                    "refresh_token": refreshToken,
                ]
            ).merged(refreshToken: refreshToken)
            try await setTokenState(refreshed)
            return refreshed
        } catch BluettiError.authenticationExpired {
            try await clearSession()
            throw BluettiError.authenticationExpired
        }
    }

    public func listDevices() async throws -> [BluettiDevice] {
        try await performAuthenticatedRequest(
            method: .get,
            pathComponents: ["api", "bluiotdata", "ha", "v1", "devices"]
        )
    }

    public func refreshDevice(serialNumber: String) async throws -> BluettiDevice {
        let products = try await listDevices()
        let productDevice = products.first(where: { $0.serialNumber == serialNumber })

        var statusDevices = try await loadDeviceStatuses(serialNumber: serialNumber)
        if statusDevices.first?.isBoundByCurrentUser == false {
            let _: BindDevicesResponse = try await performAuthenticatedRequest(
                method: .post,
                pathComponents: ["api", "bluiotdata", "ha", "v1", "bindDevices"],
                body: BindDevicesPayload(bindSnList: [serialNumber])
            )
            statusDevices = try await loadDeviceStatuses(serialNumber: serialNumber)
        }

        guard let statusDevice = statusDevices.first(where: { $0.serialNumber == serialNumber }) ?? productDevice else {
            throw BluettiError.deviceNotFound(serialNumber)
        }

        if let productDevice {
            return productDevice.merged(with: statusDevice)
        }

        return statusDevice
    }

    public func setState(serialNumber: String, fnCode: String, value: String) async throws -> BluettiDevice {
        let device = try await refreshDevice(serialNumber: serialNumber)
        return try await sendCommand(using: device, serialNumber: serialNumber, fnCode: fnCode, value: value)
    }

    public func setACOutput(serialNumber: String, isOn: Bool) async throws -> BluettiDevice {
        try await setPreferredSwitch(
            serialNumber: serialNumber,
            candidateCodes: BluettiKnownStateCodes.acOutput,
            isOn: isOn
        )
    }

    public func setDCOutput(serialNumber: String, isOn: Bool) async throws -> BluettiDevice {
        try await setPreferredSwitch(
            serialNumber: serialNumber,
            candidateCodes: BluettiKnownStateCodes.dcOutput,
            isOn: isOn
        )
    }

    private func setPreferredSwitch(serialNumber: String, candidateCodes: [String], isOn: Bool) async throws -> BluettiDevice {
        let device = try await refreshDevice(serialNumber: serialNumber)
        guard let state = device.state(matching: candidateCodes) else {
            throw BluettiError.stateNotFound(
                fnCode: candidateCodes.first ?? "unknown",
                serialNumber: serialNumber
            )
        }
        return try await sendCommand(
            using: device,
            serialNumber: serialNumber,
            fnCode: state.fnCode,
            value: isOn ? "1" : "0"
        )
    }

    private func sendCommand(using device: BluettiDevice, serialNumber: String, fnCode: String, value: String) async throws -> BluettiDevice {
        try device.validateCommand(fnCode: fnCode, value: value)

        try await performAuthenticatedCommandAcceptanceRequest(
            method: .post,
            pathComponents: ["api", "bluiotdata", "ha", "v1", "fulfillment"],
            body: DeviceCommandPayload(sn: serialNumber, fnCode: fnCode, fnValue: value)
        )

        return try device.updatingState(fnCode: fnCode, value: value)
    }

    private func loadDeviceStatuses(serialNumber: String?) async throws -> [BluettiDevice] {
        try await performAuthenticatedRequest(
            method: .get,
            pathComponents: ["api", "bluiotdata", "ha", "v1", "deviceStates"],
            queryItems: serialNumber.map { [URLQueryItem(name: "sns", value: $0)] } ?? []
        )
    }

    private func currentTokens() async throws -> BluettiTokenState? {
        if cachedTokens == nil {
            cachedTokens = try await tokenStore.loadTokens()
        }
        return cachedTokens
    }

    private func requireAccessToken() async throws -> String {
        if let accessToken = try await currentTokens()?.accessToken {
            return accessToken
        }

        if try await currentTokens()?.refreshToken != nil {
            let refreshed = try await refreshAccessToken()
            if let accessToken = refreshed.accessToken {
                return accessToken
            }
        }

        try await clearSession()
        throw BluettiError.sessionNotConfigured
    }

    private func performAuthenticatedRequest<Value: Decodable>(
        method: HTTPMethod,
        pathComponents: [String],
        queryItems: [URLQueryItem] = []
    ) async throws -> Value {
        try await performAuthenticatedRequest(
            method: method,
            pathComponents: pathComponents,
            queryItems: queryItems,
            bodyData: nil,
            contentType: nil
        )
    }

    private func performAuthenticatedRequest<Value: Decodable, Body: Encodable>(
        method: HTTPMethod,
        pathComponents: [String],
        queryItems: [URLQueryItem] = [],
        body: Body
    ) async throws -> Value {
        let bodyData = try jsonEncoder.encode(body)
        return try await performAuthenticatedRequest(
            method: method,
            pathComponents: pathComponents,
            queryItems: queryItems,
            bodyData: bodyData,
            contentType: "application/json"
        )
    }

    private func performAuthenticatedCommandAcceptanceRequest<Body: Encodable>(
        method: HTTPMethod,
        pathComponents: [String],
        queryItems: [URLQueryItem] = [],
        body: Body
    ) async throws {
        let bodyData = try jsonEncoder.encode(body)
        try await performAuthenticatedCommandAcceptanceRequest(
            method: method,
            pathComponents: pathComponents,
            queryItems: queryItems,
            bodyData: bodyData,
            contentType: "application/json"
        )
    }

    private func performAuthenticatedRequest<Value: Decodable>(
        method: HTTPMethod,
        pathComponents: [String],
        queryItems: [URLQueryItem],
        bodyData: Data?,
        contentType: String?
    ) async throws -> Value {
        var attemptedRefresh = false
        while true {
            let accessToken = try await requireAccessToken()
            do {
                return try await performEnvelopeRequest(
                    method: method,
                    pathComponents: pathComponents,
                    queryItems: queryItems,
                    accessToken: accessToken,
                    bodyData: bodyData,
                    contentType: contentType
                )
            } catch BluettiError.authenticationExpired {
                if attemptedRefresh {
                    try await clearSession()
                    throw BluettiError.authenticationExpired
                }
                _ = try await refreshAccessToken()
                attemptedRefresh = true
            }
        }
    }

    private func performAuthenticatedCommandAcceptanceRequest(
        method: HTTPMethod,
        pathComponents: [String],
        queryItems: [URLQueryItem],
        bodyData: Data?,
        contentType: String?
    ) async throws {
        var attemptedRefresh = false
        while true {
            let accessToken = try await requireAccessToken()
            do {
                try await performCommandAcceptanceEnvelopeRequest(
                    method: method,
                    pathComponents: pathComponents,
                    queryItems: queryItems,
                    accessToken: accessToken,
                    bodyData: bodyData,
                    contentType: contentType
                )
                return
            } catch BluettiError.authenticationExpired {
                if attemptedRefresh {
                    try await clearSession()
                    throw BluettiError.authenticationExpired
                }
                _ = try await refreshAccessToken()
                attemptedRefresh = true
            }
        }
    }

    private func performEnvelopeRequest<Value: Decodable>(
        method: HTTPMethod,
        pathComponents: [String],
        queryItems: [URLQueryItem],
        accessToken: String,
        bodyData: Data?,
        contentType: String?
    ) async throws -> Value {
        let (envelope, data): (BluettiEnvelope<Value>, Data) = try await executeGatewayEnvelopeRequest(
            method: method,
            pathComponents: pathComponents,
            queryItems: queryItems,
            accessToken: accessToken,
            bodyData: bodyData,
            contentType: contentType,
            responseType: Value.self
        )

        if envelope.msgCode == 805 {
            throw BluettiError.authenticationExpired
        }
        if envelope.msgCode != 0 {
            throw BluettiError.cloudError(code: envelope.msgCode, description: responseDescription(for: data))
        }
        guard let value = envelope.data else {
            throw BluettiError.invalidResponse("The BLUETTI gateway response did not contain data.")
        }
        return value
    }

    private func performCommandAcceptanceEnvelopeRequest(
        method: HTTPMethod,
        pathComponents: [String],
        queryItems: [URLQueryItem],
        accessToken: String,
        bodyData: Data?,
        contentType: String?
    ) async throws {
        let (envelope, data): (BluettiEnvelope<ControlResultPayload?>, Data) = try await executeGatewayEnvelopeRequest(
            method: method,
            pathComponents: pathComponents,
            queryItems: queryItems,
            accessToken: accessToken,
            bodyData: bodyData,
            contentType: contentType,
            responseType: ControlResultPayload?.self
        )

        if envelope.msgCode == 805 {
            throw BluettiError.authenticationExpired
        }
        if envelope.msgCode != 0 {
            throw BluettiError.cloudError(code: envelope.msgCode, description: responseDescription(for: data))
        }
    }

    private func executeGatewayEnvelopeRequest<Value: Decodable>(
        method: HTTPMethod,
        pathComponents: [String],
        queryItems: [URLQueryItem],
        accessToken: String,
        bodyData: Data?,
        contentType: String?,
        responseType: Value.Type
    ) async throws -> (BluettiEnvelope<Value>, Data) {
        var components = URLComponents(url: gatewayURL(pathComponents: pathComponents), resolvingAgainstBaseURL: false)
        if !queryItems.isEmpty {
            components?.queryItems = queryItems
        }
        guard let url = components?.url else {
            throw BluettiError.invalidResponse("Failed to build a BLUETTI gateway URL.")
        }

        var request = URLRequest(url: url)
        request.httpMethod = method.rawValue
        request.timeoutInterval = configuration.requestTimeout
        request.setValue(accessToken, forHTTPHeaderField: "Authorization")
        if let bodyData {
            request.httpBody = bodyData
        }
        if let contentType {
            request.setValue(contentType, forHTTPHeaderField: "Content-Type")
        }

        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw BluettiError.invalidResponse("The BLUETTI gateway response was not an HTTP response.")
        }

        if httpResponse.statusCode >= 400 {
            throw BluettiError.transportError(status: httpResponse.statusCode, description: responseDescription(for: data))
        }

        return (try decodeEnvelope(responseType, from: data), data)
    }

    private func requestOAuthToken(form: [String: String]) async throws -> BluettiTokenState {
        var request = URLRequest(url: ssoURL(pathComponents: ["oauth2", "token"]))
        request.httpMethod = HTTPMethod.post.rawValue
        request.timeoutInterval = configuration.requestTimeout
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue("application/x-www-form-urlencoded; charset=utf-8", forHTTPHeaderField: "Content-Type")
        request.httpBody = form
            .sorted(by: { $0.key < $1.key })
            .map { "\($0.key.urlFormEncoded)=\($0.value.urlFormEncoded)" }
            .joined(separator: "&")
            .data(using: .utf8)

        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw BluettiError.invalidResponse("The BLUETTI OAuth response was not an HTTP response.")
        }

        if httpResponse.statusCode >= 400 {
            if let oauthError = try? jsonDecoder.decode(OAuthErrorResponse.self, from: data),
               OAuthErrorResponse.authenticationFailures.contains(oauthError.error) {
                throw BluettiError.authenticationExpired
            }
            throw BluettiError.transportError(status: httpResponse.statusCode, description: responseDescription(for: data))
        }

        do {
            let response = try jsonDecoder.decode(OAuthTokenGrantResponse.self, from: data)
            return BluettiTokenState(accessToken: response.accessToken, refreshToken: response.refreshToken)
        } catch {
            throw BluettiError.invalidResponse("The BLUETTI OAuth token response was invalid.")
        }
    }

    private func decodeEnvelope<Value: Decodable>(_ type: Value.Type, from data: Data) throws -> BluettiEnvelope<Value> {
        do {
            return try jsonDecoder.decode(BluettiEnvelope<Value>.self, from: data)
        } catch {
            throw BluettiError.invalidResponse("The BLUETTI gateway response envelope was invalid.")
        }
    }

    private func responseDescription(for data: Data) -> String {
        if let string = String(data: data, encoding: .utf8), !string.isEmpty {
            return string
        }
        return "No response payload"
    }

    private func gatewayURL(pathComponents: [String]) -> URL {
        pathComponents.reduce(configuration.gatewayBaseURL) { url, component in
            url.appendingPathComponent(component)
        }
    }

    private func ssoURL(pathComponents: [String]) -> URL {
        pathComponents.reduce(configuration.ssoBaseURL) { url, component in
            url.appendingPathComponent(component)
        }
    }

    private func removeLiveUpdateSubscriber(_ subscriberID: UUID) {
        liveUpdateSubscribers.removeValue(forKey: subscriberID)
    }

    private func liveUpdateSocketURL() -> URL? {
        guard let scheme = configuration.liveUpdatesBaseURL.scheme?.lowercased(), scheme == "wss" || scheme == "ws" else {
            return nil
        }

        return configuration.liveUpdatesBaseURL.appendingPathComponent("websocket")
    }

    private func updateLiveUpdateSnapshot(_ snapshot: BluettiLiveUpdateSnapshot) {
        liveUpdateSnapshotValue = snapshot
        publishLiveUpdateEvent(.status(snapshot))
    }

    private func publishLiveUpdateEvent(_ event: BluettiLiveUpdateEvent) {
        for continuation in liveUpdateSubscribers.values {
            continuation.yield(event)
        }
    }

    private func stopLiveUpdatesInternal(resetToDisabled: Bool) async {
        let webSocketTask = liveUpdateWebSocketTask
        liveUpdateWebSocketTask = nil
        liveUpdateReceiveTask?.cancel()
        liveUpdateReceiveTask = nil
        liveUpdateHeartbeatTask?.cancel()
        liveUpdateHeartbeatTask = nil
        liveUpdateAccessToken = nil
        currentLiveUpdateSocketURL = nil
        await webSocketTask?.cancel(with: .normalClosure, reason: nil)

        if resetToDisabled {
            updateLiveUpdateSnapshot(
                BluettiLiveUpdateSnapshot(configured: false, status: .disabled, lastError: nil)
            )
        }
    }

    private func degradeLiveUpdates(with error: Error) async {
        let webSocketTask = liveUpdateWebSocketTask
        let isConfigured = liveUpdateAccessToken != nil && currentLiveUpdateSocketURL != nil

        liveUpdateWebSocketTask = nil
        liveUpdateHeartbeatTask?.cancel()
        liveUpdateHeartbeatTask = nil
        await webSocketTask?.cancel(with: .normalClosure, reason: nil)

        updateLiveUpdateSnapshot(
            BluettiLiveUpdateSnapshot(
                configured: isConfigured,
                status: .degraded,
                lastError: sanitizedLiveUpdateError(error)
            )
        )
    }

    private func sanitizedLiveUpdateError(_ error: Error) -> String {
        if let transportError = error as? BluettiLiveUpdateTransportError,
           let description = transportError.errorDescription {
            return description
        }
        if let bluettiError = error as? BluettiError,
           case .authenticationExpired = bluettiError {
            return BluettiLiveUpdateTransportError.authenticationExpired.errorDescription ?? "Live updates authentication expired."
        }
        if error is CancellationError {
            return BluettiLiveUpdateTransportError.disconnected.errorDescription ?? "Live updates disconnected."
        }

        let description = (error as NSError).localizedDescription
        if description.isEmpty || description == "The operation couldn’t be completed. (Swift.CancellationError error 1.)" {
            return BluettiLiveUpdateTransportError.disconnected.errorDescription ?? "Live updates disconnected."
        }
        return description
    }

    private func runLiveUpdateReceiveLoop() async {
        while !Task.isCancelled {
            guard let webSocketTask = liveUpdateWebSocketTask else {
                return
            }

            do {
                let message = try await webSocketTask.receive()
                try await handleLiveUpdateMessage(message)
            } catch is CancellationError {
                return
            } catch {
                guard liveUpdateWebSocketTask != nil else {
                    return
                }
                let liveUpdateError = (error as? BluettiLiveUpdateTransportError) ?? BluettiLiveUpdateTransportError.disconnected
                await degradeLiveUpdates(with: liveUpdateError)
                return
            }
        }
    }

    private func runLiveUpdateHeartbeatLoop() async {
        while !Task.isCancelled {
            try? await Task.sleep(for: .seconds(10))
            guard !Task.isCancelled else {
                return
            }
            guard liveUpdateSnapshotValue.status == .connected else {
                continue
            }

            do {
                try await sendLiveUpdateFrame("\n")
            } catch {
                await degradeLiveUpdates(with: error)
                return
            }
        }
    }

    private func sendLiveUpdateFrame(_ frame: String) async throws {
        guard let webSocketTask = liveUpdateWebSocketTask else {
            throw BluettiLiveUpdateTransportError.disconnected
        }
        try await webSocketTask.send(.string(frame))
    }

    private func handleLiveUpdateMessage(_ message: URLSessionWebSocketTask.Message) async throws {
        switch message {
        case let .string(text):
            try await handleLiveUpdateFrame(text)
        case let .data(data):
            guard let text = String(data: data, encoding: .utf8) else {
                throw BluettiLiveUpdateTransportError.invalidPayload
            }
            try await handleLiveUpdateFrame(text)
        @unknown default:
            throw BluettiLiveUpdateTransportError.invalidPayload
        }
    }

    private func handleLiveUpdateFrame(_ text: String) async throws {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty {
            return
        }

        let frame = try BluettiStompFrame(text: text)
        switch frame.command {
        case "CONNECTED":
            guard let userName = frame.headers["user-name"], !userName.isEmpty else {
                throw BluettiLiveUpdateTransportError.invalidResponse("Live updates did not return a BLUETTI user identifier.")
            }
            try await sendLiveUpdateFrame(
                BluettiStompFrame.subscribeFrame(destination: "/ws-subscribe/user/\(userName)/notify")
            )
            updateLiveUpdateSnapshot(
                BluettiLiveUpdateSnapshot(configured: true, status: .connected, lastError: nil)
            )
        case "MESSAGE":
            guard let deviceSerialNumber = try liveUpdateDeviceSerialNumber(from: frame.body) else {
                return
            }
            publishLiveUpdateEvent(.deviceUpdate(serialNumber: deviceSerialNumber))
        case "ERROR":
            throw try liveUpdateError(from: frame)
        default:
            return
        }
    }

    private func liveUpdateDeviceSerialNumber(from body: String) throws -> String? {
        guard !body.isEmpty else {
            return nil
        }

        let payload = try jsonDecoder.decode(BluettiLiveUpdateMessagePayload.self, from: Data(body.utf8))
        return payload.data?.deviceSn
    }

    private func liveUpdateError(from frame: BluettiStompFrame) throws -> Error {
        let serializedMessage = frame.headers["message"]?.replacingOccurrences(of: "\\c", with: ":")
        let rawPayload = serializedMessage?.isEmpty == false ? serializedMessage! : frame.body
        guard !rawPayload.isEmpty,
              let data = rawPayload.data(using: .utf8),
              let object = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            return BluettiLiveUpdateTransportError.invalidPayload
        }

        let code = object["msgCode"] as? Int ?? 0
        let description = (object["message"] as? String) ?? (object["msg"] as? String) ?? "Unknown live update error."
        if code == 805 {
            return BluettiLiveUpdateTransportError.authenticationExpired
        }
        return BluettiLiveUpdateTransportError.cloudError(code: code, description: description)
    }
}

private enum HTTPMethod: String {
    case get = "GET"
    case post = "POST"
}

private struct OAuthTokenGrantResponse: Decodable {
    let accessToken: String
    let refreshToken: String?

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case refreshToken = "refresh_token"
    }
}

private struct OAuthErrorResponse: Decodable {
    static let authenticationFailures: Set<String> = ["invalid_grant", "invalid_token", "unauthorized_client"]

    let error: String
}

private struct BindDevicesPayload: Encodable {
    let bindSnList: [String]
}

private struct BindDevicesResponse: Decodable {
    let accepted: Bool?
    let bindSnList: [String]?
}

private struct DeviceCommandPayload: Encodable {
    let sn: String
    let fnCode: String
    let fnValue: String
}

private struct ControlResultPayload: Decodable {
    let accepted: Bool?
    let sn: String?
}

private extension String {
    var urlFormEncoded: String {
        addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed.subtracting(CharacterSet(charactersIn: "+&="))) ?? self
    }
}