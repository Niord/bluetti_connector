// swift-tools-version: 6.0

import PackageDescription

let package = Package(
    name: "BluettiMonitorSample",
    platforms: [
        .macOS(.v13),
    ],
    products: [
        .executable(
            name: "BluettiMonitorSample",
            targets: ["BluettiMonitorSample"]
        ),
    ],
    dependencies: [
        .package(path: "../BluettiKit"),
    ],
    targets: [
        .executableTarget(
            name: "BluettiMonitorSample",
            dependencies: [
                .product(name: "BluettiKit", package: "BluettiKit"),
            ]
        ),
    ]
)