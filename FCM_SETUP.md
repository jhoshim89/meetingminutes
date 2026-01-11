# FCM Web Push Notification Setup Guide

Complete setup guide for Firebase Cloud Messaging (FCM) Web Push notifications in Meeting Minutes PWA.

## Table of Contents

1. [Firebase Project Setup](#firebase-project-setup)
2. [Flutter Configuration](#flutter-configuration)
3. [Supabase Configuration](#supabase-configuration)
4. [Testing](#testing)
5. [Troubleshooting](#troubleshooting)

---

## Firebase Project Setup

### Step 1: Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Add project"
3. Enter project name: `meeting-minutes-pwa`
4. Follow the setup wizard (you can disable Google Analytics if not needed)

### Step 2: Add Web App

1. In Firebase Console, click the web icon (`</>`) to add a web app
2. Enter app nickname: `Meeting Minutes Web`
3. Check "Also set up Firebase Hosting" (optional)
4. Click "Register app"
5. Copy the Firebase config object (you'll need this later)

```javascript
const firebaseConfig = {
  apiKey: "AIzaSy...",
  authDomain: "meeting-minutes-pwa.firebaseapp.com",
  projectId: "meeting-minutes-pwa",
  storageBucket: "meeting-minutes-pwa.appspot.com",
  messagingSenderId: "123456789012",
  appId: "1:123456789012:web:abcdef1234567890",
  measurementId: "G-XXXXXXXXXX"
};
```

### Step 3: Enable Cloud Messaging

1. In Firebase Console, go to **Project Settings** > **Cloud Messaging**
2. Under "Web configuration", click **Generate key pair**
3. Copy the **VAPID key** (starts with `B...`)
4. **Important**: Save this key securely - you'll need it for token generation

### Step 4: Get Server Key (for Edge Function)

1. Still in **Cloud Messaging** tab
2. Under "Cloud Messaging API (Legacy)", find **Server key**
3. Copy this key - you'll need it for Supabase Edge Function
4. **Note**: This is for FCM HTTP v1 API. For production, use Service Account JSON instead.

---

## Flutter Configuration

### Step 1: Update pubspec.yaml

Already done! The following packages are added:

```yaml
dependencies:
  firebase_core: ^2.24.0
  firebase_messaging: ^14.7.0
  table_calendar: ^3.0.9
  timezone: ^0.9.2
```

Install dependencies:

```bash
cd flutter_app
flutter pub get
```

### Step 2: Configure web/index.html

1. Open `flutter_app/web/index.html`
2. Replace the placeholder Firebase config with your actual config:

```html
<script>
  const firebaseConfig = {
    apiKey: "YOUR_API_KEY",
    authDomain: "YOUR_PROJECT_ID.firebaseapp.com",
    projectId: "YOUR_PROJECT_ID",
    storageBucket: "YOUR_PROJECT_ID.appspot.com",
    messagingSenderId: "YOUR_MESSAGING_SENDER_ID",
    appId: "YOUR_APP_ID",
    measurementId: "YOUR_MEASUREMENT_ID"
  };

  if (!firebase.apps.length) {
    firebase.initializeApp(firebaseConfig);
  }
</script>
```

### Step 3: Configure firebase-messaging-sw.js

1. Open `flutter_app/web/firebase-messaging-sw.js`
2. Replace the placeholder config with your actual config (same as above)

```javascript
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  // ... same as index.html
};

firebase.initializeApp(firebaseConfig);
```

### Step 4: Initialize FCM in Flutter App

1. Open `flutter_app/lib/main.dart`
2. Initialize FCM before `runApp()`:

```dart
import 'package:firebase_core/firebase_core.dart';
import 'services/fcm_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize Supabase
  await Supabase.initialize(
    url: 'YOUR_SUPABASE_URL',
    anonKey: 'YOUR_SUPABASE_ANON_KEY',
  );

  // Initialize FCM
  try {
    await FCMService().initialize();
    debugPrint('[Main] FCM initialized');
  } catch (e) {
    debugPrint('[Main] FCM initialization error: $e');
  }

  runApp(const MyApp());
}
```

### Step 5: Listen to Notification Events

Add notification listeners in your app:

```dart
class _MyAppState extends State<MyApp> {
  @override
  void initState() {
    super.initState();
    _setupNotificationListeners();
  }

  void _setupNotificationListeners() {
    // Foreground messages
    FCMService().onMessage.listen((RemoteMessage message) {
      print('Foreground notification: ${message.notification?.title}');

      // Show in-app notification or navigate
      final appointmentId = message.data['appointmentId'];
      if (appointmentId != null) {
        // Navigate to appointment details
      }
    });

    // Background messages that opened the app
    FCMService().onMessageOpenedApp.listen((RemoteMessage message) {
      print('Notification opened app: ${message.data}');

      final appointmentId = message.data['appointmentId'];
      if (appointmentId != null) {
        // Navigate to appointment details
      }
    });

    // Check if app was opened from terminated state
    FCMService().getInitialMessage().then((RemoteMessage? message) {
      if (message != null) {
        print('App opened from notification: ${message.data}');
        // Handle initial message
      }
    });
  }
}
```

---

## Supabase Configuration

### Step 1: Run Database Migration

1. Copy the migration SQL file:
   - Location: `supabase/migrations/20260109_fcm_schema.sql`

2. Run migration in Supabase Dashboard:
   - Go to **SQL Editor**
   - Click **New query**
   - Paste the entire SQL file content
   - Click **Run**

3. Verify tables created:
   - `user_fcm_tokens`
   - `appointments`

### Step 2: Deploy Edge Function

1. Install Supabase CLI:

```bash
npm install -g supabase
```

2. Login to Supabase:

```bash
supabase login
```

3. Link your project:

```bash
cd D:\Productions\meetingminutes
supabase link --project-ref YOUR_PROJECT_REF
```

4. Set Edge Function secrets:

```bash
supabase secrets set FCM_SERVER_KEY="YOUR_FCM_SERVER_KEY"
supabase secrets set FCM_PROJECT_ID="YOUR_FIREBASE_PROJECT_ID"
```

5. Deploy the Edge Function:

```bash
supabase functions deploy send-appointment-reminder
```

### Step 3: Setup Cron Job (Scheduler)

1. Go to **Database** > **Cron Jobs** in Supabase Dashboard
2. Click **Create cron job**
3. Configure:
   - **Name**: `send-appointment-reminders`
   - **Schedule**: `* * * * *` (every 1 minute)
   - **Command**:
   ```sql
   SELECT net.http_post(
     url := 'https://YOUR_PROJECT_REF.supabase.co/functions/v1/send-appointment-reminder',
     headers := jsonb_build_object(
       'Content-Type', 'application/json',
       'Authorization', 'Bearer ' || current_setting('app.settings.service_role_key')
     ),
     body := '{}'::jsonb
   );
   ```
4. Click **Create**

**Alternative**: Use external cron service (cron-job.org, GitHub Actions, etc.) to call the Edge Function every minute:

```bash
curl -X POST https://YOUR_PROJECT_REF.supabase.co/functions/v1/send-appointment-reminder \
  -H "Authorization: Bearer YOUR_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json"
```

---

## Testing

### Test 1: FCM Token Generation

1. Build and run the Flutter web app:

```bash
cd flutter_app
flutter run -d chrome --web-port=8080
```

2. Open browser console (F12)
3. Look for log: `[FCMService] Token saved: ...`
4. Check Supabase `user_fcm_tokens` table - should have a new row

### Test 2: Create Test Appointment

1. Open the app
2. Go to Scheduler screen
3. Create an appointment 10 minutes in the future
4. Set reminder for 5 minutes before
5. Verify appointment appears in calendar

### Test 3: Test Notification Manually

Use Firebase Console to send a test notification:

1. Go to **Cloud Messaging** > **Send your first message**
2. Enter notification title and body
3. Click **Send test message**
4. Enter your FCM token (from browser console)
5. Click **Test**

You should receive a notification if:
- App is open (foreground notification)
- App is closed (background notification via service worker)

### Test 4: Test Scheduler

1. Create an appointment that should trigger soon (within 15 minutes)
2. Wait for the cron job to run (every 1 minute)
3. Check Edge Function logs in Supabase Dashboard
4. You should receive a push notification 15 minutes before the meeting

### Test 5: iOS Safari Testing

1. Deploy app to a hosting service (Firebase Hosting, Vercel, etc.)
2. Open on iPhone with iOS 16.4+ using Safari
3. Add to Home Screen (creates PWA)
4. Grant notification permission when prompted
5. Create a test appointment
6. Receive notification

**Note**: Web Push on iOS requires:
- HTTPS (localhost works for development)
- iOS 16.4 or later
- Safari browser (not Chrome/Firefox on iOS)
- Added to Home Screen as PWA

---

## Troubleshooting

### Issue: No FCM token generated

**Solutions**:
- Check Firebase config is correct in `index.html` and `firebase-messaging-sw.js`
- Verify service worker is registered (check browser console)
- Make sure using HTTPS (or localhost)
- Check notification permissions in browser settings

### Issue: Service worker not loading

**Solutions**:
- Clear browser cache and service workers
- Check `firebase-messaging-sw.js` is in `/web` folder
- Verify Firebase SDK URLs are loading (check Network tab)
- Try hard refresh: `Ctrl+Shift+R`

### Issue: Notifications not received

**Solutions**:
- Check FCM token is saved in Supabase
- Verify Edge Function is deployed and running
- Check Edge Function logs for errors
- Confirm appointment is within reminder window (15 minutes)
- Test with Firebase Console test message first

### Issue: iOS notifications not working

**Solutions**:
- Verify iOS version is 16.4+
- Must use Safari browser (not Chrome)
- App must be added to Home Screen as PWA
- Check notification permissions in iOS Settings > Safari > Advanced
- Ensure HTTPS is enabled (required for iOS)

### Issue: Edge Function errors

**Solutions**:
- Check FCM_SERVER_KEY is set correctly
- Verify FCM_PROJECT_ID matches Firebase project
- Check Supabase service role key has correct permissions
- Review Edge Function logs in Supabase Dashboard

### Debug Commands

**Check service worker status**:
```javascript
navigator.serviceWorker.getRegistrations().then(registrations => {
  console.log('Service Workers:', registrations);
});
```

**Check notification permission**:
```javascript
console.log('Notification permission:', Notification.permission);
```

**Request permission manually**:
```javascript
Notification.requestPermission().then(permission => {
  console.log('Permission:', permission);
});
```

**Get current FCM token**:
```dart
final token = await FCMService().getToken();
print('FCM Token: $token');
```

---

## Production Checklist

- [ ] Replace Firebase config placeholders with production values
- [ ] Set up proper FCM Server Key or Service Account JSON
- [ ] Enable HTTPS on hosting (required for Web Push)
- [ ] Test notifications on iOS Safari 16.4+
- [ ] Set up monitoring for Edge Function execution
- [ ] Configure proper cron schedule (currently every 1 minute)
- [ ] Implement notification click tracking/analytics
- [ ] Add user settings for notification preferences
- [ ] Test notification delivery across different time zones
- [ ] Set up error alerting for failed notifications
- [ ] Review and adjust reminder timing (currently 15 minutes before)
- [ ] Implement notification batching for multiple appointments

---

## Additional Resources

- [Firebase Cloud Messaging Documentation](https://firebase.google.com/docs/cloud-messaging)
- [Flutter Firebase Messaging Plugin](https://pub.dev/packages/firebase_messaging)
- [iOS Web Push Support](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/)
- [Supabase Edge Functions](https://supabase.com/docs/guides/functions)
- [Web Push Protocol](https://web.dev/push-notifications-overview/)

---

## Support

For issues or questions:
- Check Supabase Dashboard logs
- Review Firebase Console for FCM metrics
- Test with Firebase Console test messages
- Enable verbose logging in FCM Service

Last updated: 2026-01-09
