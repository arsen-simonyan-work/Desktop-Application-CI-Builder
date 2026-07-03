from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from app_paths import get_resource_path
from generator import (
    PLATFORM_LINUX,
    PLATFORM_MACOS,
    PLATFORM_WINDOWS,
    ScaffoldConfig,
    detect_existing_scaffold,
    generate_scaffold,
    make_bundle_id,
    slugify_executable_name,
    slugify_package_name,
    summarize_paths,
)
from ui.custom_file_browser import DirectoryBrowserDialog, FileBrowserDialog
from version import APP_NAME, APP_WM_CLASS, BUNDLE_ID, __version__


APP_ICON_PATH = get_resource_path("assets", "icons", "app-icon.png")
APP_WINDOWS_ICON_PATH = get_resource_path("assets", "icons", "app-icon.ico")
APP_DIALOG_ICON_PATH = APP_WINDOWS_ICON_PATH if os.name == "nt" else APP_ICON_PATH


class App(ctk.CTk):
    PATH_PICKER_ICON = "📂"
    OUTER_PAD = 12
    PANEL_GAP = 8
    INNER_PAD = 6
    CARD_PAD_X = 2
    CARD_PAD_Y = 6
    FIELD_PAD_X = 12
    FIELD_PAD_Y = 12
    PALETTE = {
        "bg": "#10141a",
        "panel": "#161d26",
        "card": "#1d2631",
        "border": "#32404f",
        "text": "#eef4fb",
        "muted": "#96a5b5",
        "accent": "#d67a3c",
        "accent_hover": "#b9662f",
        "button_text": "#fff7f0",
        "log_bg": "#131923",
    }

    def __init__(self) -> None:
        ctk.set_appearance_mode("dark")
        self._configure_platform_process_identity()
        super().__init__(className=APP_WM_CLASS)

        self.loaded_scaffold_config: ScaffoldConfig | None = None

        self.target_dir_var = ctk.StringVar(value="")
        self.icon_path_var = ctk.StringVar(value="")
        self.app_name_var = ctk.StringVar(value="My Desktop App")
        self.version_var = ctk.StringVar(value="0.1.0")
        self.package_name_var = ctk.StringVar(value="my-desktop-app")
        self.bundle_id_var = ctk.StringVar(value="com.example.mydesktopapp")
        self.entry_script_var = ctk.StringVar(value="main.py")
        self.executable_name_var = ctk.StringVar(value="MyDesktopApp")
        self.manufacturer_var = ctk.StringVar(value="Example Studio")
        self.linux_platform_var = ctk.BooleanVar(value=True)
        self.windows_platform_var = ctk.BooleanVar(value=True)
        self.macos_platform_var = ctk.BooleanVar(value=True)

        self.title(f"{APP_NAME} {__version__}")
        self.geometry("1280x820")
        self.minsize(1160, 760)
        self.configure(fg_color=self.PALETTE["bg"])

        self._apply_window_identity()
        self.after(50, self._apply_window_identity)

        self._build_ui()
        self._sync_derived_fields()

    @staticmethod
    def _configure_platform_process_identity() -> None:
        if os.name != "nt":
            return
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(BUNDLE_ID)
        except Exception:
            pass

    def _apply_window_identity(self) -> None:
        self._apply_macos_dock_icon()

        if os.name == "nt" and APP_WINDOWS_ICON_PATH.is_file():
            try:
                self.iconbitmap(default=str(APP_WINDOWS_ICON_PATH))
                return
            except tk.TclError:
                pass

        if APP_ICON_PATH.is_file():
            try:
                icon_image = tk.PhotoImage(file=str(APP_ICON_PATH))
                self.iconphoto(True, icon_image)
                self._app_icon_image = icon_image
            except tk.TclError:
                pass

    def _apply_macos_dock_icon(self) -> None:
        if sys.platform != "darwin" or not APP_ICON_PATH.is_file():
            return

        try:
            from AppKit import NSApplication, NSImage

            icon_image = NSImage.alloc().initByReferencingFile_(str(APP_ICON_PATH))
            if icon_image and icon_image.isValid():
                NSApplication.sharedApplication().setApplicationIconImage_(icon_image)
                self._macos_app_icon_image = icon_image
        except Exception:
            pass

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1, uniform="main")
        self.grid_columnconfigure(1, weight=1, uniform="main")
        self.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(
            self,
            fg_color=self.PALETTE["panel"],
            corner_radius=20,
            border_width=1,
            border_color=self.PALETTE["border"],
        )
        left.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(self.OUTER_PAD, self.PANEL_GAP),
            pady=self.OUTER_PAD,
        )
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(0, weight=1)

        right = ctk.CTkFrame(
            self,
            fg_color=self.PALETTE["panel"],
            corner_radius=20,
            border_width=1,
            border_color=self.PALETTE["border"],
        )
        right.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(self.PANEL_GAP, self.OUTER_PAD),
            pady=self.OUTER_PAD,
        )
        right.grid_rowconfigure(2, weight=1)
        right.grid_columnconfigure(0, weight=1)

        form = ctk.CTkScrollableFrame(
            left,
            fg_color=self.PALETTE["panel"],
            corner_radius=0,
        )
        form.grid(row=0, column=0, sticky="nsew", padx=self.INNER_PAD, pady=self.INNER_PAD)
        form.grid_columnconfigure(0, weight=1)

        self._build_path_section(form)
        self._build_metadata_section(form)
        self._build_identity_section(form)
        self._build_platform_section(form)
        self._build_actions_section(form)

        guide = ctk.CTkFrame(
            right,
            fg_color=self.PALETTE["card"],
            corner_radius=18,
            border_width=1,
            border_color=self.PALETTE["border"],
        )
        guide.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=self.INNER_PAD,
            pady=(self.INNER_PAD, self.CARD_PAD_Y),
        )
        guide.grid_columnconfigure(0, weight=1)

        guide_title = ctk.CTkLabel(
            guide,
            text="What It Generates",
            text_color=self.PALETTE["text"],
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        guide.grid_rowconfigure(0, weight=0)
        guide_title.grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        guide_body = ctk.CTkLabel(
            guide,
            text=(
                "- GitHub Actions release workflow\n"
                "- PyInstaller spec and packaging scripts\n"
                "- Runtime and platform-specific icon assets\n"
                "- Stored scaffold metadata for later editing\n\n"
                "Select an existing generated folder to load its values and update the scaffold in place."
            ),
            text_color=self.PALETTE["muted"],
            justify="left",
            anchor="w",
            font=ctk.CTkFont(size=14),
        )
        guide_body.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 14))

        log_label = ctk.CTkLabel(
            right,
            text="Generation Log",
            text_color=self.PALETTE["text"],
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        log_label.grid(row=1, column=0, sticky="nw", padx=self.INNER_PAD, pady=(2, 4))

        self.log = ctk.CTkTextbox(
            right,
            corner_radius=20,
            fg_color=self.PALETTE["log_bg"],
            text_color=self.PALETTE["text"],
            border_width=1,
            border_color=self.PALETTE["border"],
            font=ctk.CTkFont(family="Courier", size=13),
        )
        self.log.grid(row=2, column=0, sticky="nsew", padx=self.INNER_PAD, pady=(0, self.INNER_PAD))
        self._set_log(
            "Ready.\n\n"
            "1. Choose the target project folder.\n"
            "2. If this folder already has a generated scaffold, values will load automatically.\n"
            "3. Choose the master icon PNG.\n"
            "4. Review metadata and platforms.\n"
            "5. Click Generate Scaffold or Update Scaffold."
        )

    def _build_path_section(self, parent: ctk.CTkScrollableFrame) -> None:
        card = self._make_card(parent, "Paths", 0)
        self._labeled_path_field(
            card,
            row=0,
            label="Target Project Folder",
            variable=self.target_dir_var,
            command=self._choose_target_dir,
        )
        self._labeled_path_field(
            card,
            row=1,
            label="Master Icon PNG",
            variable=self.icon_path_var,
            command=self._choose_icon,
        )

    def _build_metadata_section(self, parent: ctk.CTkScrollableFrame) -> None:
        card = self._make_card(parent, "Metadata", 1)
        self._labeled_entry(card, 0, 0, "App Name", self.app_name_var)
        self._labeled_entry(card, 0, 1, "Version", self.version_var)
        self._labeled_entry(card, 1, 0, "Entry Script", self.entry_script_var)
        self._labeled_entry(card, 1, 1, "Executable Name", self.executable_name_var)
        self._labeled_entry(card, 2, 0, "Manufacturer", self.manufacturer_var)

        autofill = ctk.CTkButton(
            card,
            text="Autofill Derived Fields",
            fg_color=self.PALETTE["card"],
            hover_color=self.PALETTE["border"],
            text_color=self.PALETTE["text"],
            border_width=1,
            border_color=self.PALETTE["border"],
            command=self._sync_derived_fields,
        )
        autofill.grid(
            row=7,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=self.FIELD_PAD_X,
            pady=(2, self.FIELD_PAD_Y),
        )

    def _build_identity_section(self, parent: ctk.CTkScrollableFrame) -> None:
        card = self._make_card(parent, "Package Identity", 2)
        self._labeled_entry(card, 0, 0, "Package Name", self.package_name_var)
        self._labeled_entry(card, 0, 1, "Bundle ID", self.bundle_id_var)

    def _build_platform_section(self, parent: ctk.CTkScrollableFrame) -> None:
        card = ctk.CTkFrame(
            parent,
            fg_color=self.PALETTE["card"],
            corner_radius=18,
            border_width=1,
            border_color=self.PALETTE["border"],
        )
        card.grid(row=3, column=0, sticky="ew", padx=self.CARD_PAD_X, pady=(0, self.CARD_PAD_Y))
        card.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=self.FIELD_PAD_X, pady=self.FIELD_PAD_Y)
        header.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(
            header,
            text="Target Platform",
            text_color=self.PALETTE["text"],
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title_label.grid(row=0, column=0, sticky="w")

        checkbox_row = ctk.CTkFrame(header, fg_color="transparent")
        checkbox_row.grid(row=0, column=1, sticky="e")

        linux_checkbox = ctk.CTkCheckBox(
            checkbox_row,
            text="Linux (deb)",
            variable=self.linux_platform_var,
            text_color=self.PALETTE["text"],
            fg_color=self.PALETTE["accent"],
            hover_color=self.PALETTE["accent_hover"],
            border_color=self.PALETTE["border"],
        )
        linux_checkbox.grid(row=0, column=0, sticky="w")

        windows_checkbox = ctk.CTkCheckBox(
            checkbox_row,
            text="Windows (msi)",
            variable=self.windows_platform_var,
            text_color=self.PALETTE["text"],
            fg_color=self.PALETTE["accent"],
            hover_color=self.PALETTE["accent_hover"],
            border_color=self.PALETTE["border"],
        )
        windows_checkbox.grid(row=0, column=1, sticky="w", padx=(18, 0))

        macos_checkbox = ctk.CTkCheckBox(
            checkbox_row,
            text="macOS (dmg)",
            variable=self.macos_platform_var,
            text_color=self.PALETTE["text"],
            fg_color=self.PALETTE["accent"],
            hover_color=self.PALETTE["accent_hover"],
            border_color=self.PALETTE["border"],
        )
        macos_checkbox.grid(row=0, column=2, sticky="w", padx=(18, 0))

    def _build_actions_section(self, parent: ctk.CTkScrollableFrame) -> None:
        card = ctk.CTkFrame(
            parent,
            fg_color=self.PALETTE["card"],
            corner_radius=18,
            border_width=1,
            border_color=self.PALETTE["border"],
        )
        card.grid(row=4, column=0, sticky="ew", padx=self.CARD_PAD_X, pady=(0, self.CARD_PAD_Y))
        card.grid_columnconfigure(0, weight=1)

        self.generate_button = ctk.CTkButton(
            card,
            text="Generate Scaffold",
            fg_color=self.PALETTE["accent"],
            hover_color=self.PALETTE["accent_hover"],
            text_color=self.PALETTE["button_text"],
            height=46,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._generate,
        )
        self.generate_button.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=self.FIELD_PAD_X,
            pady=self.FIELD_PAD_Y,
        )

    def _make_card(self, parent: ctk.CTkScrollableFrame, title: str, row: int) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            parent,
            fg_color=self.PALETTE["card"],
            corner_radius=18,
            border_width=1,
            border_color=self.PALETTE["border"],
        )
        card.grid(row=row, column=0, sticky="ew", padx=self.CARD_PAD_X, pady=(0, self.CARD_PAD_Y))
        card.grid_columnconfigure(0, weight=1, uniform=f"card_{row}")
        card.grid_columnconfigure(1, weight=1, uniform=f"card_{row}")

        title_label = ctk.CTkLabel(
            card,
            text=title,
            text_color=self.PALETTE["text"],
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title_label.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            padx=self.FIELD_PAD_X,
            pady=(self.FIELD_PAD_Y, 10),
        )
        return card

    def _labeled_entry(
        self,
        parent: ctk.CTkFrame,
        row: int,
        column: int,
        label: str,
        variable: ctk.StringVar,
    ) -> None:
        base_row = row * 2 + 1
        label_widget = ctk.CTkLabel(
            parent,
            text=label,
            text_color=self.PALETTE["muted"],
            anchor="w",
        )
        label_widget.grid(row=base_row, column=column, sticky="ew", padx=self.FIELD_PAD_X, pady=(0, 4))

        entry = ctk.CTkEntry(
            parent,
            textvariable=variable,
            fg_color=self.PALETTE["panel"],
            text_color=self.PALETTE["text"],
            border_color=self.PALETTE["border"],
            height=38,
        )
        entry.grid(
            row=base_row + 1,
            column=column,
            sticky="ew",
            padx=self.FIELD_PAD_X,
            pady=(0, self.FIELD_PAD_Y),
        )

    def _labeled_path_field(
        self,
        parent: ctk.CTkFrame,
        row: int,
        label: str,
        variable: ctk.StringVar,
        command,
    ) -> None:
        field = ctk.CTkFrame(parent, fg_color="transparent")
        field.grid(
            row=row + 1,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=self.FIELD_PAD_X,
            pady=(0, self.FIELD_PAD_Y),
        )
        field.grid_columnconfigure(0, minsize=128)
        field.grid_columnconfigure(1, weight=1)

        label_widget = ctk.CTkLabel(
            field,
            text=label,
            text_color=self.PALETTE["muted"],
            anchor="w",
        )
        label_widget.grid(row=0, column=0, sticky="w", padx=(0, 12))

        entry = ctk.CTkEntry(
            field,
            textvariable=variable,
            fg_color=self.PALETTE["panel"],
            text_color=self.PALETTE["text"],
            border_color=self.PALETTE["border"],
            height=38,
            state="readonly",
        )
        entry.grid(row=0, column=1, sticky="ew", padx=(0, 0))

        button = ctk.CTkButton(
            field,
            text=self.PATH_PICKER_ICON,
            width=30,
            height=38,
            fg_color=self.PALETTE["panel"],
            hover_color=self.PALETTE["card"],
            text_color=self.PALETTE["text"],
            border_width=1,
            border_color=self.PALETTE["border"],
            corner_radius=10,
            font=ctk.CTkFont(size=15),
            command=command,
        )
        button.grid(row=0, column=2, padx=(8, 0))

    def _set_generate_mode(self, is_edit_mode: bool) -> None:
        label = "Update Scaffold" if is_edit_mode else "Generate Scaffold"
        self.generate_button.configure(text=label)

    def _populate_from_scaffold(self, config: ScaffoldConfig) -> None:
        self.target_dir_var.set(str(config.target_dir))
        self.icon_path_var.set(str(config.icon_path) if config.icon_path.exists() else "")
        self.app_name_var.set(config.app_name)
        self.version_var.set(config.version)
        self.package_name_var.set(config.package_name)
        self.bundle_id_var.set(config.bundle_id)
        self.entry_script_var.set(config.entry_script)
        self.executable_name_var.set(config.executable_name)
        self.manufacturer_var.set(config.manufacturer)
        self.linux_platform_var.set(PLATFORM_LINUX in config.platforms)
        self.windows_platform_var.set(PLATFORM_WINDOWS in config.platforms)
        self.macos_platform_var.set(PLATFORM_MACOS in config.platforms)

    def _load_target_dir(self, target_dir: Path) -> None:
        self.target_dir_var.set(str(target_dir))
        detected = detect_existing_scaffold(target_dir)
        self.loaded_scaffold_config = detected
        self._set_generate_mode(detected is not None)

        if detected is None:
            self._append_log(
                f"\nSelected target folder:\n{target_dir}\n\n"
                "No existing scaffold metadata detected. You can generate a new scaffold here.\n"
            )
            return

        self._populate_from_scaffold(detected)
        self._set_log(
            "Existing scaffold loaded for editing.\n\n"
            f"Target: {detected.target_dir}\n"
            f"App: {detected.app_name}\n"
            f"Version: {detected.version}\n"
            f"Platforms: {', '.join(detected.platforms)}\n\n"
            "Review values, adjust anything you need, then click Update Scaffold."
        )

    def _choose_target_dir(self) -> None:
        initial_dir = self.target_dir_var.get().strip() or str(Path.cwd())
        selected = DirectoryBrowserDialog(
            self,
            initial_dir=initial_dir,
            title="Select target project folder",
            icon_path=APP_DIALOG_ICON_PATH,
        ).show()
        if selected:
            self._load_target_dir(Path(selected))

    def _choose_icon(self) -> None:
        initial_path = self.icon_path_var.get().strip() or self.target_dir_var.get().strip() or str(Path.cwd())
        selected = FileBrowserDialog(
            self,
            initial_path=initial_path,
            title="Select master icon PNG",
            icon_path=APP_DIALOG_ICON_PATH,
            allowed_extensions=[".png"],
        ).show()
        if selected:
            self.icon_path_var.set(selected)

    def _sync_derived_fields(self) -> None:
        app_name = self.app_name_var.get().strip() or "My Desktop App"
        manufacturer = self.manufacturer_var.get().strip() or "Example Studio"
        package_name = slugify_package_name(app_name)
        bundle_id = make_bundle_id(package_name, manufacturer)
        executable_name = slugify_executable_name(app_name)

        self.package_name_var.set(package_name)
        self.bundle_id_var.set(bundle_id)
        self.executable_name_var.set(executable_name)
        if not self.manufacturer_var.get().strip():
            self.manufacturer_var.set("Example Studio")

    def _selected_platforms(self) -> tuple[str, ...]:
        platforms: list[str] = []
        if self.linux_platform_var.get():
            platforms.append(PLATFORM_LINUX)
        if self.windows_platform_var.get():
            platforms.append(PLATFORM_WINDOWS)
        if self.macos_platform_var.get():
            platforms.append(PLATFORM_MACOS)
        return tuple(platforms)

    def _build_config(self) -> ScaffoldConfig:
        executable_name = self.executable_name_var.get().strip()
        package_name = self.package_name_var.get().strip()
        return ScaffoldConfig(
            target_dir=Path(self.target_dir_var.get().strip()),
            icon_path=Path(self.icon_path_var.get().strip()),
            app_name=self.app_name_var.get().strip(),
            version=self.version_var.get().strip(),
            package_name=package_name,
            executable_name=executable_name,
            bundle_id=self.bundle_id_var.get().strip(),
            entry_script=self.entry_script_var.get().strip(),
            manufacturer=self.manufacturer_var.get().strip(),
            app_data_dir_name=executable_name,
            linux_data_dir_name=package_name,
            platforms=self._selected_platforms(),
        )

    def _generate(self) -> None:
        previous_config = self.loaded_scaffold_config
        edit_mode = previous_config is not None
        idle_label = "Update Scaffold" if edit_mode else "Generate Scaffold"

        try:
            config = self._build_config()
            self.generate_button.configure(state="disabled", text="Generating...")
            created = generate_scaffold(config, previous_config=previous_config)
        except Exception as exc:
            self._append_log(f"\nERROR\n{exc}\n")
            messagebox.showerror(APP_NAME, str(exc))
        else:
            reloaded = detect_existing_scaffold(config.target_dir) or config
            self.loaded_scaffold_config = reloaded
            self._populate_from_scaffold(reloaded)
            self._set_generate_mode(True)

            summary = summarize_paths(created, config.target_dir)
            status_text = "Scaffold updated successfully." if edit_mode else "Scaffold generated successfully."
            self._set_log(
                f"{status_text}\n\n"
                f"Target: {config.target_dir}\n\n"
                "Created, updated, or removed:\n"
                f"{summary}"
            )
            messagebox.showinfo(APP_NAME, status_text)
        finally:
            self.generate_button.configure(state="normal", text=idle_label)
            if self.loaded_scaffold_config is not None:
                self._set_generate_mode(True)

    def _set_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.insert("1.0", text)
        self.log.configure(state="disabled")

    def _append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")


if __name__ == "__main__":
    app = App()
    app.mainloop()
