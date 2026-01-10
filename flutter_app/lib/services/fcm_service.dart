import 'dart:async';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'supabase_service.dart';

/// FCM Service for Web Push Notifications (iOS Safari 16.4+)
///
/// Handles Firebase Cloud Messaging initialization, token management,
/// and notification event streams for PWA applications.
///
/// Usage:
/// ```dart
/// await FCMService().initialize();
/// String? token = await FCMService().getToken();
/// ```
class FCMService {
  static final FCMService _instance = FCMService._internal();
  factory FCMService() => _instance;
  FCMService._internal();

  FirebaseMessaging? _messaging;
  final StreamController<RemoteMessage> _messageController =
      StreamController<RemoteMessage>.broadcast();

  bool _initialized = false;
  String? _cachedToken;

  /// Initialize Firebase and FCM
  ///
  /// Call this once during app startup, preferably in main.dart
  /// before runApp().
  ///
  /// Throws [FirebaseException] if Firebase initialization fails.
  Future<void> initialize() async {
    if (_initialized) {
      debugPrint('[FCMService] Already initialized');
      return;
    }

    try {
      // Initialize Firebase (web requires manual config in index.html)
      if (Firebase.apps.isEmpty) {
        await Firebase.initializeApp();
        debugPrint('[FCMService] Firebase initialized');
      }

      _messaging = FirebaseMessaging.instance;

      // Request permission for Web Push (iOS Safari 16.4+)
      final settings = await requestPermission();
      debugPrint('[FCMService] Permission status: ${settings.authorizationStatus}');

      // Setup message handlers
      _setupMessageHandlers();

      // Get and save FCM token
      final token = await getToken();
      if (token != null) {
        await saveTokenToSupabase(token);
        debugPrint('[FCMService] Token saved: ${token.substring(0, 20)}...');
      }

      // Listen for token refresh
      FirebaseMessaging.instance.onTokenRefresh.listen((newToken) {
        debugPrint('[FCMService] Token refreshed');
        _cachedToken = newToken;
        saveTokenToSupabase(newToken);
      });

      _initialized = true;
      debugPrint('[FCMService] Initialization complete');
    } catch (e) {
      debugPrint('[FCMService] Initialization error: $e');
      rethrow;
    }
  }

  /// Request notification permission from user
  ///
  /// For Web (iOS Safari 16.4+), this triggers the browser's
  /// native permission dialog.
  ///
  /// Returns [NotificationSettings] with authorization status.
  Future<NotificationSettings> requestPermission() async {
    if (_messaging == null) {
      throw StateError('FCM not initialized. Call initialize() first.');
    }

    final settings = await _messaging!.requestPermission(
      alert: true,
      announcement: false,
      badge: true,
      carPlay: false,
      criticalAlert: false,
      provisional: false,
      sound: true,
    );

    return settings;
  }

  /// Get current FCM token
  ///
  /// For Web Push, requires VAPID key configured in Firebase Console.
  /// The VAPID key should be set in web/index.html Firebase config.
  ///
  /// Returns token string or null if unavailable.
  Future<String?> getToken() async {
    if (_messaging == null) {
      throw StateError('FCM not initialized. Call initialize() first.');
    }

    try {
      // For web, getToken() requires VAPID key for Web Push
      final token = await _messaging!.getToken(
        vapidKey: 'BDMNI8L7UkgAsi82mj-EymZGf7HuImIDgnj44TXUtA1DJbwEf8IJURYNTuFBWTQAptgA_2MwcKR7LBc0rxCBh2Y',
      );

      _cachedToken = token;
      return token;
    } catch (e) {
      debugPrint('[FCMService] Error getting token: $e');
      return null;
    }
  }

  /// Stream of FCM token refresh events
  Stream<String> get onTokenRefresh => FirebaseMessaging.instance.onTokenRefresh;

  /// Stream of foreground messages
  ///
  /// Listen to this stream to handle notifications when app is open.
  /// Background notifications are handled by firebase-messaging-sw.js
  Stream<RemoteMessage> get onMessage => _messageController.stream;

  /// Get message that opened the app (if any)
  ///
  /// Call this on app startup to handle notification taps
  /// that launched the app from terminated state.
  Future<RemoteMessage?> getInitialMessage() async {
    if (_messaging == null) {
      throw StateError('FCM not initialized. Call initialize() first.');
    }
    return await _messaging!.getInitialMessage();
  }

  /// Stream of messages that opened the app from background
  ///
  /// Listen to this to handle notification taps when app was
  /// in background (not terminated).
  Stream<RemoteMessage> get onMessageOpenedApp =>
      FirebaseMessaging.onMessageOpenedApp;

