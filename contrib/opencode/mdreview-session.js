// Expose the opencode session id to shell commands.
//
// opencode marks its presence in the environment (OPENCODE=1) but does not
// export a session id the way Claude Code does. This plugin closes that gap
// through the shell.env hook, which opencode fires for every shell command
// with the session that issued it — so mdreview submissions can record which
// conversation they came from.
//
// Installed to ~/.config/opencode/plugins/ by `mise run setup`.
export const MdreviewSession = async () => ({
  "shell.env": async (input, output) => {
    if (input.sessionID) {
      output.env.OPENCODE_SESSION_ID = input.sessionID;
    }
  },
});
