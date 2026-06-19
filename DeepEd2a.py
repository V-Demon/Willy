#!/usr/bin/env python3
"""
EFFECTS FORGE v2.0 — EFFECTS EDITOR BLACK EDITION
Éditeur de bibliothèque d'effets (effets.json) avec validation, recherche, duplication.
"""
import sys
import json
import uuid
import os
import re
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QFileDialog, QMessageBox, QTabWidget, QDialog, QDialogButtonBox,
    QFormLayout, QLineEdit, QTextEdit, QComboBox, QLabel,
    QSplitter, QStatusBar, QToolBar, QSizePolicy, QTreeWidget,
    QTreeWidgetItem, QInputDialog, QMenu
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor, QBrush, QTextCharFormat, QSyntaxHighlighter

# ============================================================================
#  COLOUR PALETTE
# ============================================================================
C = {
    'bg':           '#050805', 'bg_panel':     '#0a0f0a', 'bg_card':      '#0d140d',
    'bg_hover':     '#142014', 'border':       '#1a2e1a', 'border_bright':'#2a5a2a',
    'amber':        '#ffb000', 'amber_dim':    '#7a5500',
    'green':        '#00ff41', 'green_dim':    '#004d14', 'green_mid':    '#00b32d',
    'green_bright': '#80ff9f', 'white_dim':    '#4a664a',
    'red':          '#ff3030', 'cyan':         '#00e5ff', 'cyan_dim':     '#00558a',
    'fn_color':     '#00ff41', 'var_color':    '#ffb000', 'comment':      '#2a5a2a',
    'ctrl_color':   '#c586c0', 'flow_color':   '#d4d4d4'
}

STYLESHEET = f"""
QMainWindow, QWidget {{ background-color: {C['bg']}; color: {C['green']}; font-family: 'Courier New', monospace; font-size: 11px; }}
QToolBar {{ background-color: {C['bg_panel']}; border-bottom: 1px solid {C['border_bright']}; spacing: 6px; padding: 4px; }}
QTabWidget::pane {{ border: 1px solid {C['border_bright']}; background: {C['bg']}; }}
QTabBar::tab {{ background: {C['bg_panel']}; color: {C['white_dim']}; border: 1px solid {C['border']}; padding: 4px 12px; font-size: 10px; }}
QTabBar::tab:selected {{ background: {C['bg']}; color: {C['amber']}; border-color: {C['amber_dim']}; }}
QTableWidget {{ background-color: {C['bg_panel']}; color: {C['green']}; border: 1px solid {C['border']}; alternate-background-color: {C['bg_card']}; font-size: 10px; }}
QTableWidget::item:hover {{ background-color: {C['bg_hover']}; color: {C['amber']}; }}
QTableWidget::item:selected {{ background-color: {C['green_dim']}; color: {C['green_bright']}; }}
QHeaderView::section {{ background-color: {C['bg_card']}; color: {C['amber']}; border: 1px solid {C['border']}; padding: 4px; }}
QLineEdit, QComboBox, QTextEdit {{ background-color: {C['bg_card']}; color: {C['green']}; border: 1px solid {C['border_bright']}; padding: 4px; font-family: 'Courier New', monospace; }}
QLabel {{ color: {C['amber']}; }}
QStatusBar {{ background-color: {C['bg_panel']}; color: {C['amber_dim']}; border-top: 1px solid {C['border']}; }}
QPushButton {{ background-color: {C['green_dim']}; color: {C['green']}; border: 1px solid {C['border_bright']}; padding: 4px 10px; font-weight: bold; }}
QPushButton:hover {{ background-color: {C['border_bright']}; color: {C['amber']}; }}
QPushButton:pressed {{ background-color: {C['green']}; color: {C['bg']}; }}
QMenu {{ background-color: {C['bg_panel']}; color: {C['green']}; border: 1px solid {C['border_bright']}; }}
QMenu::item:selected {{ background-color: {C['green_dim']}; color: {C['green_bright']}; }}
"""


