import 'dart:async';
import 'package:just_audio/just_audio.dart';

class AudioService {
  static final AudioService _instance = AudioService._internal();
  factory AudioService() => _instance;
  AudioService._internal() {
    _setupListeners();
  }

  final AudioPlayer _audioPlayer = AudioPlayer();

  // Stream controllers for UI updates
  final _playingController = StreamController<bool>.broadcast();
  final _positionController = StreamController<Duration>.broadcast();
  final _durationController = StreamController<Duration>.broadcast();

  Stream<bool> get playingStream => _playingController.stream;
  Stream<Duration> get positionStream => _positionController.stream;
  Stream<Duration> get durationStream => _durationController.stream;

  bool _isInitialized = false;
  String? _currentAudioUrl;

  bool get isPlaying => _audioPlayer.playing;
  Duration get position => _audioPlayer.position;
  Duration get duration => _audioPlayer.duration ?? Duration.zero;

  void _setupListeners() {
    _audioPlayer.playingStream.listen((isPlaying) {
      _playingController.add(isPlaying);
    });

    _audioPlayer.positionStream.listen((position) {
      _positionController.add(position);
    });

    _audioPlayer.durationStream.listen((duration) {
      _durationController.add(duration ?? Duration.zero);
    });
  }

  /// Load and play audio from URL
  Future<void> playAudio(String url) async {
    try {
      if (_currentAudioUrl != url) {
        await _audioPlayer.setUrl(url);
        _currentAudioUrl = url;
        _isInitialized = true;
      }
      await _audioPlayer.play();
    } catch (e) {
      throw Exception('Failed to play audio: $e');
    }
  }

  /// Pause audio playback
  Future<void> pause() async {
    try {
      await _audioPlayer.pause();
    } catch (e) {
      throw Exception('Failed to pause audio: $e');
    }
  }

  /// Resume audio playback
  Future<void> resume() async {
    try {
      await _audioPlayer.play();
    } catch (e) {
      throw Exception('Failed to resume audio: $e');
    }
  }

  /// Stop audio and reset position
  Future<void> stop() async {
    try {
      await _audioPlayer.stop();
      await _audioPlayer.seek(Duration.zero);
    } catch (e) {
      throw Exception('Failed to stop audio: $e');
    }
  }

  /// Seek to specific position
  Future<void> seek(Duration position) async {
    try {
      await _audioPlayer.seek(position);
    } catch (e) {
      throw Exception('Failed to seek: $e');
    }
  }

  /// Get current playback status
  PlayerState? get playerState => _audioPlayer.playerState;

  /// Dispose resources
  Future<void> dispose() async {
    await _audioPlayer.dispose();
    await _playingController.close();
    await _positionController.close();
    await _durationController.close();
  }

  /// Reset to initial state
  Future<void> reset() async {
    try {
      await _audioPlayer.stop();
      _currentAudioUrl = null;
      _isInitialized = false;
    } catch (e) {
      // Silently fail
    }
  }
}
