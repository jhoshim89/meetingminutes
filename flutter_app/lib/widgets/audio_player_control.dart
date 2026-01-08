import 'package:flutter/material.dart';
import '../services/audio_service.dart';

class AudioPlayerControl extends StatefulWidget {
  final String audioUrl;
  final VoidCallback? onPlayStateChanged;
  final bool showWaveform;

  const AudioPlayerControl({
    Key? key,
    required this.audioUrl,
    this.onPlayStateChanged,
    this.showWaveform = false,
  }) : super(key: key);

  @override
  State<AudioPlayerControl> createState() => _AudioPlayerControlState();
}

class _AudioPlayerControlState extends State<AudioPlayerControl> {
  final AudioService _audioService = AudioService();
  bool _isPlaying = false;
  Duration _position = Duration.zero;
  Duration _duration = Duration.zero;

  @override
  void initState() {
    super.initState();
    _setupAudioListeners();
  }

  void _setupAudioListeners() {
    _audioService.playingStream.listen((isPlaying) {
      if (mounted) {
        setState(() {
          _isPlaying = isPlaying;
        });
      }
    });

    _audioService.positionStream.listen((position) {
      if (mounted) {
        setState(() {
          _position = position;
        });
      }
    });

    _audioService.durationStream.listen((duration) {
      if (mounted) {
        setState(() {
          _duration = duration;
        });
      }
    });
  }

  Future<void> _togglePlayback() async {
    try {
      if (_isPlaying) {
        await _audioService.pause();
      } else {
        if (_position >= _duration && _duration > Duration.zero) {
          // Restart playback if at end
          await _audioService.stop();
        }
        await _audioService.playAudio(widget.audioUrl);
      }
      widget.onPlayStateChanged?.call();
    } catch (e) {
      _showError('Failed to control audio: $e');
    }
  }

  Future<void> _onSliderChanged(double value) async {
    try {
      final position = Duration(milliseconds: value.toInt());
      await _audioService.seek(position);
    } catch (e) {
      _showError('Failed to seek: $e');
    }
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
      ),
    );
  }

  String _formatDuration(Duration duration) {
    String twoDigits(int n) => n.toString().padLeft(2, '0');
    final minutes = twoDigits(duration.inMinutes.remainder(60));
    final seconds = twoDigits(duration.inSeconds.remainder(60));
    return '$minutes:$seconds';
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Container(
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
      decoration: BoxDecoration(
        color: isDark ? Colors.grey[800] : Colors.grey[100],
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        children: [
          // Play button and time display
          Row(
            children: [
              // Play/Pause button
              Material(
                color: Colors.transparent,
                child: InkWell(
                  onTap: _togglePlayback,
                  borderRadius: BorderRadius.circular(24),
                  child: Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: Colors.blue.withOpacity(0.1),
                    ),
                    child: Icon(
                      _isPlaying ? Icons.pause : Icons.play_arrow,
                      color: Colors.blue,
                      size: 24,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 12),

              // Duration display
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Progress bar
                    ClipRRect(
                      borderRadius: BorderRadius.circular(4),
                      child: LinearProgressIndicator(
                        value: _duration.inMilliseconds > 0
                            ? _position.inMilliseconds / _duration.inMilliseconds
                            : 0,
                        minHeight: 4,
                        backgroundColor: isDark
                            ? Colors.grey[700]
                            : Colors.grey[300],
                        valueColor: const AlwaysStoppedAnimation<Color>(
                          Colors.blue,
                        ),
                      ),
                    ),
                    const SizedBox(height: 6),

                    // Time labels
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          _formatDuration(_position),
                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.grey[600],
                            fontFeatures: const [
                              FontFeature.tabularFigures(),
                            ],
                          ),
                        ),
                        Text(
                          _formatDuration(_duration),
                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.grey[600],
                            fontFeatures: const [
                              FontFeature.tabularFigures(),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),

          // Optional: Waveform visualization (simplified version)
          if (widget.showWaveform) ...[
            const SizedBox(height: 12),
            _buildSimpleWaveform(),
          ],
        ],
      ),
    );
  }

  Widget _buildSimpleWaveform() {
    return Row(
      children: List.generate(
        20,
        (index) {
          final progress = _duration.inMilliseconds > 0
              ? _position.inMilliseconds / _duration.inMilliseconds
              : 0;
          final isPlayed = index / 20 <= progress;

          return Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 1),
              child: Container(
                height: 20,
                decoration: BoxDecoration(
                  color: isPlayed ? Colors.blue : Colors.grey[300],
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  @override
  void dispose() {
    super.dispose();
  }
}
