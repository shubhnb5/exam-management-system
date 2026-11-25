// Firebase Phone Authentication (used when the backend runs with
// OTP_PROVIDER=firebase). Google sends the OTP SMS; after the student enters
// the code, Firebase returns a signed ID token that our backend verifies.
// The Firebase SDK is loaded lazily, only when this channel is in use.

let verifier = null;

async function loadAuth(config) {
  const [{ initializeApp, getApps }, authModule] = await Promise.all([import("firebase/app"), import("firebase/auth")]);
  const app = getApps().find((a) => a.name === "student-otp") || initializeApp(config, "student-otp");
  const auth = authModule.getAuth(app);
  auth.languageCode = "en";
  return { auth, authModule };
}

/** Sends the OTP SMS to +91<mobile>. Returns a confirmation handle. */
export async function sendFirebaseOtp(config, mobile, container) {
  const { auth, authModule } = await loadAuth(config);
  if (verifier) {
    try {
      verifier.clear();
    } catch {
      // already cleared
    }
    verifier = null;
  }
  // A fresh element each time: reCAPTCHA can only render once per element.
  container.innerHTML = "";
  const el = document.createElement("div");
  container.appendChild(el);
  verifier = new authModule.RecaptchaVerifier(auth, el, { size: "invisible" });
  return authModule.signInWithPhoneNumber(auth, `+91${mobile}`, verifier);
}

/** Checks the code with Firebase; returns the ID token for our backend. */
export async function confirmFirebaseOtp(confirmation, code) {
  const credential = await confirmation.confirm(code);
  const idToken = await credential.user.getIdToken();
  try {
    // We only need the proof; the student's session is our own login.
    await credential.user.auth.signOut();
  } catch {
    // ignore
  }
  return idToken;
}

export function isFirebaseError(err) {
  return typeof err?.code === "string" && err.code.startsWith("auth/");
}

export function firebaseErrorMessage(err) {
  if (/api-key|admin-restricted|app-not-authorized/.test(err?.code || "")) {
    return "OTP service is not set up correctly yet. Please contact the admin.";
  }
  switch (err?.code) {
    case "auth/invalid-verification-code":
    case "auth/missing-verification-code":
      return "Incorrect OTP. Please check the code and try again.";
    case "auth/code-expired":
      return "This OTP has expired. Please request a new one.";
    case "auth/too-many-requests":
      return "Too many attempts. Please wait a while and try again.";
    case "auth/invalid-phone-number":
      return "Enter a valid 10-digit mobile number.";
    case "auth/quota-exceeded":
      return "The OTP service is busy right now. Please try again in a few minutes.";
    case "auth/network-request-failed":
      return "Network problem. Check your internet connection and try again.";
    case "auth/captcha-check-failed":
    case "auth/invalid-app-credential":
    case "auth/missing-app-credential":
      return "Security check failed. Please refresh the page and try again.";
    case "auth/unauthorized-domain":
    case "auth/operation-not-allowed":
    case "auth/billing-not-enabled":
    case "auth/invalid-api-key":
      return "OTP service is not set up correctly yet. Please contact the admin.";
    default:
      return "Could not complete the OTP step. Please try again.";
  }
}
