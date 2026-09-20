import { handleSignIn, handleSignOut } from "@/lib/bff/reviewer-session-handler";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// BFF-AUTH: auth_sign_in. The API's one-time tokens become HttpOnly cookies, never a response body.
export function POST(request: Request): Promise<Response> {
  return handleSignIn(request);
}

// BFF-AUTH: auth_sign_out. Always clears the local cookies.
export function DELETE(request: Request): Promise<Response> {
  return handleSignOut(request);
}
