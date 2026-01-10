// Native platform (iOS/Android/Desktop) implementation
import 'dart:io';
import 'dart:typed_data';

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

/// Get file info from local file path (native platforms)
Future<FileInfo> getFileInfo(String filePath) async {
  final file = File(filePath);

  // Verify file exists
  if (!await file.exists()) {
    throw Exception('Audio file not found at: $filePath');
  }

  final bytes = await file.readAsBytes();
  final extension = filePath.split('.').last;

  return FileInfo(
    bytes: bytes,
    size: bytes.length,
    extension: extension,
  );
}
