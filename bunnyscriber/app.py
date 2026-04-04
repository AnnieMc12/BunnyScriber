"""
BunnyScriber — Main GUI Application.

       /)  /)
      ( ^.^ )    BunnyScriber
      (")_(")    Accurate Speaker-Attributed Transcripts

PyQt6-based desktop application for multi-speaker audio transcription.
"""

import os
import sys
import random

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QSpinBox,
    QComboBox,
    QLineEdit,
    QTextEdit,
    QProgressBar,
    QGroupBox,
    QStackedWidget,
    QFrame,
    QCheckBox,
    QSizePolicy,
    QMessageBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QScrollArea,
    QTabWidget,
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QPixmap, QFont, QIcon

from bunnyscriber.constants import (
    COLORS,
    BUNNY_IMG_HEIGHT,
    IDLE_MESSAGES,
    WORKING_MESSAGES,
    SUCCESS_MESSAGES,
    ERROR_MESSAGES,
    PHASE_NAMES,
    WHISPER_MODELS,
    APP_NAME,
    bunny_path,
)
from bunnyscriber.config import load_config, save_config, get_work_dir
from bunnyscriber.progress import PipelineSignals, ProgressMessage
from bunnyscriber.pipeline import PipelineWorker, check_resumable
from bunnyscriber.backends.base import TranscriptionBackend
from bunnyscriber.backends.whisper_local import WhisperLocalBackend
from bunnyscriber.backends.openai_api import OpenAIWhisperBackend
from bunnyscriber.backends.groq_api import GroqWhisperBackend
from bunnyscriber.backends.mistral_api import MistralTranscriptionBackend
from bunnyscriber.backends.custom import CustomEndpointBackend


# ── Backend Registry ─────────────────────────────────────────────────

BACKEND_OPTIONS = {
    "openai": ("OpenAI Whisper API", OpenAIWhisperBackend),
    "groq": ("Groq Whisper API", GroqWhisperBackend),
    "mistral": ("Mistral API", MistralTranscriptionBackend),
    "whisper_local": ("Local Whisper", WhisperLocalBackend),
}


def _create_backend(config: dict) -> TranscriptionBackend:
    """Create a transcription backend instance from config."""
    backend_id = config.get("backend")
    api_keys = config.get("api_keys", {})

    if backend_id == "openai":
        return OpenAIWhisperBackend(api_key=api_keys.get("openai", ""))
    elif backend_id == "groq":
        return GroqWhisperBackend(api_key=api_keys.get("groq", ""))
    elif backend_id == "mistral":
        return MistralTranscriptionBackend(api_key=api_keys.get("mistral", ""))
    elif backend_id == "whisper_local":
        return WhisperLocalBackend(
            model_size=config.get("whisper_model_size", "base"),
        )
    elif backend_id and backend_id.startswith("custom_"):
        idx = int(backend_id.split("_")[1])
        endpoints = config.get("custom_endpoints", [])
        if idx < len(endpoints):
            return CustomEndpointBackend.from_dict(endpoints[idx])

    return None


# ── Stylesheet ───────────────────────────────────────────────────────

