import 'dart:io';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../models/meeting_model.dart';
import '../models/speaker_model.dart';
import '../models/transcript_model.dart';

class SupabaseService {
  static final SupabaseService _instance = SupabaseService._internal();
  factory SupabaseService() => _instance;
  SupabaseService._internal();

  SupabaseClient get client => Supabase.instance.client;

  // Auth helpers
  User? get currentUser => client.auth.currentUser;
  String? get userId => currentUser?.id;
  bool get isAuthenticated => currentUser != null;

  // ====================
  // MEETINGS
  // ====================

  Future<List<MeetingModel>> getMeetings({
    int limit = 50,
    int offset = 0,
    String? status,
  }) async {
    try {
      var query = client.from('meetings').select().eq('user_id', userId!);

      if (status != null) {
        query = query.eq('status', status);
      }

      final response = await query
          .order('created_at', ascending: false)
          .range(offset, offset + limit - 1);

      return (response as List)
          .map((json) => MeetingModel.fromJson(json))
          .toList();
    } catch (e) {
      throw Exception('Failed to fetch meetings: $e');
    }
  }

  Future<MeetingModel> getMeetingById(String meetingId) async {
    try {
      final response = await client
          .from('meetings')
          .select()
          .eq('id', meetingId)
          .eq('user_id', userId!)
          .single();

      return MeetingModel.fromJson(response);
    } catch (e) {
      throw Exception('Failed to fetch meeting: $e');
    }
  }

  Future<MeetingModel> createMeeting({
    required String title,
    String? audioUrl,
    Map<String, dynamic>? metadata,
  }) async {
    try {
      final response = await client.from('meetings').insert({
        'user_id': userId,
        'title': title,
        'duration_seconds': 0,
        'status': 'recording',
        'audio_url': audioUrl,
        'metadata': metadata,
      }).select().single();

      return MeetingModel.fromJson(response);
    } catch (e) {
      throw Exception('Failed to create meeting: $e');
    }
  }

  Future<MeetingModel> updateMeeting(String meetingId, {
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
      final updates = <String, dynamic>{
        'updated_at': DateTime.now().toIso8601String(),
      };

      if (title != null) updates['title'] = title;
      if (durationSeconds != null) updates['duration_seconds'] = durationSeconds;
      if (status != null) updates['status'] = status;
      if (audioUrl != null) updates['audio_url'] = audioUrl;
      if (transcriptUrl != null) updates['transcript_url'] = transcriptUrl;
      if (summary != null) updates['summary'] = summary;
      if (speakerCount != null) updates['speaker_count'] = speakerCount;
      if (metadata != null) updates['metadata'] = metadata;

      final response = await client
          .from('meetings')
          .update(updates)
          .eq('id', meetingId)
          .eq('user_id', userId!)
          .select()
          .single();

      return MeetingModel.fromJson(response);
    } catch (e) {
      throw Exception('Failed to update meeting: $e');
    }
  }

  Future<void> deleteMeeting(String meetingId) async {
    try {
      await client
          .from('meetings')
          .delete()
          .eq('id', meetingId)
          .eq('user_id', userId!);
    } catch (e) {
      throw Exception('Failed to delete meeting: $e');
    }
  }

  Future<List<MeetingModel>> searchMeetings(String query) async {
    try {
      final response = await client
          .from('meetings')
          .select()
          .eq('user_id', userId!)
          .ilike('title', '%$query%')
          .order('created_at', ascending: false)
          .limit(20);

      return (response as List)
          .map((json) => MeetingModel.fromJson(json))
          .toList();
    } catch (e) {
      throw Exception('Failed to search meetings: $e');
    }
  }

  // ====================
  // SPEAKERS
  // ====================

  Future<List<SpeakerModel>> getSpeakers({
    bool? isRegistered,
  }) async {
    try {
      var query = client.from('speakers').select().eq('user_id', userId!);

      if (isRegistered != null) {
        query = query.eq('is_registered', isRegistered);
      }

      final response = await query.order('created_at', ascending: false);

      return (response as List)
          .map((json) => SpeakerModel.fromJson(json))
          .toList();
    } catch (e) {
      throw Exception('Failed to fetch speakers: $e');
    }
  }

