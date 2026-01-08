import 'dart:async';
import 'package:flutter/foundation.dart';
import '../models/meeting_model.dart';
import '../models/transcript_model.dart';
import '../services/supabase_service.dart';
import '../services/realtime_service.dart';

class MeetingProvider with ChangeNotifier {
  final SupabaseService _supabaseService = SupabaseService();
  final RealtimeService _realtimeService = RealtimeService();

  StreamSubscription? _realtimeSubscription;

  List<MeetingModel> _meetings = [];
  MeetingModel? _currentMeeting;
  List<TranscriptModel> _transcripts = [];
  bool _isLoading = false;
  String? _error;

  // Getters
  List<MeetingModel> get meetings => _meetings;
  MeetingModel? get currentMeeting => _currentMeeting;
  List<TranscriptModel> get transcripts => _transcripts;
  bool get isLoading => _isLoading;
  String? get error => _error;

  // Filtered meetings
  List<MeetingModel> get completedMeetings =>
      _meetings.where((m) => m.status == 'completed').toList();

  List<MeetingModel> get processingMeetings =>
      _meetings.where((m) => m.status == 'processing').toList();

  MeetingProvider() {
    _initializeRealtime();
  }

  /// Initialize realtime subscription for meeting updates
  Future<void> _initializeRealtime() async {
    try {
      // Subscribe to realtime channel
      await _realtimeService.subscribe();

      // Listen to all processing updates
      _realtimeSubscription = _realtimeService.updateStream.listen((update) {
        debugPrint(
          'MeetingProvider: Received update for ${update.meetingId} - ${update.status}',
        );

        // Update meeting in list if it exists
        final index = _meetings.indexWhere((m) => m.id == update.meetingId);
        if (index != -1) {
          _meetings[index] = _meetings[index].copyWith(status: update.status);
          notifyListeners();

          // Reload full meeting data if completed
          if (update.isCompleted) {
            _reloadMeeting(update.meetingId);
          }
        }
      });
    } catch (e) {
      debugPrint('MeetingProvider: Failed to initialize realtime: $e');
    }
  }

  /// Reload specific meeting from database
  Future<void> _reloadMeeting(String meetingId) async {
    try {
      final meeting = await _supabaseService.getMeetingById(meetingId);
      final index = _meetings.indexWhere((m) => m.id == meetingId);
      if (index != -1) {
        _meetings[index] = meeting;
        notifyListeners();
      }
    } catch (e) {
      debugPrint('MeetingProvider: Failed to reload meeting: $e');
    }
  }

  Future<void> fetchMeetings({String? status}) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _meetings = await _supabaseService.getMeetings(status: status);
      _error = null;
    } catch (e) {
      _error = e.toString();
      debugPrint('Fetch meetings error: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> fetchMeetingById(String meetingId) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _currentMeeting = await _supabaseService.getMeetingById(meetingId);
      _error = null;
    } catch (e) {
      _error = e.toString();
      debugPrint('Fetch meeting error: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<MeetingModel?> createMeeting({
    required String title,
    String? audioUrl,
    Map<String, dynamic>? metadata,
  }) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final meeting = await _supabaseService.createMeeting(
        title: title,
        audioUrl: audioUrl,
        metadata: metadata,
      );

      _meetings.insert(0, meeting);
      _currentMeeting = meeting;
      _error = null;

      notifyListeners();
      return meeting;
    } catch (e) {
      _error = e.toString();
      debugPrint('Create meeting error: $e');
      notifyListeners();
      return null;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> updateMeeting(
    String meetingId, {
    String? title,
    int? durationSeconds,
    String? status,
    String? audioUrl,
    String? transcriptUrl,
    String? summary,
    int? speakerCount,
    Map<String, dynamic>? metadata,
  }) async {
    try {
      final updatedMeeting = await _supabaseService.updateMeeting(
        meetingId,
        title: title,
        durationSeconds: durationSeconds,
        status: status,
        audioUrl: audioUrl,
        transcriptUrl: transcriptUrl,
        summary: summary,
        speakerCount: speakerCount,
        metadata: metadata,
      );

      // Update in list
      final index = _meetings.indexWhere((m) => m.id == meetingId);
      if (index != -1) {
        _meetings[index] = updatedMeeting;
      }

      // Update current meeting if it matches
      if (_currentMeeting?.id == meetingId) {
        _currentMeeting = updatedMeeting;
      }

      notifyListeners();
    } catch (e) {
      _error = e.toString();
      debugPrint('Update meeting error: $e');
      notifyListeners();
    }
  }

  Future<void> deleteMeeting(String meetingId) async {
    try {
      await _supabaseService.deleteMeeting(meetingId);
      _meetings.removeWhere((m) => m.id == meetingId);

      if (_currentMeeting?.id == meetingId) {
        _currentMeeting = null;
      }

      notifyListeners();
    } catch (e) {
      _error = e.toString();
      debugPrint('Delete meeting error: $e');
      notifyListeners();
    }
  }

  Future<void> fetchTranscripts(String meetingId) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _transcripts = await _supabaseService.getTranscripts(meetingId);
      _error = null;
    } catch (e) {
      _error = e.toString();
      debugPrint('Fetch transcripts error: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  void clearCurrentMeeting() {
    _currentMeeting = null;
    _transcripts = [];
    notifyListeners();
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }

  void reset() {
    _meetings = [];
    _currentMeeting = null;
    _transcripts = [];
    _error = null;
    notifyListeners();
  }

  Future<void> loadMeetings() async {
    await fetchMeetings();
  }

  @override
  void dispose() {
    _realtimeSubscription?.cancel();
    super.dispose();
  }
}
