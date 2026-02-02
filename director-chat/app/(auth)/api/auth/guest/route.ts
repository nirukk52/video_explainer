import { NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";
import { signIn } from "@/app/(auth)/auth";
import { isDevelopmentEnvironment } from "@/lib/constants";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const redirectUrl = searchParams.get("redirectUrl") || "/";

  const token = await getToken({
    req: request,
    secret: process.env.AUTH_SECRET,
    secureCookie: !isDevelopmentEnvironment,
  });

  if (token) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  try {
    return await signIn("guest", { redirect: true, redirectTo: redirectUrl });
  } catch (err) {
    console.error("[auth] guest signIn failed:", err);
    const cause = err instanceof Error ? err.cause : undefined;
    const message =
      cause instanceof Error ? cause.message : "Guest sign-in failed";
    return NextResponse.redirect(
      new URL(`/login?error=GuestSignInFailed&message=${encodeURIComponent(message)}`, request.url)
    );
  }
}
