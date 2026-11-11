import AppKit
import CoreImage
import Foundation

let arguments = CommandLine.arguments
guard arguments.count == 3 else {
    FileHandle.standardError.write(Data("usage: pair_qr.swift <payload> <output.png>\n".utf8))
    exit(2)
}

let payload = arguments[1]
let output = arguments[2]

guard let filter = CIFilter(name: "CIQRCodeGenerator") else { exit(1) }
filter.setValue(Data(payload.utf8), forKey: "inputMessage")
filter.setValue("M", forKey: "inputCorrectionLevel")

guard let qr = filter.outputImage?.transformed(by: CGAffineTransform(scaleX: 12, y: 12)) else {
    exit(1)
}

// Composite onto white: a transparent background becomes unreadable on dark themes.
let image = qr.composited(over: CIImage(color: .white).cropped(to: qr.extent))

let context = CIContext()
guard let cgImage = context.createCGImage(image, from: image.extent) else { exit(1) }
let representation = NSBitmapImageRep(cgImage: cgImage)
guard let png = representation.representation(using: .png, properties: [:]) else { exit(1) }

try png.write(to: URL(fileURLWithPath: output))
