// Web platform stub implementation
// These functions are not used on web, but needed for compilation

Future<String> getRecordingPath() async {
  // Web doesn't use file paths - returns empty string
  // Recording uses Blob URL instead
  return '';
}

Future<void> deleteFile(String path) async {
  // Web doesn't support file deletion
  // Blob URLs are garbage collected automatically
}

Future<bool> fileExists(String path) async {
  // Web doesn't support file system checks
  return false;
}
