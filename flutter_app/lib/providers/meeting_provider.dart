import 'dart:async';
import 'package:flutter/foundation.dart';
import '../models/meeting_model.dart';
import '../models/meeting_summary_model.dart';
import '../models/transcript_model.dart';
import '../services/supabase_service.dart';
import '../services/realtime_service.dart';
import 'appointment_provider.dart';

class MeetingProvider with ChangeNotifier {
  final SupabaseService _supabaseService = SupabaseService();
  final RealtimeService _realtimeService = RealtimeService();

  StreamSubscription? _realtimeSubscription;

  List<MeetingModel> _meetings = [];
  MeetingModel? _currentMeeting;
  MeetingSummaryModel? _currentSummary;
  List<TranscriptModel> _transcripts = [];
  bool _isLoading = false;
  String? _error;
  String? _selectedTemplateId;

  // Getters
  List<MeetingModel> get meetings => _meetings;
  MeetingModel? get currentMeeting => _currentMeeting;
  MeetingSummaryModel? get currentSummary => _currentSummary;
  List<TranscriptModel> get transcripts => _transcripts;
  bool get isLoading => _isLoading;
  String? get error => _error;
  String? get selectedTemplateId => _selectedTemplateId;

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

  Future<void> fetchMeetings({String? status, String? templateId}) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _meetings = await _supabaseService.getMeetings(
        status: status,
        templateId: templateId ?? _selectedTemplateId,
      );
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
      // Try to fetch summary as well, but don't fail if not found
      fetchMeetingSummary(meetingId);
      _error = null;
    } catch (e) {
      _error = e.toString();
      debugPrint('Fetch meeting error: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> fetchMeetingSummary(String meetingId) async {
    // Don't set global loading as this might be secondary
    try {
      _currentSummary = await _supabaseService.getMeetingSummary(meetingId);
      notifyListeners();
    } catch (e) {
      debugPrint('Fetch meeting summary error: $e');
    }
  }

  Future<MeetingModel?> createMeeting({
    required String title,
    String? audioUrl,
    Map<String, dynamic>? metadata,
    String? templateId,
    List<String>? tags,
  }) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final meeting = await _supabaseService.createMeeting(
        title: title,
        audioUrl: audioUrl,
        metadata: metadata,
        templateId: templateId ?? _selectedTemplateId,
        tags: tags,
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

  /// Delete meeting with all associated data (audio, appointment)
  Future<bool> deleteMeetingComplete(
    String meetingId, {
    AppointmentProvider? appointmentProvider,
  }) async {
    try {
      // 1. Get meeting details first (for audio URL)
      final meeting = await _supabaseService.getMeetingById(meetingId);

      // 2. Delete audio from storage if exists
      if (meeting.audioUrl != null && meeting.audioUrl!.isNotEmpty) {
        try {
          await _supabaseService.deleteAudio(meeting.audioUrl!);
          debugPrint('Deleted audio file for meeting $meetingId');
        } catch (e) {
          debugPrint('Failed to delete audio: $e');
          // Continue with deletion even if audio deletion fails
        }
      }

      // 3. Delete meeting record (transcripts cascade via DB)
      await _supabaseService.deleteMeeting(meetingId);

      // 4. Delete associated appointment if provider available
      if (appointmentProvider != null) {
        await appointmentProvider.deleteAppointmentByMeetingId(meetingId);
      }

      // 5. Update local state
      _meetings.removeWhere((m) => m.id == meetingId);
      if (_currentMeeting?.id == meetingId) {
        _currentMeeting = null;
      }

      notifyListeners();
      return true;
    } catch (e) {
      _error = e.toString();
      debugPrint('Delete meeting complete error: $e');
      notifyListeners();
      return false;
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

  /// Update speaker assignment for a transcript line
  /// Returns true if successful, false otherwise
  Future<bool> updateTranscriptSpeaker(
    String transcriptId, {
    required String? speakerId,
    required String? speakerName,
  }) async {
    try {
      final updatedTranscript = await _supabaseService.updateTranscriptSpeaker(
        transcriptId,
        speakerId: speakerId,
        speakerName: speakerName,
      );

      // Update in local list
      final index = _transcripts.indexWhere((t) => t.id == transcriptId);
      if (index != -1) {
        _transcripts[index] = updatedTranscript;
        notifyListeners();
      }

      return true;
    } catch (e) {
      _error = e.toString();
      debugPrint('Update transcript speaker error: $e');
      notifyListeners();
      return false;
    }
  }

  void clearCurrentMeeting() {
    _currentMeeting = null;
    _currentSummary = null;
    _transcripts = [];
    notifyListeners();
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }

  // Template filtering
  void setTemplateFilter(String? templateId) {
    _selectedTemplateId = templateId;
    notifyListeners();
    fetchMeetings();
  }

  void clearTemplateFilter() {
    _selectedTemplateId = null;
    notifyListeners();
    fetchMeetings();
  }

  // Get meetings filtered by current template
  List<MeetingModel> get filteredMeetings {
    if (_selectedTemplateId == null) return _meetings;
    return _meetings.where((m) => m.templateId == _selectedTemplateId).toList();
  }

  void reset() {
    _meetings = [];
    _currentMeeting = null;
    _currentSummary = null;
    _transcripts = [];
    _error = null;
    _selectedTemplateId = null;
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
