# Quick Start: FCM Web Push Notifications

Get FCM Web Push notifications running in 10 minutes.

## Prerequisites

- Firebase account
- Supabase project
- Flutter development environment

## 5-Minute Setup

### 1. Firebase Setup (2 minutes)

```bash
# 1. Go to https://console.firebase.google.com/
# 2. Create new project: "meeting-minutes-pwa"
# 3. Add Web App, copy the config
# 4. Go to Project Settings > Cloud Messaging
# 5. Generate VAPID key pair
# 6. Copy Server Key
```

### 2. Update Flutter Files (2 minutes)

Replace Firebase config in **2 files**:

**File 1**: `flutter_app/web/index.html`
```javascript
// Line 43-51
const firebaseConfig = {
  apiKey: "PASTE_YOUR_API_KEY",
  authDomain: "PASTE_YOUR_AUTH_DOMAIN",
  projectId: "PASTE_YOUR_PROJECT_ID",
  storageBucket: "PASTE_YOUR_STORAGE_BUCKET",
  messagingSenderId: "PASTE_YOUR_SENDER_ID",
  appId: "PASTE_YOUR_APP_ID"
};
```

**File 2**: `flutter_app/web/firebase-messaging-sw.js`
```javascript
// Line 11-18 (same config as above)
```

### 3. Supabase Setup (3 minutes)

```bash
# Install Supabase CLI
npm install -g supabase

# Login
supabase login

# Link project
cd D:\Productions\meetingminutes
supabase link --project-ref YOUR_PROJECT_REF

# Run migration (creates tables)
# Go to Supabase Dashboard > SQL Editor
# Paste content from: supabase/migrations/20260109_fcm_schema.sql
# Click Run

# Set secrets
supabase secrets set FCM_SERVER_KEY="YOUR_SERVER_KEY"
supabase secrets set FCM_PROJECT_ID="YOUR_PROJECT_ID"

# Deploy function
supabase functions deploy send-appointment-reminder
```

### 4. Initialize in Flutter (2 minutes)

Add to `flutter_app/lib/main.dart`:

```dart
import 'services/fcm_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // ... existing Supabase init ...

  // Add FCM initialization
  await FCMService().initialize();

  runApp(const MyApp());
}
```

### 5. Test It! (1 minute)

```bash
# Run app
cd flutter_app
flutter run -d chrome

# Check console for: "[FCMService] Token saved"

# Create test appointment:
# 1. Open app
# 2. Navigate to Scheduler
# 3. Create appointment 10 minutes in future
# 4. Set reminder for 5 minutes before
# 5. Wait and receive notification!
```

## Setup Cron Job (Scheduler)

**Option A: Supabase pg_cron** (Recommended)

```sql
-- Run in Supabase SQL Editor
SELECT cron.schedule(
  'send-appointment-reminders',
  '* * * * *', -- Every minute
  $$
  SELECT net.http_post(
    url := 'https://YOUR_PROJECT_REF.supabase.co/functions/v1/send-appointment-reminder',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || current_setting('app.settings.service_role_key')
    )
  );
  $$
);
```

**Option B: External Cron** (Alternative)

Use cron-job.org or GitHub Actions to call:
```
POST https://YOUR_PROJECT_REF.supabase.co/functions/v1/send-appointment-reminder
Authorization: Bearer YOUR_SERVICE_ROLE_KEY
```

## Verify Everything Works

### ✅ Checklist

- [ ] Firebase config updated in both files
- [ ] Service worker registered (check browser console)
- [ ] FCM token saved to Supabase `user_fcm_tokens` table
- [ ] Database tables created (`appointments`, `user_fcm_tokens`)
- [ ] Edge function deployed successfully
- [ ] Cron job scheduled
- [ ] Test appointment created
- [ ] Notification received!

### 🔍 Quick Debug

**No FCM token?**
```javascript
// Check in browser console
navigator.serviceWorker.getRegistrations().then(r => console.log(r));
```

**No notification?**
- Check Edge Function logs in Supabase Dashboard
- Verify appointment time is within 15-minute window
- Test with Firebase Console test message

**iOS not working?**
- iOS 16.4+ required
- Must use Safari (not Chrome)
- Add to Home Screen as PWA
- Grant notification permission

## File Locations

```
D:\Productions\meetingminutes\
├── flutter_app/
│   ├── lib/
│   │   └── services/
│   │       └── fcm_service.dart          ← FCM logic
│   ├── web/
│   │   ├── index.html                    ← Firebase config #1
│   │   └── firebase-messaging-sw.js      ← Firebase config #2
│   └── pubspec.yaml                      ← Dependencies added
├── supabase/
│   ├── migrations/
│   │   └── 20260109_fcm_schema.sql       ← Database schema
│   └── functions/
│       └── send-appointment-reminder/
│           └── index.ts                   ← Edge function
└── FCM_SETUP.md                          ← Full documentation
```

## Need Help?

See full documentation: `FCM_SETUP.md`

Common issues:
- HTTPS required (localhost OK for dev)
- iOS needs PWA + Safari + 16.4+
- Clear cache if service worker not updating
- Check Supabase logs for Edge Function errors

## Next Steps

After basic setup works:

1. Add notification listeners in app
2. Customize notification messages
3. Add user notification preferences
4. Implement notification analytics
5. Test on iOS Safari
6. Deploy to production hosting

That's it! You now have FCM Web Push notifications running. 🎉
