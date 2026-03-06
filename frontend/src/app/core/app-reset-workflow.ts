export type AppResetWorkflowParams = {
  resetEditorState: () => void
  resetLexiconState: () => void
  clearVerificationErrors: () => void
  bumpWordbankRefresh: () => void
  bumpSentencebankRefresh: () => void
}

export function runAppDatabaseResetWorkflow(params: AppResetWorkflowParams) {
  params.resetEditorState()
  params.resetLexiconState()
  params.clearVerificationErrors()
  params.bumpWordbankRefresh()
  params.bumpSentencebankRefresh()
}