  /// Save FCM token to Supabase user_fcm_tokens table
  ///
  /// Stores token with user_id, device_type='web', and platform='ios'.
  /// Updates existing token if already present.
  Future<void> saveTokenToSupabase(String token) async {
    try {
      final supabase = SupabaseService().client;
      final userId = supabase.auth.currentUser?.id;

      if (userId == null) {
        debugPrint('[FCMService] Cannot save token: user not logged in');
        return;
      }

      // Upsert token (insert or update if exists)
      await supabase.from('user_fcm_tokens').upsert({
        'user_id': userId,
        'token': token,
        'device_type': 'web',
        'platform': 'ios', // iOS Safari 16.4+
        'updated_at': DateTime.now().toIso8601String(),
      }, onConflict: 'user_id,token');

      debugPrint('[FCMService] Token saved to Supabase');
    } catch (e) {
      debugPrint('[FCMService] Error saving token to Supabase: $e');
    }
  }

  /// Get current notification permission status
  ///
  /// Returns [AuthorizationStatus] enum value:
  /// - authorized: User granted permission
  /// - denied: User denied permission
  /// - notDetermined: User hasn't been asked yet
  /// - provisional: Provisional permission (iOS only)
  Future<AuthorizationStatus> getPermissionStatus() async {
    if (_messaging == null) {
      throw StateError('FCM not initialized. Call initialize() first.');
    }

    final settings = await _messaging!.getNotificationSettings();
    return settings.authorizationStatus;
  }

  /// Subscribe to FCM topic
  ///
  /// Topics allow sending notifications to groups of devices.
  /// Example: subscribeToTopic('meeting-reminders')
  Future<void> subscribeToTopic(String topic) async {
    if (_messaging == null) {
      throw StateError('FCM not initialized. Call initialize() first.');
    }

    try {
      await _messaging!.subscribeToTopic(topic);
      debugPrint('[FCMService] Subscribed to topic: $topic');
    } catch (e) {
      debugPrint('[FCMService] Error subscribing to topic: $e');
    }
  }

  /// Unsubscribe from FCM topic
  Future<void> unsubscribeFromTopic(String topic) async {
    if (_messaging == null) {
      throw StateError('FCM not initialized. Call initialize() first.');
    }

    try {
      await _messaging!.unsubscribeFromTopic(topic);
      debugPrint('[FCMService] Unsubscribed from topic: $topic');
    } catch (e) {
      debugPrint('[FCMService] Error unsubscribing from topic: $e');
    }
  }

  /// Delete FCM token and remove from Supabase
  ///
  /// Call this on logout to clean up tokens.
  Future<void> deleteToken() async {
    if (_messaging == null) {
      throw StateError('FCM not initialized. Call initialize() first.');
    }

    try {
      // Delete from FCM
      await _messaging!.deleteToken();
      debugPrint('[FCMService] Token deleted from FCM');

      // Delete from Supabase
      if (_cachedToken != null) {
        final supabase = SupabaseService().client;
        await supabase
            .from('user_fcm_tokens')
            .delete()
            .eq('token', _cachedToken!);
        debugPrint('[FCMService] Token deleted from Supabase');
      }

      _cachedToken = null;
    } catch (e) {
      debugPrint('[FCMService] Error deleting token: $e');
    }
  }

  /// Setup message handlers for foreground notifications
  void _setupMessageHandlers() {
    // Foreground messages
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      debugPrint('[FCMService] Foreground message received');
      debugPrint('[FCMService] Title: ${message.notification?.title}');
      debugPrint('[FCMService] Body: ${message.notification?.body}');
      debugPrint('[FCMService] Data: ${message.data}');

      // Emit to stream for app-level handling
      _messageController.add(message);
    });

    // Messages that opened the app from background
    FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
      debugPrint('[FCMService] Notification opened app from background');
      debugPrint('[FCMService] Data: ${message.data}');

      // Emit to stream for app-level handling (e.g., navigate to meeting)
      _messageController.add(message);
    });
  }

  /// Check if FCM is initialized
  bool get isInitialized => _initialized;

  /// Get cached token (if available)
  String? get cachedToken => _cachedToken;

  /// Dispose resources
  void dispose() {
    _messageController.close();
  }
}

/// Background message handler
///
/// Must be a top-level function (not inside a class).
/// Handles messages when app is terminated (not just backgrounded).
///
/// For Web, this is handled by firebase-messaging-sw.js service worker.
/// This handler is for native mobile platforms.
@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  // Initialize Firebase for background handler
  await Firebase.initializeApp();

  debugPrint('[FCMService] Background message received');
  debugPrint('[FCMService] Title: ${message.notification?.title}');
  debugPrint('[FCMService] Body: ${message.notification?.body}');
  debugPrint('[FCMService] Data: ${message.data}');

  // Handle background notification logic here
  // Note: Cannot access UI or navigation context here
}
