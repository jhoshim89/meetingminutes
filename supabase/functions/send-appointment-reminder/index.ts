// Supabase Edge Function: Send Appointment Reminder via FCM V1 API
// Scheduled to run every 1 minute via cron job
// Sends Web Push notifications to users for upcoming meetings
//
// Required Secrets:
// - SUPABASE_URL (auto-injected)
// - SUPABASE_SERVICE_ROLE_KEY (auto-injected)
// - FIREBASE_SERVICE_ACCOUNT_JSON (service account JSON from Firebase Console)

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.39.0";
import { create, getNumericDate } from "https://deno.land/x/djwt@v2.9.1/mod.ts";
import { decode as base64Decode } from "https://deno.land/std@0.168.0/encoding/base64.ts";

// Environment variables
const SUPABASE_URL = Deno.env.get("SUPABASE_URL") || "";
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
const FIREBASE_SERVICE_ACCOUNT_JSON = Deno.env.get("FIREBASE_SERVICE_ACCOUNT_JSON") || "";

// FCM V1 API constants
const FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging";
const GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token";

// Cached access token
let cachedAccessToken: string | null = null;
let tokenExpiry: number = 0;

interface ServiceAccount {
  type: string;
  project_id: string;
  private_key_id: string;
  private_key: string;
  client_email: string;
  client_id: string;
  auth_uri: string;
  token_uri: string;
}

interface Appointment {
  id: string;
  user_id: string;
  title: string;
  scheduled_at: string;
  location?: string;
  description?: string;
  notification_sent: boolean;
  reminder_minutes: number;
}

interface FCMToken {
  token: string;
  device_type: string;
  platform: string;
}

serve(async (req) => {
  try {
    console.log("[Reminder] Starting appointment reminder job");

    // Validate service account is configured
    if (!FIREBASE_SERVICE_ACCOUNT_JSON) {
      throw new Error("FIREBASE_SERVICE_ACCOUNT_JSON not configured. Set in Supabase Edge Function secrets.");
    }

    // Initialize Supabase client with service role key (bypasses RLS)
    const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

    // 1. Query upcoming appointments that need reminders
    // Get appointments where reminder_time is now (scheduled_at - reminder_minutes)
    const now = new Date();
    const reminderWindow = new Date(now.getTime() + 15 * 60 * 1000); // 15 minutes ahead

    const { data: appointments, error: appointmentsError } = await supabase
      .from("appointments")
      .select("*")
      .gte("scheduled_at", now.toISOString())
      .lte("scheduled_at", reminderWindow.toISOString())
      .eq("notification_sent", false)
      .eq("status", "pending")
      .order("scheduled_at", { ascending: true });

    if (appointmentsError) {
      throw new Error(`Query error: ${appointmentsError.message}`);
    }

    if (!appointments || appointments.length === 0) {
      console.log("[Reminder] No appointments need reminders");
      return new Response(
        JSON.stringify({ message: "No reminders to send", count: 0 }),
        { headers: { "Content-Type": "application/json" }, status: 200 }
      );
    }

    console.log(`[Reminder] Found ${appointments.length} appointments`);

    // 2. Process each appointment
    const results = await Promise.all(
      appointments.map(async (appointment: Appointment) => {
        try {
          // Check if it's time to send reminder (scheduled_at - reminder_minutes)
          const scheduledTime = new Date(appointment.scheduled_at);
          const reminderTime = new Date(scheduledTime.getTime() - (appointment.reminder_minutes || 5) * 60 * 1000);

          // Only send if current time is past reminder time
          if (now < reminderTime) {
            console.log(`[Reminder] Not yet time for appointment ${appointment.id}`);
            return { appointmentId: appointment.id, sent: false, reason: "Not yet time" };
          }

          // Get user's FCM tokens
          const { data: tokens, error: tokensError } = await supabase
            .from("user_fcm_tokens")
            .select("token, device_type, platform")
            .eq("user_id", appointment.user_id);

          if (tokensError || !tokens || tokens.length === 0) {
            console.log(`[Reminder] No FCM tokens for user ${appointment.user_id}`);
            return { appointmentId: appointment.id, sent: false, reason: "No tokens" };
          }

          // Send notification to each device
          const sendResults = await Promise.all(
            tokens.map((tokenData: FCMToken) =>
              sendFCMNotification(appointment, tokenData.token)
            )
          );

          const successCount = sendResults.filter((r) => r.success).length;

          // Update notification_sent flag if at least one succeeded
          if (successCount > 0) {
            await supabase
              .from("appointments")
              .update({ notification_sent: true })
              .eq("id", appointment.id);

            console.log(`[Reminder] Sent to ${successCount}/${tokens.length} devices for appointment ${appointment.id}`);
          }

          return {
            appointmentId: appointment.id,
            sent: successCount > 0,
            devicesNotified: successCount,
            totalDevices: tokens.length,
          };
        } catch (error) {
          console.error(`[Reminder] Error processing appointment ${appointment.id}:`, error);
          return { appointmentId: appointment.id, sent: false, error: error.message };
        }
      })
    );

    // 3. Return summary
    const totalSent = results.filter((r) => r.sent).length;
    console.log(`[Reminder] Job complete: ${totalSent}/${appointments.length} notifications sent`);

    return new Response(
      JSON.stringify({
        message: "Reminder job complete",
        processed: appointments.length,
        sent: totalSent,
        results: results,
      }),
      { headers: { "Content-Type": "application/json" }, status: 200 }
    );
  } catch (error) {
    console.error("[Reminder] Job failed:", error);
    return new Response(
      JSON.stringify({ error: error.message }),
      { headers: { "Content-Type": "application/json" }, status: 500 }
    );
  }
});

