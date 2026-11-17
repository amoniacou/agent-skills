The reviewer writes the answer of round N to a file in `{{directory}}`. Then it sends tuios mail `done` with the subject `review-N`.

1. Run this command with `run_in_background`, because a review can take more than 10 minutes:

   ```bash
   tuios wait-for agent-message -w {{author}} --timeout 1800000
   ```

2. Read the mail at once, because tuios keeps mail only in memory:

   ```bash
   tuios read-agent-messages -w {{author}} --unread --json
   ```

   Use only a message with `from` equal to `{{reviewer}}`. If there is no such message, wait again.

3. Print the answer:

   ```bash
   python3 "{{script}}" answer {{directory}} N
   ```

   Do not read the answer file with Read: the file is outside the project, and Read asks the user for a permission.

If `wait-for` times out, run `tuios list-agents --json`. If the reviewer state is `needs_input`, run `tuios peek-prompt -w {{reviewer}}` and tell the user at once what the reviewer waits on. The user answers in the tuios Inbox or in the pane. Do not answer it yourself.
