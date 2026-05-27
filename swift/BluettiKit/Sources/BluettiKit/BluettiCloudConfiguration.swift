import Foundation

public struct BluettiCloudConfiguration: Sendable, Equatable {
    public var ssoBaseURL: URL
    public var gatewayBaseURL: URL
    public var liveUpdatesBaseURL: URL
    public var oauthClientID: String
    public var oauthClientSecret: String
    public var requestTimeout: TimeInterval

    public init(
        ssoBaseURL: URL,
        gatewayBaseURL: URL,
        liveUpdatesBaseURL: URL? = nil,
        oauthClientID: String = "HomeAssistant",
        oauthClientSecret: String = "SG9tZUFzc2lzdGFudA==",
        requestTimeout: TimeInterval = 15
    ) {
        self.ssoBaseURL = ssoBaseURL
        self.gatewayBaseURL = gatewayBaseURL
        self.liveUpdatesBaseURL = liveUpdatesBaseURL ?? Self.defaultLiveUpdatesBaseURL(for: gatewayBaseURL)
        self.oauthClientID = oauthClientID
        self.oauthClientSecret = oauthClientSecret
        self.requestTimeout = requestTimeout
    }

    public static let production = BluettiCloudConfiguration(
        ssoBaseURL: URL(string: "https://sso.bluettipower.com")!,
        gatewayBaseURL: URL(string: "https://gw.bluettipower.com")!
    )

    private static func defaultLiveUpdatesBaseURL(for gatewayBaseURL: URL) -> URL {
        var components = URLComponents(url: gatewayBaseURL, resolvingAgainstBaseURL: false)
        let normalizedScheme = components?.scheme?.lowercased()
        components?.scheme = normalizedScheme == "http" ? "ws" : "wss"
        components?.path = "/api/edgeiotgw/ws-coordination"
        components?.query = nil
        components?.fragment = nil
        return components?.url ?? gatewayBaseURL
    }
}