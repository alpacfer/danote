import { fireEvent, render, screen } from "@testing-library/react"

import App from "@/App"
import { SAVED_NOTES_STORAGE_KEY } from "@/app/core/constants"

export function renderApp() {
  return render(<App />)
}

export function seedSavedNotes(notes: unknown[]) {
  window.localStorage.setItem(SAVED_NOTES_STORAGE_KEY, JSON.stringify(notes))
}

export async function waitForAppReady() {
  return screen.findByLabelText("backend-connection-status")
}

export function responseOf(payload: unknown): Response {
  return {
    ok: true,
    status: 200,
    json: async () => payload,
  } as Response
}

export function getNotesEditor(): HTMLElement {
  return screen.getByRole("textbox", { name: /lesson notes/i })
}

export function setNotesEditorText(value: string) {
  const input = screen.getByTestId("lesson-notes-test-input")
  fireEvent.change(input, { target: { value } })
}
