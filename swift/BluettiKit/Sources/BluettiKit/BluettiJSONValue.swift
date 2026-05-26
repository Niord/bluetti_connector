import Foundation

public enum BluettiJSONValue: Codable, Equatable, Sendable {
    case string(String)
    case number(Double)
    case bool(Bool)
    case object([String: BluettiJSONValue])
    case array([BluettiJSONValue])
    case null

    public init(from decoder: Decoder) throws {
        if var arrayContainer = try? decoder.unkeyedContainer() {
            var values: [BluettiJSONValue] = []
            while !arrayContainer.isAtEnd {
                values.append(try arrayContainer.decode(BluettiJSONValue.self))
            }
            self = .array(values)
            return
        }

        if let objectContainer = try? decoder.container(keyedBy: DynamicCodingKey.self) {
            var object: [String: BluettiJSONValue] = [:]
            for key in objectContainer.allKeys {
                object[key.stringValue] = try objectContainer.decode(BluettiJSONValue.self, forKey: key)
            }
            self = .object(object)
            return
        }

        let singleValueContainer = try decoder.singleValueContainer()
        if singleValueContainer.decodeNil() {
            self = .null
        } else if let boolValue = try? singleValueContainer.decode(Bool.self) {
            self = .bool(boolValue)
        } else if let intValue = try? singleValueContainer.decode(Int.self) {
            self = .number(Double(intValue))
        } else if let doubleValue = try? singleValueContainer.decode(Double.self) {
            self = .number(doubleValue)
        } else if let stringValue = try? singleValueContainer.decode(String.self) {
            self = .string(stringValue)
        } else {
            throw DecodingError.dataCorruptedError(
                in: singleValueContainer,
                debugDescription: "Unsupported JSON value."
            )
        }
    }

    public func encode(to encoder: Encoder) throws {
        switch self {
        case let .string(value):
            var container = encoder.singleValueContainer()
            try container.encode(value)
        case let .number(value):
            var container = encoder.singleValueContainer()
            try container.encode(value)
        case let .bool(value):
            var container = encoder.singleValueContainer()
            try container.encode(value)
        case let .object(value):
            var container = encoder.container(keyedBy: DynamicCodingKey.self)
            for (key, item) in value {
                try container.encode(item, forKey: DynamicCodingKey(stringValue: key))
            }
        case let .array(value):
            var container = encoder.unkeyedContainer()
            for item in value {
                try container.encode(item)
            }
        case .null:
            var container = encoder.singleValueContainer()
            try container.encodeNil()
        }
    }
}

private struct DynamicCodingKey: CodingKey {
    var stringValue: String
    var intValue: Int?

    init(stringValue: String) {
        self.stringValue = stringValue
        intValue = nil
    }

    init?(intValue: Int) {
        stringValue = String(intValue)
        self.intValue = intValue
    }
}