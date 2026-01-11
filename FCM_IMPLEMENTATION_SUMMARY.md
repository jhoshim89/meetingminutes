# FCM Web Push Implementation Summary

Complete implementation of Firebase Cloud Messaging (FCM) Web Push notifications and scheduler service for Meeting Minutes PWA.

## What Was Implemented

### 1. Flutter App Components

#### Dependencies Added (`flutter_app/pubspec.yaml`)
```yaml
firebase_core: ^2.24.0          # Firebase initialization
firebase_messaging: ^14.7.0     # FCM Web Push
table_calendar: ^3.0.9          # Calendar UI
timezone: ^0.9.2                # Timezone handling
```

#### FCM Service (`lib/services/fcm_service.dart`)
- Singleton service for FCM operations
- Token management (get, save, delete, refresh)
- Permission handling
- Message stream (foreground, background, opened app)
- Supabase token persistence
- Topic subscription support

**Key Features**:
- Auto-saves tokens to Supabase `user_fcm_tokens` table
- Handles token refresh automatically
- Provides streams for notification events
- Works with iOS Safari 16.4+ Web Push API

#### Scheduler Screen (`lib/screens/scheduler_screen.dart`)
- Calendar view with appointments
- Create/edit/delete appointments
- Notification settings per appointment
- Material Design UI
- Integrates with existing `AppointmentProvider`

#### Appointment Provider Updates
- Added `getAppointmentsForDay()` helper
- Added `loadAppointments()` alias
- Existing CRUD operations work seamlessly

### 2. Web Configuration Files

#### Firebase SDK Integration (`web/index.html`)
- Firebase SDK scripts (v9.23.0)
- Firebase initialization
- Service Worker registration
- Auto-updates on new versions

#### Service Worker (`web/firebase-messaging-sw.js`)
- Background message handler
- Notification display with custom UI
- Click/close event handlers
- Deep linking to appointments
- Action buttons (View, Dismiss)

### 3. Supabase Backend

#### Database Schema (`supabase/migrations/20260109_fcm_schema.sql`)

**Tables**:
- `user_fcm_tokens`: Stores FCM tokens per user/device
- `appointments`: Meeting appointments with reminder settings

**Features**:
- Row Level Security (RLS) enabled
- Indexes for performance
- Helper functions for queries
- Triggers for `updated_at` timestamps

**Helper Functions**:
- `get_upcoming_appointments_for_reminder()`: Query appointments needing reminders
- `mark_notification_sent()`: Update notification status
- `reset_notifications()`: Testing utility

#### Edge Function (`supabase/functions/send-appointment-reminder/index.ts`)

**Functionality**:
- Runs every 1 minute via cron
- Queries appointments within 15-minute window
- Sends FCM notifications to all user devices
- Updates `notification_sent` flag
- Error handling and logging

**FCM Integration**:
- Uses FCM HTTP v1 API
- Supports multiple devices per user
- Custom notification payload
- Web Push specific options

### 4. Documentation

#### Setup Guides
- **FCM_SETUP.md**: Complete step-by-step setup guide (production-ready)
- **QUICK_START_FCM.md**: 10-minute quick start guide
- **FCM_IMPLEMENTATION_SUMMARY.md**: This file

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Flutter Web App (PWA)                   │
├─────────────────────────────────────────────────────────────┤
│  ┌───────────────┐      ┌──────────────┐                   │
│  │ Scheduler UI  │─────▶│ FCM Service  │                   │
│  │ (Calendar)    │      │ (Token Mgmt) │                   │
│  └───────────────┘      └──────┬───────┘                   │
│                                 │                            │
│                                 ▼                            │
│                   ┌─────────────────────┐                   │
│                   │ Service Worker      │                   │
│                   │ (Background Push)   │                   │
│                   └─────────────────────┘                   │
└─────────────────────┬─────────────────────────────────┬─────┘
                      │                                 │
                      ▼                                 ▼
        ┌─────────────────────────┐       ┌──────────────────┐
        │   Firebase Cloud        │       │    Supabase      │
        │   Messaging (FCM)       │       │    Database      │
        │   ┌─────────────────┐   │       │  ┌─────────────┐ │
        │   │ Push Gateway    │   │       │  │user_fcm_    │ │
        │   │ (Web Push API)  │   │       │  │  tokens     │ │
        │   └─────────────────┘   │       │  ├─────────────┤ │
        └─────────────────────────┘       │  │appointments │ │
                      ▲                   │  └─────────────┘ │
                      │                   └─────────┬─────────┘
                      │                             │
                      │                             ▼
                      │                   ┌──────────────────┐
                      │                   │  Edge Function   │
                      └───────────────────│  (Scheduler)     │
                                          │  ┌─────────────┐ │
                                          │  │ Cron: 1min  │ │
                                          │  │ Query & Send│ │
                                          │  └─────────────┘ │
                                          └──────────────────┘
