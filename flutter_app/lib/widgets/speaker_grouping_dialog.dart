import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/meeting_provider.dart';
import '../providers/speaker_provider.dart';
import '../models/speaker_model.dart';
import '../models/transcript_model.dart';

class SpeakerGroupingDialog extends StatefulWidget {
  final String meetingId;
  final List<TranscriptModel> transcripts;

  const SpeakerGroupingDialog({
    Key? key,
    required this.meetingId,
    required this.transcripts,
  }) : super(key: key);

  @override
  State<SpeakerGroupingDialog> createState() => _SpeakerGroupingDialogState();
}

class _SpeakerGroupingDialogState extends State<SpeakerGroupingDialog> {
  // Set of selected speaker identifiers (Ids or Names)
  final Set<String> _selectedSpeakers = {};
  
  // Map to store unique speakers found in transcripts
  // Key: Display Name, Value: (SpeakerID?, SpeakerName)
  final Map<String, ({String? id, String name})> _uniqueSpeakers = {};
  
  bool _isProcessing = false;

  @override
  void initState() {
    super.initState();
    _extractUniqueSpeakers();
  }

  void _extractUniqueSpeakers() {
    for (var t in widget.transcripts) {
      final name = t.speakerName ?? 'Unknown Speaker';
      final id = t.speakerId;
      
      // Use name as key for uniqueness in the list
      // If we have an ID, we prefer storing that for the "value"
      if (!_uniqueSpeakers.containsKey(name)) {
        _uniqueSpeakers[name] = (id: id, name: name);
      } else {
        // If we already have this name but current one has ID and stored one doesn't, update it
        if (id != null && _uniqueSpeakers[name]?.id == null) {
          _uniqueSpeakers[name] = (id: id, name: name);
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final speakerList = _uniqueSpeakers.values.toList()
      ..sort((a, b) => a.name.compareTo(b.name));

    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Container(
        padding: const EdgeInsets.all(24),
        constraints: const BoxConstraints(maxWidth: 400, maxHeight: 600),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Group Speakers',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              'Select speakers to merge into one identity.',
              style: TextStyle(color: Colors.grey[600]),
            ),
            const SizedBox(height: 16),
            
            // Speaker List
            Expanded(
              child: Container(
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.grey[200]!),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: ListView.separated(
                  itemCount: speakerList.length,
                  separatorBuilder: (ctx, i) => const Divider(height: 1),
                  itemBuilder: (context, index) {
                    final speaker = speakerList[index];
                    final identifier = speaker.id ?? speaker.name; // Use ID if available, else name
                    final isSelected = _selectedSpeakers.contains(identifier);
                    
                    return CheckboxListTile(
                      value: isSelected,
                      title: Text(speaker.name),
                      subtitle: speaker.id != null 
                          ? const Text('Registered', style: TextStyle(fontSize: 10, color: Colors.blue))
                          : null,
                      onChanged: (val) {
                        setState(() {
                          if (val == true) {
                            _selectedSpeakers.add(identifier);
                          } else {
                            _selectedSpeakers.remove(identifier);
                          }
                        });
                      },
                    );
                  },
                ),
              ),
            ),
            
            const SizedBox(height: 16),
            
            // Actions
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(
                  onPressed: _isProcessing ? null : () => Navigator.pop(context),
                  child: const Text('Cancel'),
                ),
                const SizedBox(width: 8),
                ElevatedButton(
                  onPressed: _isProcessing || _selectedSpeakers.length < 2 
                      ? null 
                      : () => _showTargetSpeakerSelection(context),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.blue,
                    foregroundColor: Colors.white,
                  ),
                  child: _isProcessing 
                      ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                      : Text('Merge (${_selectedSpeakers.length})'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _showTargetSpeakerSelection(BuildContext context) async {
    // 1. Identify which selected speakers match registered speakers vs raw names
    final selectedIds = <String>[];
    final selectedNames = <String>[];

    for (var key in _selectedSpeakers) {
      // Check if this key corresponds to a known ID from our map
      // Note: _selectedSpeakers stores "identifier" which is ID if available, else Name
      // We need to look up in _uniqueSpeakers values to verify
      
      bool isId = false;
      // We need to find the speaker object from our list that matches this identifier
      // This is slightly inefficient but list is small
      for (var s in _uniqueSpeakers.values) {
        if (s.id == key) {
           selectedIds.add(key);
           isId = true;
           break;
        }
      }
      if (!isId) {
        // It must be a name
        selectedNames.add(key);
      }
    }

    // 2. Prompt user to choose the "primary" identity or create a new one
    final target = await showDialog<({String? id, String name})>(
      context: context,
      builder: (ctx) => _TargetSpeakerSelectionDialog(
        uniqueSpeakers: _uniqueSpeakers.values.where((s) {
            final id = s.id ?? s.name;
            return _selectedSpeakers.contains(id);
        }).toList(),
      ),
    );

    if (target != null && mounted) {
      _performMerge(selectedIds, selectedNames, target);
    }
  }

  Future<void> _performMerge(
    List<String> ids, 
    List<String> names, 
    ({String? id, String name}) target
  ) async {
    setState(() => _isProcessing = true);

    try {
      final success = await context.read<MeetingProvider>().mergeSpeakers(
        meetingId: widget.meetingId,
        sourceSpeakerIds: ids,
        sourceSpeakerNames: names,
        targetSpeakerId: target.id,
        targetSpeakerName: target.name,
      );

      if (mounted) {
        if (success) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Speakers merged successfully'), backgroundColor: Colors.green),
          );
          Navigator.pop(context); // Close main dialog
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Failed to merge speakers'), backgroundColor: Colors.red),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e'), backgroundColor: Colors.red),
        );
      }
    } finally {
      if (mounted) setState(() => _isProcessing = false);
    }
  }
}

