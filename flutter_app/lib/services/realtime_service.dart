import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../models/meeting_model.dart';

/// Processing status update from PC Worker
class ProcessingUpdate {
  final String meetingId;
  final String status; // 'pending', 'processing', 'completed', 'failed'
  final String? message;
  final Map<String, dynamic>? data;
  final DateTime timestamp;

  ProcessingUpdate({
    required this.meetingId,
    required this.status,
    this.message,
    this.data,
    required this.timestamp,
  });

  factory ProcessingUpdate.fromJson(Map<String, dynamic> json) {
    return ProcessingUpdate(
      meetingId: json['meeting_id'] as String,
      status: json['status'] as String,
      message: json['message'] as String?,
      data: json['data'] as Map<String, dynamic>?,
      timestamp: json['timestamp'] != null
          ? DateTime.parse(json['timestamp'] as String)
          : DateTime.now(),
    );
  }

  bool get isPending => status == 'pending';
  bool get isProcessing => status == 'processing';
  bool get isCompleted => status == 'completed';
  bool get isFailed => status == 'failed';
}

/// Service for real-time communication with PC Worker via Supabase Realtime
///
/// Subscribes to processing status updates and broadcasts them to listeners
class RealtimeService {
  static final RealtimeService _instance = RealtimeService._internal();
  factory RealtimeService() => _instance;
  RealtimeService._internal();

  final _client = Supabase.instance.client;

  RealtimeChannel? _channel;
  bool _isSubscribed = false;

  // Stream controllers for broadcasting updates
  final _updateController = StreamController<ProcessingUpdate>.broadcast();
  final _connectionController = StreamController<bool>.broadcast();

  /// Stream of processing updates
  Stream<ProcessingUpdate> get updateStream => _updateController.stream;

  /// Stream of connection status (true = connected, false = disconnected)
  Stream<bool> get connectionStream => _connectionController.stream;

  bool get isSubscribed => _isSubscribed;

  /// Subscribe to realtime updates for the current user
  ///
  /// Creates a channel subscription based on user_id
  /// Receives updates when PC Worker processes meetings
  Future<void> subscribe() async {
    if (_isSubscribed) {
      debugPrint('RealtimeService: Already subscribed');
      return;
    }

    final userId = _client.auth.currentUser?.id;
    if (userId == null) {
      throw Exception('User not authenticated');
    }

    try {
      debugPrint('RealtimeService: Subscribing to channel for user: $userId');

      // Create channel for this user
      _channel = _client.channel('user:$userId:meetings');

      // Subscribe to broadcast events
      _channel!
          .onBroadcast(
            event: 'processing_update',
            callback: (payload) {
              debugPrint('RealtimeService: Received broadcast: $payload');
              _handleProcessingUpdate(payload);
            },
          )
          .subscribe((status, error) {
            debugPrint('RealtimeService: Subscription status: $status');

            if (status == RealtimeSubscribeStatus.subscribed) {
              _isSubscribed = true;
              _connectionController.add(true);
              debugPrint('RealtimeService: Successfully subscribed');
            } else if (status == RealtimeSubscribeStatus.closed) {
              _isSubscribed = false;
              _connectionController.add(false);
              debugPrint('RealtimeService: Channel closed');
            } else if (status == RealtimeSubscribeStatus.channelError) {
              _isSubscribed = false;
              _connectionController.add(false);
              debugPrint('RealtimeService: Channel error: $error');
            }
          });
    } catch (e) {
      debugPrint('RealtimeService: Subscription error: $e');
      _isSubscribed = false;
      _connectionController.add(false);
      rethrow;
    }
  }

  /// Unsubscribe from realtime updates
  Future<void> unsubscribe() async {
    if (!_isSubscribed || _channel == null) {
      return;
    }

    try {
      debugPrint('RealtimeService: Unsubscribing');
      await _client.removeChannel(_channel!);
      _channel = null;
      _isSubscribed = false;
      _connectionController.add(false);
    } catch (e) {
      debugPrint('RealtimeService: Unsubscribe error: $e');
    }
  }

  /// Handle processing update from PC Worker
  void _handleProcessingUpdate(Map<String, dynamic> payload) {
    try {
      final update = ProcessingUpdate.fromJson(payload);

      debugPrint(
        'RealtimeService: Processing update - '
        'Meeting: ${update.meetingId}, '
        'Status: ${update.status}, '
        'Message: ${update.message ?? "N/A"}',
      );

      // Broadcast to listeners
      _updateController.add(update);
    } catch (e) {
      debugPrint('RealtimeService: Failed to parse update: $e');
    }
  }

  /// Send a test message (for debugging)
  Future<void> sendTestMessage(String meetingId, String status) async {
    if (!_isSubscribed || _channel == null) {
      throw Exception('Not subscribed to realtime channel');
    }

    try {
      await _channel!.sendBroadcastMessage(
        event: 'processing_update',
        payload: {
          'meeting_id': meetingId,
          'status': status,
          'message': 'Test message from mobile',
          'timestamp': DateTime.now().toIso8601String(),
        },
      );

      debugPrint('RealtimeService: Test message sent');
    } catch (e) {
      debugPrint('RealtimeService: Failed to send test message: $e');
      rethrow;
    }
  }

  /// Listen for specific meeting updates
  ///
  /// Returns a filtered stream that only emits updates for the given meeting
  Stream<ProcessingUpdate> listenToMeeting(String meetingId) {
    return updateStream.where((update) => update.meetingId == meetingId);
  }

  /// Check connection health
  Future<bool> checkConnection() async {
    try {
      if (!_isSubscribed || _channel == null) {
        return false;
      }

      // Channel exists and is subscribed
      return true;
    } catch (e) {
      return false;
    }
  }

  /// Dispose resources
  void dispose() {
    debugPrint('RealtimeService: Disposing');
    unsubscribe();
    _updateController.close();
    _connectionController.close();
  }
}
