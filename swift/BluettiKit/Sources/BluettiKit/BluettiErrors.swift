import Foundation

public enum BluettiError: Error, LocalizedError, Equatable, Sendable {
    case sessionNotConfigured
    case authenticationExpired
    case invalidOAuthState
    case missingAuthorizationCode
    case deviceNotFound(String)
    case stateNotFound(fnCode: String, serialNumber: String)
    case unsupportedCommand(fnCode: String)
    case invalidCommandValue(fnCode: String, value: String)
    case cloudError(code: Int, description: String)
    case transportError(status: Int, description: String)
    case invalidResponse(String)

    public var errorDescription: String? {
        switch self {
        case .sessionNotConfigured:
            return "No BLUETTI session is configured."
        case .authenticationExpired:
            return "The BLUETTI session expired and could not be refreshed."
        case .invalidOAuthState:
            return "The BLUETTI OAuth callback state is invalid."
        case .missingAuthorizationCode:
            return "The BLUETTI OAuth callback did not include an authorization code."
        case let .deviceNotFound(serialNumber):
            return "No BLUETTI device was found for serial number \(serialNumber)."
        case let .stateNotFound(fnCode, serialNumber):
            return "The BLUETTI device \(serialNumber) does not expose state \(fnCode)."
        case let .unsupportedCommand(fnCode):
            return "BLUETTI state \(fnCode) is read-only."
        case let .invalidCommandValue(fnCode, value):
            return "Value \(value) is not allowed for BLUETTI state \(fnCode)."
        case let .cloudError(code, description):
            return "BLUETTI cloud rejected the request with code \(code): \(description)"
        case let .transportError(status, description):
            return "BLUETTI request failed with HTTP \(status): \(description)"
        case let .invalidResponse(description):
            return description
        }
    }
}