  Future<SpeakerModel> getSpeakerById(String speakerId) async {
    try {
      final response = await client
          .from('speakers')
          .select()
          .eq('id', speakerId)
          .eq('user_id', userId!)
          .single();

      return SpeakerModel.fromJson(response);
    } catch (e) {
      throw Exception('Failed to fetch speaker: $e');
    }
  }

  Future<SpeakerModel> updateSpeaker(
    String speakerId, {
    String? name,
    bool? isRegistered,
    Map<String, dynamic>? metadata,
  }) async {
    try {
      final updates = <String, dynamic>{
        'updated_at': DateTime.now().toIso8601String(),
      };

      if (name != null) updates['name'] = name;
      if (isRegistered != null) updates['is_registered'] = isRegistered;
      if (metadata != null) updates['metadata'] = metadata;

      final response = await client
          .from('speakers')
          .update(updates)
          .eq('id', speakerId)
          .eq('user_id', userId!)
          .select()
          .single();

      return SpeakerModel.fromJson(response);
    } catch (e) {
      throw Exception('Failed to update speaker: $e');
    }
  }

  // ====================
  // TRANSCRIPTS
  // ====================

  Future<List<TranscriptModel>> getTranscripts(String meetingId) async {
    try {
      final response = await client
          .from('transcripts')
          .select()
          .eq('meeting_id', meetingId)
          .order('start_time', ascending: true);

      return (response as List)
          .map((json) => TranscriptModel.fromJson(json))
          .toList();
    } catch (e) {
      throw Exception('Failed to fetch transcripts: $e');
    }
  }

  // ====================
  // STORAGE
  // ====================

  Future<String> uploadAudio(String filePath, String meetingId) async {
    try {
      final file = File(filePath);
      if (!await file.exists()) {
        throw Exception('Audio file not found');
      }

      final fileName = '$meetingId-${DateTime.now().millisecondsSinceEpoch}.m4a';
      final storagePath = 'audio/$userId/$fileName';

      await client.storage.from('meetings').upload(
        storagePath,
        file,
        fileOptions: const FileOptions(
          contentType: 'audio/m4a',
        ),
      );

      final publicUrl = client.storage.from('meetings').getPublicUrl(storagePath);
      return publicUrl;
    } catch (e) {
      throw Exception('Failed to upload audio: $e');
    }
  }

  Future<void> deleteAudio(String audioUrl) async {
    try {
      // Extract path from URL
      final uri = Uri.parse(audioUrl);
      final pathSegments = uri.pathSegments;
      final storagePath = pathSegments.sublist(pathSegments.indexOf('meetings') + 1).join('/');

      await client.storage.from('meetings').remove([storagePath]);
    } catch (e) {
      throw Exception('Failed to delete audio: $e');
    }
  }

  /// Get audio sample URL for a speaker
  /// Returns a signed URL for the speaker's audio sample
  String getAudioSampleUrl(String speakerId) {
    try {
      // Storage path format: audio/{user_id}/{speaker_id}_sample.wav
      final storagePath = 'audio/$userId/${speakerId}_sample.wav';

      // Generate signed URL with 7 day expiry
      final signedUrl = client.storage.from('meetings').getPublicUrl(
        storagePath,
      );

      return signedUrl;
    } catch (e) {
      throw Exception('Failed to get audio sample URL: $e');
    }
  }

  /// Download audio sample file to temporary location
  /// Returns the file path
  Future<String> downloadAudioSample(String speakerId) async {
    try {
      final storagePath = 'audio/$userId/${speakerId}_sample.wav';
      final bytes = await client.storage.from('meetings').download(storagePath);

      // Save to temporary directory
      final tempDir = Directory.systemTemp;
      final tempFile = File('${tempDir.path}/speaker_${speakerId}_sample.wav');
      await tempFile.writeAsBytes(bytes);

      return tempFile.path;
    } catch (e) {
      throw Exception('Failed to download audio sample: $e');
    }
  }

  // ====================
  // AUTH
  // ====================

  Future<void> signInAnonymously() async {
    try {
      await client.auth.signInAnonymously();
    } catch (e) {
      throw Exception('Failed to sign in: $e');
    }
  }

  Future<void> signOut() async {
    try {
      await client.auth.signOut();
    } catch (e) {
      throw Exception('Failed to sign out: $e');
    }
  }
}
