package com.sigma.school;

import android.webkit.JavascriptInterface;
import android.util.Log;

import org.json.JSONObject;

/** Trusted-page bridge: only installed on SIGMA-origin pages by MainActivity. */
final class SigmaMobileBridge {
    private static final String TAG = "SIGMA-Mobile";
    interface Listener {
        void showNativeNotification(String title, String body, String notificationId);
    }

    private final SecureOfflineQueue queue;
    private final Listener listener;

    SigmaMobileBridge(SecureOfflineQueue queue, Listener listener) {
        this.queue = queue;
        this.listener = listener;
    }

    @JavascriptInterface
    public void enqueueSyncOperation(String entityType, String entityId, String operationType,
                                     long baseVersion, String payloadJson) {
        try {
            JSONObject op = new JSONObject();
            op.put("entity_type", entityType);
            op.put("entity_id", entityId);
            op.put("operation_type", operationType);
            op.put("base_version", baseVersion);
            op.put("payload", new JSONObject(payloadJson));
            queue.enqueue(op);
        } catch (Exception ex) {
            Log.w(TAG, "Requête offline invalide/rejetée", ex);
        }
    }

    @JavascriptInterface
    public int pendingSyncOperations() {
        try { return queue.size(); } catch (Exception ex) { Log.w(TAG, "Lecture de la file offline impossible", ex); return 0; }
    }

    @JavascriptInterface
    public String peekSyncOperations() {
        try { return queue.peekJson(); } catch (Exception ex) { Log.w(TAG, "Lecture de la file offline impossible", ex); return "[]"; }
    }

    @JavascriptInterface
    public void ackSyncOperations(String operationIdsJson) {
        try { queue.ackJson(operationIdsJson); } catch (Exception ex) { Log.w(TAG, "ACK de la file offline impossible", ex); }
    }

    @JavascriptInterface
    public String drainSyncOperations() {
        try { return queue.drainJson(); } catch (Exception ex) { Log.w(TAG, "Vidage de la file offline impossible", ex); return "[]"; }
    }

    @JavascriptInterface
    public void notify(String title, String body, String notificationId) {
        if (listener != null) listener.showNativeNotification(title, body, notificationId);
    }
}