/**
 * Send FCM Web Push notification using HTTP v1 API
 */
async function sendFCMNotification(
  appointment: Appointment,
  fcmToken: string
): Promise<{ success: boolean; error?: string }> {
  try {
    // Parse service account to get project ID
    const serviceAccount: ServiceAccount = JSON.parse(FIREBASE_SERVICE_ACCOUNT_JSON);
    const projectId = serviceAccount.project_id;
    const fcmEndpoint = `https://fcm.googleapis.com/v1/projects/${projectId}/messages:send`;

    // Calculate time until meeting
    const scheduledTime = new Date(appointment.scheduled_at);
    const now = new Date();
    const minutesUntil = Math.floor((scheduledTime.getTime() - now.getTime()) / (1000 * 60));

    // Build notification payload for FCM V1 API
    const message = {
      message: {
        token: fcmToken,
        notification: {
          title: "Meeting Reminder",
          body: `"${appointment.title}" starts in ${minutesUntil} minutes`,
        },
        data: {
          appointment_id: appointment.id,
          meeting_title: appointment.title,
          meeting_time: appointment.scheduled_at,
          minutes_until: minutesUntil.toString(),
          click_action: `/?appointment=${appointment.id}`,
        },
        webpush: {
          notification: {
            icon: "/icons/Icon-192.png",
            badge: "/icons/Icon-192.png",
            requireInteraction: true,
            tag: appointment.id, // Prevents duplicates
          },
          fcm_options: {
            link: `/?appointment=${appointment.id}`,
          },
        },
      },
    };

    // Get OAuth2 access token for FCM V1 API
    const accessToken = await getAccessToken();

    // Send to FCM
    const response = await fetch(fcmEndpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify(message),
    });

    if (!response.ok) {
      const errorData = await response.json();
      console.error(`[FCM] Error sending to token ${fcmToken.substring(0, 20)}...:`, errorData);

      // Handle specific errors
      const errorCode = errorData.error?.details?.[0]?.errorCode;
      if (errorCode === "UNREGISTERED" || errorCode === "INVALID_ARGUMENT") {
        // Token is invalid, should be removed from database
        console.log(`[FCM] Token is invalid, should remove from database`);
      }

      return { success: false, error: errorData.error?.message || "Unknown error" };
    }

    const result = await response.json();
    console.log(`[FCM] Sent successfully:`, result.name);
    return { success: true };
  } catch (error) {
    console.error("[FCM] Send error:", error);
    return { success: false, error: error.message };
  }
}

/**
 * Get OAuth2 access token for FCM V1 API using Service Account
 *
 * Flow:
 * 1. Create JWT signed with service account private key
 * 2. Exchange JWT for OAuth2 access token
 * 3. Cache token until expiry
 */
async function getAccessToken(): Promise<string> {
  // Return cached token if still valid (with 5 minute buffer)
  const now = Date.now();
  if (cachedAccessToken && tokenExpiry > now + 5 * 60 * 1000) {
    console.log("[OAuth] Using cached access token");
    return cachedAccessToken;
  }

  console.log("[OAuth] Generating new access token");

  // Parse service account JSON
  const serviceAccount: ServiceAccount = JSON.parse(FIREBASE_SERVICE_ACCOUNT_JSON);

  // Create JWT header and claims
  const header = { alg: "RS256", typ: "JWT" };
  const issuedAt = Math.floor(now / 1000);
  const expiresAt = issuedAt + 3600; // 1 hour

  const claims = {
    iss: serviceAccount.client_email,
    sub: serviceAccount.client_email,
    aud: GOOGLE_TOKEN_URL,
    iat: issuedAt,
    exp: expiresAt,
    scope: FCM_SCOPE,
  };

  // Import private key for signing
  const privateKey = await importPrivateKey(serviceAccount.private_key);

  // Create signed JWT
  const jwt = await create(header, claims, privateKey);

  // Exchange JWT for access token
  const tokenResponse = await fetch(GOOGLE_TOKEN_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
      assertion: jwt,
    }),
  });

  if (!tokenResponse.ok) {
    const error = await tokenResponse.text();
    throw new Error(`Failed to get access token: ${error}`);
  }

  const tokenData = await tokenResponse.json();

  // Cache the token
  cachedAccessToken = tokenData.access_token;
  tokenExpiry = now + (tokenData.expires_in * 1000);

  console.log("[OAuth] Access token obtained successfully");
  return cachedAccessToken;
}

/**
 * Import PEM private key for JWT signing
 */
async function importPrivateKey(pemKey: string): Promise<CryptoKey> {
  // Remove PEM headers and decode base64
  const pemContents = pemKey
    .replace("-----BEGIN PRIVATE KEY-----", "")
    .replace("-----END PRIVATE KEY-----", "")
    .replace(/\n/g, "")
    .replace(/\r/g, "")
    .trim();

  const binaryKey = base64Decode(pemContents);

  // Import as PKCS#8 private key
  const key = await crypto.subtle.importKey(
    "pkcs8",
    binaryKey,
    {
      name: "RSASSA-PKCS1-v1_5",
      hash: "SHA-256",
    },
    false,
    ["sign"]
  );

  return key;
}

console.log("[Reminder] Function loaded and ready (FCM V1 API)");
