#!/usr/bin/env python3
"""MS-DOS CLAUDE AGENT v3.0 — PyQt6 native window edition"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QColor, QFont, QKeySequence, QShortcut, QTextCharFormat, QTextCursor,
)
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFileDialog,
    QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QPushButton, QSplitter, QTextEdit, QVBoxLayout, QWidget,
)

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
    load_dotenv(Path(__file__).parent / ".env.local")
except ImportError:
    pass

import lang   # localisation — must come after config is loaded

# ── platform ──────────────────────────────────────────────────────────────────
IS_WIN = sys.platform == "win32"
NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_ANSI  = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def strip_ansi(s: str) -> str:
    return _ANSI.sub("", s)

def build_claude_cmd(has_session: bool, model: str, user_text: str,
                     skip_perms: bool = True) -> tuple[list, dict]:
    """AUTO mode: non-interactive -p with full stats."""
    env = os.environ.copy()
    env["_CLAUDE_MSG"] = user_text
    if IS_WIN:
        parts = ["claude"]
        if has_session:
            parts.append("--continue")
        else:
            parts += ["--model", model]
        parts.append("--dangerously-skip-permissions")
        parts += ["--output-format", "stream-json", "--verbose"]
        parts += ["-p", "$env:_CLAUDE_MSG"]
        cmd = ["powershell.exe", "-NoProfile", "-NonInteractive",
               "-Command", " ".join(parts)]
    else:
        flags = "--continue" if has_session else f"--model {model}"
        cmd = ["bash", "-c",
               f'claude {flags} --dangerously-skip-permissions '
               f'--output-format stream-json --verbose -p "$_CLAUDE_MSG"']
    return cmd, env


def build_claude_cmd_manual(has_session: bool, model: str, user_text: str,
                            allowed_tools: list) -> tuple[list, dict]:
    """MANUAL mode: -p with explicit --allowedTools list (no hanging, no TTY needed)."""
    env = os.environ.copy()
    env["_CLAUDE_MSG"] = user_text
    tools_str = ",".join(allowed_tools) if allowed_tools else ""
    if IS_WIN:
        parts = ["claude"]
        if has_session:
            parts.append("--continue")
        else:
            parts += ["--model", model]
        if tools_str:
            parts += ["--allowedTools", tools_str]
        parts += ["--output-format", "stream-json", "--verbose"]
        parts += ["-p", "$env:_CLAUDE_MSG"]
        cmd = ["powershell.exe", "-NoProfile", "-NonInteractive",
               "-Command", " ".join(parts)]
    else:
        flags = "--continue" if has_session else f"--model {model}"
        tools_arg = f"--allowedTools {tools_str}" if tools_str else ""
        cmd = ["bash", "-c",
               f'claude {flags} {tools_arg} --output-format stream-json --verbose -p "$_CLAUDE_MSG"']
    return cmd, env

# ── config ────────────────────────────────────────────────────────────────────
CFG_FILE = Path(__file__).parent / ".msdos_agent.json"
MODELS   = {
    "opus":   "claude-opus-4-7",
    "sonnet": "claude-sonnet-4-6",
    "haiku":  "claude-haiku-4-5-20251001",
}
MODEL_CYCLE = list(MODELS.values())
_CFG_DEF = {
    "model": "claude-opus-4-7",
    "start_dir": str(Path.home()),
    "recent_dirs": [],
    "win_w": 1280, "win_h": 720,
    "skip_perms": True,
    "lang": "ru",
}

def load_cfg() -> dict:
    if CFG_FILE.exists():
        try:
            return {**_CFG_DEF, **json.loads(CFG_FILE.read_text(encoding="utf-8"))}
        except Exception:
            pass
    return _CFG_DEF.copy()

def save_cfg(cfg: dict) -> None:
    try:
        CFG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

# ── palette ───────────────────────────────────────────────────────────────────
MONO     = "Courier New"
SZ       = 11
C_BG     = "#000000"
C_GREEN  = "#00cc00"
C_DIM    = "#006600"
C_YELLOW = "#ffff55"
C_CYAN   = "#55ffff"
C_WHITE  = "#ffffff"
C_RED    = "#ff5555"
C_BLUE   = "#00007a"
C_NAVY   = "#000044"

# ── worker thread ─────────────────────────────────────────────────────────────
class ClaudeWorker(QThread):
    line_ready   = pyqtSignal(str)
    stats_ready  = pyqtSignal(dict)
    prompt_ready = pyqtSignal(str, list)   # (prompt_text, [("key","Label"), ...])
    done         = pyqtSignal(int)

    def __init__(self, cmd: list, env: dict, cwd: str) -> None:
        super().__init__()
        self.cmd, self.env, self.cwd = cmd, env, cwd
        self._usage: dict = {}
        self._proc:  Optional[subprocess.Popen] = None
        self._ans_event = threading.Event()

    def provide_answer(self, key: str) -> None:
        self._ans_event.set()

    def run(self) -> None:
        try:
            proc = subprocess.Popen(
                self.cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                env=self.env, cwd=self.cwd,
                creationflags=NO_WIN if IS_WIN else 0,
            )
            self._proc = proc
            for raw in proc.stdout:
                line = raw.rstrip("\r\n")
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    self._handle_json(obj)
                except json.JSONDecodeError:
                    clean = strip_ansi(line)
                    if clean.strip():
                        self.line_ready.emit(clean)
            proc.wait()
            self.done.emit(proc.returncode or 0)
        except FileNotFoundError:
            self.line_ready.emit(lang.t("claude_not_found"))
            self.done.emit(1)
        except Exception as e:
            self.line_ready.emit(lang.t("error_prefix") + str(e))
            self.done.emit(1)

    def _handle_json(self, obj: dict) -> None:
        t   = obj.get("type", "")

        if t == "assistant":
            msg = obj.get("message", {})
            for block in msg.get("content", []):
                btype = block.get("type", "")
                if btype == "text":
                    for ln in block["text"].split("\n"):
                        self.line_ready.emit(ln)
                elif btype == "tool_use":
                    name = block.get("name", "")
                    args = json.dumps(block.get("input", ""), ensure_ascii=False)[:80]
                    self.line_ready.emit(lang.t("tool_use", name=name, args=args))
            u = msg.get("usage", {})
            if u:
                self._usage = u

        elif t == "tool_result":
            content = obj.get("content", "")
            if isinstance(content, str) and content.strip():
                for ln in content.split("\n"):
                    self.line_ready.emit(f"  {ln}")

        elif t == "result":
            stats = {
                "in":          self._usage.get("input_tokens", 0),
                "out":         self._usage.get("output_tokens", 0),
                "cache_read":  self._usage.get("cache_read_input_tokens", 0),
                "cache_write": self._usage.get("cache_creation_input_tokens", 0),
                "cost":        obj.get("cost_usd", 0.0),
                "total_cost":  obj.get("total_cost_usd", 0.0),
                "duration_ms": obj.get("duration_ms", 0),
                "turns":       obj.get("num_turns", 1),
            }
            self.stats_ready.emit(stats)
            if obj.get("subtype") == "error":
                self.line_ready.emit(lang.t("error_prefix") + obj.get("error", ""))

        elif t in ("system", "user"):
            pass  # ignore init/echo events

# ── tool select dialog (MANUAL mode pre-flight) ──────────────────────────────
_TOOL_KEYS = [
    "Write", "Edit", "MultiEdit", "Bash",
    "Read", "Glob", "Grep", "LS", "WebFetch", "WebSearch", "TodoWrite",
]

class ToolSelectDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(lang.t("tools_title"))
        self.setModal(True)
        self.setStyleSheet(f"""
            QDialog      {{ background:#001100; }}
            QLabel       {{ color:{C_GREEN}; font-family:'{MONO}'; font-size:{SZ}pt; }}
            QCheckBox    {{ color:{C_CYAN};  font-family:'{MONO}'; font-size:{SZ}pt; spacing:6px; }}
            QCheckBox::indicator {{ width:14px; height:14px; }}
            QCheckBox::indicator:unchecked {{ background:#002200; border:1px solid #005500; }}
            QCheckBox::indicator:checked   {{ background:#005500; border:1px solid #00aa00; }}
            QPushButton  {{ font-family:'{MONO}'; font-size:{SZ}pt;
                            border:1px solid #005500; padding:4px 18px; }}
            #run_btn  {{ background:#004400; color:#00ff00; }}
            #run_btn:hover  {{ background:#006600; }}
            #deny_btn {{ background:#440000; color:#ff5555; }}
            #deny_btn:hover {{ background:#660000; }}
        """)
        v = QVBoxLayout(self)
        v.setSpacing(6)
        v.addWidget(QLabel(lang.t("tools_header")))

        self._checks: dict[str, QCheckBox] = {}
        default_on = {"Write", "Edit", "MultiEdit", "Bash", "Read", "Glob", "Grep", "LS"}
        for key in _TOOL_KEYS:
            cb = QCheckBox(lang.t(f"tool_{key}"))
            cb.setChecked(key in default_on)
            self._checks[key] = cb
            v.addWidget(cb)

        v.addSpacing(8)
        row = QHBoxLayout()
        run = QPushButton(lang.t("tools_run"))
        run.setObjectName("run_btn")
        run.clicked.connect(self.accept)
        deny = QPushButton(lang.t("tools_cancel"))
        deny.setObjectName("deny_btn")
        deny.clicked.connect(self.reject)
        row.addWidget(run)
        row.addWidget(deny)
        v.addLayout(row)
        self.resize(420, 420)

    def selected_tools(self) -> list:
        return [k for k, cb in self._checks.items() if cb.isChecked()]

    def keyPressEvent(self, e) -> None:
        if e.key() == Qt.Key.Key_Escape:
            self.reject()
        elif e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.accept()


# ── permission dialog ─────────────────────────────────────────────────────────
class PermissionDialog(QDialog):
    def __init__(self, prompt: str, options: list, parent=None) -> None:
        super().__init__(parent)
        self.selected = "n"
        self.setWindowTitle(lang.t("perm_title"))
        self.setModal(True)
        self.setStyleSheet(f"""
            QDialog   {{ background:#1a0000; }}
            QLabel    {{ color:{C_YELLOW}; font-family:'{MONO}'; font-size:{SZ}pt; }}
            #prompt   {{ color:{C_WHITE}; font-family:'{MONO}'; font-size:{SZ}pt;
                         background:#110000; border:1px solid #aa0000;
                         padding:8px; }}
            QPushButton {{
                font-family:'{MONO}'; font-size:{SZ}pt;
                border:1px solid #555500; padding:4px 14px; min-width:120px;
            }}
            #btn_y {{ background:#005500; color:#00ff00; }}
            #btn_y:hover {{ background:#007700; }}
            #btn_n {{ background:#550000; color:#ff5555; }}
            #btn_n:hover {{ background:#770000; }}
            #btn_a {{ background:#003355; color:#55aaff; }}
            #btn_a:hover {{ background:#004477; }}
            #btn_d {{ background:#333300; color:#888800; }}
            #btn_d:hover {{ background:#444400; }}
        """)
        v = QVBoxLayout(self)
        v.setSpacing(10)

        hdr = QLabel(lang.t("perm_header"))
        hdr.setStyleSheet(f"color:{C_YELLOW}; font-weight:bold;")
        v.addWidget(hdr)

        prompt_lbl = QLabel(prompt)
        prompt_lbl.setObjectName("prompt")
        prompt_lbl.setWordWrap(True)
        v.addWidget(prompt_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        color_id = {"y": "btn_y", "n": "btn_n", "a": "btn_a", "d": "btn_d"}
        for key, label in options:
            btn = QPushButton(label)
            btn.setObjectName(color_id.get(key.lower(), "btn_n"))
            btn.clicked.connect(lambda _, k=key: self._pick(k))
            btn_row.addWidget(btn)
        v.addLayout(btn_row)
        self.resize(460, 180)

    def _pick(self, key: str) -> None:
        self.selected = key
        self.accept()

    def keyPressEvent(self, e) -> None:
        if e.key() == Qt.Key.Key_Escape:
            self._pick("n")


# ── help dialog ───────────────────────────────────────────────────────────────
class HelpDialog(QDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle(lang.t("help_title"))
        self.setStyleSheet(f"""
            QDialog   {{ background:{C_NAVY}; }}
            QLabel    {{ color:{C_GREEN}; font-family:'{MONO}'; font-size:{SZ}pt; }}
            QPushButton {{ background:#0000cc; color:{C_WHITE}; border:none; padding:4px 20px; font-family:'{MONO}'; }}
            QPushButton:hover {{ background:#0000ff; color:{C_YELLOW}; }}
        """)
        v = QVBoxLayout(self)
        v.addWidget(QLabel(lang.t("help_content")))
        btn = QPushButton(lang.t("help_ok"))
        btn.clicked.connect(self.accept)
        v.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self.resize(440, 380)

    def keyPressEvent(self, e) -> None:
        if e.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Return, Qt.Key.Key_F1):
            self.accept()

# ── file viewer dialog ────────────────────────────────────────────────────────
class FileViewDialog(QDialog):
    def __init__(self, path: Path, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle(lang.t("view_title", name=path.name))
        self.setStyleSheet(f"""
            QDialog  {{ background:#000022; }}
            QTextEdit {{ background:#000022; color:{C_GREEN}; border:1px solid #003300;
                        font-family:'{MONO}'; font-size:{SZ}pt; }}
            QPushButton {{ background:#0000aa; color:{C_WHITE}; border:none;
                          padding:4px 20px; font-family:'{MONO}'; }}
            QPushButton:hover {{ background:#0000cc; color:{C_YELLOW}; }}
        """)
        v = QVBoxLayout(self)
        te = QTextEdit()
        te.setReadOnly(True)
        try:
            te.setPlainText(path.read_text(encoding="utf-8", errors="replace"))
        except Exception as exc:
            te.setPlainText(lang.t("view_read_err", err=exc))
        v.addWidget(te)
        btn = QPushButton(lang.t("view_close"))
        btn.clicked.connect(self.accept)
        v.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self.resize(760, 520)

    def keyPressEvent(self, e) -> None:
        if e.key() in (Qt.Key.Key_Escape, Qt.Key.Key_F3):
            self.accept()

# ── settings dialog ───────────────────────────────────────────────────────────
class SettingsDialog(QDialog):
    def __init__(self, cfg: dict, parent=None) -> None:
        super().__init__(parent)
        self._cfg = cfg
        self.setWindowTitle(lang.t("settings_title"))
        self.setModal(True)
        self.setStyleSheet(f"""
            QDialog     {{ background:#001122; }}
            QLabel      {{ color:{C_GREEN}; font-family:'{MONO}'; font-size:{SZ}pt; }}
            QLineEdit   {{ background:#000033; color:{C_CYAN}; border:1px solid #003366;
                           font-family:'{MONO}'; font-size:{SZ}pt; padding:2px 4px; }}
            QComboBox   {{ background:#000033; color:{C_CYAN}; border:1px solid #003366;
                           font-family:'{MONO}'; font-size:{SZ}pt; padding:2px 4px; }}
            QComboBox QAbstractItemView {{ background:#000033; color:{C_CYAN};
                           selection-background-color:#003366; }}
            QPushButton {{ font-family:'{MONO}'; font-size:{SZ}pt;
                           border:1px solid #003366; padding:4px 16px; }}
            #save_btn   {{ background:#004400; color:#00ff00; }}
            #save_btn:hover {{ background:#006600; }}
            #cancel_btn {{ background:#440000; color:#ff5555; }}
            #cancel_btn:hover {{ background:#660000; }}
            #browse_btn {{ background:#000055; color:{C_CYAN}; border:1px solid #003366;
                           padding:2px 6px; font-family:'{MONO}'; font-size:{SZ}pt; }}
            #browse_btn:hover {{ background:#000088; }}
            #hint_lbl   {{ color:#005588; font-size:9pt; }}
        """)
        v = QVBoxLayout(self)
        v.setSpacing(10)
        v.setContentsMargins(16, 16, 16, 16)

        # Language
        r1 = QHBoxLayout()
        lbl1 = QLabel(lang.t("settings_lang"))
        lbl1.setFixedWidth(200)
        r1.addWidget(lbl1)
        self._lang_combo = QComboBox()
        self._lang_combo.addItems(["Русский", "English"])
        self._lang_combo.setCurrentIndex(0 if cfg.get("lang", "ru") == "ru" else 1)
        r1.addWidget(self._lang_combo, 1)
        v.addLayout(r1)

        # Model
        r2 = QHBoxLayout()
        lbl2 = QLabel(lang.t("settings_model"))
        lbl2.setFixedWidth(200)
        r2.addWidget(lbl2)
        self._model_combo = QComboBox()
        self._model_combo.addItems(MODEL_CYCLE)
        cur_model = cfg.get("model", "claude-opus-4-7")
        idx = MODEL_CYCLE.index(cur_model) if cur_model in MODEL_CYCLE else 0
        self._model_combo.setCurrentIndex(idx)
        r2.addWidget(self._model_combo, 1)
        v.addLayout(r2)

        # Start directory
        r3 = QHBoxLayout()
        lbl3 = QLabel(lang.t("settings_dir"))
        lbl3.setFixedWidth(200)
        r3.addWidget(lbl3)
        self._dir_edit = QLineEdit(cfg.get("start_dir", str(Path.home())))
        r3.addWidget(self._dir_edit, 1)
        browse = QPushButton("…")
        browse.setObjectName("browse_btn")
        browse.setFixedWidth(28)
        browse.clicked.connect(self._browse)
        r3.addWidget(browse)
        v.addLayout(r3)

        hint = QLabel(lang.t("settings_dir_hint"))
        hint.setObjectName("hint_lbl")
        v.addWidget(hint)

        v.addSpacing(6)
        r4 = QHBoxLayout()
        r4.addStretch()
        save_btn = QPushButton(lang.t("settings_save"))
        save_btn.setObjectName("save_btn")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton(lang.t("settings_cancel"))
        cancel_btn.setObjectName("cancel_btn")
        cancel_btn.clicked.connect(self.reject)
        r4.addWidget(save_btn)
        r4.addWidget(cancel_btn)
        v.addLayout(r4)

        self.resize(500, 220)

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, lang.t("settings_dir"), self._dir_edit.text())
        if path:
            self._dir_edit.setText(path)

    def result_values(self) -> tuple[str, str, str]:
        lang_val  = "ru" if self._lang_combo.currentIndex() == 0 else "en"
        model_val = self._model_combo.currentText()
        dir_val   = self._dir_edit.text().strip() or str(Path.home())
        return lang_val, model_val, dir_val

    def keyPressEvent(self, e) -> None:
        if e.key() == Qt.Key.Key_Escape:
            self.reject()
        elif e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.accept()


# ── main window ───────────────────────────────────────────────────────────────
class MsDosWindow(QMainWindow):

    def __init__(self) -> None:
        super().__init__()
        self.cfg         = load_cfg()
        lang.load(self.cfg)          # init localisation before any UI
        self.model       = self.cfg.get("model", "claude-opus-4-7")
        self.workdir     = Path(self.cfg.get("start_dir", str(Path.home())))
        self.cur_dir     = Path(self.cfg.get("start_dir", str(Path.home())))
        self.has_session = False
        self.msg_count   = 0
        self.busy        = False
        self.skip_perms  = self.cfg.get("skip_perms", True)
        self.total_cost       = 0.0
        self.worker: Optional[ClaudeWorker] = None
        self._dir_mtime       = 0.0
        self._last_allowed:   list = []

        self._build_ui()
        self._bind_keys()
        self._boot_msg()
        self._load_dir(self.cur_dir)
        self._upd_status()
        self.input_field.setFocus()

        self._fs_timer = QTimer(self)
        self._fs_timer.timeout.connect(self._auto_refresh)
        self._fs_timer.start(2000)

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.setWindowTitle(lang.t("win_title"))
        self.resize(self.cfg.get("win_w", 1280), self.cfg.get("win_h", 720))
        self.setStyleSheet(self._qss())

        root_w = QWidget()
        self.setCentralWidget(root_w)
        root = QVBoxLayout(root_w)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── title bar ──
        title = QLabel("  " + lang.t("title_bar"))
        title.setObjectName("titleBar")
        title.setFixedHeight(22)
        root.addWidget(title)

        # ── splitter ──
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet("QSplitter::handle { background:#333333; }")
        root.addWidget(splitter, 1)

        # left: chat
        left_w = QWidget()
        left_w.setObjectName("leftPanel")
        lv = QVBoxLayout(left_w)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(0)

        self.chat_log = QTextEdit()
        self.chat_log.setObjectName("chatLog")
        self.chat_log.setReadOnly(True)
        self.chat_log.setFont(QFont(MONO, SZ))
        lv.addWidget(self.chat_log)

        self.stats_lbl = QLabel(lang.t("tokens_empty"))
        self.stats_lbl.setObjectName("statsBar")
        self.stats_lbl.setFixedHeight(18)
        lv.addWidget(self.stats_lbl)

        self.retry_bar = QWidget()
        self.retry_bar.setObjectName("retryBar")
        self.retry_bar.setFixedHeight(26)
        self.retry_bar.setVisible(False)
        rb = QHBoxLayout(self.retry_bar)
        rb.setContentsMargins(4, 2, 4, 2)
        rb.setSpacing(6)
        rb.addWidget(QLabel(lang.t("retry_label")))
        retry_btn = QPushButton(lang.t("retry_btn"))
        retry_btn.setObjectName("retryBtn")
        retry_btn.setFont(QFont(MONO, 9, QFont.Weight.Bold))
        retry_btn.clicked.connect(self._retry_with_more_tools)
        rb.addWidget(retry_btn)
        rb.addStretch()
        lv.addWidget(self.retry_bar)

        input_row = QWidget()
        input_row.setObjectName("inputRow")
        ir = QHBoxLayout(input_row)
        ir.setContentsMargins(4, 2, 4, 2)
        ir.setSpacing(4)

        prompt_lbl = QLabel(lang.t("prompt_label"))
        prompt_lbl.setObjectName("promptLbl")
        prompt_lbl.setFont(QFont(MONO, SZ, QFont.Weight.Bold))
        ir.addWidget(prompt_lbl)

        self.input_field = QLineEdit()
        self.input_field.setObjectName("inputField")
        self.input_field.setFont(QFont(MONO, SZ))
        self.input_field.setPlaceholderText(lang.t("input_placeholder"))
        self.input_field.returnPressed.connect(self._on_submit)
        ir.addWidget(self.input_field)

        self.stop_btn = QPushButton(lang.t("stop_btn"))
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setFont(QFont(MONO, 9, QFont.Weight.Bold))
        self.stop_btn.setFixedWidth(72)
        self.stop_btn.setFixedHeight(24)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._kill_worker)
        ir.addWidget(self.stop_btn)

        self.perm_btn = QPushButton(lang.t("auto_btn_on"))
        self.perm_btn.setObjectName("permBtn")
        self.perm_btn.setFont(QFont(MONO, 9, QFont.Weight.Bold))
        self.perm_btn.setFixedWidth(72)
        self.perm_btn.setFixedHeight(24)
        self.perm_btn.setCheckable(True)
        self.perm_btn.setChecked(True)
        self.perm_btn.setToolTip(lang.t("auto_on_tip"))
        self.perm_btn.clicked.connect(self._toggle_perms)
        ir.addWidget(self.perm_btn)

        lv.addWidget(input_row)
        splitter.addWidget(left_w)

        # right: file manager
        right_w = QWidget()
        right_w.setObjectName("rightPanel")
        rv = QVBoxLayout(right_w)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)

        self.path_lbl = QLabel("")
        self.path_lbl.setObjectName("pathLbl")
        self.path_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.path_lbl.setFixedHeight(22)
        rv.addWidget(self.path_lbl)

        self.file_list = QListWidget()
        self.file_list.setObjectName("fileList")
        self.file_list.setFont(QFont(MONO, SZ))
        self.file_list.itemDoubleClicked.connect(self._on_dclick)
        rv.addWidget(self.file_list)

        self.dir_info = QLabel("")
        self.dir_info.setObjectName("dirInfo")
        self.dir_info.setFixedHeight(18)
        rv.addWidget(self.dir_info)

        splitter.addWidget(right_w)
        splitter.setSizes([760, 480])

        # ── status bar ──
        self.status_lbl = QLabel("")
        self.status_lbl.setObjectName("statusBar")
        self.status_lbl.setFixedHeight(20)
        root.addWidget(self.status_lbl)

        # ── F-key bar ──
        fbar = QWidget()
        fbar.setObjectName("fkeyBar")
        fbar.setFixedHeight(26)
        fh = QHBoxLayout(fbar)
        fh.setContentsMargins(0, 0, 0, 0)
        fh.setSpacing(1)

        fkeys = [
            ("F1",  "fk_help",     self._action_help),
            ("F2",  "fk_model",    self._action_model),
            ("F3",  "fk_view",     self._action_view),
            ("F4",  "fk_applydir", self._action_apply_dir),
            ("F5",  "fk_refresh",  self._action_refresh),
            ("F6",  "fk_newchat",  self._action_new_chat),
            ("F7",  "fk_history",  self._action_history),
            ("F8",  "fk_dirup",    self._action_dir_up),
            ("F9",  "fk_settings", self._action_settings),
            ("F10", "fk_exit",     self.close),
        ]
        for key, lkey, slot in fkeys:
            btn = QPushButton(f"{key} {lang.t(lkey)}")
            btn.setObjectName("fkeyBtn")
            btn.setFont(QFont(MONO, 9))
            btn.setFixedHeight(24)
            btn.clicked.connect(slot)
            fh.addWidget(btn)

        root.addWidget(fbar)

    def _qss(self) -> str:
        return f"""
        QMainWindow, QWidget     {{ background:{C_BG}; color:{C_GREEN}; }}
        #titleBar {{
            background:#aaaaaa; color:#000000;
            font-family:'{MONO}'; font-size:11pt; font-weight:bold;
        }}
        #leftPanel  {{ background:{C_BG}; }}
        #chatLog {{
            background:{C_BG}; color:{C_GREEN}; border:none;
            selection-background-color:#003300;
        }}
        #retryBar {{
            background:#1a0e00; border-top:1px solid #aa5500;
        }}
        #retryBar QLabel {{ color:{C_YELLOW}; font-family:'{MONO}'; font-size:9pt; }}
        #retryBtn {{
            background:#553300; color:{C_YELLOW};
            border:1px solid #aa6600; font-family:'{MONO}'; font-size:9pt;
            padding:2px 8px;
        }}
        #retryBtn:hover {{ background:#774400; color:#ffffff; }}
        #statsBar {{
            background:#001a00; color:#009900;
            font-family:'{MONO}'; font-size:8pt;
            border-top:1px solid #003300; padding-left:4px;
        }}
        #inputRow   {{ background:{C_BG}; border-top:1px solid #1a1a1a; }}
        #promptLbl  {{ color:#00ff00; background:{C_BG}; }}
        #inputField {{
            background:{C_BG}; color:#00ff00; border:none;
            selection-background-color:#003300;
        }}
        #rightPanel {{ background:{C_BLUE}; }}
        #pathLbl {{
            background:{C_NAVY}; color:{C_YELLOW};
            font-family:'{MONO}'; font-size:{SZ}pt; font-weight:bold;
            border-bottom:1px solid #0000cc;
        }}
        #fileList {{
            background:{C_BLUE}; color:{C_CYAN};
            border:none; outline:0;
        }}
        #fileList::item          {{ padding:1px 4px; }}
        #fileList::item:selected {{ background:#aaaaaa; color:#000000; }}
        #dirInfo {{
            background:{C_NAVY}; color:#888888;
            font-family:'{MONO}'; font-size:9pt; padding-left:4px;
        }}
        #statusBar {{
            background:#0000aa; color:{C_WHITE};
            font-family:'{MONO}'; font-size:9pt; padding-left:6px;
        }}
        #fkeyBar {{ background:{C_BG}; }}
        #fkeyBtn {{
            background:#0000aa; color:{C_WHITE};
            border:none; text-align:left; padding:0 6px;
            font-family:'{MONO}';
        }}
        #fkeyBtn:hover   {{ background:#0000dd; color:{C_YELLOW}; }}
        #fkeyBtn:pressed {{ background:#000077; }}
        #stopBtn {{
            background:#440000; color:#ff5555;
            border:1px solid #880000; font-family:'{MONO}'; font-size:9pt;
        }}
        #stopBtn:enabled {{ background:#660000; color:#ff8888; border:1px solid #aa0000; }}
        #stopBtn:enabled:hover {{ background:#880000; color:{C_YELLOW}; }}
        #permBtn {{
            background:#444400; color:{C_YELLOW};
            border:1px solid #888800; font-family:'{MONO}'; font-size:9pt;
        }}
        #permBtn:checked {{
            background:#006600; color:#00ff00;
            border:1px solid #00aa00;
        }}
        #permBtn:hover {{ border:1px solid {C_YELLOW}; }}
        """

    # ── shortcuts ─────────────────────────────────────────────────────────────

    def _bind_keys(self) -> None:
        pairs = [
            ("F1",    self._action_help),
            ("F2",    self._action_model),
            ("F3",    self._action_view),
            ("F4",    self._action_apply_dir),
            ("F5",    self._action_refresh),
            ("F6",    self._action_new_chat),
            ("F7",    self._action_history),
            ("F8",    self._action_dir_up),
            ("F9",    self._action_settings),
            ("F10",   self.close),
            ("Ctrl+N", self._action_new_chat),
            ("Ctrl+L", self.chat_log.clear),
        ]
        for key, slot in pairs:
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(slot)

    # ── boot ──────────────────────────────────────────────────────────────────

    def _boot_msg(self) -> None:
        self._log(lang.t("boot_version"), C_GREEN, bold=True)
        self._log(lang.t("boot_engine"), C_DIM)
        self._log("")
        self._log(lang.t("boot_hint"), "#005500")
        self._log("─" * 74, "#003300")
        self._log("")

    # ── chat helpers ──────────────────────────────────────────────────────────

    def _log(self, text: str, color: str = C_GREEN, bold: bool = False) -> None:
        cur = self.chat_log.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        fmt.setFont(QFont(MONO, SZ, QFont.Weight.Bold if bold else QFont.Weight.Normal))
        cur.insertText(text + "\n", fmt)
        self.chat_log.setTextCursor(cur)
        self.chat_log.ensureCursorVisible()

    def _upd_status(self) -> None:
        state = lang.t("state_busy") if self.busy else lang.t("state_ready")
        self.status_lbl.setText(
            lang.t("status", model=self.model, workdir=self.workdir,
                   state=state, count=self.msg_count)
        )

    # ── input ─────────────────────────────────────────────────────────────────

    def _on_submit(self) -> None:
        text = self.input_field.text().strip()
        if not text or self.busy:
            return
        self.input_field.clear()
        if text.startswith("/"):
            self._slash(text)
        else:
            self._log("")
            self._log(f"  {lang.t('you')}> {text}", C_YELLOW, bold=True)
            self._log("")
            self._run_claude(text)

    def _retry_with_more_tools(self) -> None:
        if self.busy:
            return
        dlg = ToolSelectDialog(self)
        for key, cb in dlg._checks.items():
            if key in self._last_allowed:
                cb.setChecked(True)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        allowed = dlg.selected_tools()
        self._last_allowed = allowed
        self.retry_bar.setVisible(False)
        prompt = lang.t("retry_prompt")
        self._log("")
        self._log(lang.t("retry_msg", tools=", ".join(allowed)), C_YELLOW)
        self._log("")
        cmd, env = build_claude_cmd_manual(True, self.model, prompt, allowed)
        self.busy = True
        self.input_field.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._upd_status()
        self.worker = ClaudeWorker(cmd, env, str(self.workdir))
        self.worker.line_ready.connect(self._on_line)
        self.worker.stats_ready.connect(self._on_stats)
        self.worker.prompt_ready.connect(self._on_prompt)
        self.worker.done.connect(self._on_done)
        self.worker.start()

    def _toggle_perms(self) -> None:
        self.skip_perms = self.perm_btn.isChecked()
        self.cfg["skip_perms"] = self.skip_perms
        save_cfg(self.cfg)
        if self.skip_perms:
            self._log(lang.t("auto_on_msg"), C_YELLOW)
        else:
            self._log(lang.t("auto_off_msg"), "#ff8800")
        self._log("")

    # ── claude runner ─────────────────────────────────────────────────────────

    def _run_claude(self, text: str) -> None:
        self.busy = True
        self.input_field.setEnabled(False)
        self._upd_status()

        self.retry_bar.setVisible(False)
        if self.skip_perms:
            cmd, env = build_claude_cmd(self.has_session, self.model, text)
        else:
            dlg = ToolSelectDialog(self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                self.busy = False
                self.stop_btn.setEnabled(False)
                self.input_field.setEnabled(True)
                self.input_field.setFocus()
                self._upd_status()
                return
            allowed = dlg.selected_tools()
            self._last_allowed = allowed
            tools_label = ", ".join(allowed) if allowed else lang.t("tools_none")
            self._log(lang.t("allowed_tools", tools=tools_label), C_YELLOW)
            self._log("")
            cmd, env = build_claude_cmd_manual(
                self.has_session, self.model, text, allowed)

        self.worker = ClaudeWorker(cmd, env, str(self.workdir))

        self.worker.line_ready.connect(self._on_line)
        self.worker.stats_ready.connect(self._on_stats)
        self.worker.prompt_ready.connect(self._on_prompt)
        self.worker.done.connect(self._on_done)
        self.worker.start()
        self.has_session = True
        self.stop_btn.setEnabled(True)

    _DENIED_RE = re.compile(
        r"don.t have (permission|access)|"
        r"не (имею|могу|удалось)|"
        r"permission.*(denied|not granted)|"
        r"tool.*not.*allow|"
        r"недостаточно прав|не разрешено",
        re.IGNORECASE,
    )

    def _on_line(self, line: str) -> None:
        self._log(f"  {line}" if line.strip() else "", C_GREEN)
        if not self.skip_perms and line.strip() and self._DENIED_RE.search(line):
            self.retry_bar.setVisible(True)

    def _on_prompt(self, text: str, options: list) -> None:
        dlg = PermissionDialog(text, options, self)
        dlg.exec()
        if self.worker:
            self.worker.provide_answer(dlg.selected)

    def _on_stats(self, s: dict) -> None:
        self.total_cost += s.get("cost", 0.0)
        dur = s["duration_ms"] / 1000
        cr  = s["cache_read"]
        cw  = s["cache_write"]
        cache_str = lang.t("tokens_cache", r=cr, w=cw) if (cr or cw) else ""
        text = lang.t(
            "tokens_fmt",
            i=s["in"], o=s["out"], cache=cache_str,
            cost=s["cost"], total=self.total_cost,
            dur=dur, turns=s["turns"],
        )
        self.stats_lbl.setText(text)

    def _kill_worker(self) -> None:
        if self.worker:
            proc = self.worker._proc
            if proc:
                try:
                    if IS_WIN:
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                            capture_output=True,
                        )
                    else:
                        import signal as _signal
                        os.killpg(os.getpgid(proc.pid), _signal.SIGKILL)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
            self.worker.provide_answer("n")
        self._log(lang.t("stopped"), C_RED)
        self._log("")
        self.busy = False
        self.stop_btn.setEnabled(False)
        self.input_field.setEnabled(True)
        self.input_field.setFocus()
        self._upd_status()

    def _on_done(self, rc: int) -> None:
        if rc not in (0, -9, -15):
            self._log(lang.t("exit_code", rc=rc), C_RED)
        self._log("")
        self.msg_count += 1
        self.busy = False
        self.stop_btn.setEnabled(False)
        self.input_field.setEnabled(True)
        self.input_field.setFocus()
        self._upd_status()

    # ── slash commands ────────────────────────────────────────────────────────

    def _slash(self, raw: str) -> None:
        parts = raw.split()
        cmd, args = parts[0].lower(), parts[1:]

        if cmd in ("/exit", "/quit"):
            self.close()
        elif cmd in ("/cls", "/clear"):
            self.chat_log.clear()
        elif cmd in ("/new", "/reset"):
            self._action_new_chat()
        elif cmd == "/model" and args:
            chosen = MODELS.get(args[0].lower(), args[0])
            self.model, self.has_session = chosen, False
            self._log(lang.t("model_changed", model=chosen), C_YELLOW, bold=True)
            self._log("")
            self._upd_status()
        else:
            self._log(lang.t("slash_echo", cmd=raw), C_YELLOW)
            self._log("")
            self._run_claude(raw)

    # ── file manager ──────────────────────────────────────────────────────────

    def _load_dir(self, path: Path) -> None:
        self.file_list.clear()
        try:
            entries = sorted(path.iterdir(),
                             key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            self.dir_info.setText(lang.t("fm_no_access"))
            return
        except Exception as e:
            self.dir_info.setText(lang.t("fm_error", err=e))
            return

        if path.parent != path:
            item = QListWidgetItem(lang.t("fm_up"))
            item.setForeground(QColor(C_YELLOW))
            item.setData(Qt.ItemDataRole.UserRole, ("dir", path.parent))
            self.file_list.addItem(item)

        dirs = files = 0
        for e in entries:
            try:
                if e.is_dir():
                    item = QListWidgetItem(f"  ▶ {e.name[:44]:<46} <DIR>")
                    item.setForeground(QColor(C_WHITE))
                    item.setFont(QFont(MONO, SZ, QFont.Weight.Bold))
                    item.setData(Qt.ItemDataRole.UserRole, ("dir", e))
                    dirs += 1
                else:
                    try:
                        sz = e.stat().st_size
                        sz_s = f"{sz/1024:.0f}K" if sz >= 1024 else f"{sz}B"
                    except Exception:
                        sz_s = "?"
                    item = QListWidgetItem(f"    {e.name[:44]:<46} {sz_s:>6}")
                    item.setForeground(QColor(C_CYAN))
                    item.setData(Qt.ItemDataRole.UserRole, ("file", e))
                    files += 1
                self.file_list.addItem(item)
            except Exception:
                pass

        self.cur_dir = path
        try:
            self._dir_mtime = path.stat().st_mtime
        except Exception:
            self._dir_mtime = 0.0
        self.path_lbl.setText(lang.t("fm_path", path=path))
        self.dir_info.setText(lang.t("fm_info", dirs=dirs, files=files))

    def _on_dclick(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.ItemDataRole.UserRole)
        if data and data[0] == "dir":
            self._load_dir(data[1])

    def _selected(self):
        items = self.file_list.selectedItems()
        return items[0].data(Qt.ItemDataRole.UserRole) if items else None

    # ── F-key actions ─────────────────────────────────────────────────────────

    def _action_help(self) -> None:
        HelpDialog(self).exec()

    def _action_model(self) -> None:
        idx = MODEL_CYCLE.index(self.model) if self.model in MODEL_CYCLE else 0
        self.model, self.has_session = MODEL_CYCLE[(idx + 1) % len(MODEL_CYCLE)], False
        self._log(lang.t("model_changed", model=self.model), C_YELLOW, bold=True)
        self._log("")
        self._upd_status()

    def _action_view(self) -> None:
        sel = self._selected()
        if sel and sel[0] == "file":
            FileViewDialog(sel[1], self).exec()
        else:
            self._log(lang.t("view_select"), C_YELLOW)

    def _action_apply_dir(self) -> None:
        sel    = self._selected()
        target = sel[1] if (sel and sel[0] == "dir") else self.cur_dir
        if target.is_dir():
            self.workdir = target
            recent = self.cfg.setdefault("recent_dirs", [])
            s = str(target)
            if s in recent:
                recent.remove(s)
            recent.insert(0, s)
            self.cfg["recent_dirs"] = recent[:20]
            save_cfg(self.cfg)
            self._log(lang.t("dir_applied", path=target), C_GREEN, bold=True)
            self._log("")
            self._upd_status()
        else:
            self._log(lang.t("dir_invalid"), C_YELLOW)

    def _action_refresh(self) -> None:
        self._load_dir(self.cur_dir)

    def _auto_refresh(self) -> None:
        try:
            mtime = self.cur_dir.stat().st_mtime
            if mtime != self._dir_mtime:
                self._load_dir(self.cur_dir)
        except Exception:
            pass

    def _action_dir_up(self) -> None:
        p = self.cur_dir.parent
        if p != self.cur_dir:
            self._load_dir(p)

    def _action_history(self) -> None:
        recent = self.cfg.get("recent_dirs", [])
        if not recent:
            self._log(lang.t("history_empty"), C_YELLOW)
            return
        self._log("")
        self._log(lang.t("history_title"), C_GREEN, bold=True)
        for i, d in enumerate(recent[:10], 1):
            self._log(f"  {i:>2}. {d}", C_GREEN)
        self._log("")

    def _action_settings(self) -> None:
        dlg = SettingsDialog(self.cfg, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        lang_val, model_val, dir_val = dlg.result_values()
        old_lang = self.cfg.get("lang", "ru")
        self.cfg["lang"]      = lang_val
        self.cfg["model"]     = model_val
        self.cfg["start_dir"] = dir_val
        self.model = model_val
        save_cfg(self.cfg)
        self._upd_status()
        if lang_val != old_lang:
            QMessageBox.information(
                self, lang.t("settings_title"), lang.t("settings_restart"))

    def _action_new_chat(self) -> None:
        self.has_session = False
        self.msg_count   = 0
        self.total_cost  = 0.0
        self.chat_log.clear()
        self.stats_lbl.setText(lang.t("tokens_empty"))
        self._log(lang.t("new_chat_msg"), C_GREEN, bold=True)
        self._log("")
        self._upd_status()

    # ── close ─────────────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        if self.busy:
            r = QMessageBox.question(
                self, lang.t("quit_title"),
                lang.t("quit_msg"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if r != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        self.cfg.update({
            "model":      self.model,
            "start_dir":  str(self.cur_dir),
            "win_w":      self.width(),
            "win_h":      self.height(),
            "skip_perms": self.skip_perms,
        })
        save_cfg(self.cfg)
        event.accept()


# ── entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("ClaudeNC.exe")
    win = MsDosWindow()
    win.show()
    sys.exit(app.exec())
