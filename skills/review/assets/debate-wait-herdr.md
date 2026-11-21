The reviewer writes the answer of round N to a file in `{{directory}}`. Then it sends the notice `review-N done`. The notice arrives in this session as `<hc from="{{reviewer}} …">review-N done</hc>`. The reviewer pane closes when this session ends.

1. Run this command with `run_in_background`, because a review can take more than 10 minutes:

   ```bash
   hc wait --children any --json --timeout 1800
   ```

2. Do what the result tells:

   | result | do |
   |---|---|
   | the notice of round N from `{{reviewer}}` | print the answer with `python3 "{{script}}" answer {{directory}} N` |
   | `reason: timeout` | wait again |
   | news of a different child, for example the reviewer of an earlier cycle | wait again |
   | `{{reviewer}}` is `blocked` | run `hc read {{reviewer}}`; tell the user what the reviewer waits on; the user answers in the pane; wait again |
   | `{{reviewer}}` has `error`, or it exited | run `hc read {{reviewer}} --lines 50`; tell the user that round N failed; stop the debate |
   | `{{reviewer}}` is `done` or `idle`, with no notice | run the `answer` command; on exit 0, use the answer; on exit 1, if its `turn` is 0, wait again; else run `hc read {{reviewer}} --lines 50`, tell the user, and stop |

   Do not read the answer file with Read: the file is outside the project, and Read asks the user for a permission.

The notice can arrive late while the user types in this session: `hc` waits up to 60 seconds for the draft of the user.
