import Foundation

public actor BluettiClient {
    private let configuration: BluettiCloudConfiguration
    private let tokenStore: any BluettiTokenStore
    private let session: URLSession
    private let jsonDecoder = JSONDecoder()
    private let jsonEncoder = JSONEncoder()

    private var cachedTokens: BluettiTokenState?

    public init(
        configuration: BluettiCloudConfiguration = .production,
        tokenStore: (any BluettiTokenStore)? = nil,
        session: URLSession = .shared
    ) {
        self.configuration = configuration
        self.tokenStore = tokenStore ?? InMemoryTokenStore()
        self.session = session
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

    public func setTokenState(_ tokens: BluettiTokenState) async throws {
        if !tokens.hasAnyToken {
            try await clearSession()
            return
        }

        cachedTokens = tokens
        try await tokenStore.saveTokens(tokens)
    }

    public func clearSession() async throws {
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

        let _: ControlResultPayload = try await performAuthenticatedRequest(
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

    private func performEnvelopeRequest<Value: Decodable>(
        method: HTTPMethod,
        pathComponents: [String],
        queryItems: [URLQueryItem],
        accessToken: String,
        bodyData: Data?,
        contentType: String?
    ) async throws -> Value {
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

        let envelope = try decodeEnvelope(Value.self, from: data)
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