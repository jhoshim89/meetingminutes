import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import '../lib/models/speaker_model.dart';
import '../lib/providers/speaker_provider.dart';
import '../lib/services/supabase_service.dart';

// Mock classes
class MockSupabaseService extends Mock implements SupabaseService {}

void main() {
  group('SpeakerProvider Tests', () {
    late SpeakerProvider speakerProvider;
    late MockSupabaseService mockSupabaseService;

    setUp(() {
      mockSupabaseService = MockSupabaseService();
      speakerProvider = SpeakerProvider();
    });

    test('should calculate cosine similarity correctly', () {
      // Test vectors
      final a = [1.0, 0.0, 0.0];
      final b = [1.0, 0.0, 0.0];

      final similarity = speakerProvider.calculateCosineSimilarity(a, b);

      expect(similarity, equals(1.0));
    });

    test('should calculate cosine similarity for orthogonal vectors', () {
      final a = [1.0, 0.0, 0.0];
      final b = [0.0, 1.0, 0.0];

      final similarity = speakerProvider.calculateCosineSimilarity(a, b);

      expect(similarity, closeTo(0.0, 0.01));
    });

    test('should handle empty embedding list in auto-match', () async {
      final result = await speakerProvider.autoMatchSpeaker(embedding: []);

      expect(result, isNull);
    });

    test('should return null if no registered speakers exist', () async {
      speakerProvider.reset();

      final result = await speakerProvider.autoMatchSpeaker(
        embedding: [0.1, 0.2, 0.3],
      );

      expect(result, isNull);
    });

    test('should cache audio sample URLs', () async {
      final speakerId = 'test-speaker-123';

      // First call
      final url1 = await speakerProvider.getAudioSampleUrl(speakerId);

      // Second call should return cached
      final url2 = await speakerProvider.getAudioSampleUrl(speakerId);

      // Should be the same
      expect(url1, equals(url2));
    });

    test('should clear audio sample cache', () {
      speakerProvider.clearAudioSampleCache();

      // Cache should be empty
      expect(speakerProvider.audioSampleCache.isEmpty, isTrue);
    });

    test('should prevent duplicate audio sample loading', () async {
      final speakerId = 'test-speaker-456';

      // Mark as loading
      speakerProvider.markAudioSampleLoading(speakerId);

      expect(
        speakerProvider.isLoadingAudioSample(speakerId),
        isTrue,
      );
    });

    test('should validate speaker name correctly', () {
      // Valid names
      expect(speakerProvider.isValidSpeakerName('John Doe'), isTrue);
      expect(speakerProvider.isValidSpeakerName('Dr. Smith'), isTrue);

      // Invalid names
      expect(speakerProvider.isValidSpeakerName(''), isFalse);
      expect(speakerProvider.isValidSpeakerName('J'), isFalse); // Too short
      expect(speakerProvider.isValidSpeakerName('A' * 51), isFalse); // Too long
    });

    test('should calculate speaker confidence correctly', () async {
      // Create test speaker with embeddings
      final testSpeaker = SpeakerModel(
        id: 'test-speaker-001',
        name: 'John Doe',
        embeddings: [1.0, 0.0, 0.0, 0.0],
        sampleCount: 5,
        createdAt: DateTime.now(),
        isRegistered: true,
      );

      // Calculate confidence
      final confidence = await speakerProvider.getSpeakerConfidence(
        speakerId: testSpeaker.id,
        embedding: [1.0, 0.0, 0.0, 0.0],
      );

      // Should be 100 for identical vectors
      expect(confidence, equals(100));
    });

    test('should reset provider state correctly', () {
      speakerProvider.reset();

      expect(speakerProvider.speakers.isEmpty, isTrue);
      expect(speakerProvider.unregisteredSpeakers.isEmpty, isTrue);
      expect(speakerProvider.error, isNull);
    });
  });

  group('SpeakerModel Tests', () {
    test('should parse speaker from JSON', () {
      final json = {
        'id': 'speaker-123',
        'name': 'John Doe',
        'user_id': 'user-456',
        'sample_count': 5,
        'is_registered': true,
        'created_at': DateTime.now().toIso8601String(),
        'embeddings': [0.1, 0.2, 0.3],
      };

      final speaker = SpeakerModel.fromJson(json);

      expect(speaker.id, equals('speaker-123'));
      expect(speaker.name, equals('John Doe'));
      expect(speaker.isRegistered, isTrue);
      expect(speaker.sampleCount, equals(5));
    });

    test('should convert speaker to JSON', () {
      final speaker = SpeakerModel(
        id: 'speaker-123',
        name: 'John Doe',
        sampleCount: 5,
        createdAt: DateTime.now(),
        isRegistered: true,
      );

      final json = speaker.toJson();

      expect(json['id'], equals('speaker-123'));
      expect(json['name'], equals('John Doe'));
      expect(json['is_registered'], isTrue);
    });

    test('should handle copyWith correctly', () {
      final original = SpeakerModel(
        id: 'speaker-123',
        name: 'John Doe',
        sampleCount: 5,
        createdAt: DateTime.now(),
        isRegistered: false,
      );

      final updated = original.copyWith(
        name: 'Jane Doe',
        isRegistered: true,
      );

      expect(updated.id, equals(original.id));
      expect(updated.name, equals('Jane Doe'));
      expect(updated.isRegistered, isTrue);
    });

    test('should return display name correctly', () {
      final registeredSpeaker = SpeakerModel(
        id: 'speaker-123',
        name: 'John Doe',
        sampleCount: 5,
        createdAt: DateTime.now(),
        isRegistered: true,
      );

      final unregisteredSpeaker = SpeakerModel(
        id: 'speaker-456',
        name: null,
        sampleCount: 3,
        createdAt: DateTime.now(),
        isRegistered: false,
      );

      expect(registeredSpeaker.displayName, equals('John Doe'));
      expect(unregisteredSpeaker.displayName, equals('Unknown Speaker'));
    });
  });

  group('Covariance Similarity Tests', () {
    late SpeakerProvider speakerProvider;

    setUp(() {
      speakerProvider = SpeakerProvider();
    });

    test('should calculate high similarity for same vectors', () {
      final a = [0.5, 0.5, 0.5, 0.5];
      final b = [0.5, 0.5, 0.5, 0.5];

      final similarity = speakerProvider.calculateCosineSimilarity(a, b);

      expect(similarity, closeTo(1.0, 0.01));
    });

    test('should calculate low similarity for different vectors', () {
      final a = [1.0, 0.0, 0.0, 0.0];
      final b = [0.0, 1.0, 0.0, 0.0];

      final similarity = speakerProvider.calculateCosineSimilarity(a, b);

      expect(similarity, closeTo(0.0, 0.01));
    });

    test('should handle vector normalization', () {
      final a = [1.0, 1.0];
      final b = [2.0, 2.0]; // Normalized equivalent

      final similarity = speakerProvider.calculateCosineSimilarity(a, b);

      expect(similarity, closeTo(1.0, 0.01));
    });
  });

  group('Audio Service Tests', () {
    // AudioService 테스트는 실제 just_audio 라이브러리 통합 필요
    // Mock AudioPlayer를 사용하여 테스트 가능

    test('should format duration correctly', () {
      final duration = Duration(minutes: 1, seconds: 30);
      final formatted = _formatDuration(duration);

      expect(formatted, equals('01:30'));
    });

    test('should format short duration', () {
      final duration = Duration(seconds: 5);
      final formatted = _formatDuration(duration);

      expect(formatted, equals('00:05'));
    });
  });
}

/// Helper function to format duration
String _formatDuration(Duration duration) {
  String twoDigits(int n) => n.toString().padLeft(2, '0');
  final minutes = twoDigits(duration.inMinutes.remainder(60));
  final seconds = twoDigits(duration.inSeconds.remainder(60));
  return '$minutes:$seconds';
}
