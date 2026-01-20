"""
GitHub Trending to Notion - Desktop Client (Notion Style UI)
桌面客户端 - Notion 风格界面
"""

import os
import sys
import threading
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

try:
    import customtkinter as ctk
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "customtkinter"])
    import customtkinter as ctk

# 设置主题
ctk.set_appearance_mode("Light")

# Notion 风格颜色
C_SIDEBAR = "#F7F7F5"
C_BG = "#FFFFFF"
C_TEXT = "#37352F"
C_TEXT_SEC = "#787774"
C_TEXT_LIGHT = "#9B9A97"
C_BORDER = "#E9E9E7"
C_HOVER = "#EFEFEF"
C_ACCENT = "#2383E2"
C_SUCCESS = "#0F7B6C"
C_ERROR = "#E03E3E"
C_WARNING = "#D9730D"


# SVG 图标（使用 Unicode 字符模拟，因为 CTk 不支持原生 SVG）
ICONS = {
    "logo": "N",  # Notion 风格 N
    "dashboard": chr(0xE871),  # house
    "config": chr(0xE8B8),  # settings
    "schedule": chr(0xE8B5),  # clock
    "history": chr(0xE8D0),  # history
    "settings": chr(0xE8B8),  # settings
    "sync": chr(0xE8D3),  # sync
    "check": chr(0xE876),  # check
    "copy": chr(0xE14D),  # content_copy
    "eye": chr(0xE8F4),  # visibility
    "eye_off": chr(0xE8F5),  # visibility_off
    "link": chr(0xE89E),  # link
    "refresh": chr(0xE8D3),  # refresh
    "status_ok": chr(0xE876),  # check_circle
    "status_error": chr(0xE88E),  # error
    "status_loading": chr(0xE8D7),  # loading
    "close": chr(0xE5C9),  # close
    "add": chr(0xE145),  # add
    "remove": chr(0xE15B),  # remove
}

# 确保 seguisym.ttf 字体支持
def get_icon(name, fallback=""):
    return ICONS.get(name, fallback)


class IconButton(ctk.CTkButton):
    """图标按钮"""

    def __init__(self, parent, icon, command=None, tooltip=None, width=28, height=28, **kwargs):
        default_kwargs = {
            "width": width,
            "height": height,
            "corner_radius": 4,
            "fg_color": "transparent",
            "hover_color": C_HOVER,
            "text_color": C_TEXT_SEC,
            "font": ("Segoe UI Symbol", 14),
        }
        default_kwargs.update(kwargs)
        super().__init__(parent, text=icon, command=command, **default_kwargs)

        if tooltip:
            self.bind("<Enter>", lambda e: self._show_tooltip(tooltip))
            self.bind("<Leave>", lambda e: self._hide_tooltip())

    def _show_tooltip(self, text):
        self.tooltip = tk.Toplevel(self)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{self.winfo_rootx() + 30}+{self.winfo_rooty()}")
        label = tk.Label(self.tooltip, text=text, bg="#333", fg="white", font=("", 10), padx=5, pady=2)
        label.pack()

    def _hide_tooltip(self):
        if hasattr(self, 'tooltip'):
            self.tooltip.destroy()


class LinkButton(ctk.CTkButton):
    """链接按钮"""

    def __init__(self, parent, text, url, **kwargs):
        default_kwargs = {
            "text": text,
            "font": ("", 12),
            "fg_color": "transparent",
            "hover_color": C_HOVER,
            "text_color": C_ACCENT,
            "anchor": "w",
            "height": 24,
            "corner_radius": 4,
        }
        default_kwargs.update(kwargs)
        super().__init__(parent, **default_kwargs)
        self.url = url
        self.configure(command=self._open_link)

    def _open_link(self):
        webbrowser.open(self.url)


