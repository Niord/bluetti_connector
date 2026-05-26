import Foundation

public enum BluettiKnownStateCodes {
    public static let batterySOC = ["SOC"]
    public static let acOutput = ["SetCtrlAc", "AC_OUTPUT_ON"]
    public static let dcOutput = ["SetCtrlDc", "DC_OUTPUT_ON"]
    public static let pvInputPower = ["PVAllTotalPower"]
    public static let gridInputPower = ["GridAllTotalPower"]
    public static let acLoadPower = ["ACLoadAllTotalPower"]
    public static let dcLoadPower = ["DCLoadAllTotalPower"]
}

public struct BluettiControlOption: Codable, Equatable, Sendable {
    public var value: String
    public var label: String

    public init(value: String, label: String) {
        self.value = value
        self.label = label
    }
}

public enum BluettiControlKind: String, Codable, Sendable {
    case switchControl = "switch"
    case select
}

public struct BluettiStateModeOption: Codable, Equatable, Sendable {
    public var code: String
    public var name: String?

    public init(code: String, name: String? = nil) {
        self.code = code
        self.name = name
    }
}

public struct BluettiState: Codable, Equatable, Identifiable, Sendable {
    public var id: String { fnCode }

    public var fnCode: String
    public var fnName: String
    public var fnValue: String?
    public var fnType: String?
    public var supportModeValues: [BluettiStateModeOption]
    public var sensorInfo: [String: BluettiJSONValue]

    public init(
        fnCode: String,
        fnName: String,
        fnValue: String? = nil,
        fnType: String? = nil,
        supportModeValues: [BluettiStateModeOption] = [],
        sensorInfo: [String: BluettiJSONValue] = [:]
    ) {
        self.fnCode = fnCode
        self.fnName = fnName
        self.fnValue = fnValue
        self.fnType = fnType
        self.supportModeValues = supportModeValues
        self.sensorInfo = sensorInfo
    }

    enum CodingKeys: String, CodingKey {
        case fnCode
        case fnName
        case fnValue
        case fnType
        case supportModeValues
        case sensorInfo
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        fnCode = try container.decode(String.self, forKey: .fnCode)
        fnName = try container.decodeIfPresent(String.self, forKey: .fnName) ?? ""
        fnValue = try container.decodeIfPresent(String.self, forKey: .fnValue)
        fnType = try container.decodeIfPresent(String.self, forKey: .fnType)
        supportModeValues = try container.decodeIfPresent([BluettiStateModeOption].self, forKey: .supportModeValues) ?? []
        sensorInfo = try container.decodeIfPresent([String: BluettiJSONValue].self, forKey: .sensorInfo) ?? [:]
    }

    public var controlKind: BluettiControlKind? {
        let normalizedType = fnType?.lowercased() ?? ""
        if normalizedType.contains("switch") {
            return .switchControl
        }
        if !supportModeValues.isEmpty {
            return .select
        }
        return nil
    }

    public var isCommandCapable: Bool {
        controlKind != nil
    }

    public var allowedValues: [BluettiControlOption] {
        let modeOptions = supportModeValues.map {
            BluettiControlOption(value: $0.code, label: $0.name ?? $0.code)
        }
        if !modeOptions.isEmpty {
            return modeOptions
        }
        if controlKind == .switchControl {
            return [
                BluettiControlOption(value: "0", label: "Off"),
                BluettiControlOption(value: "1", label: "On"),
            ]
        }
        return []
    }

    public var displayValue: String {
        allowedValues.first(where: { $0.value == fnValue })?.label ?? fnValue ?? "Unknown"
    }

    public var numericValue: Double? {
        guard let fnValue else {
            return nil
        }
        return Double(fnValue)
    }

    public var boolValue: Bool? {
        guard controlKind == .switchControl else {
            return nil
        }
        switch fnValue {
        case "1":
            return true
        case "0":
            return false
        default:
            return nil
        }
    }

    public func validate(commandValue: String) throws {
        guard isCommandCapable else {
            throw BluettiError.unsupportedCommand(fnCode: fnCode)
        }
        guard allowedValues.contains(where: { $0.value == commandValue }) else {
            throw BluettiError.invalidCommandValue(fnCode: fnCode, value: commandValue)
        }
    }

    public func updating(value: String) throws -> BluettiState {
        try validate(commandValue: value)
        var copy = self
        copy.fnValue = value
        return copy
    }
}

public struct BluettiPowerMetrics: Equatable, Sendable {
    public var pvInputWatts: Double?
    public var gridInputWatts: Double?
    public var acLoadWatts: Double?
    public var dcLoadWatts: Double?

