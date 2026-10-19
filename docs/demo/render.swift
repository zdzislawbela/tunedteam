// Renders frames.json (a character grid per frame) to PNGs: render.swift frames.json outdir scale
import AppKit

let args = CommandLine.arguments
let data = try! Data(contentsOf: URL(fileURLWithPath: args[1]))
let doc = try! JSONSerialization.jsonObject(with: data) as! [String: Any]
let outDir = args[2]
let scale = CGFloat(Double(args[3]) ?? 1)
let cols = doc["cols"] as! Int, rows = doc["rows"] as! Int
let frames = doc["frames"] as! [[String: Any]]
let refs = doc["refs"] as! [Int]

let font = NSFont(name: "Menlo", size: 12 * scale)!
let bold = NSFont(name: "Menlo-Bold", size: 12 * scale)!
let cw = ("M" as NSString).size(withAttributes: [.font: font]).width
let ch = (15 * scale).rounded()
let W = doc["W"] as! Int, H = doc["H"] as! Int
let ox = CGFloat(doc["ox"] as! Int), oy = CGFloat(doc["oy"] as! Int)

func color(_ hex: String) -> NSColor {
    let v = Int(hex.dropFirst(), radix: 16)!
    return NSColor(srgbRed: CGFloat(v >> 16 & 255) / 255, green: CGFloat(v >> 8 & 255) / 255, blue: CGFloat(v & 255) / 255, alpha: 1)
}

// Box-drawing characters as lines, so borders join without gaps: (left, right, up, down)
let boxes: [Character: (Bool, Bool, Bool, Bool)] = [
    "─": (true, true, false, false), "│": (false, false, true, true),
    "╭": (false, true, false, true), "┌": (false, true, false, true), "╮": (true, false, false, true), "┐": (true, false, false, true),
    "╰": (false, true, true, false), "└": (false, true, true, false), "╯": (true, false, true, false), "┘": (true, false, true, false),
]

var colorCache: [String: NSColor] = [:]
func c(_ hex: String) -> NSColor {
    if let v = colorCache[hex] { return v }
    let v = color(hex); colorCache[hex] = v; return v
}

for (idx, fr) in frames.enumerated() {
    let frame = fr["g"] as! [[[Any]]]
    let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: W, pixelsHigh: H, bitsPerSample: 8, samplesPerPixel: 4,
                               hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    let ctx = NSGraphicsContext(bitmapImageRep: rep)!
    NSGraphicsContext.current = ctx
    c(doc["bg"] as! String).setFill()
    NSRect(x: 0, y: 0, width: W, height: H).fill()
    for (r, runs) in frame.enumerated() {
        let top = CGFloat(H) - oy - CGFloat(r + 1) * ch
        for run in runs {
            let col = run[0] as! Int, text = run[1] as! String
            let fg = c(run[2] as! String), bg = c(run[3] as! String), isBold = run[4] as! Bool
            let x0 = ox + CGFloat(col) * cw
            let n = text.count
            if run[3] as! String != doc["bg"] as! String {
                bg.setFill()
                NSRect(x: x0, y: top, width: CGFloat(n) * cw, height: ch).fill()
            }
            let attrs: [NSAttributedString.Key: Any] = [.font: isBold ? bold : font, .foregroundColor: fg]
            for (k, char) in text.enumerated() where char != " " {
                let x = x0 + CGFloat(k) * cw
                if let b = boxes[char] {
                    fg.setFill()
                    let mx = (x + cw / 2).rounded(.down), my = (top + ch / 2).rounded(.down), t = max(1, scale.rounded())
                    if b.0 { NSRect(x: x, y: my, width: mx - x + t, height: t).fill() }
                    if b.1 { NSRect(x: mx, y: my, width: x + cw - mx, height: t).fill() }
                    if b.2 { NSRect(x: mx, y: my, width: t, height: top + ch - my).fill() }
                    if b.3 { NSRect(x: mx, y: top, width: t, height: my - top + t).fill() }
                    continue
                }
                (String(char) as NSString).draw(at: NSPoint(x: x, y: top + (ch - font.ascender + font.descender) / 2 - font.descender * 0.0 + 0), withAttributes: attrs)
            }
        }
    }
    for item in fr["ui"] as! [[Any]] {
        let kind = item[0] as! String
        func n(_ i: Int) -> CGFloat { CGFloat((item[i] as! NSNumber).doubleValue) }
        if kind == "r" {
            c(item[5] as! String).setFill()
            NSRect(x: n(1), y: CGFloat(H) - n(2) - n(4), width: n(3), height: n(4)).fill()
        } else if kind == "o" {
            c(item[4] as! String).setFill()
            NSBezierPath(ovalIn: NSRect(x: n(1), y: CGFloat(H) - n(2) - n(3), width: n(3), height: n(3))).fill()
        } else if kind == "t" {
            let f = NSFont.systemFont(ofSize: n(5) * scale, weight: (item[6] as! Bool) ? .semibold : .regular)
            let str = item[3] as! String
            (str as NSString).draw(at: NSPoint(x: n(1), y: CGFloat(H) - n(2) - (f.ascender - f.descender)),
                                   withAttributes: [.font: f, .foregroundColor: c(item[4] as! String)])
        }
    }
    ctx.flushGraphics()
    let png = rep.representation(using: .png, properties: [:])!
    try! png.write(to: URL(fileURLWithPath: "\(outDir)/u\(String(format: "%04d", idx)).png"))
}
for (k, ref) in refs.enumerated() {
    let src = "\(outDir)/u\(String(format: "%04d", ref)).png", dst = "\(outDir)/f\(String(format: "%04d", k)).png"
    try? FileManager.default.removeItem(atPath: dst)
    try! FileManager.default.linkItem(atPath: src, toPath: dst)
}
print("\(W)x\(H), \(frames.count) unique, \(refs.count) frames")