class ConfigEntry(ctk.CTkFrame):
    """配置输入框（带显示/隐藏、复制、验证）"""

    def __init__(self, parent, label, attr_name, config, show="●", validate_func=None, help_text="", link_text="", link_url=""):
        super().__init__(parent, fg_color="transparent")

        self.attr_name = attr_name
        self.config = config
        self.validate_func = validate_func
        self.is_password = show == "●"
        self.value = config.get(self._get_config_key(), "")

        # 顶部行（标签 + 验证状态）
        top_row = ctk.CTkFrame(self, fg_color="transparent")
        top_row.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(top_row, text=label, font=("", 13), text_color=C_TEXT, anchor="w").pack(side="left")

        self.status_label = ctk.CTkLabel(top_row, text="", font=("", 11))
        self.status_label.pack(side="right")

        # 中间行（输入框 + 按钮）
        input_row = ctk.CTkFrame(self, fg_color="transparent")
        input_row.pack(fill="x", pady=(0, 4))

        self.entry = ctk.CTkEntry(
            input_row,
            show=show if self.is_password else "",
            height=36,
            corner_radius=4,
            border_width=1,
            border_color=C_BORDER,
            font=("", 13),
        )
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.insert(0, self.value)

        # 按钮容器
        btn_frame = ctk.CTkFrame(input_row, fg_color="transparent")
        btn_frame.pack(side="left", padx=(8, 0))

        # 显示/隐藏按钮
        if self.is_password:
            self.eye_btn = IconButton(btn_frame, ICONS["eye_off"], command=self.toggle_visibility)
            self.eye_btn.pack(side="left", padx=(0, 4))

        # 复制按钮
        IconButton(btn_frame, ICONS["copy"], command=self.copy_value, tooltip="复制").pack(side="left", padx=(0, 4))

        # 验证按钮
        if validate_func:
            self.validate_btn = ctk.CTkButton(
                btn_frame,
                text="验证",
                command=self.validate,
                width=60,
                height=36,
                corner_radius=4,
                fg_color="transparent",
                text_color=C_ACCENT,
                hover_color=C_HOVER,
                font=("", 12)
            )
            self.validate_btn.pack(side="left")

        # 底部行（帮助文本 + 链接）
        bottom_row = ctk.CTkFrame(self, fg_color="transparent")
        bottom_row.pack(fill="x")

        if help_text:
            ctk.CTkLabel(bottom_row, text=help_text, font=("", 11), text_color=C_TEXT_LIGHT, anchor="w").pack(side="left")

        if link_text and link_url:
            LinkButton(bottom_row, link_text, link_url).pack(side="left", padx=(8, 0))

    def _get_config_key(self):
        mapping = {
            "notion_token": "NOTION_TOKEN",
            "notion_db": "NOTION_DATABASE_ID",
            "github_token": "GITHUB_TOKEN",
            "volcano_key": "VOLCANO_API_KEY",
            "volcano_model": "VOLCANO_MODEL",
            "proxy": "PROXY",
        }
        return mapping.get(self.attr_name, "")

    def get_value(self):
        return self.entry.get()

    def toggle_visibility(self):
        if self.entry.cget("show") == "●":
            self.entry.configure(show="")
            self.eye_btn.configure(text=ICONS["eye"])
        else:
            self.entry.configure(show="●")
            self.eye_btn.configure(text=ICONS["eye_off"])

    def copy_value(self):
        value = self.entry.get()
        if value:
            self.clipboard_clear()
            self.clipboard_append(value)
            self.update_idletasks()
            self.show_status("已复制", C_SUCCESS)

    def validate(self):
        if self.validate_func:
            self.show_status("验证中...", C_ACCENT)
            self.validate_btn.configure(state="disabled", text="验证中")
            threading.Thread(target=self._validate_thread, daemon=True).start()

    def _validate_thread(self):
        result = self.validate_func(self.get_value())
        self.after(0, lambda: self._validate_done(result))

    def _validate_done(self, result):
        self.validate_btn.configure(state="normal", text="验证")
        if result.get("success"):
            self.show_status(ICONS["status_ok"] + " 连接成功", C_SUCCESS)
        else:
            self.show_status(ICONS["status_error"] + " " + result.get("error", "验证失败"), C_ERROR)

    def show_status(self, text, color):
        self.status_label.configure(text=text, text_color=color)