STYLESHEET = f"""
QMainWindow {{
    background-color: {COLORS['bg']};
}}
QWidget {{
    font-family: Georgia, serif;
    color: {COLORS['text']};
}}
QLabel {{
    color: {COLORS['text']};
}}
QLabel[class="title"] {{
    font-size: 22px;
    font-weight: bold;
    color: {COLORS['text']};
}}
QLabel[class="subtitle"] {{
    font-size: 13px;
    color: {COLORS['text_light']};
}}
QLabel[class="bunny-msg"] {{
    font-size: 12px;
    font-style: italic;
    color: {COLORS['text_light']};
    padding: 4px;
}}
QLabel[class="phase-label"] {{
    font-size: 14px;
    font-weight: bold;
    color: {COLORS['text_light']};
}}
QLabel[class="footer"] {{
    font-size: 10px;
    color: {COLORS['text_light']};
}}
QGroupBox {{
    background-color: {COLORS['frame_bg']};
    border: 1px solid {COLORS['accent']};
    border-radius: 8px;
    margin-top: 12px;
    padding: 12px;
    padding-top: 24px;
    font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {COLORS['text']};
}}
QPushButton {{
    background-color: {COLORS['button']};
    color: {COLORS['white']};
    border: none;
    border-radius: 6px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: bold;
    font-family: Georgia, serif;
    min-height: 28px;
}}
QPushButton:hover {{
    background-color: {COLORS['button_hover']};
}}
QPushButton:pressed {{
    background-color: {COLORS['button_pressed']};
}}
QPushButton:disabled {{
    background-color: {COLORS['disabled']};
    color: {COLORS['disabled_text']};
}}
QPushButton[class="start-btn"] {{
    font-size: 16px;
    padding: 12px 40px;
    border-radius: 10px;
    min-height: 36px;
}}
QPushButton[class="small-btn"] {{
    font-size: 11px;
    padding: 4px 12px;
    min-height: 20px;
}}
QLineEdit {{
    background-color: {COLORS['white']};
    border: 1px solid {COLORS['accent']};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
    color: {COLORS['text']};
}}
QLineEdit:focus {{
    border: 2px solid {COLORS['button_hover']};
}}
QTextEdit {{
    background-color: {COLORS['white']};
    border: 1px solid {COLORS['accent']};
    border-radius: 6px;
    padding: 8px;
    font-family: Consolas, monospace;
    font-size: 11px;
    color: {COLORS['text']};
}}
QComboBox {{
    background-color: {COLORS['white']};
    border: 1px solid {COLORS['accent']};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
    color: {COLORS['text']};
}}
QSpinBox {{
    background-color: {COLORS['white']};
    border: 1px solid {COLORS['accent']};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
    color: {COLORS['text']};
}}
QProgressBar {{
    background-color: {COLORS['progress_bg']};
    border: 1px solid {COLORS['accent']};
    border-radius: 6px;
    text-align: center;
    font-size: 11px;
    color: {COLORS['text']};
    min-height: 22px;
}}
QProgressBar::chunk {{
    background-color: {COLORS['progress_bar']};
    border-radius: 5px;
}}
QTabWidget::pane {{
    background-color: {COLORS['frame_bg']};
    border: 1px solid {COLORS['accent']};
    border-radius: 6px;
}}
QTabBar::tab {{
    background-color: {COLORS['button']};
    color: {COLORS['white']};
    border-radius: 6px 6px 0 0;
    padding: 8px 16px;
    margin-right: 2px;
    font-weight: bold;
}}
QTabBar::tab:selected {{
    background-color: {COLORS['button_hover']};
}}
QScrollArea {{
    border: none;
    background-color: transparent;
}}
QCheckBox {{
    font-size: 12px;
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {COLORS['accent']};
    border-radius: 3px;
    background-color: {COLORS['white']};
}}
QCheckBox::indicator:checked {{
    background-color: {COLORS['button_hover']};
    border-color: {COLORS['button_pressed']};
}}
"""


# ═════════════════════════════════════════════════════════════════════
# Setup Wizard
# ═════════════════════════════════════════════════════════════════════


