package com.sigma.school;

import android.content.Context;
import android.content.SharedPreferences;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;

import org.json.JSONArray;
import org.json.JSONObject;

import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

/** Small encrypted-at-rest queue for mobile sync intents. */
final class SecureOfflineQueue {
    private static final String PREFS = "sigma_mobile_secure";
    private static final String QUEUE = "offline_queue";
    private static final String KEY_ALIAS = "sigma_mobile_queue_key_v1";
    private static final int MAX_OPERATIONS = 5000;
    private static final int MAX_OPERATION_BYTES = 64 * 1024;
    private static final int MAX_QUEUE_BYTES = 512 * 1024;
    private final Context context;

    SecureOfflineQueue(Context context) {
        this.context = context.getApplicationContext();
    }

    synchronized void enqueue(JSONObject operation) throws Exception {
        JSONArray queue = read();
        JSONObject item = new JSONObject(operation.toString());
        if (item.toString().getBytes(StandardCharsets.UTF_8).length > MAX_OPERATION_BYTES) throw new IllegalArgumentException("Opération offline trop volumineuse");
        item.put("queue_id", UUID.randomUUID().toString());
        item.put("queued_at", System.currentTimeMillis());
        if (queue.length() >= MAX_OPERATIONS) throw new IllegalStateException("File offline pleine");
        queue.put(item);
        if (queue.toString().getBytes(StandardCharsets.UTF_8).length > MAX_QUEUE_BYTES) throw new IllegalStateException("File offline trop volumineuse");
        write(queue);
    }

    /** Non-destructive read for ACK-safe synchronization. */
    synchronized String peekJson() throws Exception {
        return read().toString();
    }

    /** ACK only the operations confirmed by the server. */
    synchronized void ackJson(String operationIdsJson) throws Exception {
        JSONArray ids = new JSONArray(operationIdsJson);
        java.util.HashSet<String> acknowledged = new java.util.HashSet<>();
        for (int i = 0; i < ids.length(); i++) {
            acknowledged.add(ids.getString(i));
        }
        if (acknowledged.isEmpty()) return;
        JSONArray queue = read();
        JSONArray remaining = new JSONArray();
        for (int i = 0; i < queue.length(); i++) {
            JSONObject item = queue.getJSONObject(i);
            if (!acknowledged.contains(item.optString("queue_id"))) {
                remaining.put(item);
            }
        }
        write(remaining);
    }

    /** Legacy destructive API kept for backward compatibility. New clients must use peek + ACK. */
    synchronized String drainJson() throws Exception {
        JSONArray queue = read();
        write(new JSONArray());
        return queue.toString();
    }

    synchronized int size() throws Exception { return read().length(); }

    private JSONArray read() throws Exception {
        String encoded = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(QUEUE, null);
        if (encoded == null || encoded.isEmpty()) return new JSONArray();
        byte[] packed = Base64.decode(encoded, Base64.NO_WRAP);
        byte[] iv = new byte[12];
        System.arraycopy(packed, 0, iv, 0, iv.length);
        byte[] ciphertext = new byte[packed.length - iv.length];
        System.arraycopy(packed, iv.length, ciphertext, 0, ciphertext.length);
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.DECRYPT_MODE, key(), new GCMParameterSpec(128, iv));
        String json = new String(cipher.doFinal(ciphertext), StandardCharsets.UTF_8);
        return new JSONArray(json);
    }

    private void write(JSONArray queue) throws Exception {
        byte[] iv = new byte[12];
        new java.security.SecureRandom().nextBytes(iv);
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, key(), new GCMParameterSpec(128, iv));
        byte[] ciphertext = cipher.doFinal(queue.toString().getBytes(StandardCharsets.UTF_8));
        byte[] packed = new byte[iv.length + ciphertext.length];
        System.arraycopy(iv, 0, packed, 0, iv.length);
        System.arraycopy(ciphertext, 0, packed, iv.length, ciphertext.length);
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
                .putString(QUEUE, Base64.encodeToString(packed, Base64.NO_WRAP)).apply();
    }

    private SecretKey key() throws Exception {
        KeyStore store = KeyStore.getInstance("AndroidKeyStore");
        store.load(null);
        if (store.containsAlias(KEY_ALIAS)) return ((KeyStore.SecretKeyEntry) store.getEntry(KEY_ALIAS, null)).getSecretKey();
        KeyGenerator generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore");
        generator.init(new KeyGenParameterSpec.Builder(KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setRandomizedEncryptionRequired(true)
                .build());
        return generator.generateKey();
    }
}
