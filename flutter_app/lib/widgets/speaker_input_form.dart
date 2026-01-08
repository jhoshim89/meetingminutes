import 'package:flutter/material.dart';

class SpeakerInputForm extends StatefulWidget {
  final TextEditingController nameController;
  final VoidCallback onSave;
  final VoidCallback onCancel;
  final bool isLoading;

  const SpeakerInputForm({
    Key? key,
    required this.nameController,
    required this.onSave,
    required this.onCancel,
    this.isLoading = false,
  }) : super(key: key);

  @override
  State<SpeakerInputForm> createState() => _SpeakerInputFormState();
}

class _SpeakerInputFormState extends State<SpeakerInputForm> {
  late FocusNode _focusNode;

  @override
  void initState() {
    super.initState();
    _focusNode = FocusNode();
    // Request focus when form appears
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _focusNode.requestFocus();
    });
  }

  @override
  void dispose() {
    _focusNode.dispose();
    super.dispose();
  }

  void _handleSave() {
    final name = widget.nameController.text.trim();
    if (name.isEmpty) {
      _showValidationError('Please enter a speaker name');
      return;
    }

    if (name.length < 2) {
      _showValidationError('Speaker name must be at least 2 characters');
      return;
    }

    if (name.length > 50) {
      _showValidationError('Speaker name must be less than 50 characters');
      return;
    }

    widget.onSave();
  }

  void _showValidationError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.orange,
        duration: const Duration(seconds: 2),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Instructions
        Text(
          'Speaker Name',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'Give this speaker a name to help identify them in future meetings.',
          style: TextStyle(
            fontSize: 13,
            color: Colors.grey[600],
            height: 1.4,
          ),
        ),
        const SizedBox(height: 20),

        // Name input field
        TextFormField(
          controller: widget.nameController,
          focusNode: _focusNode,
          enabled: !widget.isLoading,
          autofocus: true,
          textCapitalization: TextCapitalization.words,
          maxLength: 50,
          decoration: InputDecoration(
            labelText: 'Speaker Name',
            hintText: 'e.g., John Doe, Prof. Smith',
            prefixIcon: const Icon(Icons.person),
            suffixIcon: widget.nameController.text.isNotEmpty
                ? IconButton(
              icon: const Icon(Icons.clear),
              onPressed: () {
                widget.nameController.clear();
                setState(() {});
              },
            )
                : null,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: BorderSide(
                color: isDark ? Colors.grey[600]! : Colors.grey[300]!,
              ),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: const BorderSide(
                color: Colors.blue,
                width: 2,
              ),
            ),
            disabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: BorderSide(
                color: isDark ? Colors.grey[700]! : Colors.grey[200]!,
              ),
            ),
          ),
          onChanged: (value) {
            setState(() {});
          },
          onFieldSubmitted: (value) {
            if (!widget.isLoading) {
              _handleSave();
            }
          },
        ),
        const SizedBox(height: 24),

        // Action buttons
        Row(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            TextButton(
              onPressed: widget.isLoading ? null : widget.onCancel,
              child: const Text('Cancel'),
            ),
            const SizedBox(width: 12),
            ElevatedButton.icon(
              onPressed: widget.isLoading ? null : _handleSave,
              icon: widget.isLoading
                  ? const SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  valueColor: AlwaysStoppedAnimation<Color>(
                    Colors.white,
                  ),
                ),
              )
                  : const Icon(Icons.check),
              label: Text(
                widget.isLoading ? 'Saving...' : 'Save',
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.blue,
                disabledBackgroundColor: Colors.grey[300],
              ),
            ),
          ],
        ),
      ],
    );
  }
}
