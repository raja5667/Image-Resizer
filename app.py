import sys
import os
from pathlib import Path
from PIL import Image

from PyQt6.QtCore import (
    Qt, QPropertyAnimation, pyqtProperty, QTimer, 
    QEasingCurve, QSize
)
from PyQt6.QtGui import (
    QPixmap, QPainter, QPen, QColor, QLinearGradient, QBrush, QDoubleValidator
)
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QMessageBox, QFrame, QGraphicsDropShadowEffect,
    QLineEdit, QCheckBox, QProgressBar, QListWidget, QListWidgetItem, QGridLayout
)
from fpdf import FPDF

# ----------------------------------------------------------------------
# UI COMPONENT: UNIFIED PREVIEW & DROP ZONE
# ----------------------------------------------------------------------

class UnifiedCyberPreview(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("Drop images here\nor click anywhere to 'Add Images'")
        self.setWordWrap(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAcceptDrops(True)
        self.pixmap_data = None
        
        self.setStyleSheet("""
            QLabel {
                color: white; 
                font-size: 16px; 
                background: rgba(10, 25, 41, 0.7); 
                border-radius: 20px;
                border: 2px solid #1e3a5f;
            }
        """)

    def set_image(self, path):
        if not path or not os.path.exists(path):
            return
        self.pixmap_data = QPixmap(path)
        self.setText("") 
        self.setStyleSheet("QLabel { background: #050a10; border-radius: 20px; border: 2px solid #00eaff; }")
        self.update_preview()

    def clear_preview(self):
        self.pixmap_data = None
        self.setPixmap(QPixmap())
        self.setText("Drop images here\nor click anywhere to 'Add Images'")
        self.setStyleSheet("""
            QLabel {
                color: white; 
                font-size: 16px; 
                background: rgba(10, 25, 41, 0.7); 
                border-radius: 20px;
                border: 2px solid #1e3a5f;
            }
        """)

    def update_preview(self):
        if self.pixmap_data:
            scaled = self.pixmap_data.scaled(
                self.size() - QSize(40, 40), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.setPixmap(scaled)

    def mousePressEvent(self, event):
        if hasattr(self.window(), 'load_images'):
            self.window().load_images()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            self.setStyleSheet(self.styleSheet() + "border: 2px solid #00eaff;")

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            paths = [u.toLocalFile() for u in urls]
            if hasattr(self.window(), 'handle_multiple_files'):
                self.window().handle_multiple_files(paths)

# ----------------------------------------------------------------------
# STYLED CYBER WIDGETS
# ----------------------------------------------------------------------

class NeonCyberGlowButton(QPushButton):
    def __init__(self, text, color="#00eaff", parent=None):
        super().__init__(text, parent)
        self._glow = 20
        self.setMinimumHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: #0a0a0a;
                color: {color};
                border: 3px solid {color};
                border-radius: 12px;
                font-weight: bold;
                font-size: 13px;
            }}
        """)
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setColor(QColor(color))
        self.shadow.setBlurRadius(self._glow)
        self.shadow.setOffset(0, 0)
        self.setGraphicsEffect(self.shadow)
        self.anim = QPropertyAnimation(self, b"glow")
        self.anim.setDuration(300)

    def enterEvent(self, event): self.anim.setEndValue(45); self.anim.start()
    def leaveEvent(self, event): self.anim.setEndValue(20); self.anim.start()
    @pyqtProperty(int)
    def glow(self): return self._glow
    @glow.setter
    def glow(self, v): self._glow = v; self.shadow.setBlurRadius(v)

class AnimatedGradientButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._shift = 0.0
        self._is_animating = False
        self.anim = QPropertyAnimation(self, b"shift", self)
        self.anim.setDuration(2000)
        self.anim.setStartValue(0); self.anim.setEndValue(100); self.anim.setLoopCount(-1)
        self.setFixedHeight(50)

    @pyqtProperty(float)
    def shift(self): return self._shift
    @shift.setter
    def shift(self, val): self._shift = val; self.update()

    def start_animation(self):
        self._is_animating = True
        self.anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(2, 2, -2, -2)
        painter.setBrush(QColor(20, 20, 25))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 10, 10)
        if self._is_animating:
            s = (self._shift % 100) / 100
            grad = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.bottom())
            grad.setColorAt((0.0 + s) % 1.0, QColor("#ff007f"))
            grad.setColorAt((0.5 + s) % 1.0, QColor("#00ffcc"))
            grad.setColorAt((1.0 + s) % 1.0, QColor("#ff007f"))
            painter.setPen(QPen(QBrush(grad), 4))
            painter.drawRoundedRect(rect, 10, 10)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())

# ----------------------------------------------------------------------
# MAIN APPLICATION
# ----------------------------------------------------------------------

class ImageResizerPro(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ImageResizer Pro v2.6 — Cyberpunk Metric Edition")
        self.setFixedSize(1050, 680) 
        
        self.loaded_files = {} 
        self.ratio = 1.0
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # LEFT SIDE: Preview
        self.left_panel = QFrame()
        self.left_panel.setObjectName("PreviewFrame")
        left_layout = QVBoxLayout(self.left_panel)
        self.preview_area = UnifiedCyberPreview()
        left_layout.addWidget(self.preview_area)
        
        # RIGHT SIDE: Controls
        self.right_panel = QFrame()
        self.right_panel.setFixedWidth(380)
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setSpacing(15)

        title = QLabel("IMAGERESIZER PRO")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #00eaff;")
        right_layout.addWidget(title)

        # Buttons Row
        btn_row = QHBoxLayout()
        self.btn_add_folder = NeonCyberGlowButton("Add Folder", "#00eaff")
        self.btn_remove = NeonCyberGlowButton("Remove Selected", "#ff007f")
        
        self.btn_add_folder.clicked.connect(self.load_folder)
        self.btn_remove.clicked.connect(self.remove_selected)
        
        btn_row.addWidget(self.btn_add_folder)
        btn_row.addWidget(self.btn_remove)
        right_layout.addLayout(btn_row)

        # --- DIMENSION INPUTS BOX ---
        input_group = QFrame()
        input_group.setStyleSheet("background: #111b2d; border-radius: 12px; padding: 10px;")

        input_group = QFrame()
        input_group.setStyleSheet("""
            background: #111b2d;
            border-radius: 14px;
            padding: 8px;
        """)
        
        grid = QGridLayout(input_group)
        grid.setContentsMargins(10, 10, 10, 10)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        
        input_style = """
            background: #1e293b;
            color: white;
            border: 1px solid #334155;
            padding: 8px;
            border-radius: 6px;
        """
        cm_validator = QDoubleValidator(0.1, 1000.0, 2, self)
        cm_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        
        # Width
        lbl_w = QLabel("Width (cm):")
        self.w_input = QLineEdit("10.0")
        self.w_input.setValidator(cm_validator)
        self.w_input.setStyleSheet(input_style)
        self.w_input.setFixedWidth(318)
        
        # Height
        lbl_h = QLabel("Height (cm):")
        self.h_input = QLineEdit("15.0")
        self.h_input.setValidator(cm_validator)
        self.h_input.setStyleSheet(input_style)
        self.h_input.setFixedWidth(318)

        # Enter key navigation
        self.w_input.returnPressed.connect(self.focus_height)
        self.h_input.returnPressed.connect(self.focus_width)
        
        # Checkbox (top-right)
        self.cb_apply_all = QCheckBox("")
        self.cb_apply_all.setToolTip("Apply same size to all images")
        self.cb_apply_all.setStyleSheet("""
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 2px solid #00eaff;
                border-radius: 4px;
                background: #0a0a0a;
            }
            QCheckBox::indicator:checked {
                background-color: #00eaff;
            }
        """)
        
        grid.addWidget(lbl_w, 0, 0)
        grid.addWidget(self.w_input, 1, 0)
        grid.addWidget(lbl_h, 2, 0)
        grid.addWidget(self.h_input, 3, 0)
        
        grid.addWidget(
            self.cb_apply_all,
            0, 1,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight
        )
        
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 0)
        
        right_layout.addWidget(input_group)

        # --- REMAINING CHECKBOXES (Below the box) ---
        self.cb_ratio = QCheckBox("Maintain Aspect Ratio")
        self.cb_ratio.setChecked(True)
        
        self.cb_pdf = QCheckBox("Auto Arrange A4 PDF")
        self.cb_pdf.setChecked(True)
        
        # Apply style and add to the main right panel
        for cb in [self.cb_ratio, self.cb_pdf]:
            cb.setStyleSheet("QCheckBox { color: #94a3b8; margin-top: 5px; }")
            right_layout.addWidget(cb)
        
        # MULTI-IMAGE LIST
        list_container = QFrame()
        list_container.setStyleSheet("background: #0a0f1e; border-radius: 10px; border: 1px solid #1e293b;")
        list_layout = QVBoxLayout(list_container)
        
        self.file_list = QListWidget()
        self.file_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; color: #94a3b8; font-family: 'Consolas'; font-size: 12px; }
            QListWidget::item { padding: 3px; border-bottom: 1px solid #111b2d; border-radius: 4px; }
            QListWidget::item:selected { color: #00eaff; background: rgba(0, 234, 255, 0.1); border: 1px solid #00eaff; }
        """)
        self.file_list.itemClicked.connect(self.on_item_clicked)
        list_layout.addWidget(self.file_list)
        right_layout.addWidget(list_container, 1)

        self.progress = QProgressBar()
        self.progress.setFixedHeight(10)
        self.progress.setStyleSheet("QProgressBar { background: #0f172a; border-radius: 5px; } QProgressBar::chunk { background: #00eaff; }")
        right_layout.addWidget(self.progress)

        self.btn_run = AnimatedGradientButton("START CONVERSION")
        self.btn_run.clicked.connect(self.process)
        right_layout.addWidget(self.btn_run)

        layout.addWidget(self.left_panel, 1)
        layout.addWidget(self.right_panel)

        self.setStyleSheet(self.get_main_style())
        self.cb_apply_all.toggled.connect(self.save_current_dimensions)
        
        self.w_input.textChanged.connect(self.sync_height)
        self.h_input.textChanged.connect(self.sync_width)

    def get_main_style(self):
        return """
            QWidget { background-color: #020617; color: #e5e7eb; font-family: 'Segoe UI'; }
            QLabel { font-weight: 600; }
            QFrame#PreviewFrame { border-radius: 20px; background: #0a0f1e; border: 1px solid #1e293b; }
        """

    def load_images(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Images", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if files:
            self.handle_multiple_files(files)

    def load_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            valid_exts = ('.png', '.jpg', '.jpeg', '.webp')
            files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(valid_exts)]
            if files:
                self.handle_multiple_files(files)

    def handle_multiple_files(self, paths):
        for path in paths:
            fname = os.path.basename(path)
            if fname not in self.loaded_files:
                self.loaded_files[fname] = {
                    "path": path,
                    "width": self.w_input.text() if self.cb_apply_all.isChecked() else "10.0",
                    "height": self.h_input.text() if self.cb_apply_all.isChecked() else "15.0"
                }
                # Create item without the number first; we will update all labels next
                item = QListWidgetItem()
                item.setText(fname)                      # display text
                item.setData(Qt.ItemDataRole.UserRole, fname)  # ✅ real key
                self.file_list.addItem(item)
        
        self.reindex_list() # Helper to add the numbers
        
        if paths:
            self.file_list.setCurrentRow(self.file_list.count() - 1)
            self.on_item_clicked(self.file_list.currentItem())
            self.btn_run.start_animation()

    def on_item_clicked(self, item):
        display_name = item.text()
        fname = item.data(Qt.ItemDataRole.UserRole)
        data = self.loaded_files.get(fname)
        if data:
            try:
                with Image.open(data["path"]) as img:
                    self.ratio = img.width / img.height
                
                self.w_input.blockSignals(True)
                self.h_input.blockSignals(True)
                self.w_input.setText(data["width"])
                self.h_input.setText(data["height"])
                self.w_input.blockSignals(False)
                self.h_input.blockSignals(False)
                
                self.preview_area.set_image(data["path"])
            except Exception as e:
                print(f"Error loading {fname}: {e}")

    def remove_selected(self):
        current_item = self.file_list.currentItem()
        if current_item:
            # We need the original filename (without the "1. ") to remove from dictionary
            # A simple way is to find the data by searching or storing the clean name in item data
            display_text = current_item.text()
            fname = display_text.split(". ", 1)[-1] # Removes the "1. " prefix
            
            self.loaded_files.pop(fname, None)
            self.file_list.takeItem(self.file_list.row(current_item))
            
            self.reindex_list() # Refresh numbers for remaining items
            
            if self.file_list.count() == 0:
                self.preview_area.clear_preview()
            else:
                self.file_list.setCurrentRow(0)
                self.on_item_clicked(self.file_list.currentItem())

    def reindex_list(self):
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            raw_name = item.data(Qt.ItemDataRole.UserRole)
            item.setText(f"{i + 1}. {raw_name}")
           
    def sync_height(self):
        if self.cb_ratio.isChecked() and self.file_list.currentItem():
            try:
                w = float(self.w_input.text() or 0)
                self.h_input.blockSignals(True)
                self.h_input.setText(f"{w / self.ratio:.1f}")
                self.h_input.blockSignals(False)
            except: pass
        self.save_current_dimensions()

    def sync_width(self):
        if self.cb_ratio.isChecked() and self.file_list.currentItem():
            try:
                h = float(self.h_input.text() or 0)
                self.w_input.blockSignals(True)
                self.w_input.setText(f"{h * self.ratio:.1f}")
                self.w_input.blockSignals(False)
            except: pass
        self.save_current_dimensions()
    
    def focus_height(self):
        self.h_input.setFocus()
        self.h_input.selectAll()
    
    def focus_width(self):
        self.w_input.setFocus()
        self.w_input.selectAll()

    def save_current_dimensions(self):
        w_val = self.w_input.text()
        h_val = self.h_input.text()
    
        if self.cb_apply_all.isChecked():
            for fname in self.loaded_files:
                self.loaded_files[fname]["width"] = w_val
                self.loaded_files[fname]["height"] = h_val
        else:
            item = self.file_list.currentItem()
            if item:
                fname = item.data(Qt.ItemDataRole.UserRole)  # ✅ FIX
                if fname in self.loaded_files:
                    self.loaded_files[fname]["width"] = w_val
                    self.loaded_files[fname]["height"] = h_val
  
    def generate_a4_pdf(self, images_info, pdf_path):
        """images_info is now a list of (path, w_cm, h_cm)"""
        pdf = FPDF("P", "mm", "A4")
        pdf.set_auto_page_break(False)
        pdf.add_page()
    
        PAGE_W, PAGE_H = 210, 297
        MARGIN = 10
        GAP = 2
    
        x = MARGIN
        y = MARGIN
        row_max_height = 0
    
        for img_path, w_cm, h_cm in images_info:
            # Convert CM to MM for FPDF
            w_mm = w_cm * 10
            h_mm = h_cm * 10
    
            # Check if we need a new row
            if x + w_mm > PAGE_W - MARGIN:
                x = MARGIN
                y += row_max_height + GAP
                row_max_height = 0
    
            # Check if we need a new page
            if y + h_mm > PAGE_H - MARGIN:
                pdf.add_page()
                x = MARGIN
                y = MARGIN
                row_max_height = 0
    
            pdf.image(img_path, x=x, y=y, w=w_mm, h=h_mm)
    
            x += w_mm + GAP
            row_max_height = max(row_max_height, h_mm)
    
        pdf.output(pdf_path)

    def process(self):
        if not self.loaded_files:
            QMessageBox.warning(self, "Error", "No images loaded!")
            return
    
        output_dir = Path(r"D:\Users\Raja1\Downloads")
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except:
            QMessageBox.critical(self, "Error", "Could not access output folder.")
            return
    
        self.progress.setValue(0)
        total = len(self.loaded_files)
        # We now store a tuple of (path, width_cm, height_cm)
        images_data_for_pdf = []
        
        only_pdf = self.cb_pdf.isChecked()
    
        for i, (fname, data) in enumerate(self.loaded_files.items()):
            try:
                with Image.open(data["path"]) as img:
                    dpi = 300
                    cm_to_inch = 2.54
    
                    target_w = int((float(data["width"]) / cm_to_inch) * dpi)
                    target_h = int((float(data["height"]) / cm_to_inch) * dpi)
    
                    resized_img = img.resize(
                        (target_w, target_h),
                        Image.Resampling.LANCZOS
                    )
    
                    save_path = output_dir / f"temp_resized_{fname}" if only_pdf else output_dir / f"resized_{fname}"
                    resized_img.save(save_path, quality=95)
                    
                    # Store path AND the CM dimensions you entered manually
                    images_data_for_pdf.append((str(save_path), float(data["width"]), float(data["height"])))
    
                self.progress.setValue(int(((i + 1) / total) * 100))
                QApplication.processEvents()
    
            except Exception as e:
                print(f"Failed to process {fname}: {e}")
    
        if only_pdf and images_data_for_pdf:
            pdf_path = output_dir / "ImageResizer_Export.pdf"
            # Pass the rich data list to the PDF function
            self.generate_a4_pdf(images_data_for_pdf, str(pdf_path))
            
            for img_info in images_data_for_pdf:
                try:
                    p = Path(img_info[0])
                    if p.exists(): p.unlink()
                except: pass
            
            msg = f"PDF Generated successfully!\nLocation: {pdf_path}"
        else:
            msg = f"All images resized and saved to:\n{output_dir}"
    
        QMessageBox.information(self, "Success", msg)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageResizerPro()
    window.show()
    sys.exit(app.exec())