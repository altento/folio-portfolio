# Tk domain extraction startup smoke

The updated Tk entry point started from a temporary copy after the model extraction. It loaded three generated demonstration projects and wrote to an isolated SQLite file in Windows Temp. The evidence records the UI Automation limitation: inner Tk controls remain absent from the UIA tree. This is startup smoke only, not a full workflow or screen-reader acceptance.
