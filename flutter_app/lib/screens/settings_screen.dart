import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../services/supabase_service.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({Key? key}) : super(key: key);

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final SupabaseService _supabaseService = SupabaseService();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
      ),
      body: ListView(
        children: [
          // User Profile Section
          Consumer<AuthProvider>(
            builder: (context, authProvider, child) {
              return Container(
                padding: const EdgeInsets.all(16),
                color: Colors.blue.withOpacity(0.05),
                child: Column(
                  children: [
                    CircleAvatar(
                      radius: 40,
                      backgroundColor: Colors.blue.withOpacity(0.2),
                      child: const Icon(
                        Icons.person,
                        size: 48,
                        color: Colors.blue,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      authProvider.isAuthenticated ? 'Signed In' : 'Not Signed In',
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    if (authProvider.userId != null) ...[
                      const SizedBox(height: 4),
                      Text(
                        'User ID: ${authProvider.userId!.substring(0, 8)}...',
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.grey[600],
                        ),
                      ),
                    ],
                    if (!authProvider.isAuthenticated) ...[
                      const SizedBox(height: 12),
                      ElevatedButton(
                        onPressed: authProvider.isLoading
                            ? null
                            : () => authProvider.signInAnonymously(),
                        child: authProvider.isLoading
                            ? const SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Text('Sign In Anonymously'),
                      ),
                    ],
                  ],
                ),
              );
            },
          ),

          const Divider(),

          // Meeting Templates Section
          const Padding(
            padding: EdgeInsets.all(16),
            child: Text(
              'Meeting Templates',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          _buildListTile(
            icon: Icons.business_center,
            title: 'Default Meeting',
            subtitle: 'Standard meeting template',
            onTap: () {
              _showComingSoonDialog(context);
            },
          ),
          _buildListTile(
            icon: Icons.groups,
            title: 'Team Standup',
            subtitle: 'Daily standup template',
            onTap: () {
              _showComingSoonDialog(context);
            },
          ),
          _buildListTile(
            icon: Icons.assignment,
            title: 'Client Review',
            subtitle: 'Client review template',
            onTap: () {
              _showComingSoonDialog(context);
            },
          ),

          const Divider(),

          // App Settings Section
          const Padding(
            padding: EdgeInsets.all(16),
            child: Text(
              'App Settings',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          _buildListTile(
            icon: Icons.high_quality,
            title: 'Audio Quality',
            subtitle: 'High (128 kbps)',
            onTap: () {
              _showAudioQualityDialog(context);
            },
          ),
          _buildListTile(
            icon: Icons.cloud_upload,
            title: 'Storage Location',
            subtitle: 'Cloud (Supabase)',
            trailing: Chip(
              label: const Text(
                'Cloud',
                style: TextStyle(fontSize: 12),
              ),
              backgroundColor: Colors.blue.withOpacity(0.1),
            ),
          ),
          _buildListTile(
            icon: Icons.notifications,
            title: 'Notifications',
            subtitle: 'Manage notification preferences',
            onTap: () {
              _showComingSoonDialog(context);
            },
          ),

          const Divider(),

          // About Section
          const Padding(
            padding: EdgeInsets.all(16),
            child: Text(
              'About',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          _buildListTile(
            icon: Icons.info,
            title: 'About',
            subtitle: 'Version 1.0.0',
            onTap: () {
              _showAboutDialog(context);
            },
          ),
          _buildListTile(
            icon: Icons.help,
            title: 'Help & Support',
            subtitle: 'Get help using the app',
            onTap: () {
              _showComingSoonDialog(context);
            },
          ),
          _buildListTile(
            icon: Icons.privacy_tip,
            title: 'Privacy Policy',
            subtitle: 'View privacy policy',
            onTap: () {
              _showComingSoonDialog(context);
            },
          ),

          const SizedBox(height: 24),

          // Sign Out Button
          Consumer<AuthProvider>(
            builder: (context, authProvider, child) {
              if (!authProvider.isAuthenticated) {
                return const SizedBox.shrink();
              }

              return Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: OutlinedButton.icon(
                  onPressed: authProvider.isLoading
                      ? null
                      : () => _showSignOutDialog(context),
                  icon: const Icon(Icons.logout, color: Colors.red),
                  label: const Text(
                    'Sign Out',
                    style: TextStyle(color: Colors.red),
                  ),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: Colors.red),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
              );
            },
          ),

          const SizedBox(height: 24),
        ],
      ),
    );
  }

  Widget _buildListTile({
    required IconData icon,
    required String title,
    required String subtitle,
    VoidCallback? onTap,
    Widget? trailing,
  }) {
    return ListTile(
      leading: Icon(icon, color: Colors.blue),
      title: Text(title),
      subtitle: Text(subtitle),
      trailing: trailing ?? const Icon(Icons.arrow_forward_ios, size: 16),
      onTap: onTap,
    );
  }

  void _showAboutDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('About Meeting Minutes'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: const [
            Text(
              'Version 1.0.0',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 16),
            Text('Voice Asset MVP - Meeting Automation Mobile App'),
            SizedBox(height: 8),
            Text(
              'Record, transcribe, and analyze your meetings with AI-powered speaker identification.',
            ),
            SizedBox(height: 16),
            Text(
              'Powered by:',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 4),
            Text('- Flutter & Dart'),
            Text('- Supabase'),
            Text('- OpenAI Whisper'),
            Text('- Speaker Diarization AI'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  void _showAudioQualityDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Audio Quality'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            RadioListTile<String>(
              title: const Text('Low (64 kbps)'),
              subtitle: const Text('Smaller file size'),
              value: 'low',
              groupValue: 'high',
              onChanged: (value) {
                Navigator.pop(context);
                _showComingSoonDialog(context);
              },
            ),
            RadioListTile<String>(
              title: const Text('Medium (96 kbps)'),
              subtitle: const Text('Balanced'),
              value: 'medium',
              groupValue: 'high',
              onChanged: (value) {
                Navigator.pop(context);
                _showComingSoonDialog(context);
              },
            ),
            RadioListTile<String>(
              title: const Text('High (128 kbps)'),
              subtitle: const Text('Best quality'),
              value: 'high',
              groupValue: 'high',
              onChanged: (value) {
                Navigator.pop(context);
              },
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  void _showComingSoonDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Coming Soon'),
        content: const Text('This feature is coming soon in a future update.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  void _showSignOutDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Sign Out?'),
        content: const Text('Are you sure you want to sign out?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              context.read<AuthProvider>().signOut();
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Signed out successfully'),
                  backgroundColor: Colors.green,
                ),
              );
            },
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Sign Out'),
          ),
        ],
      ),
    );
  }
}
