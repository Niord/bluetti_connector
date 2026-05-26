// swift-tools-version: 6.0

import PackageDescription

let package = Package(
    name: "BluettiKit",
    platforms: [
        .macOS(.v13),
    ],
    products: [
        .library(
            name: "BluettiKit",
            targets: ["BluettiKit"]
        ),
    ],
    targets: [
        .target(
            name: "BluettiKit"
        ),
        .testTarget(
            name: "BluettiKitTests",
            dependencies: ["BluettiKit"]
        ),
    ]
)