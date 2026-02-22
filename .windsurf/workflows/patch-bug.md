---
description: Auto-patch a bug reported by the Titan Bug Reporter app
---

# Patch Bug Workflow

When the Bug Reporter app creates a patch task, follow these steps:

1. Read the patch task file from `/opt/titan/state/patches/task_<id>.md`
// turbo
2. Read the referenced module source file from `/opt/titan/core/<module_name>.py`
3. Analyze the bug description, error log, and patch instructions
4. Identify the root cause in the source code
5. Implement the minimal fix that resolves the issue without breaking other functionality
6. If the bug is a decline pattern, check `transaction_monitor.py` decline code mappings and update if needed
7. If the bug is a detection vector, verify no branded strings, window globals, or console logs leak to the browser
8. Test the fix by checking for syntax errors: `python3 -c "import py_compile; py_compile.compile('<file>', doraise=True)"`
9. Update the patch task JSON status to "patched" and record the diff
10. Notify the user that the patch has been applied