```

## Data Flow

### 1. Token Registration
```
User opens app
  ↓
FCM Service.initialize()
  ↓
Request notification permission
  ↓
Get FCM token
  ↓
Save to Supabase user_fcm_tokens
```

### 2. Create Appointment
```
User creates appointment
  ↓
AppointmentProvider.createAppointment()
  ↓
Save to Supabase appointments table
  ↓
Set notification_sent = false
```

### 3. Send Reminder
```
Cron triggers Edge Function (every 1 min)
  ↓
Query appointments (next 15 minutes, not sent)
  ↓
Get user FCM tokens
  ↓
Send FCM notification to each device
  ↓
Update notification_sent = true
  ↓
User receives push notification
```

### 4. Notification Interaction
```
User taps notification
  ↓
Service Worker handles click
  ↓
Open/focus app
  ↓
Navigate to appointment details
```

## Key Technologies

| Component | Technology | Version |
|-----------|-----------|---------|
| Frontend | Flutter Web | 3.x |
| State Management | Provider | 6.0.0 |
| Database | PostgreSQL (Supabase) | Latest |
| Push Service | Firebase Cloud Messaging | v1 API |
| Serverless | Supabase Edge Functions (Deno) | Latest |
| Scheduler | pg_cron or external cron | N/A |

## Browser Support

| Browser | Platform | Version | Support |
|---------|----------|---------|---------|
| Safari | iOS | 16.4+ | ✅ Full (PWA required) |
| Safari | macOS | Latest | ✅ Full |
| Chrome | Desktop | Latest | ✅ Full |
| Firefox | Desktop | Latest | ✅ Full |
| Edge | Desktop | Latest | ✅ Full |
| Chrome | iOS | Any | ❌ (iOS restriction) |

**Important**: On iOS, Web Push only works with Safari and requires the app to be added to Home Screen as a PWA.

## Configuration Files

### Required Updates

You must replace placeholders in these files:

1. **`flutter_app/web/index.html`** (lines 43-51)
   - Firebase configuration object

2. **`flutter_app/web/firebase-messaging-sw.js`** (lines 11-18)
   - Firebase configuration object (same as above)

3. **Supabase Edge Function Secrets**
   ```bash
   supabase secrets set FCM_SERVER_KEY="your-key"
   supabase secrets set FCM_PROJECT_ID="your-project-id"
   ```

### Configuration Sources

Get these values from:
- **Firebase Config**: Firebase Console > Project Settings > General > Your apps > Web app
- **FCM Server Key**: Firebase Console > Project Settings > Cloud Messaging > Server key
- **VAPID Key**: Firebase Console > Project Settings > Cloud Messaging > Web Push certificates

## API Endpoints

### Supabase Edge Function

```
POST https://{PROJECT_REF}.supabase.co/functions/v1/send-appointment-reminder
Authorization: Bearer {SERVICE_ROLE_KEY}
Content-Type: application/json

Response:
{
  "message": "Reminder job complete",
  "processed": 5,
  "sent": 4,
  "results": [...]
}
```

### FCM API (used by Edge Function)

```
POST https://fcm.googleapis.com/v1/projects/{PROJECT_ID}/messages:send
Authorization: Bearer {ACCESS_TOKEN}
Content-Type: application/json