class SetupWizard(QDialog):
    """First-run setup wizard for configuring the transcription backend."""

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle(f"{APP_NAME} — Setup")
        self.setMinimumSize(500, 450)
        self.setStyleSheet(STYLESHEET)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ── Welcome ──
        title = QLabel(f"Welcome to {APP_NAME}!")
        title.setProperty("class", "title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Bunny image
        bunny_label = QLabel()
        pix = QPixmap(bunny_path("idle"))
        if not pix.isNull():
            bunny_label.setPixmap(
                pix.scaledToHeight(BUNNY_IMG_HEIGHT, Qt.TransformationMode.SmoothTransformation)
            )
        bunny_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(bunny_label)

        desc = QLabel(
            f"{APP_NAME} creates accurate, speaker-attributed transcripts\n"
            "of multi-speaker audio files like podcasts and interviews.\n\n"
            "Let's set up your transcription backend!"
        )
        desc.setProperty("class", "subtitle")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # ── Backend Selection ──
        backend_group = QGroupBox("Transcription Backend")
        bg_layout = QVBoxLayout(backend_group)

        self.backend_combo = QComboBox()
        for key, (name, _) in BACKEND_OPTIONS.items():
            self.backend_combo.addItem(name, key)
        self.backend_combo.currentIndexChanged.connect(self._on_backend_changed)
        bg_layout.addWidget(self.backend_combo)

        # API key input
        self.api_key_label = QLabel("API Key:")
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Enter your API key...")
        bg_layout.addWidget(self.api_key_label)
        bg_layout.addWidget(self.api_key_input)

        # Whisper model size (for local)
        self.model_label = QLabel("Model Size:")
        self.model_combo = QComboBox()
        for size, info in WHISPER_MODELS.items():
            self.model_combo.addItem(
                f"{size.capitalize()} — {info['quality']} quality, {info['vram']} VRAM",
                size,
            )
        self.model_combo.setCurrentIndex(1)  # base
        bg_layout.addWidget(self.model_label)
        bg_layout.addWidget(self.model_combo)

        # Test connection button
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.setProperty("class", "small-btn")
        self.test_btn.clicked.connect(self._test_connection)
        bg_layout.addWidget(self.test_btn)

        self.test_result = QLabel("")
        self.test_result.setWordWrap(True)
        bg_layout.addWidget(self.test_result)

        layout.addWidget(backend_group)

        # ── Buttons ──
        btn_layout = QHBoxLayout()
        self.done_btn = QPushButton("Get Started!")
        self.done_btn.setProperty("class", "start-btn")
        self.done_btn.clicked.connect(self._finish)
        btn_layout.addStretch()
        btn_layout.addWidget(self.done_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Initial state
        self._on_backend_changed()

    def _on_backend_changed(self):
        """Update visibility of fields based on selected backend."""
        backend_id = self.backend_combo.currentData()
        is_local = backend_id == "whisper_local"
        is_api = not is_local

        self.api_key_label.setVisible(is_api)
        self.api_key_input.setVisible(is_api)
        self.model_label.setVisible(is_local)
        self.model_combo.setVisible(is_local)
        self.test_result.setText("")

    def _test_connection(self):
        """Test the selected backend."""
        backend_id = self.backend_combo.currentData()
        api_key = self.api_key_input.text().strip()

        if backend_id == "whisper_local":
            backend = WhisperLocalBackend(
                model_size=self.model_combo.currentData()
            )
        elif backend_id == "openai":
            backend = OpenAIWhisperBackend(api_key=api_key)
        elif backend_id == "groq":
            backend = GroqWhisperBackend(api_key=api_key)
        elif backend_id == "mistral":
            backend = MistralTranscriptionBackend(api_key=api_key)
        else:
            return

        result = backend.test_connection()
        self.test_result.setText(result)

    def _finish(self):
        """Save settings and close the wizard."""
        backend_id = self.backend_combo.currentData()
        self.config["backend"] = backend_id

        if backend_id == "whisper_local":
            self.config["whisper_model_size"] = self.model_combo.currentData()
        else:
            api_key = self.api_key_input.text().strip()
            if api_key:
                if "api_keys" not in self.config:
                    self.config["api_keys"] = {}
                self.config["api_keys"][backend_id] = api_key

        self.config["first_run_complete"] = True
        save_config(self.config)
        self.accept()


# ═════════════════════════════════════════════════════════════════════
# Settings Dialog
# ═════════════════════════════════════════════════════════════════════


class SettingsDialog(QDialog):
    """Settings panel for configuring all app options."""

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle(f"{APP_NAME} — Settings")
        self.setMinimumSize(550, 500)
        self.setStyleSheet(STYLESHEET)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        tabs = QTabWidget()

        # ── Transcription Tab ──
        trans_tab = QWidget()
        trans_layout = QVBoxLayout(trans_tab)

        # Backend selection
        backend_group = QGroupBox("Transcription Backend")
        bg_layout = QFormLayout(backend_group)

        self.backend_combo = QComboBox()
        for key, (name, _) in BACKEND_OPTIONS.items():
            self.backend_combo.addItem(name, key)
        # Add custom endpoints
        for i, ep in enumerate(self.config.get("custom_endpoints", [])):
            self.backend_combo.addItem(ep.get("display_name", "Custom"), f"custom_{i}")

        current = self.config.get("backend", "openai")
        for i in range(self.backend_combo.count()):
            if self.backend_combo.itemData(i) == current:
                self.backend_combo.setCurrentIndex(i)
                break
        bg_layout.addRow("Backend:", self.backend_combo)

        # API keys
        self.api_key_inputs = {}
        for key in ("openai", "groq", "mistral", "huggingface"):
            inp = QLineEdit()
            inp.setEchoMode(QLineEdit.EchoMode.Password)
            inp.setText(self.config.get("api_keys", {}).get(key, ""))
            inp.setPlaceholderText(f"{key.capitalize()} API key...")
            self.api_key_inputs[key] = inp
            bg_layout.addRow(f"{key.capitalize()} Key:", inp)

        # Whisper model size
        self.model_combo = QComboBox()
        for size, info in WHISPER_MODELS.items():
            self.model_combo.addItem(f"{size.capitalize()} — {info['vram']}", size)
        current_model = self.config.get("whisper_model_size", "base")
        for i in range(self.model_combo.count()):
            if self.model_combo.itemData(i) == current_model:
                self.model_combo.setCurrentIndex(i)
                break
        bg_layout.addRow("Whisper Model:", self.model_combo)

        trans_layout.addWidget(backend_group)

        # Custom endpoint
        custom_group = QGroupBox("Add Custom Endpoint")
        cg_layout = QFormLayout(custom_group)

        self.custom_name = QLineEdit()
        self.custom_name.setPlaceholderText("My Custom Service")
        cg_layout.addRow("Name:", self.custom_name)

        self.custom_url = QLineEdit()
        self.custom_url.setPlaceholderText("https://api.example.com/v1")
        cg_layout.addRow("Endpoint URL:", self.custom_url)

        self.custom_key = QLineEdit()
        self.custom_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.custom_key.setPlaceholderText("API key...")
        cg_layout.addRow("API Key:", self.custom_key)

        self.custom_model = QLineEdit()
        self.custom_model.setPlaceholderText("whisper-1")
        self.custom_model.setText("whisper-1")
        cg_layout.addRow("Model:", self.custom_model)

        add_btn = QPushButton("Add Endpoint")
        add_btn.setProperty("class", "small-btn")
        add_btn.clicked.connect(self._add_custom_endpoint)
        cg_layout.addRow("", add_btn)

        trans_layout.addWidget(custom_group)
        trans_layout.addStretch()

        tabs.addTab(trans_tab, "Transcription")

        # ── Output Tab ──
        output_tab = QWidget()
        out_layout = QVBoxLayout(output_tab)

        output_group = QGroupBox("Output Settings")
        og_layout = QFormLayout(output_group)

        self.format_combo = QComboBox()
        self.format_combo.addItem("Plain Text (.txt)", "txt")
        self.format_combo.addItem("Subtitle (.srt)", "srt")
        self.format_combo.addItem("Word Document (.docx)", "docx")
        current_fmt = self.config.get("output_format", "txt")
        for i in range(self.format_combo.count()):
            if self.format_combo.itemData(i) == current_fmt:
                self.format_combo.setCurrentIndex(i)
                break
        og_layout.addRow("Output Format:", self.format_combo)

        self.auto_delete_cb = QCheckBox("Auto-delete intermediate files after completion")
        self.auto_delete_cb.setChecked(self.config.get("auto_delete_intermediates", False))
        og_layout.addRow("", self.auto_delete_cb)

        self.work_dir_input = QLineEdit()
        self.work_dir_input.setText(self.config.get("work_dir", ""))
        self.work_dir_input.setPlaceholderText("Default: ~/bunnyscriber_work")
        browse_btn = QPushButton("Browse")
        browse_btn.setProperty("class", "small-btn")
        browse_btn.clicked.connect(self._browse_work_dir)
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.work_dir_input)
        dir_layout.addWidget(browse_btn)
        og_layout.addRow("Work Directory:", dir_layout)

        out_layout.addWidget(output_group)

        # LLM cleanup
        cleanup_group = QGroupBox("LLM Cleanup Pass")
        cl_layout = QFormLayout(cleanup_group)

        self.cleanup_cb = QCheckBox("Enable LLM cleanup (checks speaker attribution)")
        self.cleanup_cb.setChecked(self.config.get("llm_cleanup_enabled", False))
        cl_layout.addRow("", self.cleanup_cb)

        self.cleanup_key = QLineEdit()
        self.cleanup_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.cleanup_key.setText(self.config.get("llm_cleanup_api_key", ""))
        self.cleanup_key.setPlaceholderText("API key for LLM cleanup...")
        cl_layout.addRow("LLM API Key:", self.cleanup_key)

        out_layout.addWidget(cleanup_group)
        out_layout.addStretch()

        tabs.addTab(output_tab, "Output & Cleanup")

        layout.addWidget(tabs)

        # ── Save / Cancel ──
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self._save)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _browse_work_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Work Directory")
        if path:
            self.work_dir_input.setText(path)

    def _add_custom_endpoint(self):
        name = self.custom_name.text().strip()
        url = self.custom_url.text().strip()
        key = self.custom_key.text().strip()
        model = self.custom_model.text().strip() or "whisper-1"

        if not name or not url:
            QMessageBox.warning(self, "Missing Info", "Name and URL are required.")
            return

        endpoint = {
            "display_name": name,
            "endpoint_url": url,
            "api_key": key,
            "model": model,
        }
        endpoints = self.config.get("custom_endpoints", [])
        endpoints.append(endpoint)
        self.config["custom_endpoints"] = endpoints

        idx = len(endpoints) - 1
        self.backend_combo.addItem(name, f"custom_{idx}")

        self.custom_name.clear()
        self.custom_url.clear()
        self.custom_key.clear()
        QMessageBox.information(self, "Added", f"Custom endpoint '{name}' added.")

    def _save(self):
        self.config["backend"] = self.backend_combo.currentData()
        self.config["whisper_model_size"] = self.model_combo.currentData()
        self.config["output_format"] = self.format_combo.currentData()
        self.config["auto_delete_intermediates"] = self.auto_delete_cb.isChecked()
        self.config["llm_cleanup_enabled"] = self.cleanup_cb.isChecked()
        self.config["llm_cleanup_api_key"] = self.cleanup_key.text().strip()

        work_dir = self.work_dir_input.text().strip()
        if work_dir:
            self.config["work_dir"] = work_dir

        # Save API keys
        api_keys = self.config.get("api_keys", {})
        for key, inp in self.api_key_inputs.items():
            val = inp.text().strip()
            if val:
                api_keys[key] = val
        self.config["api_keys"] = api_keys

        save_config(self.config)
        self.accept()


