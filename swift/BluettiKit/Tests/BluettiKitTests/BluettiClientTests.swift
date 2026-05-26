import Foundation
import XCTest
@testable import BluettiKit

final class BluettiClientTests: XCTestCase {
    func testAuthorizeURLIncludesExpectedParameters() throws {
        let client = BluettiClient()
        let redirectURI = URL(string: "bluetti-macos://oauth/callback")!

        let authorizeURL = try client.authorizeURL(redirectURI: redirectURI, state: "state-123")
        let components = try XCTUnwrap(URLComponents(url: authorizeURL, resolvingAgainstBaseURL: false))
        let queryItems = Dictionary(uniqueKeysWithValues: (components.queryItems ?? []).map { ($0.name, $0.value ?? "") })

        XCTAssertEqual(authorizeURL.path, "/oauth2/grant")
        XCTAssertEqual(queryItems["response_type"], "code")
        XCTAssertEqual(queryItems["client_id"], "HomeAssistant")
        XCTAssertEqual(queryItems["redirect_uri"], redirectURI.absoluteString)
        XCTAssertEqual(queryItems["state"], "state-123")
    }

    func testListDevicesRefreshesExpiredTokenAndExposesHelpers() async throws {
        let store = InMemoryTokenStore(initialTokens: BluettiTokenState(accessToken: "expired-access", refreshToken: "refresh-token"))
        let session = makeSession()
        var seenAuthorizations: [String] = []
        var tokenRefreshWasRequested = false

        MockURLProtocol.requestHandler = { request in
            switch request.url?.path {
            case "/api/bluiotdata/ha/v1/devices":
                let authorization = request.value(forHTTPHeaderField: "Authorization") ?? ""
                seenAuthorizations.append(authorization)
                if authorization == "expired-access" {
                    return try self.jsonResponse(
                        url: request.url!,
                        status: 200,
                        jsonObject: [
                            "msgId": "devices",
                            "msgCode": 805,
                            "data": NSNull(),
                        ]
                    )
                }

                return try self.jsonResponse(
                    url: request.url!,
                    status: 200,
                    jsonObject: [
                        "msgId": "devices",
                        "msgCode": 0,
                        "data": [
                            [
                                "sn": "AC200L-TEST-001",
                                "online": "1",
                                "model": "AC200L",
                                "name": "Workshop Battery",
                                "isBindByCurUser": "1",
                                "stateList": [
                                    [
                                        "fnCode": "SOC",
                                        "fnName": "Battery SOC",
                                        "fnValue": "81",
                                        "fnType": "number",
                                        "supportModeValues": [],
                                        "sensorInfo": ["unit": "%"],
                                    ],
                                    [
                                        "fnCode": "SetCtrlAc",
                                        "fnName": "AC Output",
                                        "fnValue": "1",
                                        "fnType": "switch",
                                        "supportModeValues": [],
                                    ],
                                    [
                                        "fnCode": "SetCtrlDc",
                                        "fnName": "DC Output",
                                        "fnValue": "0",
                                        "fnType": "switch",
                                        "supportModeValues": [],
                                    ],
                                    [
                                        "fnCode": "ACLoadAllTotalPower",
                                        "fnName": "AC Load",
                                        "fnValue": "420",
                                        "fnType": "number",
                                        "supportModeValues": [],
                                    ],
                                    [
                                        "fnCode": "DCLoadAllTotalPower",
                                        "fnName": "DC Load",
                                        "fnValue": "85",
                                        "fnType": "number",
                                        "supportModeValues": [],
                                    ],
                                ],
                            ],
                        ],
                    ]
                )

            case "/oauth2/token":
                tokenRefreshWasRequested = true
                XCTAssertEqual(request.value(forHTTPHeaderField: "Content-Type"), "application/x-www-form-urlencoded; charset=utf-8")

                return try self.jsonResponse(
                    url: request.url!,
                    status: 200,
                    jsonObject: [
                        "access_token": "fresh-access",
                        "refresh_token": "fresh-refresh",
                        "expires_in": 3600,
                        "created_at": 1716681600,
                        "token_type": "Bearer",
                    ]
                )

            default:
                XCTFail("Unexpected request: \(request.url?.absoluteString ?? "unknown")")
                return try self.jsonResponse(url: request.url!, status: 500, jsonObject: [:])
            }
        }

        let client = BluettiClient(tokenStore: store, session: session)
        let devices = try await client.listDevices()
        let device = try XCTUnwrap(devices.first)
        let persistedTokens = try await store.loadTokens()

        XCTAssertTrue(tokenRefreshWasRequested)
        XCTAssertEqual(seenAuthorizations, ["expired-access", "fresh-access"])
        XCTAssertEqual(device.batteryLevel, 81)
        XCTAssertEqual(device.acOutputEnabled, true)
        XCTAssertEqual(device.dcOutputEnabled, false)
        XCTAssertEqual(device.powerMetrics.acLoadWatts, 420)
        XCTAssertEqual(device.powerMetrics.dcLoadWatts, 85)
        XCTAssertEqual(persistedTokens?.accessToken, "fresh-access")
        XCTAssertEqual(persistedTokens?.refreshToken, "fresh-refresh")
    }

