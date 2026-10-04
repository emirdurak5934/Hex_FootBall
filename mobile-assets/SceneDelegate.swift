import UIKit
import WebKit
import Capacitor

final class FootballBridgeViewController: CAPBridgeViewController {
    private let appBackground = UIColor(
        red: 7.0 / 255.0,
        green: 11.0 / 255.0,
        blue: 19.0 / 255.0,
        alpha: 1.0
    )

    private func configureAppWebView(_ webView: WKWebView) {
        webView.isOpaque = false
        webView.backgroundColor = appBackground
        webView.underPageBackgroundColor = appBackground

        let scrollView = webView.scrollView
        scrollView.backgroundColor = appBackground
        scrollView.bounces = false
        scrollView.alwaysBounceVertical = false
        scrollView.alwaysBounceHorizontal = false
        scrollView.contentInsetAdjustmentBehavior = .never
        scrollView.showsVerticalScrollIndicator = false
        scrollView.showsHorizontalScrollIndicator = false
    }

    override func webView(
        with frame: CGRect,
        configuration: WKWebViewConfiguration
    ) -> WKWebView {
        let webView = super.webView(with: frame, configuration: configuration)
        configureAppWebView(webView)
        return webView
    }

    override func capacitorDidLoad() {
        super.capacitorDidLoad()
        view.backgroundColor = appBackground
        if let webView {
            configureAppWebView(webView)
        }
    }
}

class SceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?

    func scene(
        _ scene: UIScene,
        willConnectTo session: UISceneSession,
        options connectionOptions: UIScene.ConnectionOptions
    ) {
        guard let windowScene = scene as? UIWindowScene else { return }

        let appBackground = UIColor(
            red: 7.0 / 255.0,
            green: 11.0 / 255.0,
            blue: 19.0 / 255.0,
            alpha: 1.0
        )
        let appWindow = UIWindow(windowScene: windowScene)
        appWindow.backgroundColor = appBackground
        appWindow.rootViewController = FootballBridgeViewController()
        window = appWindow
        appWindow.makeKeyAndVisible()

        SceneDelegateProxy.shared.scene(
            scene,
            willConnectTo: session,
            options: connectionOptions
        )
    }

    func scene(_ scene: UIScene, openURLContexts URLContexts: Set<UIOpenURLContext>) {
        SceneDelegateProxy.shared.scene(scene, openURLContexts: URLContexts)
    }

    func scene(_ scene: UIScene, continue userActivity: NSUserActivity) {
        SceneDelegateProxy.shared.scene(scene, continue: userActivity)
    }
}
