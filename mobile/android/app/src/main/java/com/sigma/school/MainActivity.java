package com.sigma.school;

import android.Manifest;
import android.app.Activity;
import android.app.DownloadManager;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.ConnectivityManager;
import android.net.NetworkCapabilities;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.webkit.CookieManager;
import android.webkit.DownloadListener;
import android.webkit.URLUtil;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.TextView;
import android.widget.Toast;
import android.util.Log;

import androidx.core.app.NotificationCompat;

import java.net.URI;

public final class MainActivity extends Activity {
    private WebView webView;
    private static final String TAG = "SIGMA-Mobile";
    private TextView offlineBanner;
    private URI allowedBase;
    private SecureOfflineQueue offlineQueue;
    private final Handler notificationHandler = new Handler(Looper.getMainLooper());
    private boolean notificationPolling;
    private final Runnable notificationPoller = new Runnable() {
        @Override public void run() {
            if (!notificationPolling || webView == null || !hasNetwork()) return;
            webView.evaluateJavascript("(async()=>{try{const r=await fetch('/api/notifications?unread_only=true&limit=10',{credentials:'include'});if(!r.ok)return;const a=await r.json();return JSON.stringify(a.slice(0,10));}catch(e){return '[]';}})()", value -> handleNotificationJson(value));
            notificationHandler.postDelayed(this, 60000L);
        }
    };

    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        try { allowedBase = validateBaseUrl(BuildConfig.SIGMA_BASE_URL); }
        catch (IllegalArgumentException ex) { showMessage(getString(R.string.config_required)); return; }
        offlineQueue = new SecureOfflineQueue(this);
        createNotificationChannel();
        FrameLayout root = new FrameLayout(this);
        webView = new WebView(this);
        root.addView(webView, new FrameLayout.LayoutParams(-1, -1));
        offlineBanner = new TextView(this);
        offlineBanner.setText(R.string.offline_banner);
        offlineBanner.setGravity(Gravity.CENTER);
        offlineBanner.setPadding(24, 10, 24, 10);
        offlineBanner.setVisibility(hasNetwork() ? View.GONE : View.VISIBLE);
        FrameLayout.LayoutParams bannerParams = new FrameLayout.LayoutParams(-1, -2, Gravity.TOP);
        root.addView(offlineBanner, bannerParams);
        setContentView(root);
        configureWebView(webView);
        webView.addJavascriptInterface(new SigmaMobileBridge(offlineQueue, this::showNativeNotification), "SigmaMobile");
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 4401);
        }
        if (savedInstanceState == null) loadTarget(getIntent()); else webView.restoreState(savedInstanceState);
    }

    private void loadTarget(Intent intent) {
        Uri data = intent == null ? null : intent.getData();
        if (data != null && "sigma".equalsIgnoreCase(data.getScheme()) && "open".equalsIgnoreCase(data.getHost())) {
            String target = data.getQueryParameter("url");
            if (target != null) {
                Uri candidate = Uri.parse(target);
                if (isAllowed(candidate)) { webView.loadUrl(candidate.toString()); return; }
            }
        }
        webView.loadUrl(allowedBase.toString());
    }

    private URI validateBaseUrl(String raw) {
        try {
            URI uri = URI.create(raw == null ? "" : raw.trim());
            if (!"https".equalsIgnoreCase(uri.getScheme()) || uri.getHost() == null || uri.getHost().trim().isEmpty() || "sigma.invalid".equalsIgnoreCase(uri.getHost())) throw new IllegalArgumentException();
            String normalized = uri.toString(); if (!normalized.endsWith("/")) normalized += "/"; return URI.create(normalized);
        } catch (RuntimeException ex) { throw new IllegalArgumentException("invalid base URL", ex); }
    }

    private void configureWebView(WebView view) {
        WebSettings settings = view.getSettings();
        settings.setJavaScriptEnabled(true); settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false); settings.setAllowContentAccess(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        if (Build.VERSION.SDK_INT >= 26) settings.setSafeBrowsingEnabled(true);
        CookieManager.getInstance().setAcceptCookie(true); CookieManager.getInstance().setAcceptThirdPartyCookies(view, false);
        view.setWebChromeClient(new WebChromeClient());
        view.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest request) {
                Uri uri=request.getUrl(); if (isAllowed(uri)) return false;
                try { startActivity(new Intent(Intent.ACTION_VIEW, uri)); } catch (Exception ex) { Log.w(TAG, "Ouverture externe refusée", ex); Toast.makeText(MainActivity.this, R.string.external_blocked, Toast.LENGTH_SHORT).show(); }
                return true;
            }
            @Override public void onPageFinished(WebView v, String url) { updateNetworkBanner(); }
        });
        view.setDownloadListener((url,userAgent,contentDisposition,mimetype,contentLength) -> {
            if (!isAllowed(Uri.parse(url))) { Toast.makeText(this,R.string.external_download_blocked,Toast.LENGTH_SHORT).show(); return; }
            try {
                DownloadManager.Request request=new DownloadManager.Request(Uri.parse(url));
                String cookie=CookieManager.getInstance().getCookie(url); if(cookie!=null) request.addRequestHeader("Cookie",cookie);
                request.addRequestHeader("User-Agent",userAgent); request.setMimeType(mimetype);
                request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                request.setDestinationInExternalFilesDir(this, Environment.DIRECTORY_DOWNLOADS, URLUtil.guessFileName(url,contentDisposition,mimetype));
                ((DownloadManager)getSystemService(Context.DOWNLOAD_SERVICE)).enqueue(request);
                Toast.makeText(this,R.string.download_started,Toast.LENGTH_SHORT).show();
            } catch(Exception ex){ Log.w(TAG, "Téléchargement documentaire impossible", ex); Toast.makeText(this,R.string.download_failed,Toast.LENGTH_LONG).show(); }
        });
    }

    private boolean isAllowed(Uri uri) { return uri!=null && "https".equalsIgnoreCase(uri.getScheme()) && allowedBase.getHost().equalsIgnoreCase(uri.getHost()) && normalizedPort(allowedBase)==normalizedPort(uri); }
    private int normalizedPort(URI uri){ return uri.getPort()==-1?443:uri.getPort(); }
    private int normalizedPort(Uri uri){ return uri.getPort()==-1?443:uri.getPort(); }
    private boolean hasNetwork(){ ConnectivityManager cm=(ConnectivityManager)getSystemService(Context.CONNECTIVITY_SERVICE); if(cm==null||cm.getActiveNetwork()==null)return false; NetworkCapabilities c=cm.getNetworkCapabilities(cm.getActiveNetwork()); return c!=null&&c.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET); }
    private void updateNetworkBanner(){ if(offlineBanner!=null) offlineBanner.setVisibility(hasNetwork()?View.GONE:View.VISIBLE); }
    private void createNotificationChannel(){
        if (Build.VERSION.SDK_INT < 26) return;
        NotificationManager manager = (NotificationManager)getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager != null) manager.createNotificationChannel(new NotificationChannel("sigma_notifications", "Notifications SIGMA", NotificationManager.IMPORTANCE_DEFAULT));
    }

    private void showNativeNotification(String title, String body, String notificationId){
        NotificationManager manager=(NotificationManager)getSystemService(Context.NOTIFICATION_SERVICE);
        if(manager==null) return;
        Intent intent=new Intent(this, MainActivity.class);
        intent.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP|Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent pending=PendingIntent.getActivity(this, notificationId==null?0:notificationId.hashCode(), intent, PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
        NotificationCompat.Builder builder=new NotificationCompat.Builder(this,"sigma_notifications")
                .setSmallIcon(R.drawable.ic_sigma).setContentTitle(title==null?"SIGMA":title).setContentText(body==null?"":body)
                .setAutoCancel(true).setContentIntent(pending);
        manager.notify(notificationId==null?1:Math.abs(notificationId.hashCode()), builder.build());
    }

    private void handleNotificationJson(String raw){
        if(raw==null || raw.equals("null") || raw.length()<3) return;
        try{
            String json=android.net.Uri.decode(raw);
            if(json.startsWith("\"")) json=new org.json.JSONTokener(json).nextValue().toString();
            org.json.JSONArray items=new org.json.JSONArray(json);
            android.content.SharedPreferences seen=getSharedPreferences("sigma_mobile_notifications", MODE_PRIVATE);
            for(int i=items.length()-1;i>=0;i--){
                org.json.JSONObject n=items.getJSONObject(i); String id=String.valueOf(n.optInt("id",0));
                if(id.equals("0") || seen.getBoolean(id,false)) continue;
                showNativeNotification(n.optString("title","SIGMA"),n.optString("body",""),id); seen.edit().putBoolean(id,true).apply();
            }
        }catch(Exception ex){ Log.w(TAG, "Notification push locale invalide", ex); }
    }

    private void showMessage(String message){ TextView text=new TextView(this); text.setText(message); text.setTextSize(18f); int p=(int)(24*getResources().getDisplayMetrics().density); text.setPadding(p,p,p,p); setContentView(text); }
    @Override protected void onSaveInstanceState(Bundle outState){ if(webView!=null)webView.saveState(outState); super.onSaveInstanceState(outState); }
    @Override public void onBackPressed(){ if(webView!=null&&webView.canGoBack())webView.goBack(); else super.onBackPressed(); }
    @Override protected void onResume(){ super.onResume(); updateNetworkBanner(); notificationPolling=true; notificationHandler.removeCallbacks(notificationPoller); notificationHandler.post(notificationPoller); }
    @Override protected void onPause(){ notificationPolling=false; notificationHandler.removeCallbacks(notificationPoller); super.onPause(); }
    @Override protected void onDestroy(){ notificationPolling=false; notificationHandler.removeCallbacks(notificationPoller); if(webView!=null){webView.removeJavascriptInterface("SigmaMobile");webView.destroy();webView=null;} super.onDestroy(); }
}
