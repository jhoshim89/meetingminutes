import 'dart:async';
import 'package:flutter/foundation.dart';
import '../models/meeting_model.dart';
import '../services/storage_service.dart';
import '../services/supabase_service.dart';
import '../services/realtime_service.dart';

/// Upload state
enum UploadState {
  idle,
  uploading,
  completed,
  failed,
}

/// Upload progress information
class UploadProgress {
  final int sent;
  final int total;
  final double percentage;

  UploadProgress({
    required this.sent,
    required this.total,
  }) : percentage = total > 0 ? (sent / total) * 100 : 0;

  @override
  String toString() => '${percentage.toStringAsFixed(1)}%';
}

/// Provider for managing audio upload operations
/// Handles file upload to Supabase Storage and database updates
class UploadProvider with ChangeNotifier {
  final StorageService _storageService = StorageService();
  final SupabaseService _supabaseService = SupabaseService();
  final RealtimeService _realtimeService = RealtimeService();

  UploadState _state = UploadState.idle;
  UploadProgress? _progress;
  String? _error;
  MeetingModel? _currentMeeting;

  StreamSubscription? _realtimeSubscription;

  // Getters
  UploadState get state => _state;
  UploadProgress? get progress => _progress;
  String? get error => _error;
  MeetingModel? get currentMeeting => _currentMeeting;
  bool get isUploading => _state == UploadState.uploading;
  bool get isCompleted => _state == UploadState.completed;
  bool get isFailed => _state == UploadState.failed;

  /// Upload audio file and create meeting record
  ///
  /// Steps:
  /// 1. Create meeting record in database (status: 'pending')
  /// 2. Upload audio file to Storage
  /// 3. Update meeting record with audio URL and storage path
  /// 4. Subscribe to realtime updates for processing status
  ///
  /// Args:
  ///   filePath: Local audio file path
  ///   title: Meeting title
  ///   durationSeconds: Recording duration
  ///
  /// Returns:
  ///   MeetingModel if successful, null if failed
  Future<MeetingModel?> uploadAudio({
    required String filePath,
    required String title,
    required int durationSeconds,
    String? templateId,
    List<String>? tags,
  }) async {
    _state = UploadState.uploading;
    _error = null;
    _progress = UploadProgress(sent: 0, total: 100);
    notifyListeners();

    try {
      // Step 1: Create meeting record
      debugPrint('UploadProvider: Creating meeting record');
      final meeting = await _supabaseService.createMeeting(
        title: title,
        templateId: templateId,
        tags: tags,
        metadata: {
          'upload_started_at': DateTime.now().toIso8601String(),
        },
      );

      _currentMeeting = meeting;
      notifyListeners();

      // Step 2: Upload audio file with retry logic
      debugPrint('UploadProvider: Uploading audio file');
      final uploadResult = await _storageService.uploadAudioFile(
        filePath: filePath,
        meetingId: meeting.id,
        maxRetries: 3,
      );

      debugPrint('UploadProvider: Upload completed - ${uploadResult.publicUrl}');

      // Step 3: Update meeting with audio URL and status
      final updatedMeeting = await _supabaseService.updateMeeting(
        meeting.id,
        audioUrl: uploadResult.publicUrl,
        durationSeconds: durationSeconds,
        status: 'pending', // Ready for PC Worker to process
        metadata: {
          'upload_started_at': meeting.metadata?['upload_started_at'],
          'upload_completed_at': DateTime.now().toIso8601String(),
          'storage_path': uploadResult.storagePath,
          'file_size': uploadResult.fileSize,
        },
      );

      _currentMeeting = updatedMeeting;
      _state = UploadState.completed;
      _progress = UploadProgress(sent: 100, total: 100);
      _error = null;

      debugPrint('UploadProvider: Upload successful - Meeting ${meeting.id}');

      // Step 4: Subscribe to realtime updates
      await _subscribeToRealtimeUpdates(meeting.id);

      notifyListeners();
      return updatedMeeting;
    } catch (e) {
      _error = e.toString();
      _state = UploadState.failed;
      debugPrint('UploadProvider: Upload failed - $e');
      notifyListeners();
      return null;
    }
  }

  /// Subscribe to realtime processing updates for a meeting
  Future<void> _subscribeToRealtimeUpdates(String meetingId) async {
    try {
      // Ensure realtime service is subscribed
      if (!_realtimeService.isSubscribed) {
        await _realtimeService.subscribe();
      }

      // Listen to updates for this specific meeting
      _realtimeSubscription?.cancel();
      _realtimeSubscription = _realtimeService
          .listenToMeeting(meetingId)
          .listen((update) {
        debugPrint(
          'UploadProvider: Received update for ${update.meetingId} - '
          'Status: ${update.status}, Message: ${update.message}',
        );

        // Update meeting status based on realtime update
        _handleRealtimeUpdate(update);
      });

      debugPrint('UploadProvider: Subscribed to realtime updates');
    } catch (e) {
      debugPrint('UploadProvider: Failed to subscribe to realtime: $e');
    }
  }

  /// Handle realtime processing update
  void _handleRealtimeUpdate(ProcessingUpdate update) {
    if (_currentMeeting == null || _currentMeeting!.id != update.meetingId) {
      return;
    }

    // Update meeting status
    _currentMeeting = _currentMeeting!.copyWith(
      status: update.status,
    );

    notifyListeners();
  }

  /// Cancel upload (if in progress)
  Future<void> cancelUpload() async {
    if (_state != UploadState.uploading) {
      return;
    }

    try {
      // If meeting was created, mark it as failed
      if (_currentMeeting != null) {
        await _supabaseService.updateMeeting(
          _currentMeeting!.id,
          status: 'failed',
          metadata: {
            ..._currentMeeting!.metadata ?? {},
            'cancelled_at': DateTime.now().toIso8601String(),
          },
        );
      }

      _state = UploadState.idle;
      _progress = null;
      _error = 'Upload cancelled by user';
      _currentMeeting = null;

      notifyListeners();
    } catch (e) {
      debugPrint('UploadProvider: Cancel upload error: $e');
    }
  }

  /// Reset state
  void reset() {
    _realtimeSubscription?.cancel();
    _realtimeSubscription = null;

    _state = UploadState.idle;
    _progress = null;
    _error = null;
    _currentMeeting = null;

    notifyListeners();
  }

  /// Clear error
  void clearError() {
    _error = null;
    notifyListeners();
  }

  @override
  void dispose() {
    _realtimeSubscription?.cancel();
    super.dispose();
  }
}
