# TECH_modul_qt — контекст роботи (DEV LOG / HANDOFF)

> Мета цього файлу: щоб ми рухались швидко. Тут зібрано все важливе, що вже зроблено, які правила прийняли, де болить, і які команди/шляхи використовуємо.

---

## 0) Середовище / шляхи

- Проєкт: `C:\PythonProject\TECH_modul\TECH_modul_qt`
- Python venv: `C:\PythonProject\TECH_modul\TECH_modul_qt\.venv\Scripts\python.exe`
- Основний проблемний файл (дуже зв’язаний):  
  `src\tabs\module_widget.py`
- Дані модулів:  
  `data\modules.json` (НЕ `src\data\modules.json`)
- Запуск (shell):  
  `& $py (Join-Path $proj "src\main.py")`

Рекомендовані змінні перед тестами:
```powershell
chcp 65001 | Out-Null
$env:PYTHONIOENCODING="utf-8"
$env:PYTHONPATH = (Join-Path $proj "src")