class PythonHighlighter(QSyntaxHighlighter):
    """Colorateur syntaxique pour le code Python des effets."""
    def __init__(self, document):
        super().__init__(document)
        self._build_rules()

    def _fmt(self, color, bold=False, italic=False):
        f = QTextCharFormat()
        f.setForeground(QColor(color))
        if bold:
            f.setFontWeight(QFont.Bold)
        if italic:
            f.setFontItalic(True)
        return f

    def _build_rules(self):
        self.rules = []
        # Mots-clés Python
        kw = r'\b(and|as|assert|async|await|break|class|continue|def|del|elif|else|except|finally|for|from|global|if|import|in|is|lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield|True|False|None)\b'
        self.rules += [
            (re.compile(kw), self._fmt(C['cyan'], bold=True)),
            (re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), self._fmt(C['amber'])),
            (re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), self._fmt(C['amber'])),
            (re.compile(r'\b\d+(\.\d+)?\b'), self._fmt(C['green_bright'])),
            (re.compile(r'#.*$'), self._fmt(C['comment'], italic=True)),
            (re.compile(r'[{}()\[\];,.]'), self._fmt(C['white_dim'])),
        ]

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            for m in pattern.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)


def validate_effect_schema(data):
    """Valide la structure d'un effet."""
    errors = []
    required = ['id', 'name', 'category', 'description', 'params', 'code']
    for r in required:
        if r not in data:
            errors.append(f"Missing required field: {r}")
        elif r == 'params' and not isinstance(data.get('params', {}), dict):
            errors.append("'params' must be a dictionary")
        elif r == 'code' and not isinstance(data.get('code', ''), str):
            errors.append("'code' must be a string")
    return errors


class EffectEditorDialog(QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.data = data or {}
        self.setWindowTitle(f"{'EDIT' if data else 'ADD'} EFFECT — BLACK EDITION")
        self.setStyleSheet(STYLESHEET)
        self.setMinimumSize(900, 700)
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)

        # --- Formulaire (gauche) ---
        self.form_widget = QWidget()
        form_layout = QFormLayout(self.form_widget)

        self.id_field = QLineEdit()
        self.id_field.setPlaceholderText("Ex: sepia, auto_crop...")
        form_layout.addRow("ID:", self.id_field)

        self.name_field = QLineEdit()
        self.name_field.setPlaceholderText("Ex: Sépia")
        form_layout.addRow("NAME:", self.name_field)

        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        categories = [
            'base', 'color', 'forensic', 'enhancement', 'artistic',
            'distortion', 'blur', 'stylize', 'lighting', 'custom',
            'paleography', 'epigraphy', 'osint'
        ]
        self.category_combo.addItems(categories)
        form_layout.addRow("CATEGORY:", self.category_combo)

        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(60)
        form_layout.addRow("DESCRIPTION:", self.desc_edit)

        self.params_edit = QTextEdit()
        self.params_edit.setPlaceholderText('{"param1": "value", "param2": 42}')
        self.params_edit.setMaximumHeight(80)
        form_layout.addRow("PARAMETERS (JSON):", self.params_edit)

        self.code_edit = QTextEdit()
        self.code_edit.setPlaceholderText("import numpy as np\nfrom PIL import Image\n# ...")
        self.code_edit.setMaximumHeight(200)
        # Colorateur syntaxique pour le code Python
        self.highlighter = PythonHighlighter(self.code_edit.document())
        form_layout.addRow("CODE (Python):", self.code_edit)

        self.validate_btn = QPushButton("✓ VALIDATE SCHEMA")
        self.validate_btn.clicked.connect(self._validate)
        form_layout.addRow("", self.validate_btn)

        self.form_widget.setLayout(form_layout)

        # --- Aperçu (droite) ---
        self.preview_widget = QWidget()
        preview_layout = QVBoxLayout(self.preview_widget)

        preview_label = QLabel("📺 LIVE PREVIEW (JSON)")
        preview_label.setStyleSheet(f"color: {C['cyan']}; font-weight: bold;")
        preview_layout.addWidget(preview_label)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setStyleSheet(f"background: {C['bg_card']}; font-family: 'Courier New', monospace; font-size: 10px;")
        preview_layout.addWidget(self.preview_text)

        self.preview_widget.setLayout(preview_layout)

        # Connecter les champs pour mise à jour en direct
        self._connect_live_updates()

        splitter.addWidget(self.form_widget)
        splitter.addWidget(self.preview_widget)
        splitter.setSizes([500, 400])
        layout.addWidget(splitter)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._validate_and_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _connect_live_updates(self):
        for w in [self.id_field, self.name_field]:
            w.textChanged.connect(self._update_preview)
        self.category_combo.currentTextChanged.connect(self._update_preview)
        for w in [self.desc_edit, self.params_edit, self.code_edit]:
            w.textChanged.connect(self._update_preview)

    def _update_preview(self):
        data = self._collect_data()
        self.preview_text.setPlainText(json.dumps(data, indent=2, ensure_ascii=False)[:5000])

    def _collect_data(self):
        data = {
            'id': self.id_field.text().strip(),
            'name': self.name_field.text().strip(),
            'category': self.category_combo.currentText(),
            'description': self.desc_edit.toPlainText().strip(),
        }
        try:
            params_str = self.params_edit.toPlainText().strip()
            data['params'] = json.loads(params_str) if params_str else {}
        except:
            data['params'] = {}
        data['code'] = self.code_edit.toPlainText()
        return {k: v for k, v in data.items() if v not in ([], None, '')}

    def _load_data(self):
        if not self.data:
            return
        self.id_field.setText(self.data.get('id', ''))
        self.name_field.setText(self.data.get('name', ''))
        idx = self.category_combo.findText(self.data.get('category', ''))
        if idx >= 0:
            self.category_combo.setCurrentIndex(idx)
        else:
            self.category_combo.setCurrentText(self.data.get('category', ''))
        self.desc_edit.setPlainText(self.data.get('description', ''))
        params = self.data.get('params', {})
        self.params_edit.setPlainText(json.dumps(params, indent=2, ensure_ascii=False))
        self.code_edit.setPlainText(self.data.get('code', ''))
        self._update_preview()

    def _validate(self):
        data = self._collect_data()
        errors = validate_effect_schema(data)
        if errors:
            QMessageBox.warning(self, "Validation Errors", "\n".join(errors))
        else:
            QMessageBox.information(self, "Validation", "✅ Schema valid!")

    def _validate_and_accept(self):
        data = self._collect_data()
        errors = validate_effect_schema(data)
        if errors:
            QMessageBox.critical(self, "Cannot Save", "\n".join(errors))
            return
        self.accept()

    def get_data(self):
        data = self._collect_data()
        if not data.get('id'):
            data['id'] = f"effect_{uuid.uuid4().hex[:8]}"
        return data


