// Native platform (iOS/Android) implementation
import 'dart:io';
import 'package:path_provider/path_provider.dart';

Future<String> getRecordingPath() async {
  final directory = await getApplicationDocumentsDirectory();
  final timestamp = DateTime.now().millisecondsSinceEpoch;
  return '${directory.path}/recording_$timestamp.m4a';
}

Future<void> deleteFile(String path) async {
  final file = File(path);
  if (await file.exists()) {
    await file.delete();
  }
}

Future<bool> fileExists(String path) async {
  return await File(path).exists();
}
