import AppKit

// Reuse the dashboard's three vertical bars and blue accent.
let size = NSSize(width: 1024, height: 1024)
let image = NSImage(size: size)
image.lockFocus()
NSColor(calibratedRed: 0.07, green: 0.09, blue: 0.15, alpha: 1).setFill()
NSBezierPath(roundedRect: NSRect(x: 72, y: 72, width: 880, height: 880), xRadius: 190, yRadius: 190).fill()
NSColor(calibratedRed: 0.49, green: 0.61, blue: 1, alpha: 1).setStroke()
for (x, bottom, top) in [(330.0, 280.0, 745.0), (512.0, 215.0, 810.0), (694.0, 350.0, 675.0)] {
    let path = NSBezierPath()
    path.lineWidth = 70; path.lineCapStyle = .round
    path.move(to: NSPoint(x: x, y: bottom)); path.line(to: NSPoint(x: x, y: top)); path.stroke()
}
image.unlockFocus()
let bitmap = NSBitmapImageRep(data: image.tiffRepresentation!)!
try bitmap.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: CommandLine.arguments[1]))