    func testSetACOutputLoadsDeviceStatusAndSendsFulfillment() async throws {
        let store = InMemoryTokenStore(initialTokens: BluettiTokenState(accessToken: "active-access", refreshToken: "refresh-token"))
        let session = makeSession()
        var fulfillmentWasCalled = false

        MockURLProtocol.requestHandler = { request in
            switch request.url?.path {
            case "/api/bluiotdata/ha/v1/devices":
                return try self.jsonResponse(
                    url: request.url!,
                    status: 200,
                    jsonObject: [
                        "msgId": "devices",
                        "msgCode": 0,
                        "data": [
                            [
                                "sn": "AC200L-TEST-001",
                                "online": "1",
                                "model": "AC200L",
                                "name": "Workshop Battery",
                                "isBindByCurUser": "1",
                                "stateList": [
                                    [
                                        "fnCode": "SetCtrlAc",
                                        "fnName": "AC Output",
                                        "fnValue": "0",
                                        "fnType": "switch",
                                        "supportModeValues": [],
                                    ],
                                    [
                                        "fnCode": "SOC",
                                        "fnName": "Battery SOC",
                                        "fnValue": "55",
                                        "fnType": "number",
                                        "supportModeValues": [],
                                    ],
                                ],
                            ],
                        ],
                    ]
                )

            case "/api/bluiotdata/ha/v1/deviceStates":
                XCTAssertEqual(URLComponents(url: request.url!, resolvingAgainstBaseURL: false)?.queryItems?.first?.value, "AC200L-TEST-001")
                return try self.jsonResponse(
                    url: request.url!,
                    status: 200,
                    jsonObject: [
                        "msgId": "deviceStates",
                        "msgCode": 0,
                        "data": [
                            [
                                "sn": "AC200L-TEST-001",
                                "online": "1",
                                "model": "AC200L",
                                "name": "Workshop Battery",
                                "isBindByCurUser": "1",
                                "stateList": [
                                    [
                                        "fnCode": "SetCtrlAc",
                                        "fnName": "AC Output",
                                        "fnValue": "0",
                                        "fnType": "switch",
                                        "supportModeValues": [],
                                    ],
                                    [
                                        "fnCode": "SOC",
                                        "fnName": "Battery SOC",
                                        "fnValue": "55",
                                        "fnType": "number",
                                        "supportModeValues": [],
                                    ],
                                ],
                            ],
                        ],
                    ]
                )

            case "/api/bluiotdata/ha/v1/fulfillment":
                fulfillmentWasCalled = true
                XCTAssertEqual(request.value(forHTTPHeaderField: "Content-Type"), "application/json")
                return try self.jsonResponse(
                    url: request.url!,
                    status: 200,
                    jsonObject: [
                        "msgId": "fulfillment",
                        "msgCode": 0,
                        "data": [
                            "accepted": true,
                            "sn": "AC200L-TEST-001",
                        ],
                    ]
                )

            default:
                XCTFail("Unexpected request: \(request.url?.absoluteString ?? "unknown")")
                return try self.jsonResponse(url: request.url!, status: 500, jsonObject: [:])
            }
        }

        let client = BluettiClient(tokenStore: store, session: session)
        let updatedDevice = try await client.setACOutput(serialNumber: "AC200L-TEST-001", isOn: true)

        XCTAssertTrue(fulfillmentWasCalled)
        XCTAssertEqual(updatedDevice.acOutputEnabled, true)
    }

    private func makeSession() -> URLSession {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [MockURLProtocol.self]
        return URLSession(configuration: configuration)
    }

    private func jsonResponse(url: URL, status: Int, jsonObject: Any) throws -> (HTTPURLResponse, Data) {
        let data = try JSONSerialization.data(withJSONObject: jsonObject, options: [.sortedKeys])
        let response = try XCTUnwrap(
            HTTPURLResponse(
                url: url,
                statusCode: status,
                httpVersion: nil,
                headerFields: ["Content-Type": "application/json"]
            )
        )
        return (response, data)
    }

}