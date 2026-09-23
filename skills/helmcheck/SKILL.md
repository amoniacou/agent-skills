# Helm Validation Check
1. Run `helm template` on the changed chart with appropriate values
2. Check ALL required args, env vars, and volume mounts are present
3. Verify no duplicate keys exist
4. Report all errors at once, not one at a time
