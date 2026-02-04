# Project notes

## Python scripts: use the venv

There is a virtual environment at `python/.venv/`. If `python` isn’t found in your terminal, you likely just need to activate the venv first.

Activate (PowerShell):

```powershell
Set-Location "d:/Sync/Python Code/CursorDnD/python"
. .venv/Scripts/Activate.ps1
```

Run without activation (uses venv interpreter directly):

```powershell
& "d:/Sync/Python Code/CursorDnD/python/.venv/Scripts/python.exe" gm_loop.py --player human
```