class TimePicker(ctk.CTkFrame):
    """时间选择器 - 原生实现，Notion 风格"""

    def __init__(self, parent, command=None, initial_hour=9, initial_minute=0):
        super().__init__(parent, corner_radius=6, fg_color="white", border_width=1, border_color=C_BORDER)
        self.command = command
        self.selected_hour = initial_hour
        self.selected_minute = initial_minute
        self.hour_buttons = {}
        self.min_grid = None

        self.create_ui()

    def create_ui(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=24, pady=20)

        # 显示当前选择的时间
        self.display_frame = ctk.CTkFrame(container, corner_radius=4, fg_color=C_SIDEBAR)
        self.display_frame.pack(fill="x", pady=(0, 20))

        self.display_label = ctk.CTkLabel(
            self.display_frame,
            text=f"{self.selected_hour:02d}:{self.selected_minute:02d}",
            font=("", 32, "bold"),
            text_color=C_TEXT
        )
        self.display_label.pack(pady=16)

        # 时间选择网格
        grid = ctk.CTkFrame(container, fg_color="transparent")
        grid.pack(fill="both", expand=True)

        # 小时选择（两行显示）
        hour_grid = ctk.CTkFrame(grid, fg_color="transparent")
        hour_grid.pack(side="left", fill="both", expand=True, padx=(0, 20))

        ctk.CTkLabel(hour_grid, text="时", font=("", 11), text_color=C_TEXT_LIGHT).pack(pady=(0, 12))

        hour_btns_1 = ctk.CTkFrame(hour_grid, fg_color="transparent")
        hour_btns_1.pack(fill="x", pady=(0, 4))
        for h in range(12):
            self._create_hour_btn(hour_btns_1, h)

        hour_btns_2 = ctk.CTkFrame(hour_grid, fg_color="transparent")
        hour_btns_2.pack(fill="x", pady=(0, 4))
        for h in range(12, 24):
            self._create_hour_btn(hour_btns_2, h)

        # 分钟选择
        min_grid = ctk.CTkFrame(grid, fg_color="transparent")
        min_grid.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(min_grid, text="分", font=("", 11), text_color=C_TEXT_LIGHT).pack(pady=(0, 12))

        min_options = [(0, "00"), (15, "15"), (30, "30"), (45, "45")]
        min_row = ctk.CTkFrame(min_grid, fg_color="transparent")
        min_row.pack(fill="both", expand=True)

        for val, label in min_options:
            btn = ctk.CTkButton(
                min_row,
                text=label,
                width=70,
                height=38,
                corner_radius=4,
                fg_color="transparent" if val != self.selected_minute else C_ACCENT,
                text_color=C_TEXT if val != self.selected_minute else "white",
                hover_color=C_HOVER,
                font=("", 13),
                command=lambda v=val: self._select_minute(v)
            )
            btn.pack(side="left", padx=2, expand=True)

        self.min_grid = min_grid

    def _create_hour_btn(self, parent, hour):
        btn = ctk.CTkButton(
            parent,
            text=f"{hour:02d}",
            width=50,
            height=32,
            corner_radius=4,
            fg_color="transparent" if hour != self.selected_hour else C_ACCENT,
            text_color=C_TEXT if hour != self.selected_hour else "white",
            hover_color=C_HOVER,
            font=("", 11),
            command=lambda h=hour: self._select_hour(h)
        )
        btn.pack(side="left", padx=1)
        self.hour_buttons[hour] = btn

    def _select_hour(self, hour):
        self.selected_hour = hour
        self._refresh_display()

    def _select_minute(self, minute):
        self.selected_minute = minute
        self._refresh_display()

    def _refresh_display(self):
        # 更新显示
        self.display_label.configure(text=f"{self.selected_hour:02d}:{self.selected_minute:02d}")

        # 刷新小时按钮
        for h, btn in self.hour_buttons.items():
            if h == self.selected_hour:
                btn.configure(fg_color=C_ACCENT, text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color=C_TEXT)

        # 刷新分钟按钮
        if self.min_grid:
            for widget in self.min_grid.winfo_children():
                if isinstance(widget, ctk.CTkFrame):
                    for child in widget.winfo_children():
                        if isinstance(child, ctk.CTkButton):
                            try:
                                val = int(child.cget("text"))
                                if val == self.selected_minute:
                                    child.configure(fg_color=C_ACCENT, text_color="white")
                                else:
                                    child.configure(fg_color="transparent", text_color=C_TEXT)
                            except:
                                pass

        if self.command:
            self.command(self.selected_hour, self.selected_minute)

    def get_time(self):
        return f"{self.selected_hour:02d}:{self.selected_minute:02d}"

    def set_time(self, time_str):
        try:
            parts = time_str.split(":")
            self.selected_hour = int(parts[0])
            self.selected_minute = int(parts[1])
            self._refresh_display()
        except:
            pass

    def set_hour(self, hour):
        self.selected_hour = hour
        self._refresh_display()

    def set_minute(self, minute):
        self.selected_minute = minute
        self._refresh_display()


