@echo off
:: 1. Kich hoat moi truong ao (Thay 'venv' bang ten thu muc venv cua ban)
call venv\Scripts\activate

:: 2. Chay cac lenh python
echo --- Dang cap nhat PROJECT_MANIFEST.md ---
python get_manifest.py



:: 3. Thong bao hoan tat
echo --- Hoan tat! Kiem tra docs/architecture_erd.png va PROJECT_MANIFEST.md ---
pause