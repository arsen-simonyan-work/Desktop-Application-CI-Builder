from __future__ import annotations

from pathlib import Path
from tkinter import PhotoImage, filedialog, messagebox

import customtkinter as ctk

from app_paths import get_resource_path
from generator import (
    PLATFORM_LINUX,
    PLATFORM_MACOS,
    PLATFORM_WINDOWS,
    ScaffoldConfig,
    generate_scaffold,
    make_bundle_id,
    slugify_package_name,
    slugify_executable_name,
    summarize_paths,
)
from version import APP_NAME, __version__


class App(ctk.CTk):
    PATH_PICKER_ICON = "📂"
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
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.title(f"{APP_NAME} {__version__}")
        self.geometry("1280x820")
        self.minsize(1160, 760)
        self.configure(fg_color=self.PALETTE["bg"])

        try:
            self.wm_class("DesktopAppCiBuilder")
        except Exception:
            pass

        self._apply_window_icon()

        self.target_dir_var = ctk.StringVar(value="")
        self.icon_path_var = ctk.StringVar(value="")
        self.app_name_var = ctk.StringVar(value="My Desktop App")
        self.version_var = ctk.StringVar(value="0.1.0")
        self.package_name_var = ctk.StringVar(value="my-desktop-app")
        self.bundle_id_var = ctk.StringVar(value="com.example.mydesktopapp")
        self.entry_script_var = ctk.StringVar(value="main.py")
        self.manufacturer_var = ctk.StringVar(value="Example Studio")
        self.linux_platform_var = ctk.BooleanVar(value=True)
        self.windows_platform_var = ctk.BooleanVar(value=True)
        self.macos_platform_var = ctk.BooleanVar(value=True)

        self._build_ui()
        self._sync_derived_fields()

    def _apply_window_icon(self) -> None:
        png_icon = get_resource_path("assets", "icons", "app-icon.png")
        if png_icon.exists():
            try:
                self.window_icon = PhotoImage(file=str(png_icon))
                self.iconphoto(True, self.window_icon)
            except Exception:
                pass

        ico_icon = get_resource_path("assets", "icons", "app-icon.ico")
        if ico_icon.exists():
            try:
                self.iconbitmap(default=str(ico_icon))
            except Exception:
                pass

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1, uniform="main")
        self.grid_columnconfigure(1, weight=1, uniform="main")
        self.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(
            self,
            fg_color=self.PALETTE["panel"],
            corner_radius=24,
            border_width=1,
            border_color=self.PALETTE["border"],
        )
        left.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=20)
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(0, weight=1)

        right = ctk.CTkFrame(
            self,
            fg_color=self.PALETTE["panel"],
            corner_radius=24,
            border_width=1,
            border_color=self.PALETTE["border"],
        )
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=20)
        right.grid_rowconfigure(2, weight=1)
        right.grid_columnconfigure(0, weight=1)

        form = ctk.CTkFrame(
            left,
            fg_color=self.PALETTE["panel"],
            corner_radius=0,
        )
        form.grid(row=0, column=0, sticky="nsew", padx=9, pady=9)
        form.grid_columnconfigure(0, weight=1)

        self._build_path_section(form)
        self._build_metadata_section(form)
        self._build_identity_section(form)
        self._build_platform_section(form)
        self._build_actions_section(form)

        guide = ctk.CTkFrame(
            right,
            fg_color=self.PALETTE["card"],
            corner_radius=20,
            border_width=1,
            border_color=self.PALETTE["border"],
        )
        guide.grid(row=0, column=0, sticky="ew", padx=11, pady=(11, 6))
        guide.grid_columnconfigure(0, weight=1)

        guide_title = ctk.CTkLabel(
            guide,
            text="What It Generates",
            text_color=self.PALETTE["text"],
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        guide.grid_rowconfigure(0, weight=0)
        guide_title.grid(row=0, column=0, sticky="w", padx=18, pady=(16, 8))

        guide_body = ctk.CTkLabel(
            guide,
            text=(
                "- GitHub Actions release workflow\n"
                "- PyInstaller spec\n"
                "- Runtime and platform-specific icon assets\n"
                "- deb / msi / dmg packaging scripts by selection\n"
                "- version.py, app_paths.py, VERSION\n\n"
                "Use this for a new desktop project or apply it onto an existing Python app root."
            ),
            text_color=self.PALETTE["muted"],
            justify="left",
            anchor="w",
            font=ctk.CTkFont(size=14),
        )
        guide_body.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 16))

        log_label = ctk.CTkLabel(
            right,
            text="Generation Log",
            text_color=self.PALETTE["text"],
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        log_label.grid(row=1, column=0, sticky="nw", padx=11, pady=(3, 4))

        self.log = ctk.CTkTextbox(
            right,
            corner_radius=20,
            fg_color=self.PALETTE["log_bg"],
            text_color=self.PALETTE["text"],
            border_width=1,
            border_color=self.PALETTE["border"],
            font=ctk.CTkFont(family="Courier", size=13),
        )
        self.log.grid(row=2, column=0, sticky="nsew", padx=11, pady=(0, 11))
        self._set_log(
            "Ready.\n\n"
            "1. Choose the target project folder.\n"
            "2. Choose the master icon PNG.\n"
            "3. Review names, IDs, and platforms.\n"
            "4. Click Generate Scaffold."
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
        self._labeled_entry(card, 1, 1, "Manufacturer", self.manufacturer_var)

        autofill = ctk.CTkButton(
            card,
            text="Autofill IDs",
            fg_color=self.PALETTE["card"],
            hover_color=self.PALETTE["border"],
            text_color=self.PALETTE["text"],
            border_width=1,
            border_color=self.PALETTE["border"],
            command=self._sync_derived_fields,
        )
        autofill.grid(row=5, column=0, columnspan=2, sticky="ew", padx=14, pady=(4, 14))

    def _build_identity_section(self, parent: ctk.CTkScrollableFrame) -> None:
        card = self._make_card(parent, "Package Identity", 2)
        self._labeled_entry(card, 0, 0, "Package Name", self.package_name_var)
        self._labeled_entry(card, 0, 1, "Bundle ID", self.bundle_id_var)

    def _build_platform_section(self, parent: ctk.CTkScrollableFrame) -> None:
        card = ctk.CTkFrame(
            parent,
            fg_color=self.PALETTE["card"],
            corner_radius=20,
            border_width=1,
            border_color=self.PALETTE["border"],
        )
        card.grid(row=3, column=0, sticky="ew", padx=6, pady=(0, 16))
        card.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=14)
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
            corner_radius=20,
            border_width=1,
            border_color=self.PALETTE["border"],
        )
        card.grid(row=4, column=0, sticky="ew", padx=6, pady=(0, 16))
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
        self.generate_button.grid(row=0, column=0, sticky="ew", padx=14, pady=14)

    def _make_card(self, parent: ctk.CTkScrollableFrame, title: str, row: int) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            parent,
            fg_color=self.PALETTE["card"],
            corner_radius=20,
            border_width=1,
            border_color=self.PALETTE["border"],
        )
        card.grid(row=row, column=0, sticky="ew", padx=3, pady=(0, 8))
        card.grid_columnconfigure(0, weight=1, uniform=f"card_{row}")
        card.grid_columnconfigure(1, weight=1, uniform=f"card_{row}")

        title_label = ctk.CTkLabel(
            card,
            text=title,
            text_color=self.PALETTE["text"],
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(14, 12))
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
        label_widget.grid(row=base_row, column=column, sticky="ew", padx=14, pady=(0, 6))

        entry = ctk.CTkEntry(
            parent,
            textvariable=variable,
            fg_color=self.PALETTE["panel"],
            text_color=self.PALETTE["text"],
            border_color=self.PALETTE["border"],
            height=38,
        )
        entry.grid(row=base_row + 1, column=column, sticky="ew", padx=14, pady=(0, 14))

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
            padx=14,
            pady=(0, 12),
        )
        field.grid_columnconfigure(0, minsize=150)
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

    def _choose_target_dir(self) -> None:
        selected = filedialog.askdirectory(title="Select target project folder")
        if selected:
            self.target_dir_var.set(selected)

    def _choose_icon(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select master icon PNG",
            filetypes=[("PNG Images", "*.png")],
        )
        if selected:
            self.icon_path_var.set(selected)

    def _sync_derived_fields(self) -> None:
        app_name = self.app_name_var.get().strip() or "My Desktop App"
        manufacturer = self.manufacturer_var.get().strip() or "Example Studio"
        package_name = slugify_package_name(app_name)
        bundle_id = make_bundle_id(package_name, manufacturer)

        self.package_name_var.set(package_name)
        self.bundle_id_var.set(bundle_id)
        if manufacturer == "Example Studio" and self.manufacturer_var.get().strip() == "":
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
        app_name = self.app_name_var.get().strip()
        package_name = self.package_name_var.get().strip()
        executable_name = slugify_executable_name(app_name)
        return ScaffoldConfig(
            target_dir=Path(self.target_dir_var.get().strip()),
            icon_path=Path(self.icon_path_var.get().strip()),
            app_name=app_name,
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
        try:
            config = self._build_config()
            self.generate_button.configure(state="disabled", text="Generating...")
            created = generate_scaffold(config)
        except Exception as exc:
            self._append_log(f"\nERROR\n{exc}\n")
            messagebox.showerror(APP_NAME, str(exc))
        else:
            summary = summarize_paths(created, config.target_dir)
            self._set_log(
                "Scaffold generated successfully.\n\n"
                f"Target: {config.target_dir}\n\n"
                "Created or updated:\n"
                f"{summary}"
            )
            messagebox.showinfo(APP_NAME, "Scaffold generated successfully.")
        finally:
            self.generate_button.configure(state="normal", text="Generate Scaffold")

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