class _TargetSpeakerSelectionDialog extends StatefulWidget {
  final List<({String? id, String name})> uniqueSpeakers;

  const _TargetSpeakerSelectionDialog({required this.uniqueSpeakers});

  @override
  State<_TargetSpeakerSelectionDialog> createState() => _TargetSpeakerSelectionDialogState();
}

class _TargetSpeakerSelectionDialogState extends State<_TargetSpeakerSelectionDialog> {
  String? _selectedOption; // 'existing' or 'new'
  ({String? id, String name})? _selectedExisting;
  final _nameController = TextEditingController();

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Choose Identity'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Merge selected speakers into:'),
          const SizedBox(height: 16),
          
          // Option 1: Existing from selection
          RadioListTile<String>(
            title: const Text('One of the selected speakers'),
            value: 'existing',
            groupValue: _selectedOption,
            onChanged: (val) => setState(() => _selectedOption = val),
          ),
          if (_selectedOption == 'existing')
            Padding(
              padding: const EdgeInsets.only(left: 32, right: 16),
              child: DropdownButton<({String? id, String name})>(
                isExpanded: true,
                value: _selectedExisting,
                hint: const Text('Select primary speaker'),
                items: widget.uniqueSpeakers.map((s) => DropdownMenuItem(
                  value: s,
                  child: Text(s.name),
                )).toList(),
                onChanged: (val) => setState(() => _selectedExisting = val),
              ),
            ),

          // Option 2: New Name
          RadioListTile<String>(
            title: const Text('A new identity'),
            value: 'new',
            groupValue: _selectedOption,
            onChanged: (val) => setState(() => _selectedOption = val),
          ),
          if (_selectedOption == 'new')
            Padding(
              padding: const EdgeInsets.only(left: 32, right: 16),
              child: TextField(
                controller: _nameController,
                decoration: const InputDecoration(
                  hintText: 'Enter new name (e.g. John Doe)',
                  isDense: true,
                ),
              ),
            ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        TextButton(
          onPressed: _canProceed() ? () {
            if (_selectedOption == 'existing') {
              Navigator.pop(context, _selectedExisting);
            } else {
              Navigator.pop(context, (id: null, name: _nameController.text.trim()));
            }
          } : null,
          child: const Text('Confirm'),
        ),
      ],
    );
  }

  bool _canProceed() {
    if (_selectedOption == 'existing') return _selectedExisting != null;
    if (_selectedOption == 'new') return _nameController.text.trim().isNotEmpty;
    return false;
  }
}
