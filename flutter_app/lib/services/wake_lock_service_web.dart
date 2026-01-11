// Web platform Wake Lock implementation
// Uses Screen Wake Lock API + NoSleep video trick for maximum compatibility
// ignore: avoid_web_libraries_in_flutter
import 'dart:js_interop';
import 'package:web/web.dart' as web;

web.WakeLockSentinel? _wakeLockSentinel;
web.HTMLVideoElement? _noSleepVideo;
bool _isSupported = false;
bool _noSleepEnabled = false;

// Base64 encoded minimal MP4 video (1 second, silent, tiny)
// This is the NoSleep.js trick - playing a video prevents screen from sleeping
const String _noSleepVideoBase64 =
  'data:video/mp4;base64,AAAAIGZ0eXBpc29tAAACAGlzb21pc28yYXZjMW1wNDEAAAAIZnJlZQAAA'
  'ENtZGF0AAACrgYF//+q3EXpvebZSLeWLNgg2SPu73gyNjQgLSBjb3JlIDE0MiByMjQ3OSBkZDc5'
  'YTYxIC0gSC4yNjQvTVBFRy00IEFWQyBjb2RlYyAtIENvcHlsZWZ0IDIwMDMtMjAxNCAtIGh0dHA'
  '6Ly93d3cudmlkZW9sYW4ub3JnL3gyNjQuaHRtbCAtIG9wdGlvbnM6IGNhYmFjPTEgcmVmPTMgZG'
  'VibG9jaz0xOjA6MCBhbmFseXNlPTB4MzoweDExMyBtZT1oZXggc3VibWU9NyBwc3k9MSBwc3lfcm'
  'Q9MS4wMDowLjAwIG1peGVkX3JlZj0xIG1lX3JhbmdlPTE2IGNocm9tYV9tZT0xIHRyZWxsaXM9M'
  'SA4eDhkY3Q9MSBjcW09MCBkZWFkem9uZT0yMSwxMSBmYXN0X3Bza2lwPTEgY2hyb21hX3FwX29m'
  'ZnNldD0tMiB0aHJlYWRzPTEgbG9va2FoZWFkX3RocmVhZHM9MSBzbGljZWRfdGhyZWFkcz0wIG5'
  'yPTEgZGVjaW1hdGU9MSBpbnRlcmxhY2VkPTAgYmx1cmF5X2NvbXBhdD0wIGNvbnN0cmFpbmVkX2'
  'ludHJhPTAgYmZyYW1lcz0zIGJfcHlyYW1pZD0yIGJfYWRhcHQ9MSBiX2JpYXM9MCBkaXJlY3Q9M'
  'SB3ZWlnaHRiPTEgb3Blbl9nb3A9MCB3ZWlnaHRwPTIga2V5aW50PTI1MCBrZXlpbnRfbWluPTI1'
  'IHNjZW5lY3V0PTQwIGludHJhX3JlZnJlc2g9MCByY19sb29rYWhlYWQ9NDAgcmM9Y3JmIG1idHJ'
  'lZT0xIGNyZj0yMy4wIHFjb21wPTAuNjAgcXBtaW49MCBxcG1heD02OSBxcHN0ZXA9NCBpcF9yYX'
  'Rpbz0xLjQwIGFxPTE6MS4wMACAAAABMmliYXVkAAAA0AVBMwAJ//C0JgAcTJmjKSrQJJhLZlkJ/'
  'n4w9DVnuQAAABNBn4J4hn/wAeXYMBIFC9oVdAAAAAtBnoRqPHCH/9oVdAAAAAtBnqVqPHCH/9oV'
  'dAAAAAtBnudqPHCH/9oVdAAAAAtBnylqPHCH/9oVdAAAAAtBn0tqPHCH/9oVdAAAAAtBn21qPHC'
  'H/9oVdAAAAAtBn49qPHCH/9oVdAAAAAtBn7FqPHCH/9oVdAAAAAtBn9NqPHCH/9oVdAAAAAtBn/'
  'VqPHCH/9oVdAAAARptb292AAAAbG12aGQAAAAAAAAAAAAAAAAAAAPoAAAAZAABAAABAAAAAAAAAA'
  'AAAAABAAAAAAAAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
  'AAAAAAAAAgAAABhpb2RzAAAAABCAgIAHAE/////+/wAAAiF0cmFrAAAAXHRraGQAAAAPAAAAAAAA'
  'AAAAAAABAAAAAAAAZAAAAAAAAAAAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAEAAAAABsAAAASAAAAAAACRlZHRzAAAAHGVsc3QAAAAAAAAAAQAAAGQAAAAAAAEAAAAAAZlt'
  'ZGlhAAAAIG1kaGQAAAAAAAAAAAAAAAAAADIAAAAEAFXEAAAAAAAtaGRscgAAAAAAAAAAdmlkZQAA'
  'AAAAAAAAAAAAAFZpZGVvSGFuZGxlcgAAAAFEbWluZgAAABR2bWhkAAAAAQAAAAAAAAAAAAAAJGRp'
  'bmYAAAAcZHJlZgAAAAAAAAABAAAADHVybCAAAAABAAAA5HN0YmwAAACYc3RzZAAAAAAAAAABAAAA'
  'iGF2YzEAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAABsAEgAEgAAABIAAAAAAAAAAEAAAAAAAAAAAAA'
  'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGP//AAAAMGF2Y0MBZAAK/+EAGGdkAAqs2UGUBNAA'
  'AAPpAADqYA8UKZYBAAZo6+PLIsAAAAAYc3R0cwAAAAAAAAABAAAAAgAABAAAAAAUc3RzcwAAAAAA'
  'AAABAAAAAQAAABhjdHRzAAAAAAAAAAEAAAACAAAIAAAAABxzdHNjAAAAAAAAAAEAAAABAAAAAgAA'
  'AAEAAAAkc3RzegAAAAAAAAAAAAAAAgAAA0YAAAAMAAAAFHN0Y28AAAAAAAAAAQAAADAAAABidWR0'
  'YQAAAFptZXRhAAAAAAAAACFoZGxyAAAAAAAAAABtZGlyYXBwbAAAAAAAAAAAAAAAAC1pbHN0AAAA'
  'Jal0b28AAAAdZGF0YQAAAAEAAAAATGF2ZjU2LjQwLjEwMQ==';