# ═════════════════════════════════════════════════════════════════════
# Speaker Verification Dialog
# ═════════════════════════════════════════════════════════════════════


class SpeakerVerificationDialog(QDialog):
    """Dialog for naming speakers and reviewing uncertain segments."""

    def __init__(self, verification_data: dict, parent=None):
        super().__init__(parent)
        self.verification_data = verification_data
        self.setWindowTitle("Speaker Verification")
        self.setMinimumSize(500, 400)
        self.setStyleSheet(STYLESHEET)

        self.speaker_names = {}
        self.non_speaker_labels = set()
        self.name_inputs = {}

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("Name Your Speakers")
        header.setProperty("class", "title")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        bunny_label = QLabel()
        pix = QPixmap(bunny_path("listen"))
        if not pix.isNull():
            bunny_label.setPixmap(
                pix.scaledToHeight(100, Qt.TransformationMode.SmoothTransformation)
            )
        bunny_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(bunny_label)

        desc = QLabel(
            "Listen to each speaker sample, then type a name.\n"
            "Check 'Not a speaker' for music, sound effects, etc."
        )
        desc.setProperty("class", "subtitle")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Speaker list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        samples = self.verification_data.get("speaker_samples", {})

        for label, sample_path in samples.items():
            frame = QGroupBox(f"Speaker: {label}")
            frame_layout = QHBoxLayout(frame)

            # Play button
            play_btn = QPushButton("Play Sample")
            play_btn.setProperty("class", "small-btn")
            play_btn.clicked.connect(lambda checked, p=sample_path: self._play_sample(p))
            frame_layout.addWidget(play_btn)

            # Name input
            name_input = QLineEdit()
            name_input.setPlaceholderText(f"Name for {label}...")
            name_input.setText(label.replace("SPEAKER_", "Speaker "))
            self.name_inputs[label] = name_input
            frame_layout.addWidget(name_input)

            # Not a speaker checkbox
            not_speaker_cb = QCheckBox("Not a speaker")
            not_speaker_cb.stateChanged.connect(
                lambda state, lbl=label: self._toggle_non_speaker(lbl, state)
            )
            frame_layout.addWidget(not_speaker_cb)

            scroll_layout.addWidget(frame)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Uncertain count note
        uncertain = self.verification_data.get("uncertain_count", 0)
        if uncertain > 0:
            note = QLabel(
                f"Note: {uncertain} uncertain segment(s) will be marked as [UNIDENTIFIED]."
            )
            note.setProperty("class", "subtitle")
            note.setWordWrap(True)
            layout.addWidget(note)

        # Done button
        done_btn = QPushButton("Done — Continue Transcription")
        done_btn.setProperty("class", "start-btn")
        done_btn.clicked.connect(self._finish)
        layout.addWidget(done_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _play_sample(self, sample_path: str):
        """Play an audio sample using the system default player."""
        import subprocess
        if sys.platform == "win32":
            os.startfile(sample_path)
        elif sys.platform == "darwin":
            subprocess.Popen(["afplay", sample_path])
        else:
            subprocess.Popen(["aplay", sample_path])

    def _toggle_non_speaker(self, label: str, state: int):
        if state == Qt.CheckState.Checked.value:
            self.non_speaker_labels.add(label)
        else:
            self.non_speaker_labels.discard(label)

    def _finish(self):
        self.speaker_names = {
            label: inp.text().strip() or label
            for label, inp in self.name_inputs.items()
        }
        self.accept()


# ═════════════════════════════════════════════════════════════════════
# Main Window
# ═════════════════════════════════════════════════════════════════════


class BunnyScriberWindow(QMainWindow):
    """Main application window for BunnyScriber."""

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.worker = None

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(700, 650)

        self._build_ui()
        self._apply_theme()
        self._set_bunny("idle")
        self._check_resume()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 16, 20, 12)

        # ── Header ───────────────────────────────────────────────────
        header_layout = QHBoxLayout()

        self.bunny_label = QLabel()
        self.bunny_label.setFixedSize(QSize(BUNNY_IMG_HEIGHT, BUNNY_IMG_HEIGHT))
        self.bunny_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.bunny_label)

        title_layout = QVBoxLayout()
        title = QLabel(APP_NAME)
        title.setProperty("class", "title")
        title_layout.addWidget(title)

        subtitle = QLabel("Accurate Speaker-Attributed Transcripts")
        subtitle.setProperty("class", "subtitle")
        title_layout.addWidget(subtitle)

        self.bunny_msg = QLabel(random.choice(IDLE_MESSAGES))
        self.bunny_msg.setProperty("class", "bunny-msg")
        title_layout.addWidget(self.bunny_msg)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        # Settings button
        settings_btn = QPushButton("Settings")
        settings_btn.setProperty("class", "small-btn")
        settings_btn.clicked.connect(self._open_settings)
        header_layout.addWidget(settings_btn, alignment=Qt.AlignmentFlag.AlignTop)

        layout.addLayout(header_layout)

        # ── Input Section ────────────────────────────────────────────
        input_group = QGroupBox("Audio Input")
        ig_layout = QVBoxLayout(input_group)

        file_layout = QHBoxLayout()
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("Select an audio file (MP3, WAV, FLAC, M4A, OGG)...")
        self.file_input.setReadOnly(True)
        file_layout.addWidget(self.file_input)

        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(browse_btn)
        ig_layout.addLayout(file_layout)

        self.duration_label = QLabel("")
        self.duration_label.setProperty("class", "subtitle")
        ig_layout.addWidget(self.duration_label)

        speakers_layout = QHBoxLayout()
        speakers_layout.addWidget(QLabel("Number of speakers:"))
        self.speakers_spin = QSpinBox()
        self.speakers_spin.setRange(2, 20)
        self.speakers_spin.setValue(2)
        speakers_layout.addWidget(self.speakers_spin)
        speakers_layout.addStretch()
        ig_layout.addLayout(speakers_layout)

        layout.addWidget(input_group)

        # ── Start Button ─────────────────────────────────────────────
        self.start_btn = QPushButton("Start Transcription")
        self.start_btn.setProperty("class", "start-btn")
        self.start_btn.clicked.connect(self._start_pipeline)
        layout.addWidget(self.start_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setProperty("class", "small-btn")
        self.cancel_btn.clicked.connect(self._cancel_pipeline)
        self.cancel_btn.setVisible(False)
        layout.addWidget(self.cancel_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # ── Progress Section ─────────────────────────────────────────
        progress_group = QGroupBox("Progress")
        pg_layout = QVBoxLayout(progress_group)

        self.phase_label = QLabel("")
        self.phase_label.setProperty("class", "phase-label")
        pg_layout.addWidget(self.phase_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        pg_layout.addWidget(self.progress_bar)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(180)
        self.log_area.setPlaceholderText(
            "*sniff sniff* No transcriptions yet...\n"
            "Pick an audio file and let me at those speakers!"
        )
        pg_layout.addWidget(self.log_area)

        layout.addWidget(progress_group)

        # ── Footer ───────────────────────────────────────────────────
        footer = QLabel("Made with love and carrots")
        footer.setProperty("class", "footer")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)

    def _apply_theme(self):
        """Apply the full stylesheet to the application."""
        self.setStyleSheet(STYLESHEET)

    def _set_bunny(self, state: str, message: str = None):
        """Update the bunny image and message."""
        pix = QPixmap(bunny_path(state))
        if not pix.isNull():
            self.bunny_label.setPixmap(
                pix.scaledToHeight(
                    BUNNY_IMG_HEIGHT,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

        if message:
            self.bunny_msg.setText(message)
        elif state == "idle":
            self.bunny_msg.setText(random.choice(IDLE_MESSAGES))
        elif state == "working":
            self.bunny_msg.setText(random.choice(WORKING_MESSAGES))
        elif state == "happy":
            self.bunny_msg.setText(random.choice(SUCCESS_MESSAGES))
        elif state == "error":
            self.bunny_msg.setText(random.choice(ERROR_MESSAGES))

    # ── File Handling ────────────────────────────────────────────────

    def _browse_file(self):
        """Open file dialog for audio selection."""
        formats = " ".join(f"*{ext}" for ext in
                          (".mp3", ".wav", ".flac", ".m4a", ".ogg", ".wma", ".aac"))
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Audio File",
            "",
            f"Audio Files ({formats});;All Files (*)",
        )
        if path:
            self.file_input.setText(path)
            try:
                from bunnyscriber.audio_utils import get_audio_duration_str
                dur = get_audio_duration_str(path)
                self.duration_label.setText(f"Duration: {dur}")
            except Exception:
                self.duration_label.setText("")

    # ── Pipeline Control ─────────────────────────────────────────────

    def _check_resume(self):
        """Check for resumable pipeline state."""
        work_dir = get_work_dir(self.config)
        if not os.path.exists(work_dir):
            return
        for name in os.listdir(work_dir):
            job_dir = os.path.join(work_dir, name)
            if not os.path.isdir(job_dir):
                continue
            state = check_resumable(job_dir)
            if not state:
                continue

            reply = QMessageBox.question(
                self,
                "Resume Previous Job?",
                f"Found an incomplete transcription job: {name}\n"
                f"Status: {state.get('status', 'unknown')}\n\n"
                "Would you like to resume it?",
            )
            if reply == QMessageBox.StandardButton.Yes:
                # Restore audio path from state
                audio_path = state.get("audio_path", "")
                if audio_path and os.path.exists(audio_path):
                    self.file_input.setText(audio_path)

                num_speakers = state.get("num_speakers", 2)
                self.speakers_spin.setValue(num_speakers)

                self._log(f"Resuming job: {name}")
                self._start_pipeline(resume_state=state)
            break

    def _start_pipeline(self, resume_state=None):
        """Start the transcription pipeline.

        Args:
            resume_state: Optional saved state dict for crash recovery.
        """
        audio_path = self.file_input.text()
        if not audio_path or not os.path.exists(audio_path):
            QMessageBox.warning(self, "No File", "Please select an audio file first.")
            return

        backend = _create_backend(self.config)
        if backend is None:
            QMessageBox.warning(
                self,
                "No Backend",
                "No transcription backend configured.\n"
                "Please set one up in Settings.",
            )
            self._open_settings()
            return

        self._set_bunny("working")
        self.start_btn.setEnabled(False)
        self.cancel_btn.setVisible(True)
        self.progress_bar.setValue(0)
        self.log_area.clear()

        signals = PipelineSignals()
        signals.progress.connect(self._on_progress)
        signals.phase_changed.connect(self._on_phase_changed)
        signals.log.connect(self._log)
        signals.error.connect(self._on_error)
        signals.finished.connect(self._on_finished)
        signals.cancelled.connect(self._on_cancelled)
        signals.speaker_verification_needed.connect(self._on_verification_needed)

        self.worker = PipelineWorker(
            audio_path=audio_path,
            num_speakers=self.speakers_spin.value(),
            backend=backend,
            config=self.config,
            signals=signals,
            resume_state=resume_state,
        )
        self.worker.start()

    def _cancel_pipeline(self):
        """Cancel the running pipeline."""
        if self.worker:
            self.worker.cancel()

    def _on_progress(self, msg: ProgressMessage):
        """Handle progress updates from the pipeline."""
        self.progress_bar.setValue(int(msg.percent * 100))

    def _on_phase_changed(self, phase: str):
        """Handle phase change notifications."""
        label = PHASE_NAMES.get(phase, phase)
        self.phase_label.setText(f"Phase: {label}")
        self._set_bunny("working")

    def _log(self, text: str):
        """Append a line to the log area."""
        self.log_area.append(text)

    def _on_error(self, error: str):
        """Handle pipeline errors."""
        self._set_bunny("error")
        self._log(f"ERROR: {error}")
        self.start_btn.setEnabled(True)
        self.cancel_btn.setVisible(False)
        QMessageBox.critical(self, "Error", f"Pipeline error:\n{error}")

    def _on_finished(self, output_path: str):
        """Handle pipeline completion."""
        self._set_bunny("happy")
        self.progress_bar.setValue(100)
        self.start_btn.setEnabled(True)
        self.cancel_btn.setVisible(False)
        self._log(f"\nTranscript saved to: {output_path}")

        QMessageBox.information(
            self,
            "Done!",
            f"Transcript saved to:\n{output_path}",
        )

    def _on_cancelled(self):
        """Handle pipeline cancellation."""
        self._set_bunny("idle", "*stretches* Okay, I stopped!")
        self.start_btn.setEnabled(True)
        self.cancel_btn.setVisible(False)
        self._log("Pipeline cancelled.")

    def _on_verification_needed(self, data: dict):
        """Show the speaker verification dialog."""
        dialog = SpeakerVerificationDialog(data, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.worker.set_verification_result(
                speaker_names=dialog.speaker_names,
                non_speaker_labels=dialog.non_speaker_labels,
                uncertain_assignments={},
            )
        else:
            # User closed dialog without confirming — cancel
            self.worker.cancel()

    def _open_settings(self):
        """Open the settings dialog."""
        dialog = SettingsDialog(self.config, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.config = load_config()


# ═════════════════════════════════════════════════════════════════════
# Application Entry Point
# ═════════════════════════════════════════════════════════════════════


def main():
    """Launch the BunnyScriber application."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName(APP_NAME)

    config = load_config()

    # First-run setup wizard
    if not config.get("first_run_complete"):
        wizard = SetupWizard(config)
        wizard.setStyleSheet(STYLESHEET)
        if wizard.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)
        config = load_config()

    window = BunnyScriberWindow(config)
    window.show()
    sys.exit(app.exec())
