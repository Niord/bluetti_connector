#if canImport(AppKit) && canImport(AuthenticationServices)
import AppKit
import AuthenticationServices
import Foundation

@available(macOS 13.0, *)
public final class BluettiBrowserOAuthSession: NSObject, ASWebAuthenticationPresentationContextProviding {
    private let presentationAnchor: ASPresentationAnchor
    private var activeSession: ASWebAuthenticationSession?

    public init(presentationAnchor: ASPresentationAnchor) {
        self.presentationAnchor = presentationAnchor
        super.init()
    }

    public func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
        presentationAnchor
    }

    public func authenticate(
        with client: BluettiClient,
        redirectURI: URL,
        state: String = UUID().uuidString,
        prefersEphemeralWebBrowserSession: Bool = false
    ) async throws -> BluettiTokenState {
        let authorizeURL = try client.authorizeURL(redirectURI: redirectURI, state: state)
        let callbackURL = try await beginAuthentication(
            authorizeURL: authorizeURL,
            callbackScheme: redirectURI.scheme,
            prefersEphemeralWebBrowserSession: prefersEphemeralWebBrowserSession
        )

        let queryItems = URLComponents(url: callbackURL, resolvingAgainstBaseURL: false)?.queryItems ?? []
        let queryMap = Dictionary(uniqueKeysWithValues: queryItems.map { ($0.name, $0.value ?? "") })
        guard queryMap["state"] == state else {
            throw BluettiError.invalidOAuthState
        }
        guard let code = queryMap["code"], !code.isEmpty else {
            throw BluettiError.missingAuthorizationCode
        }
        return try await client.exchangeAuthorizationCode(code, redirectURI: redirectURI)
    }

    private func beginAuthentication(
        authorizeURL: URL,
        callbackScheme: String?,
        prefersEphemeralWebBrowserSession: Bool
    ) async throws -> URL {
        try await withCheckedThrowingContinuation { continuation in
            let completionHandler = Self.makeAuthenticationCompletionHandler(
                continuation: continuation,
                clearActiveSession: { [weak self] in
                    Task { @MainActor in
                        self?.activeSession = nil
                    }
                }
            )

            let session = ASWebAuthenticationSession(
                url: authorizeURL,
                callbackURLScheme: callbackScheme
            , completionHandler: completionHandler)

            Task { @MainActor [weak self] in
                session.presentationContextProvider = self
                session.prefersEphemeralWebBrowserSession = prefersEphemeralWebBrowserSession
                self?.activeSession = session

                if !session.start() {
                    self?.activeSession = nil
                    continuation.resume(throwing: BluettiError.invalidResponse("Failed to start BLUETTI browser OAuth session."))
                }
            }
        }
    }

    private nonisolated static func makeAuthenticationCompletionHandler(
        continuation: CheckedContinuation<URL, any Error>,
        clearActiveSession: @escaping @Sendable () -> Void
    ) -> @Sendable (URL?, (any Error)?) -> Void {
        { callbackURL, error in
            clearActiveSession()

            if let error {
                continuation.resume(throwing: error)
                return
            }

            guard let callbackURL else {
                continuation.resume(throwing: BluettiError.invalidResponse("BLUETTI browser OAuth finished without a callback URL."))
                return
            }

            continuation.resume(returning: callbackURL)
        }
    }
}
#endif