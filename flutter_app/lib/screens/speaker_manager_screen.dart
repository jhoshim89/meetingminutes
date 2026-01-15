import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/speaker_provider.dart';
import '../models/speaker_model.dart';
import '../widgets/unregistered_speaker_tile.dart';
import '../widgets/speaker_input_form.dart';
import '../widgets/audio_player_control.dart';

class SpeakerManagerScreen extends StatefulWidget {
  const SpeakerManagerScreen({Key? key}) : super(key: key);

  @override
  State<SpeakerManagerScreen> createState() => _SpeakerManagerScreenState();
}

class _SpeakerManagerScreenState extends State<SpeakerManagerScreen> {
  final TextEditingController _nameController = TextEditingController();
  SpeakerModel? _currentSpeaker;
  bool _isRegistering = false;
  String? _audioSampleUrl;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<SpeakerProvider>().fetchUnregisteredSpeakers();
    });
  }

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  /// Fetch audio sample for a speaker
  Future<void> _loadAudioSample(String speakerId) async {
    final provider = context.read<SpeakerProvider>();
    final audioUrl = await provider.getAudioSampleUrl(speakerId);

    if (mounted) {
      setState(() {
        _audioSampleUrl = audioUrl;
      });
    }
  }

  /// Show registration dialog
  void _showRegistrationDialog(BuildContext context, SpeakerModel speaker) {
    _nameController.clear();
    _currentSpeaker = speaker;
    _audioSampleUrl = null;

    // Load audio sample in background
    _loadAudioSample(speaker.id);

    showDialog(
      context: context,
      builder: (dialogContext) => _buildRegistrationDialog(dialogContext, speaker),
      barrierDismissible: !_isRegistering,
    );
  }

  /// Build registration dialog
  Widget _buildRegistrationDialog(BuildContext dialogContext, SpeakerModel speaker) {
    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header with speaker info
              Row(
                children: [
                  Container(
                    width: 56,
                    height: 56,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: [
                          Colors.blue.withOpacity(0.8),
                          Colors.purple.withOpacity(0.8),
                        ],
                      ),
                    ),
                    child: const Center(
                      child: Icon(
                        Icons.person,
                        color: Colors.white,
                        size: 28,
                      ),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Register Speaker',
                          style:
                              Theme.of(context).textTheme.titleLarge?.copyWith(
                                    fontWeight: FontWeight.bold,
                                  ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '${speaker.sampleCount} voice samples detected',
                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.grey[600],
                          ),
                        ),
                      ],
                    ),
                  ),
                  if (!_isRegistering)
                    IconButton(
                      onPressed: () => Navigator.pop(dialogContext),
                      icon: const Icon(Icons.close),
                      iconSize: 20,
                    ),
                ],
              ),
              const SizedBox(height: 24),

              // Audio Player (Added functionality)
              if (_audioSampleUrl != null) ...[
                Text(
                  'Listen to voice sample:',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: Colors.grey[700],
                      ),
                ),
                const SizedBox(height: 8),
                AudioPlayerControl(
                  audioUrl: _audioSampleUrl!,
                  showWaveform: true,
                ),
                const SizedBox(height: 24),
              ] else if (_audioSampleUrl == null) ...[
                 // Loading indicator or no audio message
                 Container(
                   padding: const EdgeInsets.symmetric(vertical: 12),
                   alignment: Alignment.center,
                   child: const Row(
                     mainAxisAlignment: MainAxisAlignment.center,
                     children: [
                        SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
                        SizedBox(width: 12),
                        Text('Loading audio sample...', style: TextStyle(color: Colors.grey, fontSize: 12)),
                     ],
                   )
                 ),
                 const SizedBox(height: 24),
              ],

              // Name input form
              SpeakerInputForm(
                nameController: _nameController,
                isLoading: _isRegistering,
                onSave: () => _registerSpeaker(context, speaker.id),
                onCancel: () {
                  _nameController.clear();
                  Navigator.pop(dialogContext);
                },
              ),

              const SizedBox(height: 16),

              // Divider with info
              Container(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Row(
                  children: [
                    Expanded(
                      child: Divider(color: Colors.grey[300]),
                    ),
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 8),
                      child: Text(
                        'Tip',
                        style: TextStyle(
                          fontSize: 11,
                          color: Colors.grey[600],
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                    Expanded(
                      child: Divider(color: Colors.grey[300]),
                    ),
                  ],
                ),
              ),

              // Help text
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.blue.withOpacity(0.05),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    Icon(
                      Icons.info_outline,
                      size: 16,
                      color: Colors.blue,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Once registered, this speaker will be automatically recognized in future meetings.',
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.blue[700],
                          height: 1.4,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// Register speaker with name
  Future<void> _registerSpeaker(
      BuildContext context, String speakerId) async {
    final name = _nameController.text.trim();

    if (name.isEmpty) {
      _showError(context, 'Please enter a speaker name');
      return;
    }

    setState(() {
      _isRegistering = true;
    });

    try {
      final provider = context.read<SpeakerProvider>();
      final success = await provider.registerSpeaker(speakerId, name);

      if (mounted) {
        if (success) {
          Navigator.pop(context);
          _showSuccess(context, '$name registered successfully!');
          _nameController.clear();
          _currentSpeaker = null;
        } else {
          _showError(context,
              'Failed to register speaker: ${provider.error}');
        }
      }
    } catch (e) {
      if (mounted) {
        _showError(context, 'Error: $e');
      }
    } finally {
      if (mounted) {
        setState(() {
          _isRegistering = false;
        });
      }
    }
  }

  void _showError(BuildContext context, String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
        duration: const Duration(seconds: 3),
      ),
    );
  }

  void _showSuccess(BuildContext context, String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(
              Icons.check_circle,
              color: Colors.white,
              size: 20,
            ),
            const SizedBox(width: 12),
            Text(message),
          ],
        ),
        backgroundColor: Colors.green,
        duration: const Duration(seconds: 2),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Speaker Manager'),
        elevation: 1,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              context.read<SpeakerProvider>().fetchUnregisteredSpeakers();
            },
            tooltip: 'Refresh unregistered speakers',
          ),
        ],
      ),
      body: Consumer<SpeakerProvider>(
        builder: (context, provider, child) {
          // Loading state
          if (provider.isLoading) {
            return const Center(
              child: CircularProgressIndicator(),
            );
          }

          // Error state
          if (provider.error != null) {
            return _buildErrorState(context, provider);
          }

          // All speakers registered state
          if (provider.unregisteredSpeakers.isEmpty) {
            return _buildEmptyState(context);
          }

          // Unregistered speakers list
          return _buildSpeakersList(context, provider);
        },
      ),
    );
  }

  /// Build error state UI
  Widget _buildErrorState(BuildContext context, SpeakerProvider provider) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 56,
              color: Colors.red[400],
            ),
            const SizedBox(height: 16),
            Text(
              'Error Loading Speakers',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              provider.error ?? 'Unknown error occurred',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.grey[600],
                height: 1.4,
              ),
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: () {
                provider.fetchUnregisteredSpeakers();
              },
              icon: const Icon(Icons.refresh),
              label: const Text('Try Again'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(
                  horizontal: 24,
                  vertical: 12,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Build empty state UI (all speakers registered)
  Widget _buildEmptyState(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.check_circle_outline,
              size: 64,
              color: Colors.green[400],
            ),
            const SizedBox(height: 16),
            Text(
              'All Speakers Registered!',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              'No unregistered speakers at the moment.\nNew speakers detected in meetings will appear here.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.grey[600],
                height: 1.5,
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Build speakers list UI
  Widget _buildSpeakersList(
      BuildContext context, SpeakerProvider provider) {
    return RefreshIndicator(
      onRefresh: () => provider.fetchUnregisteredSpeakers(),
      child: ListView.builder(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
        itemCount: provider.unregisteredSpeakers.length,
        itemBuilder: (context, index) {
          final speaker = provider.unregisteredSpeakers[index];
          final isLoadingAudio =
              provider.isLoadingAudioSample(speaker.id);

          return UnregisteredSpeakerTile(
            speaker: speaker,
            index: index,
            isLoading: isLoadingAudio,
            audioSampleUrl: _audioSampleUrl,
            onRegisterPressed: () {
              _showRegistrationDialog(context, speaker);
            },
          );
        },
      ),
    );
  }
}
