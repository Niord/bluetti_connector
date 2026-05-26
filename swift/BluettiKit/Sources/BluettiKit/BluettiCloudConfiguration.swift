import Foundation

public struct BluettiCloudConfiguration: Sendable, Equatable {
    public var ssoBaseURL: URL
    public var gatewayBaseURL: URL
    public var oauthClientID: String
    public var oauthClientSecret: String
    public var requestTimeout: TimeInterval

    public init(
        ssoBaseURL: URL,
        gatewayBaseURL: URL,
        oauthClientID: String = "HomeAssistant",
        oauthClientSecret: String = "SG9tZUFzc2lzdGFudA==",
        requestTimeout: TimeInterval = 15
    ) {
        self.ssoBaseURL = ssoBaseURL
        self.gatewayBaseURL = gatewayBaseURL
        self.oauthClientID = oauthClientID
        self.oauthClientSecret = oauthClientSecret
        self.requestTimeout = requestTimeout
    }

    public static let production = BluettiCloudConfiguration(
        ssoBaseURL: URL(string: "https://sso.bluettipower.com")!,
        gatewayBaseURL: URL(string: "https://gw.bluettipower.com")!
    )
}