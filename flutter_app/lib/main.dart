import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:provider/provider.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'dart:html' as html;
import 'screens/home_screen.dart';
import 'screens/home_navigator.dart';
import 'screens/recorder_screen.dart';
import 'screens/meeting_detail_screen.dart';
import 'screens/speaker_manager_screen.dart';
import 'screens/settings_screen.dart';
import 'screens/search_screen.dart';
import 'screens/scheduler_screen.dart';
import 'providers/auth_provider.dart';
import 'providers/meeting_provider.dart';
import 'providers/recorder_provider.dart';
import 'providers/search_provider.dart';
import 'providers/speaker_provider.dart';
import 'providers/template_provider.dart';
import 'providers/appointment_provider.dart';
import 'services/fcm_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await Supabase.initialize(
    url: 'https://wiefsjvmsfqhbgfglqjg.supabase.co',
    anonKey: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndpZWZzanZtc2ZxaGJnZmdscWpnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU3ODI0MjMsImV4cCI6MjA3MTM1ODQyM30.zIxkdhXcn3YrKGLTWcVqWdDUVfr2wQa_VWAr3Js4g4Y',
  );

  // Initialize FCM for web push notifications
  try {
    await FCMService().initialize();
  } catch (e) {
    debugPrint('FCM initialization failed: $e');
  }

  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthProvider()),
        ChangeNotifierProvider(create: (_) => MeetingProvider()),
        ChangeNotifierProvider(create: (_) => RecorderProvider()),
        ChangeNotifierProvider(create: (_) => SearchProvider()),
        ChangeNotifierProvider(create: (_) => SpeakerProvider()),
        ChangeNotifierProvider(create: (_) => TemplateProvider()),
        ChangeNotifierProvider(create: (_) => AppointmentProvider()),
      ],
      child: MaterialApp(
        title: 'Meeting Minutes',
        debugShowCheckedModeBanner: false,
        theme: _buildLightTheme(),
        darkTheme: _buildDarkTheme(),
        themeMode: ThemeMode.system,
        home: const MainNavigator(),
      ),
    );
  }

  ThemeData _buildLightTheme() {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      primarySwatch: Colors.blue,
      primaryColor: Colors.blue,
      scaffoldBackgroundColor: Colors.white,
      appBarTheme: const AppBarTheme(
        centerTitle: true,
        elevation: 0,
        backgroundColor: Colors.white,
        foregroundColor: Colors.black,
      ),
      inputDecorationTheme: InputDecorationTheme(
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 12,
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.blue,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(
            horizontal: 24,
            vertical: 12,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
        ),
      ),
      cardTheme: CardThemeData(
        color: Colors.white,
        elevation: 2,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
      ),
    );
  }

  ThemeData _buildDarkTheme() {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      primarySwatch: Colors.blue,
      primaryColor: Colors.blue,
      scaffoldBackgroundColor: const Color(0xFF121212),
      appBarTheme: AppBarTheme(
        centerTitle: true,
        elevation: 0,
        backgroundColor: const Color(0xFF1E1E1E),
        foregroundColor: Colors.white,
      ),
      inputDecorationTheme: InputDecorationTheme(
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 12,
        ),
        filled: true,
        fillColor: const Color(0xFF2C2C2C),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.blue,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(
            horizontal: 24,
            vertical: 12,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
        ),
      ),
      cardTheme: CardThemeData(
        color: const Color(0xFF1E1E1E),
        elevation: 2,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
      ),
    );
  }
}

class MainNavigator extends StatefulWidget {
  const MainNavigator({Key? key}) : super(key: key);

  @override
  State<MainNavigator> createState() => _MainNavigatorState();
}

class _MainNavigatorState extends State<MainNavigator> {
  int _currentIndex = 0;
  bool _isInitialized = false;
  String? _initialAppointmentId;

  final List<Widget> _screens = const [
    HomeNavigator(),
    SearchScreen(),
    RecorderScreen(),
    SchedulerScreen(),
    SpeakerManagerScreen(),
    SettingsScreen(),
  ];

  @override
  void initState() {
    super.initState();
    _initializeAuth();
    _checkDeepLink();
    _setupFCMListeners();
  }

  Future<void> _initializeAuth() async {
    final authProvider = Provider.of<AuthProvider>(context, listen: false);

    // Auto sign in anonymously if not authenticated
    if (!authProvider.isAuthenticated) {
      await authProvider.signInAnonymously();
    }

    setState(() {
      _isInitialized = true;
    });
  }

  void _checkDeepLink() {
    try {
      // Check URL parameters for PWA deep links
      final uri = Uri.parse(html.window.location.href);
      final appointmentId = uri.queryParameters['appointment'];

      if (appointmentId != null && appointmentId.isNotEmpty) {
        debugPrint('[DeepLink] Appointment ID from URL: $appointmentId');
        _initialAppointmentId = appointmentId;

        // Navigate to RecorderScreen after initialization
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (_isInitialized) {
            _navigateToRecorder(appointmentId);
          }
        });
      }
    } catch (e) {
      debugPrint('[DeepLink] Error checking URL: $e');
    }
  }

  void _setupFCMListeners() {
    // Handle initial message (app opened from terminated state)
    FCMService().getInitialMessage().then((message) {
      if (message != null) {
        _handleFCMMessage(message);
      }
    });

    // Handle foreground messages
    FCMService().onMessage.listen((message) {
      debugPrint('[FCM] Foreground message: ${message.data}');
      _showNotificationDialog(message);
    });

    // Handle messages that opened the app from background
    FCMService().onMessageOpenedApp.listen((message) {
      debugPrint('[FCM] Message opened app: ${message.data}');
      _handleFCMMessage(message);
    });

    // Listen for Service Worker messages (PWA)
    html.window.addEventListener('message', (event) {
      final messageEvent = event as html.MessageEvent;
      final data = messageEvent.data;

      if (data is Map && data['type'] == 'NOTIFICATION_CLICK') {
        final appointmentId = data['appointmentId'];
        if (appointmentId != null) {
          debugPrint('[SW] Service Worker notification click: $appointmentId');
          _navigateToRecorder(appointmentId);
        }
      }
    });
  }

  void _handleFCMMessage(RemoteMessage message) {
    final appointmentId = message.data['appointment_id'];

    if (appointmentId != null && appointmentId.isNotEmpty) {
      debugPrint('[FCM] Navigating to recorder for appointment: $appointmentId');
      _navigateToRecorder(appointmentId);
    }
  }

  void _navigateToRecorder(String appointmentId) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => RecorderScreen(appointmentId: appointmentId),
      ),
    );
  }

  void _showNotificationDialog(RemoteMessage message) {
    final title = message.notification?.title ?? 'Meeting Reminder';
    final body = message.notification?.body ?? '';

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: Text(body),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Dismiss'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              final appointmentId = message.data['appointment_id'];
              if (appointmentId != null) {
                _navigateToRecorder(appointmentId);
              }
            },
            child: const Text('Start Recording'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (!_isInitialized) {
      return const Scaffold(
        body: Center(
          child: CircularProgressIndicator(),
        ),
      );
    }
    return Scaffold(
      body: _screens[_currentIndex],
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) {
          setState(() {
            _currentIndex = index;
          });
        },
        type: BottomNavigationBarType.fixed,
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.home),
            label: '홈',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.search),
            label: '검색',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.mic),
            label: '녹음',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.calendar_today),
            label: '캘린더',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.person),
            label: '화자',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.settings),
            label: '설정',
          ),
        ],
      ),
    );
  }
}
