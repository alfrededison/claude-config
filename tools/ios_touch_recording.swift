// Snippets to copy into an iOS project so recordings made with ios_record_test.py show touches.
// Not compiled as-is: part A goes in the app target, part B in the UI test target.

// MARK: - A. App target: draw a fading ring at each touch inside the app.
// Use this class as the app's window and launch with the "--record-touches" argument.
import UIKit

final class TouchRecordingWindow: UIWindow {
    private let enabled = ProcessInfo.processInfo.arguments.contains("--record-touches")

    override func sendEvent(_ event: UIEvent) {
        super.sendEvent(event)
        guard enabled else { return }
        for touch in event.allTouches ?? [] where touch.phase == .began {
            let p = touch.location(in: self)
            let ring = UIView(frame: CGRect(x: p.x - 22, y: p.y - 22, width: 44, height: 44))
            ring.backgroundColor = UIColor.systemOrange.withAlphaComponent(0.45)
            ring.layer.cornerRadius = 22
            ring.isUserInteractionEnabled = false
            addSubview(ring)
            UIView.animate(withDuration: 0.6, animations: { ring.alpha = 0 }, completion: { _ in ring.removeFromSuperview() })
        }
    }
}

// MARK: - B. UI test target: log each tap/swipe so the recorder can mark touches outside the app
// (Settings, keyboard extensions, system UI), where part A cannot see them.
// Use these instead of element.tap() / press(forDuration:thenDragTo:).
import XCTest

extension XCUIElement {
    /// Tap and log the element's centre. `app` gives the screen size for scaling.
    func recordedTap(in app: XCUIApplication) {
        let f = frame, s = app.frame
        FileHandle.standardOutput.write(Data("TOUCH_TAP \(Date().timeIntervalSince1970) \(f.midX) \(f.midY) \(s.width) \(s.height)\n".utf8))
        tap()
    }
}

extension XCUIApplication {
    /// Swipe between two normalized points (0...1) and log it.
    func recordedSwipe(from a: CGVector, to b: CGVector, hold: TimeInterval = 0.1) {
        let s = frame
        FileHandle.standardOutput.write(Data(
            "TOUCH_SWIPE \(Date().timeIntervalSince1970) \(s.width * a.dx) \(s.height * a.dy) \(s.width * b.dx) \(s.height * b.dy) \(s.width) \(s.height)\n".utf8))
        coordinate(withNormalizedOffset: a).press(forDuration: hold, thenDragTo: coordinate(withNormalizedOffset: b))
    }
}
