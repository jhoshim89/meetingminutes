import 'dart:async';
import 'package:flutter/foundation.dart';
import '../models/meeting_model.dart';
import '../services/recording_service.dart';
import '../services/supabase_service.dart';
import 'upload_provider.dart';

enum RecorderState { idle, recording, paused, processing, completed, error }

class RecorderProvider with ChangeNotifier {
  final RecordingService _recordingService = RecordingService();
  final SupabaseService _supabaseService = SupabaseService();
  final UploadProvider _uploadProvider = UploadProvider();

  RecorderState _state = RecorderState.idle;
  Duration _duration = Duration.zero;
  double _amplitude = 0.0;
  String? _error;
  MeetingModel? _currentMeeting;
  String? _recordingTitle;
  String? _selectedTemplateId;
  List<String>? _recordingTags;

  StreamSubscription? _durationSubscription;
  StreamSubscription? _amplitudeSubscription;
  StreamSubscription? _stateSubscription;

  // Getters
  RecorderState get state => _state;
  Duration get duration => _duration;
  double get amplitude => _amplitude;
  String? get error => _error;
  MeetingModel? get currentMeeting => _currentMeeting;
  bool get isRecording => _state == RecorderState.recording;
  bool get isPaused => _state == RecorderState.paused;
  bool get isProcessing => _state == RecorderState.processing;
  String? get selectedTemplateId => _selectedTemplateId;
  List<String>? get recordingTags => _recordingTags;

  RecorderProvider() {
    _initialize();
  }

  void _initialize() {
    // Listen to recording service streams
    _durationSubscription = _recordingService.durationStream.listen((duration) {
      _duration = duration;
      notifyListeners();
    });

    _amplitudeSubscription = _recordingService.amplitudeStream.listen((amplitude) {
      _amplitude = amplitude;
      notifyListeners();
    });

    _stateSubscription = _recordingService.recordingStateStream.listen((isRecording) {
      if (isRecording && _state != RecorderState.recording) {
        _state = RecorderState.recording;
        notifyListeners();
      } else if (!isRecording && _state == RecorderState.recording) {
        _state = RecorderState.paused;
        notifyListeners();
      }
    });
  }

  Future<bool> checkPermission() async {
    return await _recordingService.hasPermission();
  }

  void setTemplate(String? templateId, {List<String>? tags}) {
    _selectedTemplateId = templateId;
    _recordingTags = tags;
    notifyListeners();
  }

  Future<void> startRecording({String? title, String? templateId, List<String>? tags}) async {
    try {
      _error = null;
      _recordingTitle = title ?? 'New Meeting ${DateTime.now().toString().substring(0, 16)}';
      if (templateId != null) _selectedTemplateId = templateId;
      if (tags != null) _recordingTags = tags;

      // Check permission
      if (!await _recordingService.hasPermission()) {
        _error = 'Microphone permission not granted';
        _state = RecorderState.error;
        notifyListeners();
        return;
      }

      // Start recording
      await _recordingService.startRecording();
      _state = RecorderState.recording;
      _duration = Duration.zero;
      notifyListeners();
    } catch (e) {
      _error = e.toString();
      _state = RecorderState.error;
      debugPrint('Start recording error: $e');
      notifyListeners();
    }
  }

  Future<void> pauseRecording() async {
    try {
      await _recordingService.pauseRecording();
      _state = RecorderState.paused;
      notifyListeners();
    } catch (e) {
      _error = e.toString();
      debugPrint('Pause recording error: $e');
      notifyListeners();
    }
  }

  Future<void> resumeRecording() async {
    try {
      await _recordingService.resumeRecording();
      _state = RecorderState.recording;
      notifyListeners();
    } catch (e) {
      _error = e.toString();
      debugPrint('Resume recording error: $e');
      notifyListeners();
    }
  }

  Future<MeetingModel?> stopRecording() async {
    _state = RecorderState.processing;
    notifyListeners();

    try {
      // Stop recording and get file path
      final filePath = await _recordingService.stopRecording();

      if (filePath == null) {
        throw Exception('Recording file not found');
      }

      // Upload audio file using UploadProvider (with retry logic)
      final meeting = await _uploadProvider.uploadAudio(
        filePath: filePath,
        title: _recordingTitle ?? 'Untitled Meeting',
        durationSeconds: _duration.inSeconds,
        templateId: _selectedTemplateId,
        tags: _recordingTags,
      );

      if (meeting == null) {
        throw Exception('Failed to upload recording');
      }

      _currentMeeting = meeting;
      _state = RecorderState.completed;
      _error = null;

      notifyListeners();
      return meeting;
    } catch (e) {
      _error = e.toString();
      _state = RecorderState.error;
      debugPrint('Stop recording error: $e');
      notifyListeners();
      return null;
    }
  }

  Future<void> cancelRecording() async {
    try {
      await _recordingService.cancelRecording();
      _state = RecorderState.idle;
      _duration = Duration.zero;
      _amplitude = 0.0;
      _error = null;
      _currentMeeting = null;
      _recordingTitle = null;
      notifyListeners();
    } catch (e) {
      _error = e.toString();
      debugPrint('Cancel recording error: $e');
      notifyListeners();
    }
  }

  void reset() {
    _recordingService.reset();
    _state = RecorderState.idle;
    _duration = Duration.zero;
    _amplitude = 0.0;
    _error = null;
    _currentMeeting = null;
    _recordingTitle = null;
    _selectedTemplateId = null;
    _recordingTags = null;
    notifyListeners();
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }

  @override
  void dispose() {
    _durationSubscription?.cancel();
    _amplitudeSubscription?.cancel();
    _stateSubscription?.cancel();
    _recordingService.dispose();
    super.dispose();
  }
}
