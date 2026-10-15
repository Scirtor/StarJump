package com.scirtor.starjump;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.graphics.Color;
import android.graphics.Insets;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.window.OnBackInvokedDispatcher;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.util.Collections;

/** Offline game assets use an HTTPS origin, never file:// or a local HTTP server. */
public final class MainActivity extends Activity {
    private static final String HOST = "appassets.androidplatform.net";
    private static final String START = "https://" + HOST + "/assets/index.html";
    private WebView webView;
    private boolean foreground;

    @SuppressLint("SetJavaScriptEnabled")
    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.rgb(24, 17, 37));
        webView = new WebView(this);
        root.addView(webView, new FrameLayout.LayoutParams(-1, -1));
        setContentView(root);
        if (Build.VERSION.SDK_INT >= 30) {
            root.setOnApplyWindowInsetsListener((view, insets) -> {
                Insets safe = insets.getInsets(android.view.WindowInsets.Type.systemBars()
                        | android.view.WindowInsets.Type.displayCutout());
                view.setPadding(safe.left, safe.top, safe.right, safe.bottom);
                return insets;
            });
            root.requestApplyInsets();
        } else {
            root.setFitsSystemWindows(true);
        }
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setSupportMultipleWindows(false);
        settings.setMediaPlaybackRequiresUserGesture(true);
        webView.setBackgroundColor(Color.rgb(24, 17, 37));
        webView.setWebViewClient(new WebViewClient() {
            @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                String path = uri.getPath();
                if (!"https".equals(uri.getScheme()) || !HOST.equals(uri.getHost())
                        || path == null || !path.startsWith("/assets/")
                        || path.contains("..") || !"GET".equals(request.getMethod())) {
                    return denied();
                }
                String asset = path.substring("/assets/".length());
                try {
                    return new WebResourceResponse(mime(asset), null, 200, "OK",
                            Collections.singletonMap("Cache-Control", "no-cache"), getAssets().open(asset));
                } catch (IOException error) {
                    return new WebResourceResponse("text/plain", "UTF-8", 404, "Not found",
                            Collections.emptyMap(), new ByteArrayInputStream(new byte[0]));
                }
            }
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return !START.equals(request.getUrl().toString());
            }
        });
        if (Build.VERSION.SDK_INT >= 33) {
            getOnBackInvokedDispatcher().registerOnBackInvokedCallback(
                    OnBackInvokedDispatcher.PRIORITY_DEFAULT, this::handleBack);
        }
        webView.loadUrl(START);
    }

    private static WebResourceResponse denied() {
        return new WebResourceResponse("text/plain", "UTF-8", 403, "Blocked",
                Collections.emptyMap(), new ByteArrayInputStream(new byte[0]));
    }
    private static String mime(String name) {
        if (name.endsWith(".html")) return "text/html";
        if (name.endsWith(".js")) return "application/javascript";
        if (name.endsWith(".wasm")) return "application/wasm";
        if (name.endsWith(".json") || name.endsWith(".webmanifest")) return "application/json";
        if (name.endsWith(".png")) return "image/png";
        return "application/octet-stream";
    }
    private void handleBack() {
        webView.evaluateJavascript("window.starjumpPlaying ? (window.starjumpPauseRequested = true, true) : false", value -> {
            if (!"true".equals(value)) finish();
        });
    }
    @SuppressWarnings("deprecation")
    @Override public void onBackPressed() { handleBack(); }
    @Override protected void onPause() {
        foreground = false;
        webView.evaluateJavascript("window.starjumpPauseRequested = true", value -> {
            if (!foreground) { webView.onPause(); webView.pauseTimers(); }
        });
        super.onPause();
    }
    @Override protected void onResume() {
        super.onResume();
        foreground = true;
        if (webView != null) { webView.resumeTimers(); webView.onResume(); }
    }
    @Override protected void onDestroy() {
        webView.destroy();
        super.onDestroy();
    }
}