/// Check if Wake Lock API is supported
Future<bool> isWakeLockSupported() async {
  try {
    final navigator = web.window.navigator;
    _isSupported = navigator.wakeLock != null;
    return _isSupported;
  } catch (e) {
    _isSupported = false;
    return false;
  }
}

/// Create and setup NoSleep video element
void _setupNoSleepVideo() {
  if (_noSleepVideo != null) return;

  _noSleepVideo = web.document.createElement('video') as web.HTMLVideoElement;
  _noSleepVideo!.setAttribute('playsinline', '');
  _noSleepVideo!.setAttribute('muted', '');
  _noSleepVideo!.muted = true;
  _noSleepVideo!.loop = true;
  _noSleepVideo!.src = _noSleepVideoBase64;

  // Style to hide the video
  _noSleepVideo!.style.position = 'fixed';
  _noSleepVideo!.style.top = '-9999px';
  _noSleepVideo!.style.left = '-9999px';
  _noSleepVideo!.style.width = '1px';
  _noSleepVideo!.style.height = '1px';
  _noSleepVideo!.style.opacity = '0';

  web.document.body?.appendChild(_noSleepVideo!);
}

/// Enable NoSleep video playback
Future<bool> _enableNoSleep() async {
  try {
    _setupNoSleepVideo();

    if (_noSleepVideo == null) return false;

    await _noSleepVideo!.play().toDart;
    _noSleepEnabled = true;
    print('NoSleep: Video playback started - screen will stay on');
    return true;
  } catch (e) {
    print('NoSleep: Failed to start video playback: $e');
    return false;
  }
}

/// Disable NoSleep video playback
void _disableNoSleep() {
  if (_noSleepVideo != null && _noSleepEnabled) {
    _noSleepVideo!.pause();
    _noSleepEnabled = false;
    print('NoSleep: Video playback stopped');
  }
}

/// Request wake lock to prevent screen from turning off
/// Uses both Wake Lock API and NoSleep video trick for maximum compatibility
Future<bool> requestWakeLock() async {
  bool wakeLockSuccess = false;
  bool noSleepSuccess = false;

  // Try Wake Lock API first (modern browsers)
  try {
    if (!_isSupported) {
      await isWakeLockSupported();
    }

    if (_isSupported) {
      final navigator = web.window.navigator;
      final wakeLock = navigator.wakeLock;

      if (wakeLock != null) {
        _wakeLockSentinel = await wakeLock.request('screen').toDart;
        wakeLockSuccess = true;
        print('WakeLock: Screen Wake Lock API acquired');
      }
    }
  } catch (e) {
    print('WakeLock: Wake Lock API failed: $e');
  }

  // Always enable NoSleep video as backup (especially for iOS)
  noSleepSuccess = await _enableNoSleep();

  if (wakeLockSuccess || noSleepSuccess) {
    print('WakeLock: Screen will stay on (WakeLock=$wakeLockSuccess, NoSleep=$noSleepSuccess)');
    return true;
  }

  print('WakeLock: All methods failed - screen may turn off');
  return false;
}

/// Release wake lock
Future<void> releaseWakeLock() async {
  // Release Wake Lock API
  try {
    if (_wakeLockSentinel != null && !_wakeLockSentinel!.released) {
      await _wakeLockSentinel!.release().toDart;
      _wakeLockSentinel = null;
      print('WakeLock: Screen Wake Lock API released');
    }
  } catch (e) {
    print('WakeLock: Failed to release Wake Lock API: $e');
  }

  // Stop NoSleep video
  _disableNoSleep();
}

/// Check if wake lock is currently active
bool isWakeLockActive() {
  final wakeLockActive = _wakeLockSentinel != null && !_wakeLockSentinel!.released;
  return wakeLockActive || _noSleepEnabled;
}
