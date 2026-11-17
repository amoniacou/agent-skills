## Step 0: Send round 1 after the user

The reviewer did not become ready: it waits on a question of its own, for example "trust this folder". Round 1 is not sent. Tell the user to answer the question in the pane `{{name}}`. When the user tells you that it is done, send round 1:

```bash
python3 "{{script}}" ask {{reviewer}} {{directory}} 1
```

Then continue with Step 1.
