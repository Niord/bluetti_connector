import Foundation
import Security

public struct BluettiTokenState: Codable, Equatable, Sendable {
    public var accessToken: String?
    public var refreshToken: String?

    public init(accessToken: String? = nil, refreshToken: String? = nil) {
        self.accessToken = accessToken.nilIfEmpty
        self.refreshToken = refreshToken.nilIfEmpty
    }

    public var hasAnyToken: Bool {
        accessToken != nil || refreshToken != nil
    }

    func merged(refreshToken fallbackRefreshToken: String?) -> BluettiTokenState {
        BluettiTokenState(
            accessToken: accessToken,
            refreshToken: refreshToken ?? fallbackRefreshToken
        )
    }
}

public protocol BluettiTokenStore: Sendable {
    func loadTokens() async throws -> BluettiTokenState?
    func saveTokens(_ tokens: BluettiTokenState) async throws
    func clearTokens() async throws
}

public actor InMemoryTokenStore: BluettiTokenStore {
    private var tokens: BluettiTokenState?

    public init(initialTokens: BluettiTokenState? = nil) {
        tokens = initialTokens
    }

    public func loadTokens() async throws -> BluettiTokenState? {
        tokens
    }

    public func saveTokens(_ tokens: BluettiTokenState) async throws {
        self.tokens = tokens.hasAnyToken ? tokens : nil
    }

    public func clearTokens() async throws {
        tokens = nil
    }
}

public final class BluettiKeychainTokenStore: BluettiTokenStore, @unchecked Sendable {
    private let service: String
    private let account: String

    public init(service: String = "BluettiKit", account: String = "session") {
        self.service = service
        self.account = account
    }

    public func loadTokens() async throws -> BluettiTokenState? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]

        var result: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        switch status {
        case errSecSuccess:
            guard let data = result as? Data else {
                throw BluettiError.invalidResponse("Keychain returned an unexpected token payload.")
            }
            return try JSONDecoder().decode(BluettiTokenState.self, from: data)
        case errSecItemNotFound:
            return nil
        default:
            throw BluettiError.invalidResponse("Keychain load failed with status \(status).")
        }
    }

    public func saveTokens(_ tokens: BluettiTokenState) async throws {
        if !tokens.hasAnyToken {
            try await clearTokens()
            return
        }

        let data = try JSONEncoder().encode(tokens)
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]

        let attributes: [String: Any] = [
            kSecValueData as String: data,
        ]

        let updateStatus = SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
        if updateStatus == errSecItemNotFound {
            var insertQuery = query
            insertQuery[kSecValueData as String] = data
            let insertStatus = SecItemAdd(insertQuery as CFDictionary, nil)
            guard insertStatus == errSecSuccess else {
                throw BluettiError.invalidResponse("Keychain save failed with status \(insertStatus).")
            }
            return
        }

        guard updateStatus == errSecSuccess else {
            throw BluettiError.invalidResponse("Keychain update failed with status \(updateStatus).")
        }
    }

    public func clearTokens() async throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]

        let status = SecItemDelete(query as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw BluettiError.invalidResponse("Keychain delete failed with status \(status).")
        }
    }
}

private extension Optional where Wrapped == String {
    var nilIfEmpty: String? {
        switch self?.trimmingCharacters(in: .whitespacesAndNewlines) {
        case .some(let value) where !value.isEmpty:
            return value
        default:
            return nil
        }
    }
}