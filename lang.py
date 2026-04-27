"""Localisation module — Russian / English."""
from __future__ import annotations
from pathlib import Path
import json

_CFG = Path(__file__).parent / ".msdos_agent.json"
_LANG = "ru"   # default; overridden by load()


def load(cfg: dict) -> None:
    global _LANG
    _LANG = cfg.get("lang", "ru")


def t(key: str, **kw) -> str:
    s = _STRINGS.get(_LANG, _STRINGS["ru"]).get(key, _STRINGS["ru"].get(key, key))
    return s.format(**kw) if kw else s


# ── all UI strings ─────────────────────────────────────────────────────────────
_STRINGS: dict[str, dict[str, str]] = {

# ══════════════════════════════════════════════════════════════════════════════
"ru": {

# window / title
"win_title":        "ClaudeNC.exe",
"title_bar":        "▓▓ ClaudeNC.exe  v3.0  ─────────  Norton Commander Style  ─────────  C:\\>ClaudeNC.EXE",

# boot
"boot_version":     "ClaudeNC.exe  Version 3.0",
"boot_engine":      "Движок: PowerShell › claude CLI  │  Dual panel: чат + файловый менеджер",
"boot_hint":        "  F1=Помощь  F4=Применить папку  F6=Новый чат  F10=Выход",

# status bar
"status":           "  Модель: {model}  │  Папка: {workdir}  │  {state}  │  Сообщений: {count}",
"state_ready":      "Готов",
"state_busy":       "Обработка…",
"tokens_empty":     "  Токены: —",
"tokens_fmt":       "  IN: {i:,}  OUT: {o:,}{cache}  │  💰 ${cost:.4f}  ИТОГО: ${total:.4f}  │  ⏱ {dur:.1f}s  ходов: {turns}",
"tokens_cache":     "  КЭШР: {r:,}  КЭШЗ: {w:,}",

# input
"input_placeholder": "Введите сообщение…  /help для команд",
"prompt_label":      "C:\\>",

# fkeys
"fk_help":      "Помощь",
"fk_model":     "Модель",
"fk_view":      "Просмотр",
"fk_applydir":  "Дир▶",
"fk_refresh":   "Обнов",
"fk_newchat":   "Новый чат",
"fk_history":   "История",
"fk_dirup":     "Вверх",
"fk_settings":  "Настр",
"fk_exit":      "Выход",

# chat labels
"you":          "ВЫ",
"stop_btn":     "■ СТОП",
"auto_btn_on":  "⚡ AUTO",
"stopped":      "  ■ Задание остановлено.",
"exit_code":    "  Код выхода: {rc}",
"error_prefix": "  ОШИБКА: ",
"tool_use":     "  🔧 {name}({args})",
"perm_warn":    "  ⚠  Требуется разрешение: {tool} → {target}",

# auto toggle
"auto_on_msg":  "  ⚡ AUTO ON  — разрешения пропускаются автоматически",
"auto_off_msg": "  ⚠  AUTO OFF — claude будет запрашивать разрешения (зависнет в -p режиме!)",
"auto_on_tip":  "AUTO ON  — claude работает без подтверждений (--dangerously-skip-permissions)\nAUTO OFF — claude будет запрашивать разрешение",

# new chat / model
"new_chat_msg": "  Новый чат. Сессия сброшена.",
"model_changed":"  Модель: {model}  (новая сессия)",
"allowed_tools":"  Разрешено: {tools}",
"screen_cleared":"  Экран очищен.",

# apply dir
"dir_applied":  "  ✓ Рабочая папка Claude: {path}",
"dir_invalid":  "  Выберите папку в правой панели.",
"dir_prompt":   "  Выберите папку и нажмите F4 или кнопку 'Дир▶'.",

# history
"history_empty":"  История папок пуста.",
"history_title":"  Последние папки:",

# file manager
"fm_path":      "  ═══  {path}  ═══",
"fm_info":      "  Папок: {dirs}   Файлов: {files}",
"fm_no_access": "  Нет доступа к папке",
"fm_error":     "  Ошибка: {err}",
"fm_up":        "  ▲ ..   (на уровень выше)",

# view file
"view_select":  "  Выберите файл в правой панели.",
"view_read_err":"Ошибка чтения: {err}",
"view_close":   "  Закрыть (ESC)  ",
"view_title":   "Просмотр: {name}",

# slash cmd
"slash_echo":   "  › {cmd}",
"slash_bad":    "  Неизвестная команда. Отправляю в claude...",

# error / not found
"claude_not_found": "ОШИБКА: 'claude' не найден в PATH. Установите: https://claude.ai/code",

# retry bar
"retry_label":  "  ⚠  Claude не смог выполнить действие — недостаточно прав.",
"retry_btn":    "  ↺ Расширить разрешения и продолжить  ",
"retry_msg":    "  ↺ Продолжение с расширенными правами: {tools}",
"retry_prompt": "Продолжи выполнение задания с новыми разрешениями.",

# quit dialog
"quit_title":   "Выход",
"quit_msg":     "Claude обрабатывает запрос. Всё равно выйти?",

# help dialog
"help_title":   "Помощь",
"help_content": (
    "<pre>"
    "<span style='color:#ffff55;font-weight:bold'>MS-DOS CLAUDE AGENT v3.0</span>\n\n"
    "<span style='color:#ffff55'>F1</span>  Помощь             <span style='color:#ffff55'>F2</span>  Сменить модель\n"
    "<span style='color:#ffff55'>F3</span>  Просмотр файла     <span style='color:#ffff55'>F4</span>  Применить папку\n"
    "<span style='color:#ffff55'>F5</span>  Обновить список    <span style='color:#ffff55'>F6</span>  Новый чат\n"
    "<span style='color:#ffff55'>F7</span>  История папок      <span style='color:#ffff55'>F8</span>  Перейти вверх\n"
    "<span style='color:#ffff55'>F9</span>  Настройки          <span style='color:#ffff55'>F10</span> Выход\n\n"
    "<span style='color:#00cc00'>КОМАНДЫ:</span>\n"
    "  /help  /agents  /new  /cls\n"
    "  /model opus|sonnet|haiku\n\n"
    "<span style='color:#00cc00'>НАВИГАЦИЯ:</span>\n"
    "  Двойной клик — открыть папку\n"
    "  Tab — переключить фокус чат↔файлы\n"
    "  F4 — применить текущую папку\n"
    "  Ctrl+N — новый чат  Ctrl+L — очистить\n"
    "</pre>"
),
"help_ok":      "  OK  ",

# settings dialog
"settings_title":    "Настройки",
"settings_lang":     "Язык интерфейса:",
"settings_model":    "Модель по умолчанию:",
"settings_dir":      "Начальная директория:",
"settings_dir_hint": "Папка, которая открывается при запуске",
"settings_save":     "  Сохранить  ",
"settings_cancel":   "  Отмена  ",
"settings_restart":  "Язык изменён. Перезапустите приложение для применения.",

# tool select dialog
"tools_title":    "MANUAL режим — выберите разрешения",
"tools_header":   "  Что разрешить Claude для этого запроса?\n",
"tools_run":      "  ▶ Выполнить  ",
"tools_cancel":   "  ✕ Отмена  ",

# tool names
"tool_Write":     "Write     — создавать новые файлы",
"tool_Edit":      "Edit      — редактировать файлы",
"tool_MultiEdit": "MultiEdit — массовое редактирование",
"tool_Bash":      "Bash      — выполнять команды оболочки",
"tool_Read":      "Read      — читать файлы",
"tool_Glob":      "Glob      — поиск файлов по маске",
"tool_Grep":      "Grep      — поиск по содержимому",
"tool_LS":        "LS        — список файлов",
"tool_WebFetch":  "WebFetch  — получать страницы из интернета",
"tool_WebSearch": "WebSearch — поиск в интернете",
"tool_TodoWrite": "Todo      — управление задачами",

"tools_none":     "ничего",

# perm dialog
"perm_title":     "⚠  Требуется разрешение",
"perm_header":    "  ⚠  Claude запрашивает разрешение:",
"perm_yes":       "Да (Yes)",
"perm_no":        "Нет (No)",
"perm_always":    "Всегда (Always)",
"perm_deny":      "Запретить (Deny)",

# settings info in chat (legacy)
"info_model":     "  Модель        : {model}",
"info_workdir":   "  Рабочая папка : {workdir}",
"info_curdir":    "  Браузер папок : {curdir}",
"info_cfg":       "  Конфиг-файл   : {cfg}",
"info_platform":  "  Платформа     : {platform}",
"info_auto":      "  AUTO режим    : {auto}",
"info_auto_on":   "ON (авто-разрешения)",
"info_auto_off":  "OFF (ручное подтверждение)",

},  # end ru

# ══════════════════════════════════════════════════════════════════════════════
"en": {

"win_title":        "ClaudeNC.exe",
"title_bar":        "▓▓ ClaudeNC.exe  v3.0  ─────────  Norton Commander Style  ─────────  C:\\>ClaudeNC.EXE",

"boot_version":     "ClaudeNC.exe  Version 3.0",
"boot_engine":      "Engine: PowerShell › claude CLI  │  Dual panel: chat + file manager",
"boot_hint":        "  F1=Help  F4=Apply dir  F6=New chat  F10=Exit",

"status":           "  Model: {model}  │  Dir: {workdir}  │  {state}  │  Messages: {count}",
"state_ready":      "Ready",
"state_busy":       "Processing…",
"tokens_empty":     "  Tokens: —",
"tokens_fmt":       "  IN: {i:,}  OUT: {o:,}{cache}  │  💰 ${cost:.4f}  TOTAL: ${total:.4f}  │  ⏱ {dur:.1f}s  turns: {turns}",
"tokens_cache":     "  CR: {r:,}  CW: {w:,}",

"input_placeholder": "Type a message…  /help for commands",
"prompt_label":      "C:\\>",

"fk_help":      "Help",
"fk_model":     "Model",
"fk_view":      "View",
"fk_applydir":  "Dir▶",
"fk_refresh":   "Refresh",
"fk_newchat":   "New Chat",
"fk_history":   "History",
"fk_dirup":     "Up",
"fk_settings":  "Settings",
"fk_exit":      "Exit",

"you":          "YOU",
"stop_btn":     "■ STOP",
"auto_btn_on":  "⚡ AUTO",
"stopped":      "  ■ Task stopped.",
"exit_code":    "  Exit code: {rc}",
"error_prefix": "  ERROR: ",
"tool_use":     "  🔧 {name}({args})",
"perm_warn":    "  ⚠  Permission required: {tool} → {target}",

"auto_on_msg":  "  ⚡ AUTO ON  — permissions skipped automatically",
"auto_off_msg": "  ⚠  AUTO OFF — claude will request permissions (will hang in -p mode!)",
"auto_on_tip":  "AUTO ON  — claude runs without confirmations (--dangerously-skip-permissions)\nAUTO OFF — claude will ask for permission",

"new_chat_msg": "  New chat. Session reset.",
"model_changed":"  Model: {model}  (new session)",
"allowed_tools":"  Allowed: {tools}",
"screen_cleared":"  Screen cleared.",

"dir_applied":  "  ✓ Claude working directory: {path}",
"dir_invalid":  "  Select a folder in the right panel.",
"dir_prompt":   "  Select a folder and press F4 or 'Dir▶'.",

"history_empty":"  Directory history is empty.",
"history_title":"  Recent directories:",

"fm_path":      "  ═══  {path}  ═══",
"fm_info":      "  Dirs: {dirs}   Files: {files}",
"fm_no_access": "  Access denied",
"fm_error":     "  Error: {err}",
"fm_up":        "  ▲ ..   (go up)",

"view_select":  "  Select a file in the right panel.",
"view_read_err":"Read error: {err}",
"view_close":   "  Close (ESC)  ",
"view_title":   "View: {name}",

"slash_echo":   "  › {cmd}",
"slash_bad":    "  Unknown command. Sending to claude...",

"claude_not_found": "ERROR: 'claude' not found in PATH. Install from: https://claude.ai/code",

"retry_label":  "  ⚠  Claude couldn't complete the action — insufficient permissions.",
"retry_btn":    "  ↺ Expand permissions and continue  ",
"retry_msg":    "  ↺ Continuing with expanded permissions: {tools}",
"retry_prompt": "Continue the task with the new permissions.",

"quit_title":   "Exit",
"quit_msg":     "Claude is processing a request. Exit anyway?",

"help_title":   "Help",
"help_content": (
    "<pre>"
    "<span style='color:#ffff55;font-weight:bold'>MS-DOS CLAUDE AGENT v3.0</span>\n\n"
    "<span style='color:#ffff55'>F1</span>  Help               <span style='color:#ffff55'>F2</span>  Switch model\n"
    "<span style='color:#ffff55'>F3</span>  View file          <span style='color:#ffff55'>F4</span>  Apply directory\n"
    "<span style='color:#ffff55'>F5</span>  Refresh list       <span style='color:#ffff55'>F6</span>  New chat\n"
    "<span style='color:#ffff55'>F7</span>  Dir history        <span style='color:#ffff55'>F8</span>  Go up\n"
    "<span style='color:#ffff55'>F9</span>  Settings           <span style='color:#ffff55'>F10</span> Exit\n\n"
    "<span style='color:#00cc00'>COMMANDS:</span>\n"
    "  /help  /agents  /new  /cls\n"
    "  /model opus|sonnet|haiku\n\n"
    "<span style='color:#00cc00'>NAVIGATION:</span>\n"
    "  Double-click — open folder\n"
    "  Tab — switch focus chat↔files\n"
    "  F4 — apply current folder\n"
    "  Ctrl+N — new chat  Ctrl+L — clear\n"
    "</pre>"
),
"help_ok":      "  OK  ",

"settings_title":    "Settings",
"settings_lang":     "Interface language:",
"settings_model":    "Default model:",
"settings_dir":      "Start directory:",
"settings_dir_hint": "Folder opened on startup",
"settings_save":     "  Save  ",
"settings_cancel":   "  Cancel  ",
"settings_restart":  "Language changed. Restart the app to apply.",

"tools_title":    "MANUAL mode — select permissions",
"tools_header":   "  What should Claude be allowed to do?\n",
"tools_run":      "  ▶ Run  ",
"tools_cancel":   "  ✕ Cancel  ",

"tool_Write":     "Write     — create new files",
"tool_Edit":      "Edit      — edit files",
"tool_MultiEdit": "MultiEdit — bulk editing",
"tool_Bash":      "Bash      — run shell commands",
"tool_Read":      "Read      — read files",
"tool_Glob":      "Glob      — find files by pattern",
"tool_Grep":      "Grep      — search file contents",
"tool_LS":        "LS        — list files",
"tool_WebFetch":  "WebFetch  — fetch web pages",
"tool_WebSearch": "WebSearch — search the web",
"tool_TodoWrite": "Todo      — manage tasks",

"tools_none":     "none",

"perm_title":     "⚠  Permission Required",
"perm_header":    "  ⚠  Claude is requesting permission:",
"perm_yes":       "Yes",
"perm_no":        "No",
"perm_always":    "Always",
"perm_deny":      "Deny",

"info_model":     "  Model         : {model}",
"info_workdir":   "  Working dir   : {workdir}",
"info_curdir":    "  Browser dir   : {curdir}",
"info_cfg":       "  Config file   : {cfg}",
"info_platform":  "  Platform      : {platform}",
"info_auto":      "  AUTO mode     : {auto}",
"info_auto_on":   "ON (auto-approve)",
"info_auto_off":  "OFF (manual confirm)",

},  # end en

}  # end _STRINGS
