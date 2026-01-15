import 'package:flutter/material.dart';
import 'home_screen.dart';
import 'meeting_detail_screen.dart';

class HomeNavigator extends StatefulWidget {
  const HomeNavigator({Key? key}) : super(key: key);

  @override
  State<HomeNavigator> createState() => _HomeNavigatorState();
}

class _HomeNavigatorState extends State<HomeNavigator> {
  final GlobalKey<NavigatorState> _navigatorKey = GlobalKey<NavigatorState>();

  @override
  Widget build(BuildContext context) {
    return Navigator(
      key: _navigatorKey,
      onGenerateRoute: (RouteSettings settings) {
        return MaterialPageRoute(
          settings: settings,
          builder: (BuildContext context) {
            // Handle specific named routes if needed, otherwise default handling
            // Currently HomeScreen pushes MaterialPageRoute directly with builder,
            // so this builder might act as a fallback or root.
            
            // However, HomeScreen pushes `MaterialPageRoute` directly. 
            // When `Navigator.push` is called from HomeScreen, it looks up the widget tree.
            // It finds THIS Navigator.
            
            // The '/' route is the default initial route.
            if (settings.name == '/' || settings.name == null) {
              return const HomeScreen();
            }
            
            // Fallback for named routes if used later
            return const HomeScreen();
          },
        );
      },
    );
  }
}
