import { SignInButton } from "@clerk/react"
import { type ReactNode } from "react"

type AuthSignInButtonProps = {
  children: ReactNode
}

const POST_SIGN_IN_URL = "/"

export function AuthSignInButton({ children }: AuthSignInButtonProps) {
  return (
    <SignInButton
      mode="modal"
      forceRedirectUrl={POST_SIGN_IN_URL}
      fallbackRedirectUrl={POST_SIGN_IN_URL}
      signUpForceRedirectUrl={POST_SIGN_IN_URL}
      signUpFallbackRedirectUrl={POST_SIGN_IN_URL}
    >
      {children}
    </SignInButton>
  )
}
