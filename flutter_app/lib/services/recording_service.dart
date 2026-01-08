import 'dart:async';
import 'dart:io';
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';

class RecordingService {
  static final RecordingService _instance = RecordingService._internal();
  factory RecordingService() => _instance;
  RecordingService._internal();

  final AudioRecorder _recorder = AudioRecorder();

  Timer? _timer;
  Duration _duration = Duration.zero;
  bool _isRecording = false;
  bool _isPaused = false;
  String? _currentFilePath;

  // Getters
  bool get isRecording => _isRecording;
  bool get isPaused => _isPaused;
  Duration get duration => _duration;
  String? get currentFilePath => _currentFilePath;

  // Stream controllers for state updates
  final _recordingStateController = StreamController<bool>.broadcast();
  final _durationController = StreamController<Duration>.broadcast();
  final _amplitudeController = StreamController<double>.broadcast();

  Stream<bool> get recordingStateStream => _recordingStateController.stream;
  Stream<Duration> get durationStream => _durationController.stream;
  Stream<double> get amplitudeStream => _amplitudeController.stream;

  Future<bool> hasPermission() async {
    try {
      return await _recorder.hasPermission();
    } catch (e) {
      return false;
    }
  }

  Future<void> startRecording() async {
    try {
      // Check permission
      if (!await hasPermission()) {
        throw Exception('Microphone permission not granted');
      }

      // Generate file path
      final directory = await getApplicationDocumentsDirectory();
      final timestamp = DateTime.now().millisecondsSinceEpoch;
      _currentFilePath = '${directory.path}/recording_$timestamp.m4a';

      // Start recording
      await _recorder.start(
        const RecordConfig(
          encoder: AudioEncoder.aacLc,
          bitRate: 128000,
          sampleRate: 44100,
        ),
        path: _currentFilePath!,
      );

      _isRecording = true;
      _isPaused = false;
      _duration = Duration.zero;
      _recordingStateController.add(true);

      // Start timer
      _startTimer();

      // Monitor amplitude
      _monitorAmplitude();
    } catch (e) {
      throw Exception('Failed to start recording: $e');
    }
  }

  Future<void> pauseRecording() async {
    try {
      if (!_isRecording) return;

      await _recorder.pause();
      _isPaused = true;
      _stopTimer();
      _recordingStateController.add(false);
    } catch (e) {
      throw Exception('Failed to pause recording: $e');
    }
  }

  Future<void> resumeRecording() async {
    try {
      if (!_isRecording || !_isPaused) return;

      await _recorder.resume();
      _isPaused = false;
      _recordingStateController.add(true);
      _startTimer();
      _monitorAmplitude();
    } catch (e) {
      throw Exception('Failed to resume recording: $e');
    }
  }

  Future<String?> stopRecording() async {
    try {
      if (!_isRecording) return null;

      final path = await _recorder.stop();
      _isRecording = false;
      _isPaused = false;
      _stopTimer();
      _recordingStateController.add(false);

      // Verify file exists
      if (path != null && await File(path).exists()) {
        return path;
      }

      return null;
    } catch (e) {
      throw Exception('Failed to stop recording: $e');
    }
  }

  Future<void> cancelRecording() async {
    try {
      if (!_isRecording) return;

      await _recorder.stop();
      _isRecording = false;
      _isPaused = false;
      _stopTimer();
      _recordingStateController.add(false);

      // Delete the file
      if (_currentFilePath != null) {
        final file = File(_currentFilePath!);
        if (await file.exists()) {
          await file.delete();
        }
      }

      _currentFilePath = null;
    } catch (e) {
      throw Exception('Failed to cancel recording: $e');
    }
  }

  void _startTimer() {
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      _duration = Duration(seconds: _duration.inSeconds + 1);
      _durationController.add(_duration);
    });
  }

  void _stopTimer() {
    _timer?.cancel();
    _timer = null;
  }

  Future<void> _monitorAmplitude() async {
    if (!_isRecording || _isPaused) return;

    try {
      final amplitude = await _recorder.getAmplitude();
      final normalizedAmplitude = amplitude.current / amplitude.max;
      _amplitudeController.add(normalizedAmplitude);

      // Continue monitoring
      if (_isRecording && !_isPaused) {
        await Future.delayed(const Duration(milliseconds: 100));
        _monitorAmplitude();
      }
    } catch (e) {
      // Silently fail amplitude monitoring
    }
  }

  Future<void> dispose() async {
    _timer?.cancel();
    await _recordingStateController.close();
    await _durationController.close();
    await _amplitudeController.close();
    await _recorder.dispose();
  }

  void reset() {
    _duration = Duration.zero;
    _currentFilePath = null;
    _isRecording = false;
    _isPaused = false;
  }
}
