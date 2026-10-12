import AppKit
import WebKit

final class AppDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate, WKUIDelegate, WKDownloadDelegate {
    private var window: NSWindow!
    private var web: WKWebView!
    private var status: NSTextField!
    private var process: Process?
    private var backendURL: URL?
    private var quitting = false
    private var startupError = false
    private var downloads: [WKDownload] = []
    private let files = FileManager.default
    private let data = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        .appendingPathComponent("Trading Journal", isDirectory: true)
    private var resources: URL { Bundle.main.resourceURL! }
    private var python: URL {
        #if arch(arm64)
        return resources.appendingPathComponent("runtime-arm64/bin/python3")
        #else
        return resources.appendingPathComponent("runtime-x86_64/bin/python3")
        #endif
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        createMenu()
        let config = WKWebViewConfiguration()
        web = WKWebView(frame: .zero, configuration: config)
        web.navigationDelegate = self
        web.uiDelegate = self
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1280, height: 840),
                          styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
        window.title = "Trading Journal"
        window.minSize = NSSize(width: 900, height: 620)
        window.setFrameAutosaveName("TradingJournalWindow")
        window.center()
        window.contentView = web
        status = NSTextField(labelWithString: "Starting Trading Journal…")
        status.font = .systemFont(ofSize: 18)
        status.translatesAutoresizingMaskIntoConstraints = false
        web.addSubview(status)
        NSLayoutConstraint.activate([
            status.centerXAnchor.constraint(equalTo: web.centerXAnchor),
            status.centerYAnchor.constraint(equalTo: web.centerYAnchor)
        ])
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        startBackend()
    }

    private func item(_ menu: NSMenu, _ title: String, _ action: Selector, _ key: String = "", target: AnyObject? = nil) {
        let entry = NSMenuItem(title: title, action: action, keyEquivalent: key)
        entry.target = target
        menu.addItem(entry)
    }

    private func createMenu() {
        let bar = NSMenu()
        let appMenu = NSMenu(title: "Trading Journal")
        item(appMenu, "About Trading Journal", #selector(NSApplication.orderFrontStandardAboutPanel(_:)), target: NSApp)
        appMenu.addItem(.separator())
        item(appMenu, "Open Data Folder", #selector(openData), target: self)
        item(appMenu, "Open Logs", #selector(openLogs), target: self)
        item(appMenu, "Reset Login Password…", #selector(resetPassword), target: self)
        appMenu.addItem(.separator())
        item(appMenu, "Hide Trading Journal", #selector(NSApplication.hide(_:)), "h", target: NSApp)
        appMenu.addItem(.separator())
        item(appMenu, "Quit Trading Journal", #selector(NSApplication.terminate(_:)), "q", target: NSApp)
        let appEntry = NSMenuItem(title: "Trading Journal", action: nil, keyEquivalent: ""); appEntry.submenu = appMenu; bar.addItem(appEntry)
        let edit = NSMenu(title: "Edit")
        for (title, action, key) in [("Undo", "undo:", "z"), ("Cut", "cut:", "x"),
                                    ("Copy", "copy:", "c"), ("Paste", "paste:", "v"), ("Select All", "selectAll:", "a")] {
            item(edit, title, Selector(action), key)
        }
        let editEntry = NSMenuItem(title: "Edit", action: nil, keyEquivalent: ""); editEntry.submenu = edit; bar.addItem(editEntry)
        let view = NSMenu(title: "View")
        item(view, "Reload", #selector(reload), "r", target: self)
        let viewEntry = NSMenuItem(title: "View", action: nil, keyEquivalent: ""); viewEntry.submenu = view; bar.addItem(viewEntry)
        NSApp.mainMenu = bar
    }

    private func startBackend() {
        do {
            try files.createDirectory(at: data, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
            let proc = Process()
            proc.executableURL = python
            proc.arguments = ["-I", "-B", resources.appendingPathComponent("desktop.py").path,
                              "--code", resources.appendingPathComponent("app").path, "--data", data.path,
                              "--parent", String(ProcessInfo.processInfo.processIdentifier)]
            var env = ProcessInfo.processInfo.environment
            // A GUI launch doesn't inherit a shell PATH; core functionality uses only bundled Python.
            env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
            for key in env.keys where key.hasPrefix("TJ_") || key.hasPrefix("PYTHON") { env.removeValue(forKey: key) }
            proc.environment = env
            let output = Pipe()
            proc.standardOutput = output
            proc.standardError = output
            proc.standardInput = FileHandle.nullDevice
            proc.terminationHandler = { [weak self] _ in
                DispatchQueue.main.async {
                    guard let self = self, !self.quitting, !self.startupError else { return }
                    self.showError("The journal stopped. Reopen the app. You can find details in Open Logs.")
                }
            }
            process = proc
            try proc.run()
            DispatchQueue.global(qos: .userInitiated).async { [weak self] in
                var buffer = Data()
                while true {
                    let chunk = output.fileHandleForReading.availableData
                    if chunk.isEmpty { break }
                    buffer.append(chunk)
                    while let newline = buffer.firstIndex(of: 10) {
                        let line = buffer.prefix(upTo: newline)
                        buffer.removeSubrange(...newline)
                        if let event = try? JSONSerialization.jsonObject(with: line) as? [String: Any] {
                            DispatchQueue.main.async { self?.handle(event) }
                        }
                    }
                }
            }
        } catch { showError(error.localizedDescription) }
    }

    private func handle(_ event: [String: Any]) {
        if event["event"] as? String == "ready", let address = event["url"] as? String, let url = URL(string: address) {
            backendURL = url
            status.removeFromSuperview()
            web.load(URLRequest(url: url))
        } else if event["event"] as? String == "error" {
            showError(event["message"] as? String ?? "The journal could not start.")
        }
    }

    private func showError(_ message: String) {
        guard !startupError, !quitting else { return }
        startupError = true
        status.stringValue = "Trading Journal could not start. Please reopen the app."
        let alert = NSAlert()
        alert.messageText = "Trading Journal could not start"
        alert.informativeText = message
        alert.addButton(withTitle: "Open Logs")
        alert.addButton(withTitle: "Close")
        if alert.runModal() == .alertFirstButtonReturn { openLogs() }
    }

    @objc private func openData() { NSWorkspace.shared.open(data) }
    @objc private func openLogs() {
        let logs = data.appendingPathComponent("state/desktop-logs", isDirectory: true)
        NSWorkspace.shared.open(files.fileExists(atPath: logs.path) ? logs : data)
    }
    @objc private func reload() { web.reload() }

    @objc private func resetPassword() {
        guard let url = backendURL else { return }
        let alert = NSAlert()
        alert.messageText = "Reset your login password?"
        alert.informativeText = "This signs out all sessions. Your wallets, keys and journal stay saved. Choose a new password on the next screen."
        alert.addButton(withTitle: "Cancel"); alert.addButton(withTitle: "Reset Password")
        guard alert.runModal() == .alertSecondButtonReturn else { return }
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self = self else { return }
            let proc = Process()
            proc.executableURL = self.python
            proc.arguments = ["-E", "-B", self.resources.appendingPathComponent("app/tools/reset_password.py").path, "-y"]
            var env = self.process?.environment ?? [:]; env["TJ_BASE"] = self.data.path
            proc.environment = env
            proc.standardOutput = FileHandle.nullDevice; proc.standardError = FileHandle.nullDevice
            do {
                try proc.run(); proc.waitUntilExit()
                DispatchQueue.main.async {
                    if proc.terminationStatus == 0 { self.web.load(URLRequest(url: url.appendingPathComponent("login"))) }
                    else { self.showError("Could not reset the password. Check the app data folder permissions.") }
                }
            } catch { DispatchQueue.main.async { self.showError(error.localizedDescription) } }
        }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        guard !quitting else { return .terminateLater }
        quitting = true
        window.title = "Trading Journal — Saving and closing…"
        guard let proc = process, proc.isRunning else { return .terminateNow }
        proc.terminate()
        DispatchQueue.global().async {
            proc.waitUntilExit()
            DispatchQueue.main.async { NSApp.reply(toApplicationShouldTerminate: true) }
        }
        return .terminateLater
    }

    private func isLocal(_ url: URL) -> Bool {
        guard let base = backendURL else { return false }
        return url.scheme == base.scheme && url.host == base.host && url.port == base.port
    }

    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = action.request.url else { decisionHandler(.cancel); return }
        if isLocal(url) || url.scheme == "blob" || url.absoluteString == "about:blank" {
            decisionHandler(action.shouldPerformDownload ? .download : .allow)
        } else {
            if ["https", "http", "mailto"].contains(url.scheme ?? "") { NSWorkspace.shared.open(url) }
            decisionHandler(.cancel)
        }
    }

    func webView(_ webView: WKWebView, decidePolicyFor response: WKNavigationResponse,
                 decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void) {
        let disposition = (response.response as? HTTPURLResponse)?.value(forHTTPHeaderField: "Content-Disposition") ?? ""
        decisionHandler(!response.canShowMIMEType || disposition.lowercased().contains("attachment") ? .download : .allow)
    }

    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration,
                 for action: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
        if let url = action.request.url {
            if isLocal(url) { webView.load(action.request) }
            else if ["http", "https", "mailto"].contains(url.scheme ?? "") { NSWorkspace.shared.open(url) }
        }
        return nil
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        guard let url = webView.url, isLocal(url), url.path == "/login" else { return }
        // The existing login page fetches status asynchronously; keep desktop guidance in place.
        let guidance = """
        (() => {
          const update = () => {
            const foot = document.getElementById('foot');
            const text = '비밀번호를 잊었나요? Mac 메뉴 Trading Journal → Reset Login Password를 선택하세요.';
            if (foot && foot.textContent !== text) foot.textContent = text;
          };
          update(); new MutationObserver(update).observe(document.body, {childList:true, subtree:true});
        })();
        """
        webView.evaluateJavaScript(guidance)
        fillSetupCode(attempt: 0)
    }

    private func fillSetupCode(attempt: Int) {
        guard let url = web.url, isLocal(url), url.path == "/login", attempt < 20 else { return }
        if let code = try? String(contentsOf: data.appendingPathComponent("state/auth_setup_code"), encoding: .utf8),
           let json = try? JSONSerialization.data(withJSONObject: code.trimmingCharacters(in: .whitespacesAndNewlines), options: .fragmentsAllowed),
           let literal = String(data: json, encoding: .utf8) {
            web.evaluateJavaScript("""
            (() => {
              const update = () => {
                const field = document.getElementById('sc'), help = document.getElementById('scHelp');
                if (field && !field.value) field.value = \(literal);
                const text = '이 Mac 앱이 설정 코드를 자동으로 입력했어요. 아래에서 비밀번호를 만드세요.';
                if (help && help.textContent !== text) help.textContent = text;
              };
              update(); new MutationObserver(update).observe(document.body, {childList:true, subtree:true});
            })();
            """)
        } else {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) { [weak self] in self?.fillSetupCode(attempt: attempt + 1) }
        }
    }

    func webView(_ webView: WKWebView, runJavaScriptAlertPanelWithMessage message: String,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping () -> Void) {
        let alert = NSAlert(); alert.messageText = message; alert.runModal(); completionHandler()
    }
    func webView(_ webView: WKWebView, runJavaScriptConfirmPanelWithMessage message: String,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) {
        let alert = NSAlert(); alert.messageText = message
        alert.addButton(withTitle: "OK"); alert.addButton(withTitle: "Cancel")
        completionHandler(alert.runModal() == .alertFirstButtonReturn)
    }
    func webView(_ webView: WKWebView, runJavaScriptTextInputPanelWithPrompt prompt: String, defaultText: String?,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (String?) -> Void) {
        let alert = NSAlert(); alert.messageText = prompt
        alert.addButton(withTitle: "OK"); alert.addButton(withTitle: "Cancel")
        let field = NSTextField(frame: NSRect(x: 0, y: 0, width: 320, height: 24))
        field.stringValue = defaultText ?? ""; alert.accessoryView = field
        alert.window.initialFirstResponder = field
        completionHandler(alert.runModal() == .alertFirstButtonReturn ? field.stringValue : nil)
    }
    func webView(_ webView: WKWebView, runOpenPanelWith parameters: WKOpenPanelParameters,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping ([URL]?) -> Void) {
        let panel = NSOpenPanel(); panel.allowsMultipleSelection = parameters.allowsMultipleSelection
        panel.canChooseDirectories = parameters.allowsDirectories
        completionHandler(panel.runModal() == .OK ? panel.urls : nil)
    }
    func webView(_ webView: WKWebView, navigationAction: WKNavigationAction, didBecome download: WKDownload) {
        downloads.append(download); download.delegate = self
    }
    func webView(_ webView: WKWebView, navigationResponse: WKNavigationResponse, didBecome download: WKDownload) {
        downloads.append(download); download.delegate = self
    }
    func download(_ download: WKDownload, decideDestinationUsing response: URLResponse, suggestedFilename: String,
                  completionHandler: @escaping (URL?) -> Void) {
        let panel = NSSavePanel(); panel.nameFieldStringValue = (suggestedFilename as NSString).lastPathComponent
        completionHandler(panel.runModal() == .OK ? panel.url : nil)
    }
    func downloadDidFinish(_ download: WKDownload) { downloads.removeAll { $0 === download } }
    func download(_ download: WKDownload, didFailWithError error: Error, resumeData: Data?) {
        downloads.removeAll { $0 === download }
        if (error as NSError).code != NSURLErrorCancelled {
            let alert = NSAlert(); alert.messageText = "Download could not finish"
            alert.informativeText = error.localizedDescription; alert.runModal()
        }
    }
}

let delegate = AppDelegate()
NSApplication.shared.delegate = delegate
NSApplication.shared.run()
