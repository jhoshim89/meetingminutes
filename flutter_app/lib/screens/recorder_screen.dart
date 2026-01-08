import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/recorder_provider.dart';
import '../providers/meeting_provider.dart';

class RecorderScreen extends StatefulWidget {
  const RecorderScreen({Key? key}) : super(key: key);

  @override
  State<RecorderScreen> createState() => _RecorderScreenState();
}

class _RecorderScreenState extends State<RecorderScreen> {
  final TextEditingController _titleController = TextEditingController();

  @override
  void dispose() {
    _titleController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('New Meeting'),
      ),
      body: Consumer<RecorderProvider>(
        builder: (context, recorderProvider, child) {
          return SingleChildScrollView(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                children: [
                  // Title Input (only show when not recording)
                  if (!recorderProvider.isRecording && !recorderProvider.isPaused)
                    TextField(
                      controller: _titleController,
                      decoration: InputDecoration(
                        labelText: 'Meeting Title',
                        hintText: 'Enter meeting title (optional)',
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                        prefixIcon: const Icon(Icons.title),
                      ),
                    ),

                  const SizedBox(height: 32),

                  // Recording Visualizer
                  _buildRecordingVisualizer(recorderProvider),

                  const SizedBox(height: 48),

                  // Recording Controls
                  _buildRecordingControls(context, recorderProvider),

                  const SizedBox(height: 24),

                  // Error Display
                  if (recorderProvider.error != null)
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.red.shade50,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.red.shade200),
                      ),
                      child: Row(
                        children: [
                          Icon(Icons.error_outline, color: Colors.red.shade700),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              recorderProvider.error!,
                              style: TextStyle(color: Colors.red.shade700),
                            ),
                          ),
                        ],
                      ),
                    ),

                  // Processing Indicator
                  if (recorderProvider.isProcessing) ...[
                    const SizedBox(height: 24),
                    const CircularProgressIndicator(),
                    const SizedBox(height: 16),
                    const Text(
                      'Uploading recording...',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Please wait while we process your meeting',
                      style: TextStyle(color: Colors.grey[600]),
                    ),
                  ],

                  // Success Message
                  if (recorderProvider.state == RecorderState.completed) ...[
                    const SizedBox(height: 24),
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: Colors.green.shade50,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.green.shade200),
                      ),
                      child: Column(
                        children: [
                          Icon(Icons.check_circle, color: Colors.green.shade700, size: 48),
                          const SizedBox(height: 16),
                          Text(
                            'Recording uploaded successfully!',
                            style: TextStyle(
                              color: Colors.green.shade700,
                              fontSize: 16,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'Your meeting is being processed',
                            style: TextStyle(color: Colors.grey[600]),
                          ),
                          const SizedBox(height: 16),
                          ElevatedButton(
                            onPressed: () {
                              recorderProvider.reset();
                              _titleController.clear();
                              // Refresh meetings list
                              context.read<MeetingProvider>().fetchMeetings();
                              // Navigate to home
                              DefaultTabController.of(context)?.animateTo(0);
                            },
                            child: const Text('View Meetings'),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildRecordingVisualizer(RecorderProvider provider) {
    final isActive = provider.isRecording;
    final amplitude = provider.amplitude;

    return Container(
      width: 200,
      height: 200,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: Border.all(
          color: isActive ? Colors.red : Colors.grey.shade300,
          width: 4,
        ),
      ),
      child: Stack(
        alignment: Alignment.center,
        children: [
          // Amplitude indicator
          if (isActive)
            Container(
              width: 200 * (0.5 + amplitude * 0.5),
              height: 200 * (0.5 + amplitude * 0.5),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.red.withOpacity(0.2),
              ),
            ),

          // Center content
          Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                _formatDuration(provider.duration),
                style: const TextStyle(
                  fontSize: 32,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                provider.isRecording
                    ? 'Recording...'
                    : provider.isPaused
                        ? 'Paused'
                        : 'Ready to record',
                style: TextStyle(
                  fontSize: 16,
                  color: Colors.grey[600],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildRecordingControls(BuildContext context, RecorderProvider provider) {
    if (provider.isProcessing || provider.state == RecorderState.completed) {
      return const SizedBox.shrink();
    }

    return Column(
      children: [
        // Main action button
        FloatingActionButton.large(
          onPressed: () => _handleMainAction(context, provider),
          backgroundColor: provider.isRecording || provider.isPaused ? Colors.red : Colors.blue,
          child: Icon(
            _getMainActionIcon(provider),
            size: 32,
          ),
        ),

        const SizedBox(height: 16),

        // Secondary actions
        if (provider.isRecording || provider.isPaused)
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Pause/Resume button
              ElevatedButton.icon(
                onPressed: () {
                  if (provider.isPaused) {
                    provider.resumeRecording();
                  } else {
                    provider.pauseRecording();
                  }
                },
                icon: Icon(provider.isPaused ? Icons.play_arrow : Icons.pause),
                label: Text(provider.isPaused ? 'Resume' : 'Pause'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                ),
              ),

              const SizedBox(width: 16),

              // Cancel button
              OutlinedButton.icon(
                onPressed: () {
                  _showCancelDialog(context, provider);
                },
                icon: const Icon(Icons.close),
                label: const Text('Cancel'),
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                ),
              ),
            ],
          ),
      ],
    );
  }

  IconData _getMainActionIcon(RecorderProvider provider) {
    if (provider.isRecording || provider.isPaused) {
      return Icons.stop;
    }
    return Icons.mic;
  }

  Future<void> _handleMainAction(BuildContext context, RecorderProvider provider) async {
    if (provider.isRecording || provider.isPaused) {
      // Stop recording
      final meeting = await provider.stopRecording();
      if (meeting != null) {
        _titleController.clear();
      }
    } else {
      // Start recording
      final hasPermission = await provider.checkPermission();
      if (!hasPermission) {
        if (context.mounted) {
          _showPermissionDialog(context);
        }
        return;
      }

      await provider.startRecording(
        title: _titleController.text.isEmpty ? null : _titleController.text,
      );
    }
  }

  void _showPermissionDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Microphone Permission Required'),
        content: const Text(
          'This app needs access to your microphone to record meetings. '
          'Please grant permission in your device settings.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  void _showCancelDialog(BuildContext context, RecorderProvider provider) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Cancel Recording?'),
        content: const Text(
          'Are you sure you want to cancel this recording? '
          'This action cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('No'),
          ),
          TextButton(
            onPressed: () {
              provider.cancelRecording();
              _titleController.clear();
              Navigator.pop(context);
            },
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Yes, Cancel'),
          ),
        ],
      ),
    );
  }

  String _formatDuration(Duration duration) {
    String twoDigits(int n) => n.toString().padLeft(2, '0');
    final hours = twoDigits(duration.inHours);
    final minutes = twoDigits(duration.inMinutes.remainder(60));
    final seconds = twoDigits(duration.inSeconds.remainder(60));
    return "$hours:$minutes:$seconds";
  }
}