class EffectsEditorBlack(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EFFECTS FORGE v2.0 — EFFECTS EDITOR BLACK EDITION")
        self.resize(1400, 850)
        self.setStyleSheet(STYLESHEET)
        self.lib_data = {"_meta": {}, "effects": []}
        self.current_file = None
        self.undo_stack = []
        self.redo_stack = []
        self._setup_ui()
        self._setup_toolbar()
        self._setup_statusbar()
        self.statusBar().showMessage("🔥 BLACK EDITION READY. Load an effects library to begin.")

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # Barre de filtres
        filter_bar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search by name, category, description...")
        self.search_input.textChanged.connect(self._refresh_table)
        filter_bar.addWidget(self.search_input)

        self.category_filter = QComboBox()
        self.category_filter.setEditable(True)
        categories = ['ALL', 'base', 'color', 'forensic', 'enhancement', 'artistic',
                      'distortion', 'blur', 'stylize', 'lighting', 'custom',
                      'paleography', 'epigraphy', 'osint']
        self.category_filter.addItems(categories)
        self.category_filter.currentTextChanged.connect(self._refresh_table)
        filter_bar.addWidget(QLabel("CATEGORY:"))
        filter_bar.addWidget(self.category_filter)

        filter_bar.addStretch()
        main_layout.addLayout(filter_bar)

        self.tabs = QTabWidget()
        self.effects_table = self._create_table(['ID', 'Name', 'Category', 'Description', 'Params'])
        self.meta_table = self._create_metadata_table()
        self.tabs.addTab(self.effects_table, "⚙ EFFECTS")
        self.tabs.addTab(self.meta_table, "📄 METADATA")
        main_layout.addWidget(self.tabs)

    def _create_table(self, headers):
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setStretchLastSection(True)
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(lambda pos: self._show_context_menu(table, pos))
        table.cellDoubleClicked.connect(lambda r, c: self._edit_selected())
        return table

    def _create_metadata_table(self):
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(['Field', 'Value'])
        table.horizontalHeader().setStretchLastSection(True)
        return table

    def _setup_toolbar(self):
        tb = self.addToolBar("Actions")
        tb.setMovable(False)
        actions = [
            ("📂 LOAD", self._load_file),
            ("💾 SAVE", self._save_file),
            ("🧹 CLEAN & FIX", self._clean_library),
            ("➕ ADD", self._add_entry),
            ("📋 DUPLICATE", self._duplicate_selected),
            ("✏️ EDIT", self._edit_selected),
            ("🗑 DELETE", self._delete_selected),
            ("↺ UNDO", self._undo),
            ("↷ REDO", self._redo),
            ("📊 STATS", self._show_stats),
            ("🔍 VALIDATE ALL", self._validate_all)
        ]
        for txt, slot in actions:
            btn = QPushButton(txt)
            btn.clicked.connect(slot)
            tb.addWidget(btn)

    def _setup_statusbar(self):
        sb = self.statusBar()
        self.status_msg = QLabel("READY")
        self.stats_label = QLabel("0 effects")
        sb.addWidget(self.status_msg, 1)
        sb.addPermanentWidget(self.stats_label)

    def _show_context_menu(self, table, pos):
        menu = QMenu()
        menu.addAction("Edit", self._edit_selected)
        menu.addAction("Duplicate", self._duplicate_selected)
        menu.addAction("Delete", self._delete_selected)
        menu.exec_(table.mapToGlobal(pos))

    def _push_undo(self):
        self.undo_stack.append(json.dumps(self.lib_data))
        self.redo_stack.clear()

    def _undo(self):
        if not self.undo_stack:
            self.status_msg.setText("Nothing to undo")
            return
        self.redo_stack.append(json.dumps(self.lib_data))
        self.lib_data = json.loads(self.undo_stack.pop())
        self._refresh_table()
        self._update_metadata_table()
        self.status_msg.setText("Undo done")

    def _redo(self):
        if not self.redo_stack:
            self.status_msg.setText("Nothing to redo")
            return
        self.undo_stack.append(json.dumps(self.lib_data))
        self.lib_data = json.loads(self.redo_stack.pop())
        self._refresh_table()
        self._update_metadata_table()
        self.status_msg.setText("Redo done")

    def _load_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Effects Library", "", "JSON files (*.json)")
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            self.lib_data = self._clean_data(raw)
            self.current_file = path
            self._push_undo()
            self._refresh_table()
            self._update_metadata_table()
            self.status_msg.setText(f"Loaded: {os.path.basename(path)} ({len(self.lib_data['effects'])} effects)")
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to parse JSON:\n{e}")

    def _save_file(self):
        if not self.current_file:
            path, _ = QFileDialog.getSaveFileName(self, "Save As", "", "JSON files (*.json)")
            if not path:
                return
            self.current_file = path
        try:
            with open(self.current_file, 'w', encoding='utf-8') as f:
                json.dump(self.lib_data, f, indent=2, ensure_ascii=False)
            self.status_msg.setText(f"Saved: {os.path.basename(self.current_file)}")
            QMessageBox.information(self, "Success", "Library saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))

    def _clean_library(self):
        """Nettoie et valide la bibliothèque d'effets."""
        self.lib_data = self._clean_data(self.lib_data)
        self._push_undo()
        self._refresh_table()
        self._update_metadata_table()
        self.status_msg.setText("Library cleaned & validated")
        QMessageBox.information(self, "Clean Complete", "Library has been cleaned and validated.")

    def _clean_data(self, data):
        """Nettoie les données brutes pour garantir une structure cohérente."""
        if not isinstance(data, dict):
            data = {}
        data.setdefault("_meta", {
            "version": "5.0 FORENSIC OSINT & HERITAGE EXTREME",
            "description": "INGEN Systems — Image Effect Library Master Edition",
            "custom_template": {
                "name": "Mon Effet Pro",
                "category": "custom",
                "description": "Description de l'effet custom",
                "params": {},
                "code": "# 'img' est un objet PIL.Image.Image\n# 'params' est un dict des paramètres\n# Retournez un objet PIL.Image.Image\nresult = img.copy()\nreturn result"
            }
        })
        clean_effects = []
        for e in data.get("effects", []):
            if not isinstance(e, dict):
                continue
            # S'assurer que tous les champs requis existent
            e.setdefault("id", f"effect_{uuid.uuid4().hex[:8]}")
            e.setdefault("name", "Unnamed Effect")
            e.setdefault("category", "custom")
            e.setdefault("description", "")
            e.setdefault("params", {})
            e.setdefault("code", "")
            # Vérifier que params est bien un dictionnaire
            if not isinstance(e.get("params"), dict):
                e["params"] = {}
            clean_effects.append(e)
        data["effects"] = clean_effects
        return data

    def _refresh_table(self):
        search = self.search_input.text().lower()
        cat = self.category_filter.currentText()

        def matches(e):
            if cat != 'ALL' and e.get('category') != cat:
                return False
            if search:
                haystack = f"{e.get('name','')} {e.get('category','')} {e.get('description','')} {e.get('id','')}".lower()
                if search not in haystack:
                    return False
            return True

        self.effects_table.setRowCount(0)
        filtered = [e for e in self.lib_data.get("effects", []) if matches(e)]
        for i, e in enumerate(filtered):
            self.effects_table.insertRow(i)
            self.effects_table.setItem(i, 0, QTableWidgetItem(e.get("id", "")))
            self.effects_table.setItem(i, 1, QTableWidgetItem(e.get("name", "")))
            self.effects_table.setItem(i, 2, QTableWidgetItem(e.get("category", "")))
            desc = e.get("description", "")[:60]
            if len(e.get("description", "")) > 60:
                desc += "..."
            self.effects_table.setItem(i, 3, QTableWidgetItem(desc))
            params = list(e.get("params", {}).keys())
            self.effects_table.setItem(i, 4, QTableWidgetItem(", ".join(params[:3])))

        self.stats_label.setText(f"{len(self.lib_data['effects'])} effects")

    def _update_metadata_table(self):
        meta = self.lib_data.get("_meta", {})
        self.meta_table.setRowCount(0)
        for i, (k, v) in enumerate(meta.items()):
            self.meta_table.insertRow(i)
            self.meta_table.setItem(i, 0, QTableWidgetItem(str(k)))
            val_str = json.dumps(v, ensure_ascii=False)
            if len(val_str) > 100:
                val_str = val_str[:100] + "..."
            self.meta_table.setItem(i, 1, QTableWidgetItem(val_str))

    def _get_selected_id(self):
        table = self.tabs.currentWidget()
        if table in (self.meta_table, None):
            return None, table
        sel = table.selectionModel().selectedRows()
        if not sel:
            return None, table
        return table.item(sel[0].row(), 0).text(), table

    def _add_entry(self):
        dialog = EffectEditorDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            self._push_undo()
            self.lib_data["effects"].append(data)
            self._refresh_table()
            self.status_msg.setText(f"Added: {data.get('name')}")

    def _duplicate_selected(self):
        item_id, table = self._get_selected_id()
        if not item_id:
            return
        entry = next((e for e in self.lib_data["effects"] if e.get("id") == item_id), None)
        if not entry:
            return
        new_entry = json.loads(json.dumps(entry))
        new_entry['id'] = f"effect_{uuid.uuid4().hex[:8]}"
        new_entry['name'] = f"{entry.get('name')}_copy"
        self._push_undo()
        self.lib_data["effects"].append(new_entry)
        self._refresh_table()
        self.status_msg.setText(f"Duplicated: {entry.get('name')}")

    def _edit_selected(self):
        item_id, table = self._get_selected_id()
        if not item_id:
            return
        entry = next((e for e in self.lib_data["effects"] if e.get("id") == item_id), None)
        if not entry:
            return
        dialog = EffectEditorDialog(self, data=entry)
        if dialog.exec_() == QDialog.Accepted:
            updated = dialog.get_data()
            updated["id"] = item_id
            idx = self.lib_data["effects"].index(entry)
            self._push_undo()
            self.lib_data["effects"][idx] = updated
            self._refresh_table()
            self.status_msg.setText(f"Updated: {updated.get('name')}")

    def _delete_selected(self):
        item_id, table = self._get_selected_id()
        if not item_id:
            return
        if QMessageBox.question(self, "Confirm", f"Delete {item_id}?") != QMessageBox.Yes:
            return
        self._push_undo()
        self.lib_data["effects"] = [e for e in self.lib_data["effects"] if e.get("id") != item_id]
        self._refresh_table()
        self.status_msg.setText(f"Deleted: {item_id}")

    def _show_stats(self):
        effects = self.lib_data.get("effects", [])
        categories = {}
        for e in effects:
            cat = e.get('category', 'unknown')
            categories[cat] = categories.get(cat, 0) + 1
        stats = f"📊 STATISTICS\n\nTotal effects: {len(effects)}\n\nBy category:\n" + "\n".join(f"  {k}: {v}" for k, v in sorted(categories.items(), key=lambda x: -x[1]))
        QMessageBox.information(self, "Library Statistics", stats)

    def _validate_all(self):
        errors = []
        for i, e in enumerate(self.lib_data.get("effects", [])):
            errs = validate_effect_schema(e)
            if errs:
                errors.append(f"Effect #{i} ({e.get('name')}): {', '.join(errs)}")
        if errors:
            QMessageBox.warning(self, "Validation Report", "\n".join(errors[:50]))
        else:
            QMessageBox.information(self, "Validation Report", "✅ All effects valid!")


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont('Courier New', 10))
    win = EffectsEditorBlack()
    win.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()