    public init(
        pvInputWatts: Double? = nil,
        gridInputWatts: Double? = nil,
        acLoadWatts: Double? = nil,
        dcLoadWatts: Double? = nil
    ) {
        self.pvInputWatts = pvInputWatts
        self.gridInputWatts = gridInputWatts
        self.acLoadWatts = acLoadWatts
        self.dcLoadWatts = dcLoadWatts
    }
}

public struct BluettiDevice: Codable, Equatable, Identifiable, Sendable {
    public var id: String { sn }

    public var sn: String
    public var stateList: [BluettiState]
    public var online: String
    public var model: String?
    public var name: String?
    public var isBindByCurUser: String?

    public init(
        sn: String,
        stateList: [BluettiState] = [],
        online: String = "0",
        model: String? = nil,
        name: String? = nil,
        isBindByCurUser: String? = nil
    ) {
        self.sn = sn
        self.stateList = stateList
        self.online = online
        self.model = model
        self.name = name
        self.isBindByCurUser = isBindByCurUser
    }

    enum CodingKeys: String, CodingKey {
        case sn
        case stateList
        case online
        case model
        case name
        case isBindByCurUser
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        sn = try container.decode(String.self, forKey: .sn)
        stateList = try container.decodeIfPresent([BluettiState].self, forKey: .stateList) ?? []
        online = try container.decodeIfPresent(String.self, forKey: .online) ?? "0"
        model = try container.decodeIfPresent(String.self, forKey: .model)
        name = try container.decodeIfPresent(String.self, forKey: .name)
        isBindByCurUser = try container.decodeIfPresent(String.self, forKey: .isBindByCurUser)
    }

    public var serialNumber: String { sn }
    public var deviceID: String { sn }
    public var displayName: String { name ?? sn }
    public var manufacturer: String { "Bluetti" }
    public var isOnline: Bool { online == "1" }
    public var isBoundByCurrentUser: Bool? {
        guard let isBindByCurUser else {
            return nil
        }
        return isBindByCurUser == "1"
    }

    public var batteryLevel: Int? {
        state(matching: BluettiKnownStateCodes.batterySOC)?.numericValue.map(Int.init)
    }

    public var acOutputEnabled: Bool? {
        state(matching: BluettiKnownStateCodes.acOutput)?.boolValue
    }

    public var dcOutputEnabled: Bool? {
        state(matching: BluettiKnownStateCodes.dcOutput)?.boolValue
    }

    public var powerMetrics: BluettiPowerMetrics {
        BluettiPowerMetrics(
            pvInputWatts: state(matching: BluettiKnownStateCodes.pvInputPower)?.numericValue,
            gridInputWatts: state(matching: BluettiKnownStateCodes.gridInputPower)?.numericValue,
            acLoadWatts: state(matching: BluettiKnownStateCodes.acLoadPower)?.numericValue,
            dcLoadWatts: state(matching: BluettiKnownStateCodes.dcLoadPower)?.numericValue
        )
    }

    public var commandCapableStates: [BluettiState] {
        stateList.filter(\.isCommandCapable)
    }

    public func state(forCode fnCode: String) -> BluettiState? {
        stateList.first(where: { $0.fnCode == fnCode })
    }

    public func state(matching codes: [String]) -> BluettiState? {
        for code in codes {
            if let state = state(forCode: code) {
                return state
            }
        }
        return nil
    }

    public func validateCommand(fnCode: String, value: String) throws {
        guard let state = state(forCode: fnCode) else {
            throw BluettiError.stateNotFound(fnCode: fnCode, serialNumber: serialNumber)
        }
        try state.validate(commandValue: value)
    }

    public func updatingState(fnCode: String, value: String) throws -> BluettiDevice {
        guard let index = stateList.firstIndex(where: { $0.fnCode == fnCode }) else {
            throw BluettiError.stateNotFound(fnCode: fnCode, serialNumber: serialNumber)
        }
        var copy = self
        copy.stateList[index] = try stateList[index].updating(value: value)
        return copy
    }

    public func merged(with other: BluettiDevice) -> BluettiDevice {
        var copy = self
        copy.online = other.online
        copy.model = other.model ?? copy.model
        copy.name = other.name ?? copy.name
        copy.isBindByCurUser = other.isBindByCurUser ?? copy.isBindByCurUser

        for state in other.stateList {
            if let index = copy.stateList.firstIndex(where: { $0.fnCode == state.fnCode }) {
                copy.stateList[index] = state
            } else {
                copy.stateList.append(state)
            }
        }

        return copy
    }
}

struct BluettiEnvelope<Value: Decodable>: Decodable {
    let msgId: String
    let msgCode: Int
    let data: Value?
}