class DesktopClient(ctk.CTk):
    """桌面客户端主窗口"""

    def __init__(self):
        super().__init__()

        self.title("GitHub Trending to Notion")
        self.geometry("1000x680")
        self.configure(fg_color=C_BG)

        self.project_dir = Path(__file__).parent
        self.env_file = self.project_dir / ".env"
        self.script_file = self.project_dir / "github_trending_notion.py"

        self.config = self.load_config()
        self.config_entries = {}

        self.create_ui()
        self.check_scheduled_task()

    def load_config(self):
        config = {}
        if self.env_file.exists():
            with open(self.env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config[key] = value
        return config

    def save_config(self):
        lines = []
        if self.env_file.exists():
            with open(self.env_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

        config_keys = {}
        for attr_name, entry_widget in self.config_entries.items():
            config_key = self._get_config_key(attr_name)
            value = entry_widget.get_value()
            if value:
                config_keys[config_key] = value

        new_lines = []
        written_keys = set()

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#') or not stripped or '=' not in stripped:
                new_lines.append(line)
            else:
                key = stripped.split('=', 1)[0]
                if key in config_keys:
                    new_lines.append(f"{key}={config_keys[key]}\n")
                    written_keys.add(key)
                else:
                    new_lines.append(line)

        for key, value in config_keys.items():
            if key not in written_keys:
                new_lines.append(f"{key}={value}\n")

        with open(self.env_file, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

        self.config = config_keys
        return True

    def _get_config_key(self, attr_name):
        mapping = {
            "notion_token": "NOTION_TOKEN",
            "notion_db": "NOTION_DATABASE_ID",
            "github_token": "GITHUB_TOKEN",
            "volcano_key": "VOLCANO_API_KEY",
            "volcano_model": "VOLCANO_MODEL",
            "proxy": "PROXY",
        }
        return mapping.get(attr_name, "")

    def create_ui(self):
        # 主容器
        self.main_container = ctk.CTkFrame(self, fg_color=C_BG)
        self.main_container.pack(fill="both", expand=True)

        # 侧边栏
        self.create_sidebar()

        # 内容区
        self.create_content_frames()

        self.show_dashboard()

    def create_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self.main_container,
            width=240,
            corner_radius=0,
            fg_color=C_SIDEBAR,
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Logo
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", padx=16, pady=(16, 8))

        logo = ctk.CTkFrame(logo_frame, width=32, height=32, corner_radius=6, fg_color=C_ACCENT)
        logo.pack(side="left", padx=(0, 12))
        ctk.CTkLabel(logo, text=ICONS["logo"], font=("", 20, "bold"), text_color="white").pack(expand=True)

        ctk.CTkLabel(
            logo_frame,
            text="GitHub to Notion",
            font=("", 13, "bold"),
            anchor="w",
            text_color=C_TEXT
        ).pack(side="left", fill="x")

        # 工作区标题
        ctk.CTkLabel(
            self.sidebar,
            text="工作区",
            font=("", 11),
            anchor="w",
            text_color=C_TEXT_LIGHT
        ).pack(fill="x", padx=(16, 16), pady=(20, 8))

        # 导航按钮
        self.nav_dashboard = self.create_nav_btn(ICONS["dashboard"], "仪表板", self.show_dashboard)
        self.nav_config = self.create_nav_btn(ICONS["config"], "配置", self.show_config)
        self.nav_schedule = self.create_nav_btn(ICONS["schedule"], "定时任务", self.show_schedule)
        self.nav_history = self.create_nav_btn(ICONS["history"], "历史记录", self.show_history)

        # 分隔线
        ctk.CTkFrame(self.sidebar, height=1, fg_color=C_BORDER).pack(
            fill="x", padx=(16, 16), pady=(16, 16))

        self.nav_settings = self.create_nav_btn(ICONS["settings"], "设置", self.show_settings)

        # 底部状态
        bottom = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=16, pady=16)
        ctk.CTkLabel(bottom, text=ICONS["status_ok"], font=("Segoe UI Symbol", 12), text_color=C_SUCCESS).pack(side="left")
        ctk.CTkLabel(bottom, text="已连接", font=("", 11), text_color=C_TEXT_SEC).pack(side="left", padx=(8, 0))

    def create_nav_btn(self, icon, text, command):
        btn = ctk.CTkButton(
            self.sidebar,
            text=f"{icon}  {text}",
            command=command,
            corner_radius=4,
            fg_color="transparent",
            text_color=C_TEXT_SEC,
            hover_color=C_HOVER,
            anchor="w",
            height=36,
            font=("Segoe UI Symbol", 13)
        )
        btn.pack(fill="x", padx=(8, 8), pady=2)
        return btn

    def create_content_frames(self):
        # 仪表板
        self.frame_dashboard = ctk.CTkScrollableFrame(
            self.main_container, fg_color=C_BG, scrollbar_button_color=C_BORDER)
        self.create_dashboard_content()

        # 配置
        self.frame_config = ctk.CTkScrollableFrame(
            self.main_container, fg_color=C_BG, scrollbar_button_color=C_BORDER)
        self.create_config_content()

        # 定时任务
        self.frame_schedule = ctk.CTkScrollableFrame(
            self.main_container, fg_color=C_BG, scrollbar_button_color=C_BORDER)
        self.create_schedule_content()

        # 历史记录
        self.frame_history = ctk.CTkFrame(self.main_container, fg_color=C_BG)
        self.create_history_content()

        # 设置
        self.frame_settings = ctk.CTkFrame(self.main_container, fg_color=C_BG)
        self.create_settings_content()

    def create_dashboard_content(self):
        parent = self.frame_dashboard

        # 标题
        ctk.CTkLabel(parent, text="仪表板", font=("", 28, "bold"),
                     anchor="w", text_color=C_TEXT).pack(fill="x", padx=40, pady=(32, 4))
        ctk.CTkLabel(parent, text="监控和管理 GitHub Trending 同步任务", font=("", 14),
                     anchor="w", text_color=C_TEXT_SEC).pack(fill="x", padx=40, pady=(0, 24))

        # 统计卡片
        cards = ctk.CTkFrame(parent, fg_color="transparent")
        cards.pack(fill="x", padx=40, pady=(0, 24))

        self.create_stat_card(cards, ICONS["status_ok"], "状态", "已就绪", C_SUCCESS).pack(side="left", fill="both", expand=True, padx=(0, 12))
        self.create_stat_card(cards, ICONS["sync"], "今日同步", "0 个项目", C_ACCENT).pack(side="left", fill="both", expand=True, padx=(0, 12))
        self.create_stat_card(cards, ICONS["schedule"], "下次运行", "09:00", C_TEXT_SEC).pack(side="left", fill="both", expand=True)

        # 快速操作
        quick = self.create_card(parent, "快速操作")
        btns = ctk.CTkFrame(quick, fg_color="transparent")
        btns.pack(fill="x", padx=20, pady=(0, 16))

        ctk.CTkButton(btns, text=f"{ICONS['sync']}  立即同步", command=self.run_script, width=140, height=40,
                      corner_radius=4, fg_color=C_ACCENT, hover_color="#1A6BC0", text_color="white",
                      font=("Segoe UI Symbol", 13)).pack(side="left", padx=(0, 12))
        ctk.CTkButton(btns, text=f"{ICONS['config']}  配置", command=self.show_config, width=140, height=40,
                      corner_radius=4, fg_color="transparent", text_color=C_TEXT, hover_color=C_HOVER,
                      font=("Segoe UI Symbol", 13)).pack(side="left")

        # 日志
        log = self.create_card(parent, "运行日志", show_clear=True)
        self.log_text = ctk.CTkTextbox(log, font=("Consolas", 11), fg_color=C_BG,
                                        border_width=0, height=200)
        self.log_text.pack(fill="both", expand=True, padx=0, pady=(0, 16))
        self.log_text.insert("1.0", "桌面客户端已启动\n")
        self.log_text.configure(state="disabled")

    def create_stat_card(self, parent, icon, label, value, color):
        card = ctk.CTkFrame(parent, corner_radius=6, fg_color="white", border_width=1, border_color=C_BORDER)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=16, pady=16)

        top = ctk.CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text=icon, font=("Segoe UI Symbol", 20), text_color=color).pack(side="left")
        ctk.CTkLabel(top, text=label, font=("", 13), anchor="w", text_color=C_TEXT_SEC).pack(side="left", padx=(8, 0))

        ctk.CTkLabel(inner, text=value, font=("", 24, "bold"), anchor="w", text_color=color).pack(fill="x", pady=(12, 0))
        return card

    def create_card(self, parent, title, show_clear=False):
        card = ctk.CTkFrame(parent, corner_radius=6, fg_color="white", border_width=1, border_color=C_BORDER)
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(16, 12))
        ctk.CTkLabel(header, text=title, font=("", 16, "bold"), anchor="w", text_color=C_TEXT).pack(side="left")
        if show_clear:
            ctk.CTkButton(header, text="清空", command=self.clear_log, width=60, height=28,
                         corner_radius=4, fg_color="transparent", text_color=C_TEXT_SEC,
                         hover_color=C_HOVER, font=("", 12)).pack(side="right")
        card.pack(fill="x", pady=(0, 24))
        return card

    def create_config_content(self):
        parent = self.frame_config

        ctk.CTkLabel(parent, text="配置", font=("", 28, "bold"), anchor="w", text_color=C_TEXT).pack(fill="x", padx=40, pady=(32, 4))
        ctk.CTkLabel(parent, text="配置 Notion、GitHub 和 AI 服务", font=("", 14), anchor="w",
                     text_color=C_TEXT_SEC).pack(fill="x", padx=40, pady=(0, 24))

        # Notion
        notion = self.create_card(parent, "Notion")
        notion_content = ctk.CTkFrame(notion, fg_color="transparent")
        notion_content.pack(fill="x", padx=20, pady=(0, 16))

        self.config_entries["notion_token"] = ConfigEntry(
            notion_content, "Integration Token", "notion_token", self.config,
            help_text="用于访问 Notion API",
            link_text="获取 Integration Token",
            link_url="https://www.notion.so/my-integrations",
            validate_func=self.validate_notion_token
        )
        self.config_entries["notion_token"].pack(fill="x", pady=(0, 16))

        self.config_entries["notion_db"] = ConfigEntry(
            notion_content, "Database ID", "notion_db", self.config,
            help_text="Notion 数据库的唯一标识符（从链接中复制）",
            link_text="如何获取 Database ID",
            link_url="https://www.notion.so/help/integrations-with-the-notion-api",
            validate_func=self.validate_notion_db
        )
        self.config_entries["notion_db"].pack(fill="x")

        # GitHub
        github = self.create_card(parent, "GitHub")
        github_content = ctk.CTkFrame(github, fg_color="transparent")
        github_content.pack(fill="x", padx=20, pady=(0, 16))

        self.config_entries["github_token"] = ConfigEntry(
            github_content, "Personal Access Token", "github_token", self.config,
            help_text="用于提高 API 请求限制（可选）",
            link_text="创建 Personal Access Token",
            link_url="https://github.com/settings/tokens",
            validate_func=self.validate_github_token
        )
        self.config_entries["github_token"].pack(fill="x")

        # AI
        ai = self.create_card(parent, "AI 分析（可选）")
        ai_content = ctk.CTkFrame(ai, fg_color="transparent")
        ai_content.pack(fill="x", padx=20, pady=(0, 16))

        self.config_entries["volcano_key"] = ConfigEntry(
            ai_content, "API Key", "volcano_key", self.config,
            help_text="火山引擎豆包 API 密钥",
            link_text="获取 API Key",
            link_url="https://console.volcengine.com/ark",
            validate_func=self.validate_volcano_key
        )
        self.config_entries["volcano_key"].pack(fill="x", pady=(0, 16))

        self.config_entries["volcano_model"] = ConfigEntry(
            ai_content, "Model Endpoint", "volcano_model", self.config,
            help_text="推理接入点 ID，格式：ep-xxxxx"
        )
        self.config_entries["volcano_model"].pack(fill="x")

        # 代理
        proxy = self.create_card(parent, "代理（可选）")
        proxy_content = ctk.CTkFrame(proxy, fg_color="transparent")
        proxy_content.pack(fill="x", padx=20, pady=(0, 16))

        self.config_entries["proxy"] = ConfigEntry(
            proxy_content, "代理地址", "proxy", self.config,
            help_text="例如：http://127.0.0.1:7890",
            validate_func=self.validate_proxy
        )
        self.config_entries["proxy"].pack(fill="x")

        # 保存按钮
        ctk.CTkButton(parent, text=f"{ICONS['check']}  保存配置", command=self.save_and_notify, width=140, height=40,
                      corner_radius=4, fg_color=C_ACCENT, hover_color="#1A6BC0", text_color="white",
                      font=("Segoe UI Symbol", 13)).pack(anchor="w", padx=(40, 0), pady=(0, 32))

    def validate_notion_token(self, value):
        try:
            import requests
            headers = {"Authorization": f"Bearer {value}", "Notion-Version": "2022-06-28"}
            response = requests.get("https://api.notion.com/v1/users/me", headers=headers, timeout=10)
            if response.status_code == 200:
                return {"success": True}
            return {"success": False, "error": f"认证失败 ({response.status_code})"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def validate_notion_db(self, value):
        if not self.config.get("NOTION_TOKEN"):
            return {"success": False, "error": "请先验证 Notion Token"}
        try:
            import requests
            headers = {"Authorization": f"Bearer {self.config['NOTION_TOKEN']}", "Notion-Version": "2022-06-28"}
            response = requests.get(f"https://api.notion.com/v1/databases/{value}", headers=headers, timeout=10)
            if response.status_code == 200:
                return {"success": True}
            return {"success": False, "error": f"数据库访问失败 ({response.status_code})"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def validate_github_token(self, value):
        try:
            import requests
            headers = {"Authorization": f"token {value}"} if value else {}
            response = requests.get("https://api.github.com/user", headers=headers, timeout=10)
            if response.status_code == 200:
                return {"success": True}
            elif response.status_code == 401:
                return {"success": False, "error": "Token 无效"}
            return {"success": False, "error": f"验证失败 ({response.status_code})"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def validate_volcano_key(self, value):
        # 简单验证格式
        if value.startswith("ak-") or len(value) > 20:
            return {"success": True}
        return {"success": False, "error": "API Key 格式不正确"}

    def validate_proxy(self, value):
        if not value:
            return {"success": True}
        try:
            import requests
            response = requests.get("https://www.google.com", proxies={"https": value}, timeout=5)
            return {"success": True}
        except:
            return {"success": False, "error": "代理连接失败"}

    def create_schedule_content(self):
        parent = self.frame_schedule

        ctk.CTkLabel(parent, text="定时任务", font=("", 28, "bold"), anchor="w", text_color=C_TEXT).pack(fill="x", padx=40, pady=(32, 4))
        ctk.CTkLabel(parent, text="设置自动同步时间", font=("", 14), anchor="w", text_color=C_TEXT_SEC).pack(fill="x", padx=40, pady=(0, 24))

        # 时间选择器
        time_card = ctk.CTkFrame(parent, corner_radius=6, fg_color="white", border_width=1, border_color=C_BORDER)
        time_card.pack(fill="x", padx=40, pady=(0, 24))

        time_header = ctk.CTkFrame(time_card, fg_color="transparent")
        time_header.pack(fill="x", padx=20, pady=(16, 12))
        ctk.CTkLabel(time_header, text="选择执行时间", font=("", 16, "bold"), anchor="w", text_color=C_TEXT).pack(side="left")

        time_content = ctk.CTkFrame(time_card, fg_color="transparent")
        time_content.pack(fill="x", padx=20, pady=(0, 20))

        self.time_picker = TimePicker(time_content, initial_hour=9, initial_minute=0)
        self.time_picker.pack(fill="both", expand=True)

        # 状态和控制
        control_card = ctk.CTkFrame(parent, corner_radius=6, fg_color="white", border_width=1, border_color=C_BORDER)
        control_card.pack(fill="x", padx=40, pady=(0, 24))

        control_content = ctk.CTkFrame(control_card, fg_color="transparent")
        control_content.pack(fill="x", padx=20, pady=16)

        row1 = ctk.CTkFrame(control_content, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(row1, text="当前状态", font=("", 13), text_color=C_TEXT, width=100, anchor="w").pack(side="left")
        self.schedule_status_label = ctk.CTkLabel(row1, text="检查中...", font=("", 13), text_color=C_TEXT_SEC)
        self.schedule_status_label.pack(side="left", padx=(12, 0))

        row2 = ctk.CTkFrame(control_content, fg_color="transparent")
        row2.pack(fill="x")

        ctk.CTkButton(row2, text=f"{ICONS['check']}  启用定时任务", command=self.create_scheduled_task, width=160, height=40,
                      corner_radius=4, fg_color=C_ACCENT, hover_color="#1A6BC0", text_color="white",
                      font=("Segoe UI Symbol", 13)).pack(side="left", padx=(0, 12))
        ctk.CTkButton(row2, text=f"{ICONS['close']}  禁用", command=self.delete_scheduled_task, width=120, height=40,
                      corner_radius=4, fg_color="transparent", text_color=C_ERROR, hover_color=C_HOVER,
                      font=("Segoe UI Symbol", 13)).pack(side="left")

    def create_history_content(self):
        parent = self.frame_history
        ctk.CTkLabel(parent, text="历史记录", font=("", 28, "bold"), anchor="w", text_color=C_TEXT).pack(fill="x", padx=40, pady=(32, 24))
        ctk.CTkLabel(parent, text="暂无历史记录", font=("", 14), text_color=C_TEXT_LIGHT).pack(expand=True)

    def create_settings_content(self):
        parent = self.frame_settings
        ctk.CTkLabel(parent, text="设置", font=("", 28, "bold"), anchor="w", text_color=C_TEXT).pack(fill="x", padx=40, pady=(32, 24))

        card = ctk.CTkFrame(parent, corner_radius=6, fg_color="white", border_width=1, border_color=C_BORDER)
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=20, pady=16)

        row = ctk.CTkFrame(content, fg_color="transparent")
        row.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(row, text="主题", width=150, anchor="w", font=("", 13), text_color=C_TEXT).pack(side="left")
        self.theme_selector = ctk.CTkOptionMenu(row, values=["浅色", "深色", "跟随系统"], width=160, height=36,
                                                corner_radius=4, button_color="white", button_hover_color=C_HOVER,
                                                fg_color="white", dropdown_fg_color="white", text_color=C_TEXT, font=("", 13))
        self.theme_selector.set("浅色")
        self.theme_selector.pack(side="left", padx=(12, 0))
        self.theme_selector.configure(command=self.change_theme)

        ctk.CTkFrame(content, height=1, fg_color=C_BORDER).pack(fill="x", pady=(16, 16))

        ctk.CTkLabel(content, text="GitHub Trending to Notion v1.0.0", font=("", 13), text_color=C_TEXT_SEC).pack(anchor="w")
        link = ctk.CTkLabel(content, text="打开项目文件夹", font=("", 13), text_color=C_ACCENT, cursor="hand2")
        link.pack(anchor="w", pady=(8, 0))
        link.bind("<Button-1>", lambda e: self.open_project_folder())

    def show_frame(self, frame_name):
        # 隐藏所有
        self.frame_dashboard.pack_forget()
        self.frame_config.pack_forget()
        self.frame_schedule.pack_forget()
        self.frame_history.pack_forget()
        self.frame_settings.pack_forget()

        # 显示选中的
        getattr(self, f"frame_{frame_name}").pack(side="right", fill="both", expand=True)

        # 更新导航状态
        self.current_page = frame_name
        nav_items = [
            ("dashboard", self.nav_dashboard),
            ("config", self.nav_config),
            ("schedule", self.nav_schedule),
            ("history", self.nav_history),
            ("settings", self.nav_settings),
        ]
        for name, btn in nav_items:
            if name == frame_name:
                btn.configure(fg_color=C_HOVER, text_color=C_TEXT)
            else:
                btn.configure(fg_color="transparent", text_color=C_TEXT_SEC)

    def show_dashboard(self):
        self.show_frame("dashboard")

    def show_config(self):
        self.show_frame("config")

    def show_schedule(self):
        self.show_frame("schedule")

    def show_history(self):
        self.show_frame("history")

    def show_settings(self):
        self.show_frame("settings")

    def change_theme(self, choice):
        if choice == "浅色":
            ctk.set_appearance_mode("Light")
        elif choice == "深色":
            ctk.set_appearance_mode("Dark")
        else:
            ctk.set_appearance_mode("System")

    def log(self, message):
        if hasattr(self, 'log_text'):
            self.log_text.configure(state="normal")
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_text.insert("end", f"[{timestamp}] {message}\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")

    def clear_log(self):
        if hasattr(self, 'log_text'):
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", "end")
            self.log_text.configure(state="disabled")

    def update_config_status(self):
        has_notion = bool(self.config.get('NOTION_TOKEN') and self.config.get('NOTION_DATABASE_ID'))
        return has_notion

    def save_and_notify(self):
        self.save_config()
        self.log("配置已保存")
        messagebox.showinfo("成功", "配置已保存")

    def run_script(self):
        if not self.update_config_status():
            messagebox.showwarning("配置不完整", "请先在【配置】页面完成 Notion 设置")
            self.show_config()
            return

        self.log("=" * 50)
        self.log("开始运行脚本...")

        thread = threading.Thread(target=self._run_script_thread)
        thread.daemon = True
        thread.start()

    def _run_script_thread(self):
        try:
            result = subprocess.run(
                [sys.executable, str(self.script_file)],
                capture_output=True, text=True, encoding='utf-8', cwd=str(self.project_dir)
            )
            if result.stdout:
                for line in result.stdout.split('\n'):
                    if line.strip():
                        self.log(line)
            if result.stderr:
                self.log("错误: " + result.stderr)
            if result.returncode == 0:
                self.log("脚本运行完成")
        except Exception as e:
            self.log(f"运行出错: {e}")

    def check_scheduled_task(self):
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Get-ScheduledTask -TaskName 'GitHubTrendingToNotion' -ErrorAction SilentlyContinue | Select-Object State, NextRunTime"],
                capture_output=True, text=True
            )
            if hasattr(self, 'schedule_status_label'):
                if result.returncode == 0 and "GitHubTrendingToNotion" in result.stdout:
                    self.schedule_status_label.configure(text=f"{ICONS['status_ok']} 已启用", text_color=C_SUCCESS)
                else:
                    self.schedule_status_label.configure(text="未启用", text_color=C_TEXT_LIGHT)
        except:
            pass

    def create_scheduled_task(self):
        if not self.update_config_status():
            messagebox.showwarning("配置不完整", "请先完成必要配置")
            return

        time_str = self.time_picker.get_time()
        ps_script = f"""
$taskName = "GitHubTrendingToNotion"
$scriptPath = "{self.project_dir}"
$pythonScript = Join-Path $scriptPath "github_trending_notion.py"
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {{ Unregister-ScheduledTask -TaskName $taskName -Confirm:$false }}
$action = New-ScheduledTaskAction -Execute "python" -Argument $pythonScript -WorkingDirectory $scriptPath
$trigger = New-ScheduledTaskTrigger -Daily -At {time_str}
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings
"""
        try:
            result = subprocess.run(["powershell", "-Command", ps_script], capture_output=True, text=True)
            if result.returncode == 0:
                self.schedule_status_label.configure(text=f"{ICONS['status_ok']} 已启用 (每天 {time_str})", text_color=C_SUCCESS)
                self.log(f"定时任务已创建: 每天 {time_str}")
                messagebox.showinfo("成功", f"定时任务已创建！\n每天 {time_str} 自动运行")
        except Exception as e:
            messagebox.showerror("失败", f"创建失败: {e}")

    def delete_scheduled_task(self):
        try:
            subprocess.run(["powershell", "-Command", "Unregister-ScheduledTask -TaskName 'GitHubTrendingToNotion' -Confirm:$false"],
                          capture_output=True, text=True)
            self.schedule_status_label.configure(text="未启用", text_color=C_TEXT_LIGHT)
            self.log("定时任务已删除")
            messagebox.showinfo("成功", "定时任务已删除")
        except Exception as e:
            messagebox.showerror("失败", f"删除失败: {e}")

    def open_project_folder(self):
        os.startfile(str(self.project_dir))


def main():
    app = DesktopClient()
    app.mainloop()


if __name__ == "__main__":
    main()
