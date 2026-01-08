import 'dart:math' as math;
import 'package:flutter/foundation.dart';
import '../models/speaker_model.dart';
import '../services/supabase_service.dart';

class SpeakerProvider with ChangeNotifier {
  final SupabaseService _supabaseService = SupabaseService();

  List<SpeakerModel> _speakers = [];
  List<SpeakerModel> _unregisteredSpeakers = [];
  bool _isLoading = false;
  String? _error;

  // Audio sample URLs cache
  final Map<String, String> _audioSampleCache = {};
  final Set<String> _loadingAudioSamples = {};

  // Getters
  List<SpeakerModel> get speakers => _speakers;
  List<SpeakerModel> get unregisteredSpeakers => _unregisteredSpeakers;
  List<SpeakerModel> get registeredSpeakers =>
      _speakers.where((s) => s.isRegistered).toList();
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get hasUnregisteredSpeakers => _unregisteredSpeakers.isNotEmpty;

  Future<void> fetchSpeakers() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _speakers = await _supabaseService.getSpeakers();
      _unregisteredSpeakers = _speakers.where((s) => !s.isRegistered).toList();
      _error = null;
    } catch (e) {
      _error = e.toString();
      debugPrint('Fetch speakers error: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> fetchUnregisteredSpeakers() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _unregisteredSpeakers = await _supabaseService.getSpeakers(
        isRegistered: false,
      );
      _error = null;
    } catch (e) {
      _error = e.toString();
      debugPrint('Fetch unregistered speakers error: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> registerSpeaker(String speakerId, String name) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final updatedSpeaker = await _supabaseService.updateSpeaker(
        speakerId,
        name: name,
        isRegistered: true,
      );

      // Update in lists
      final index = _speakers.indexWhere((s) => s.id == speakerId);
      if (index != -1) {
        _speakers[index] = updatedSpeaker;
      }

      _unregisteredSpeakers.removeWhere((s) => s.id == speakerId);

      _error = null;
      notifyListeners();
      return true;
    } catch (e) {
      _error = e.toString();
      debugPrint('Register speaker error: $e');
      notifyListeners();
      return false;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> updateSpeaker(
    String speakerId, {
    String? name,
    Map<String, dynamic>? metadata,
  }) async {
    try {
      final updatedSpeaker = await _supabaseService.updateSpeaker(
        speakerId,
        name: name,
        metadata: metadata,
      );

      final index = _speakers.indexWhere((s) => s.id == speakerId);
      if (index != -1) {
        _speakers[index] = updatedSpeaker;
      }

      notifyListeners();
      return true;
    } catch (e) {
      _error = e.toString();
      debugPrint('Update speaker error: $e');
      notifyListeners();
      return false;
    }
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }

  void reset() {
    _speakers = [];
    _unregisteredSpeakers = [];
    _error = null;
    notifyListeners();
  }

  /// Get audio sample URL for a speaker
  /// Returns cached URL if available, otherwise generates signed URL
  Future<String?> getAudioSampleUrl(String speakerId) async {
    // Return cached URL if available
    if (_audioSampleCache.containsKey(speakerId)) {
      return _audioSampleCache[speakerId];
    }

    // Avoid duplicate requests
    if (_loadingAudioSamples.contains(speakerId)) {
      return null;
    }

    _loadingAudioSamples.add(speakerId);
    notifyListeners();

    try {
      // Get audio sample URL from storage
      // Storage path format: audio/{user_id}/{speaker_id}_sample.wav
      final url = _supabaseService.getAudioSampleUrl(speakerId);
      _audioSampleCache[speakerId] = url;
      return url;
    } catch (e) {
      debugPrint('Failed to get audio sample URL: $e');
      return null;
    } finally {
      _loadingAudioSamples.remove(speakerId);
      notifyListeners();
    }
  }

  /// Check if audio sample is currently loading
  bool isLoadingAudioSample(String speakerId) {
    return _loadingAudioSamples.contains(speakerId);
  }

  /// Clear audio sample cache
  void clearAudioSampleCache() {
    _audioSampleCache.clear();
    notifyListeners();
  }

  /// Attempt to auto-match a new speaker with registered speakers
  /// Returns matched speaker if confidence is high enough
  Future<SpeakerModel?> autoMatchSpeaker({
    required List<double> embedding,
    double confidenceThreshold = 0.85,
  }) async {
    try {
      if (embedding.isEmpty) return null;

      final registeredSpeakers = _speakers
          .where((s) => s.isRegistered && s.embeddings != null)
          .toList();

      if (registeredSpeakers.isEmpty) return null;

      // Calculate similarity scores
      double bestScore = 0;
      SpeakerModel? bestMatch;

      for (final speaker in registeredSpeakers) {
        final score = _calculateCosineSimilarity(embedding, speaker.embeddings!);
        if (score > bestScore) {
          bestScore = score;
          bestMatch = speaker;
        }
      }

      // Return match if confidence is high enough
      if (bestScore >= confidenceThreshold) {
        return bestMatch;
      }

      return null;
    } catch (e) {
      debugPrint('Auto-match failed: $e');
      return null;
    }
  }

  /// Get the audio sample cache (for testing)
  Map<String, String> get audioSampleCache => _audioSampleCache;

  /// Mark a speaker's audio sample as loading (for testing)
  void markAudioSampleLoading(String speakerId) {
    _loadingAudioSamples.add(speakerId);
    notifyListeners();
  }

  /// Validate speaker name format
  bool isValidSpeakerName(String name) {
    final trimmed = name.trim();
    return trimmed.isNotEmpty && trimmed.length >= 2 && trimmed.length <= 50;
  }

  /// Public accessor for cosine similarity (for testing)
  double calculateCosineSimilarity(List<double> a, List<double> b) {
    return _calculateCosineSimilarity(a, b);
  }

  /// Calculate cosine similarity between two embedding vectors
  double _calculateCosineSimilarity(List<double> a, List<double> b) {
    if (a.length != b.length || a.isEmpty) return 0;

    double dotProduct = 0;
    double normA = 0;
    double normB = 0;

    for (int i = 0; i < a.length; i++) {
      dotProduct += a[i] * b[i];
      normA += a[i] * a[i];
      normB += b[i] * b[i];
    }

    normA = normA > 0 ? math.sqrt(normA) : 1;
    normB = normB > 0 ? math.sqrt(normB) : 1;

    return dotProduct / (normA * normB);
  }

  /// Get confidence score for speaker matching (0-100%)
  Future<int> getSpeakerConfidence({
    required String speakerId,
    required List<double> embedding,
  }) async {
    try {
      final speaker = _speakers.firstWhere(
        (s) => s.id == speakerId && s.embeddings != null,
        orElse: () => SpeakerModel(
          id: '',
          sampleCount: 0,
          createdAt: DateTime.fromMillisecondsSinceEpoch(0),
          isRegistered: false,
        ),
      );

      if (speaker.id.isEmpty || speaker.embeddings == null) return 0;

      final similarity = _calculateCosineSimilarity(embedding, speaker.embeddings!);
      return (similarity.clamp(0.0, 1.0) * 100).toInt();
    } catch (e) {
      debugPrint('Failed to calculate confidence: $e');
      return 0;
    }
  }
}
