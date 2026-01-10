// Firebase Cloud Messaging Service Worker
// Handles Web Push notifications for iOS Safari 16.4+ and other browsers
// Version: 1.0.0

// Import Firebase scripts (compat mode for service workers)
importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-messaging-compat.js');

// Firebase configuration for meeting-minutes-pwa
const firebaseConfig = {
  apiKey: "AIzaSyAGvZ2nnNsR-FmIsvADneCIcqeP4eJiuOE",
  authDomain: "meeting-minutes-pwa.firebaseapp.com",
  projectId: "meeting-minutes-pwa",
  storageBucket: "meeting-minutes-pwa.firebasestorage.app",
  messagingSenderId: "654552775170",
  appId: "1:654552775170:web:fc3f1f322df3a5481c451b",
  measurementId: "G-ZYX3HCDZFW"
};

// Initialize Firebase
firebase.initializeApp(firebaseConfig);

// Initialize Firebase Messaging
const messaging = firebase.messaging();

// Handle background messages (when app is closed or in background)
messaging.onBackgroundMessage((payload) => {
  console.log('[SW] Background message received:', payload);

  // Extract notification data
  const notificationTitle = payload.notification?.title || 'Meeting Reminder';
  const notificationBody = payload.notification?.body || 'You have an upcoming meeting';
  const appointmentId = payload.data?.appointment_id || payload.data?.appointmentId;
  const meetingTitle = payload.data?.meeting_title || payload.data?.meetingTitle;
  const meetingTime = payload.data?.meeting_time || payload.data?.meetingTime;

  // Build notification options
  const notificationOptions = {
    body: notificationBody,
    icon: '/icons/Icon-192.png',
    badge: '/icons/Icon-192.png',
    image: payload.notification?.image, // Optional banner image
    data: {
      appointmentId: appointmentId,
      meetingTitle: meetingTitle,
      meetingTime: meetingTime,
      url: appointmentId ? `/?appointment=${appointmentId}` : '/',
      timestamp: Date.now()
    },
    tag: appointmentId || 'meeting-reminder', // Prevents duplicate notifications
    requireInteraction: true, // Notification stays until dismissed
    vibrate: [200, 100, 200], // Vibration pattern (mobile)
    actions: [
      {
        action: 'view',
        title: 'View Meeting',
        icon: '/icons/Icon-192.png'
      },
      {
        action: 'dismiss',
        title: 'Dismiss',
        icon: '/icons/Icon-192.png'
      }
    ]
  };

  // Show notification
  return self.registration.showNotification(notificationTitle, notificationOptions);
});

// Handle notification click events
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification clicked:', event.notification.tag);

  // Close the notification
  event.notification.close();

  const action = event.action;
  const appointmentId = event.notification.data?.appointmentId;
  const url = event.notification.data?.url || '/';

  // Handle action buttons
  if (action === 'dismiss') {
    console.log('[SW] Notification dismissed');
    return;
  }

  // Default action or 'view' button: Open app
  event.waitUntil(
    clients.matchAll({
      type: 'window',
      includeUncontrolled: true
    }).then((windowClients) => {
      // Check if app is already open
      for (const client of windowClients) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          // App is open, focus it and send message
          console.log('[SW] Focusing existing window');
          client.focus();
          client.postMessage({
            type: 'NOTIFICATION_CLICK',
            appointmentId: appointmentId,
            timestamp: Date.now()
          });
          return client;
        }
      }

      // App is not open, open new window
      if (clients.openWindow) {
        console.log('[SW] Opening new window:', url);
        return clients.openWindow(url);
      }
    })
  );
});

// Handle notification close events
self.addEventListener('notificationclose', (event) => {
  console.log('[SW] Notification closed:', event.notification.tag);

  // Optional: Send analytics event to track notification dismissals
  const appointmentId = event.notification.data?.appointmentId;
  if (appointmentId) {
    // Track dismissal in analytics or backend
    console.log('[SW] Appointment notification dismissed:', appointmentId);
  }
});

// Handle push events (alternative to onBackgroundMessage)
self.addEventListener('push', (event) => {
  console.log('[SW] Push event received');

  if (event.data) {
    try {
      const payload = event.data.json();
      console.log('[SW] Push payload:', payload);

      // This is handled by onBackgroundMessage above
      // Only implement custom logic here if needed
    } catch (e) {
      console.error('[SW] Error parsing push payload:', e);
    }
  }
});

// Service Worker activation
self.addEventListener('activate', (event) => {
  console.log('[SW] Service Worker activated');

  // Cleanup old caches if needed
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          // Add cache cleanup logic if needed
          console.log('[SW] Cache found:', cacheName);
        })
      );
    })
  );
});

// Service Worker installation
self.addEventListener('install', (event) => {
  console.log('[SW] Service Worker installed');

  // Skip waiting to activate immediately
  self.skipWaiting();
});

// Handle message events from app
self.addEventListener('message', (event) => {
  console.log('[SW] Message received from app:', event.data);

  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

console.log('[SW] Firebase Messaging Service Worker loaded');
