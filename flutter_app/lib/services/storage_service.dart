import 'dart:typed_data';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:supabase_flutter/supabase_flutter.dart';
import '../models/meeting_model.dart';

// Platform-specific imports
import 'storage_service_io.dart' if (dart.library.html) 'storage_service_web.dart' as platform;

/// Upload progress callback
typedef UploadProgressCallback = void Function(int sent, int total);

/// Upload result with metadata
class UploadResult {
  final String publicUrl;
  final String storagePath;
  final int fileSize;
  final DateTime uploadedAt;

  UploadResult({
    required this.publicUrl,
    required this.storagePath,
    required this.fileSize,
    required this.uploadedAt,
  });
}

/// Service for managing Supabase Storage operations
/// Handles audio file uploads with retry logic and progress tracking
class StorageService {
  static final StorageService _instance = StorageService._internal();
  factory StorageService() => _instance;
  StorageService._internal();

  final _client = Supabase.instance.client;

  // Storage bucket names
  static const String recordingsBucket = 'recordings';
  static const String meetingsBucket = 'meetings';

  /// Upload audio file to Supabase Storage with retry logic
  ///
  /// Path structure: users/{user_id}/meetings/{meeting_id}/{timestamp}.wav
  ///
  /// Args:
  ///   filePath: Local file path
  ///   meetingId: Meeting identifier
  ///   onProgress: Optional progress callback
  ///   maxRetries: Maximum retry attempts (default: 3)
  ///
  /// Returns:
  ///   UploadResult with public URL and metadata
  ///
  /// Throws:
  ///   Exception if upload fails after all retries
  Future<UploadResult> uploadAudioFile({
    required String filePath,
    required String meetingId,
    UploadProgressCallback? onProgress,
    int maxRetries = 3,
  }) async {
    // Get file bytes and info using platform-specific implementation
    final fileInfo = await platform.getFileInfo(filePath);
    final Uint8List fileBytes = fileInfo.bytes;
    final int fileSize = fileInfo.size;
    final String fileExtension = fileInfo.extension;

    // Validate file size (max 500MB)
    if (fileSize > 500 * 1024 * 1024) {
      throw Exception('File size exceeds maximum limit of 500MB');
    }

    if (fileSize == 0) {
      throw Exception('Audio file is empty');
    }

    final userId = _client.auth.currentUser?.id;
    if (userId == null) {
      throw Exception('User not authenticated');
    }

    final timestamp = DateTime.now().millisecondsSinceEpoch;
    final storagePath = 'users/$userId/meetings/$meetingId/$timestamp.$fileExtension';

    Exception? lastError;

    // Retry loop
    for (int attempt = 0; attempt < maxRetries; attempt++) {
      try {
        if (attempt > 0) {
          // Exponential backoff: 1s, 2s, 4s
          final delaySeconds = (1 << attempt);
          await Future.delayed(Duration(seconds: delaySeconds));
        }

        // Upload file bytes (works on both web and native)
        final uploadResponse = await _client.storage.from(recordingsBucket).uploadBinary(
          storagePath,
          fileBytes,
          fileOptions: FileOptions(
            contentType: _getContentType(fileExtension),
            upsert: false,
          ),
        );

        // Get public URL
        final publicUrl = _client.storage.from(recordingsBucket).getPublicUrl(storagePath);

        return UploadResult(
          publicUrl: publicUrl,
          storagePath: storagePath,
          fileSize: fileSize,
          uploadedAt: DateTime.now(),
        );

      } on StorageException catch (e) {
        lastError = Exception('Storage error: ${e.message}');

        // Don't retry on certain errors
        if (e.statusCode == '400' || e.statusCode == '403') {
          throw lastError!;
        }
      } catch (e) {
        lastError = Exception('Upload failed: $e');
      }
    }

    // All retries exhausted
    throw Exception('Upload failed after $maxRetries attempts. Last error: $lastError');
  }

  /// Delete audio file from storage
  ///
  /// Args:
  ///   storagePath: Path in storage bucket
  ///
  /// Throws:
  ///   Exception if deletion fails
  Future<void> deleteAudioFile(String storagePath) async {
    try {
      await _client.storage.from(recordingsBucket).remove([storagePath]);
    } on StorageException catch (e) {
      throw Exception('Failed to delete audio file: ${e.message}');
    } catch (e) {
      throw Exception('Failed to delete audio file: $e');
    }
  }

  /// Delete audio file by meeting ID
  /// Queries meeting record to get storage path, then deletes
  Future<void> deleteAudioByMeetingId(String meetingId) async {
    try {
      // Get meeting to find storage path
      final response = await _client
          .from('meetings')
          .select('audio_url, metadata')
          .eq('id', meetingId)
          .single();

      final metadata = response['metadata'] as Map<String, dynamic>?;
      final storagePath = metadata?['storage_path'] as String?;

      if (storagePath != null) {
        await deleteAudioFile(storagePath);
      }
    } catch (e) {
      throw Exception('Failed to delete audio for meeting: $e');
    }
  }

  /// Get signed URL for private file access
  ///
  /// Args:
  ///   storagePath: Path in storage bucket
  ///   expiresIn: Expiration time in seconds (default: 1 hour)
  ///
  /// Returns:
  ///   Signed URL string
  Future<String> getSignedUrl(
    String storagePath, {
    int expiresIn = 3600,
  }) async {
    try {
      final signedUrl = await _client.storage
          .from(recordingsBucket)
          .createSignedUrl(storagePath, expiresIn);

      return signedUrl;
    } on StorageException catch (e) {
      throw Exception('Failed to create signed URL: ${e.message}');
    } catch (e) {
      throw Exception('Failed to create signed URL: $e');
    }
  }

  /// Get file metadata from storage
  ///
  /// Args:
  ///   storagePath: Path in storage bucket
  ///
  /// Returns:
  ///   Map with file metadata
  Future<Map<String, dynamic>> getFileMetadata(String storagePath) async {
    try {
      final files = await _client.storage
          .from(recordingsBucket)
          .list(path: storagePath);

      if (files.isEmpty) {
        throw Exception('File not found');
      }

      return {
        'name': files.first.name,
        'size': files.first.metadata?['size'],
        'mimetype': files.first.metadata?['mimetype'],
        'lastModified': files.first.metadata?['lastModified'],
      };
    } catch (e) {
      throw Exception('Failed to get file metadata: $e');
    }
  }

  /// Check if storage bucket exists and is accessible
  Future<bool> healthCheck() async {
    try {
      await _client.storage.from(recordingsBucket).list(path: '');
      return true;
    } catch (e) {
      return false;
    }
  }

  /// Get content type from file extension
  String _getContentType(String extension) {
    switch (extension.toLowerCase()) {
      case 'wav':
        return 'audio/wav';
      case 'm4a':
        return 'audio/m4a';
      case 'mp3':
        return 'audio/mpeg';
      case 'aac':
        return 'audio/aac';
      case 'ogg':
        return 'audio/ogg';
      case 'webm':
        return 'audio/webm';
      case 'opus':
        return 'audio/opus';
      default:
        return 'audio/mpeg';
    }
  }
}