Body:
{
  "message": {
    "token": "fcm-token",
    "notification": {...},
    "data": {...},
    "webpush": {...}
  }
}
```

## Database Schema

### user_fcm_tokens

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Foreign key to auth.users |
| token | TEXT | FCM token |
| device_type | TEXT | 'web', 'ios', 'android' |
| platform | TEXT | 'ios', 'android', 'web' |
| created_at | TIMESTAMPTZ | Creation timestamp |
| updated_at | TIMESTAMPTZ | Last update |

### appointments

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Foreign key to auth.users |
| title | TEXT | Meeting title |
| description | TEXT | Optional description |
| location | TEXT | Optional location |
| scheduled_at | TIMESTAMPTZ | Meeting time |
| duration_minutes | INTEGER | Meeting duration |
| notification_sent | BOOLEAN | Reminder sent flag |
| reminder_minutes_before | INTEGER | Reminder timing |
| created_at | TIMESTAMPTZ | Creation timestamp |
| updated_at | TIMESTAMPTZ | Last update |

## Security

### Row Level Security (RLS)

Both tables have RLS enabled with policies:
- Users can only access their own data
- Service role bypasses RLS (for Edge Function)

### Token Security

- FCM tokens stored securely in Supabase
- Service role key never exposed to client
- Firebase config is public (expected by design)
- HTTPS required for Web Push

### Environment Variables

Sensitive keys stored as Supabase secrets:
- `FCM_SERVER_KEY`: FCM API authentication
- `FCM_PROJECT_ID`: Firebase project identifier
- `SUPABASE_SERVICE_ROLE_KEY`: Database access (auto-provided)

## Testing Checklist

- [ ] FCM token generated and saved
- [ ] Service worker registered
- [ ] Notification permission granted
- [ ] Create test appointment
- [ ] Receive foreground notification
- [ ] Receive background notification
- [ ] Notification click opens app
- [ ] Edge Function executes successfully
- [ ] Appointment marked as sent
- [ ] Test on iOS Safari 16.4+
- [ ] Test PWA installation
- [ ] Test token refresh
- [ ] Test multiple devices

## Performance Considerations

### Optimization

- **Cron Frequency**: Every 1 minute (adjustable)
- **Query Window**: 15 minutes before appointment (configurable)
- **Batch Processing**: Handles multiple appointments per run
- **Multi-device**: Sends to all user devices in parallel

### Scalability

- **Token Storage**: Indexed by `user_id` and `token`
- **Appointment Queries**: Composite index on `(scheduled_at, notification_sent)`
- **Edge Function**: Serverless, auto-scales
- **FCM**: Google's infrastructure, highly scalable

## Limitations & Future Enhancements

### Current Limitations

- Fixed 15-minute reminder window
- Single reminder per appointment
- No timezone conversion
- Basic notification UI
- No notification analytics

### Planned Enhancements

- [ ] User-configurable reminder times
- [ ] Multiple reminders per appointment
- [ ] Timezone-aware scheduling
- [ ] Rich notification UI (images, progress bars)
- [ ] Notification analytics dashboard
- [ ] Snooze functionality
- [ ] Custom notification sounds
- [ ] Notification preferences UI
- [ ] A/B testing for notification copy

## Troubleshooting

### Common Issues

**1. Service worker not loading**
- Clear cache: Ctrl+Shift+Delete
- Hard refresh: Ctrl+Shift+R
- Check console for errors

**2. No notifications on iOS**
- iOS 16.4+ required
- Must use Safari
- Add to Home Screen (PWA)
- Check Settings > Safari > Advanced

**3. Edge Function errors**
- Check Supabase logs
- Verify secrets are set
- Test FCM_SERVER_KEY validity

**4. Notifications delayed**
- Cron runs every 1 minute
- Reminder window is 15 minutes
- Check server time vs local time

## Deployment Steps

### Development
```bash
# 1. Update Firebase config
# 2. Run migrations
# 3. Deploy Edge Function
# 4. Test locally

flutter run -d chrome
```

### Production
```bash
# 1. Deploy Flutter web app
flutter build web --release
# Deploy to Firebase Hosting, Vercel, etc.

# 2. Deploy Edge Function
supabase functions deploy send-appointment-reminder

# 3. Setup production cron
# 4. Enable HTTPS
# 5. Test on real devices
```

## Monitoring

### Metrics to Track

- FCM token generation rate
- Notification delivery rate
- Notification click-through rate
- Edge Function execution time
- Edge Function error rate
- Appointment creation rate

### Logs

- **Flutter**: Browser console (F12)
- **Edge Function**: Supabase Dashboard > Functions > Logs
- **FCM**: Firebase Console > Cloud Messaging > Reports

## Support & Resources

### Documentation
- Setup guide: `FCM_SETUP.md`
- Quick start: `QUICK_START_FCM.md`
- This summary: `FCM_IMPLEMENTATION_SUMMARY.md`

### External Resources
- [Firebase Cloud Messaging](https://firebase.google.com/docs/cloud-messaging)
- [Flutter Firebase Messaging](https://pub.dev/packages/firebase_messaging)
- [iOS Web Push](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/)
- [Supabase Edge Functions](https://supabase.com/docs/guides/functions)

### Code Locations

```
D:\Productions\meetingminutes\
├── flutter_app\
│   ├── lib\
│   │   ├── services\fcm_service.dart        # FCM logic
│   │   ├── screens\scheduler_screen.dart    # UI
│   │   └── providers\appointment_provider.dart  # State
│   ├── web\
│   │   ├── index.html                       # Config
│   │   └── firebase-messaging-sw.js         # Service Worker
│   └── pubspec.yaml                         # Dependencies
├── supabase\
│   ├── migrations\20260109_fcm_schema.sql   # Schema
│   └── functions\send-appointment-reminder\
│       └── index.ts                         # Edge Function
└── *.md                                     # Documentation
```

---

**Implementation completed**: 2026-01-09
**Status**: Ready for testing and deployment
**Next steps**: Follow QUICK_START_FCM.md for setup
