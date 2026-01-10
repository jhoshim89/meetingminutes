// Web platform implementation
import 'dart:typed_data';
// ignore: avoid_web_libraries_in_flutter
import 'dart:html' as html;

/// File information for upload
class FileInfo {
  final Uint8List bytes;
  final int size;
  final String extension;

  FileInfo({
    required this.bytes,
    required this.size,
    required this.extension,
  });
}

/// Get file info from Blob URL (web platform)
/// On web, the filePath is actually a Blob URL like "blob:https://..."
Future<FileInfo> getFileInfo(String blobUrl) async {
  try {
    // Fetch blob data from URL
    final request = await html.HttpRequest.request(
      blobUrl,
      responseType: 'arraybuffer',
    );

    final bytes = Uint8List.view(request.response as ByteBuffer);

    // Determine extension based on recording format
    // Web uses opus/webm format
    String extension = 'webm';

    // Try to extract extension from blob URL if available
    if (blobUrl.contains('.')) {
      final urlExtension = blobUrl.split('.').last.split('?').first;
      if (['webm', 'opus', 'ogg', 'wav', 'mp3'].contains(urlExtension)) {
        extension = urlExtension;
      }
    }

    return FileInfo(
      bytes: bytes,
      size: bytes.length,
      extension: extension,
    );
  } catch (e) {
    throw Exception('Failed to read audio file from blob URL: $e');
  }
}
