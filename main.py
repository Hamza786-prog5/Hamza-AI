# -*- coding: utf-8 -*-
"""
Hamza AI - offline chat app with Admin Panel
Built with Kivy (works in Pydroid 3, and can be packaged to APK with Buildozer)
"""

import os
import re
import json
import random
from datetime import datetime

from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.widget import Widget

# ---------------------------------------------------------------------------
# PATHS & STORAGE
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DATA_DIR = os.path.join(BASE_DIR, "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
STATE_FILE = os.path.join(DATA_DIR, "state.json")


def ensure_data():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(USERS_FILE):
        save_json(USERS_FILE, [])
    if not os.path.exists(CONFIG_FILE):
        save_json(CONFIG_FILE, {"admin_password": "admin123", "app_code": "0000"})
    if not os.path.exists(STATE_FILE):
        save_json(STATE_FILE, {})


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def next_user_id(users):
    return (max([u["id"] for u in users], default=0)) + 1


# ---------------------------------------------------------------------------
# OFFLINE "AI" REPLY ENGINE  (rule based - no internet / no API key)
# ---------------------------------------------------------------------------
def get_bot_reply(text):
    t = text.strip().lower()
    if not t:
        return "Ji, kuch likhen taake main jawab de sakoon."

    greetings = ["salam", "assalam", "asalam", "hello", "hi", "hey"]
    if any(g in t for g in greetings):
        return "Wa alaikum assalam! Main Hamza AI hoon. Aap ki kya madad kar sakta hoon?"

    if "naam" in t or "name" in t:
        return "Mera naam Hamza AI hai."

    if "kaise ho" in t or "kaisay ho" in t or "how are you" in t:
        return "Main theek hoon, shukriya! Aap batayen, kis cheez mein madad chahiye?"

    if "time" in t or "waqt" in t:
        return "Abhi ka waqt hai: " + datetime.now().strftime("%I:%M %p")

    if "date" in t or "tareekh" in t:
        return "Aaj ki tareekh hai: " + datetime.now().strftime("%d-%m-%Y")

    if "shukriya" in t or "thanks" in t or "thank you" in t:
        return "Khushi hui madad kar ke! Kuch aur puchna ho to batayen."

    # simple safe calculator for basic math expressions
    if re.fullmatch(r"[0-9\.\+\-\*\/\(\)\s]+", t) and any(c.isdigit() for c in t):
        try:
            result = eval(t, {"__builtins__": {}}, {})
            return f"Jawab hai: {result}"
        except Exception:
            pass

    fallback = [
        "Yeh sawal thora mushkil hai, kya aap ise aasan lafzon mein pooch saktay hain?",
        "Mujhe abhi is ka pakka jawab nahi pata, lekin main koshish kar raha hoon seekhne ki.",
        "Achi baat hai! Thora aur wazeh kar den, main behtar jawab de sakoon ga.",
    ]
    return random.choice(fallback)


# ---------------------------------------------------------------------------
# REUSABLE UI HELPERS
# ---------------------------------------------------------------------------
class RoundedButton(Button):
    def __init__(self, bg_color=(0.15, 0.45, 0.85, 1), **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = bg_color
        self.color = (1, 1, 1, 1)


class ChatBubble(BoxLayout):
    def __init__(self, text, is_user, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, padding=(dp(8), dp(4)), **kwargs)
        lbl = Label(
            text=text,
            size_hint_x=0.78,
            halign="right" if is_user else "left",
            valign="middle",
            color=(1, 1, 1, 1),
        )
        lbl.bind(width=lambda *x: lbl.setter("text_size")(lbl, (lbl.width, None)))
        lbl.bind(texture_size=lambda *x: setattr(lbl, "height", lbl.texture_size[1] + dp(20)))

        with lbl.canvas.before:
            Color(*(0.15, 0.45, 0.85, 1) if is_user else (0.22, 0.22, 0.25, 1))
            lbl.bg_rect = RoundedRectangle(radius=[dp(14)])
        lbl.bind(pos=self._update_rect, size=self._update_rect)
        self._lbl = lbl

        if is_user:
            self.add_widget(Widget(size_hint_x=0.22))
            self.add_widget(lbl)
        else:
            self.add_widget(lbl)
            self.add_widget(Widget(size_hint_x=0.22))

        self.bind(minimum_height=self._sync_height)

    def _update_rect(self, instance, value):
        instance.bg_rect.pos = instance.pos
        instance.bg_rect.size = instance.size

    def _sync_height(self, *a):
        self.height = self._lbl.height


# ---------------------------------------------------------------------------
# CHAT SCREEN
# ---------------------------------------------------------------------------
class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical")

        # ---- Top bar ----
        topbar = BoxLayout(size_hint_y=None, height=dp(56), padding=(dp(10), 0))
        with topbar.canvas.before:
            Color(0.08, 0.09, 0.14, 1)
            self._top_rect = RoundedRectangle()
        topbar.bind(pos=self._update_top, size=self._update_top)

        title = Label(text="Welcome to Hamza AI", bold=True, font_size="18sp", color=(1, 1, 1, 1))
        admin_btn = RoundedButton(
            text="Admin",
            size_hint=(None, None),
            size=(dp(80), dp(36)),
            bg_color=(0.35, 0.35, 0.4, 1),
        )
        admin_btn.bind(on_release=self.open_admin_login)
        topbar.add_widget(title)
        topbar.add_widget(admin_btn)
        root.add_widget(topbar)

        # ---- Chat area ----
        self.scroll = ScrollView(size_hint=(1, 1))
        self.chat_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4), padding=(dp(6), dp(6)))
        self.chat_box.bind(minimum_height=self.chat_box.setter("height"))
        self.scroll.add_widget(self.chat_box)
        root.add_widget(self.scroll)

        # ---- Bottom input bar ----
        bottom = BoxLayout(size_hint_y=None, height=dp(58), padding=(dp(8), dp(6)), spacing=dp(8))
        with bottom.canvas.before:
            Color(0.12, 0.13, 0.18, 1)
            self._bottom_rect = RoundedRectangle()
        bottom.bind(pos=self._update_bottom, size=self._update_bottom)

        self.text_input = TextInput(
            hint_text="Apna sawal likhen...",
            multiline=False,
            size_hint_x=0.8,
            background_color=(1, 1, 1, 1),
            padding=(dp(10), dp(10)),
        )
        self.text_input.bind(on_text_validate=self.send_message)
        send_btn = RoundedButton(text="Send", size_hint_x=0.2)
        send_btn.bind(on_release=self.send_message)
        bottom.add_widget(self.text_input)
        bottom.add_widget(send_btn)
        root.add_widget(bottom)

        self.add_widget(root)
        Clock.schedule_once(lambda dt: self.add_bubble(
            "Assalam-o-Alaikum! Main Hamza AI hoon. Aap ka sawal likhen.", False), 0.2)

    def _update_top(self, instance, value):
        instance._top_rect.pos = instance.pos
        instance._top_rect.size = instance.size

    def _update_bottom(self, instance, value):
        instance._bottom_rect.pos = instance.pos
        instance._bottom_rect.size = instance.size

    def add_bubble(self, text, is_user):
        bubble = ChatBubble(text, is_user)
        self.chat_box.add_widget(bubble)
        Clock.schedule_once(lambda dt: setattr(self.scroll, "scroll_y", 0), 0.05)

    def send_message(self, *args):
        text = self.text_input.text.strip()
        if not text:
            return
        self.add_bubble(text, True)
        self.text_input.text = ""
        reply = get_bot_reply(text)
        Clock.schedule_once(lambda dt: self.add_bubble(reply, False), 0.4)

    def open_admin_login(self, *args):
        self.manager.current = "admin_login"


# ---------------------------------------------------------------------------
# ADMIN LOGIN SCREEN
# ---------------------------------------------------------------------------
class AdminLoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(24), spacing=dp(14))
        root.add_widget(Label(text="Admin Login", font_size="22sp", bold=True, size_hint_y=None, height=dp(50)))

        self.pass_input = TextInput(
            hint_text="Admin Password",
            password=True,
            multiline=False,
            size_hint_y=None,
            height=dp(46),
        )
        root.add_widget(self.pass_input)

        self.msg_label = Label(text="", color=(1, 0.4, 0.4, 1), size_hint_y=None, height=dp(24))
        root.add_widget(self.msg_label)

        login_btn = RoundedButton(text="Login", size_hint_y=None, height=dp(46))
        login_btn.bind(on_release=self.try_login)
        root.add_widget(login_btn)

        back_btn = RoundedButton(text="Back", size_hint_y=None, height=dp(40), bg_color=(0.4, 0.4, 0.4, 1))
        back_btn.bind(on_release=lambda *a: setattr(self.manager, "current", "chat"))
        root.add_widget(back_btn)

        root.add_widget(Widget())
        self.add_widget(root)

    def try_login(self, *args):
        config = load_json(CONFIG_FILE)
        if self.pass_input.text == config.get("admin_password", "admin123"):
            self.msg_label.text = ""
            self.pass_input.text = ""
            self.manager.get_screen("admin_panel").refresh()
            self.manager.current = "admin_panel"
        else:
            self.msg_label.text = "Ghalat password, dobara koshish karen."


# ---------------------------------------------------------------------------
# ADMIN PANEL SCREEN
# ---------------------------------------------------------------------------
class AdminPanelScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.root_layout = BoxLayout(orientation="vertical")
        self.add_widget(self.root_layout)
        self.build_ui()

    def build_ui(self):
        self.root_layout.clear_widgets()

        topbar = BoxLayout(size_hint_y=None, height=dp(50), padding=(dp(10), 0))
        topbar.add_widget(Label(text="Admin Panel", bold=True, font_size="18sp"))
        back_btn = RoundedButton(text="Logout", size_hint=(None, None), size=(dp(90), dp(36)), bg_color=(0.4, 0.4, 0.4, 1))
        back_btn.bind(on_release=lambda *a: setattr(self.manager, "current", "chat"))
        topbar.add_widget(back_btn)
        self.root_layout.add_widget(topbar)

        scroll = ScrollView()
        content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(16), padding=dp(14))
        content.bind(minimum_height=content.setter("height"))

        # --- Change admin password ---
        content.add_widget(Label(text="Change Admin Password", bold=True, size_hint_y=None, height=dp(28)))
        pw_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.new_admin_pw = TextInput(hint_text="New admin password", password=True, multiline=False)
        pw_btn = RoundedButton(text="Save", size_hint_x=0.3)
        pw_btn.bind(on_release=self.change_admin_password)
        pw_row.add_widget(self.new_admin_pw)
        pw_row.add_widget(pw_btn)
        content.add_widget(pw_row)

        # --- Change app code ---
        content.add_widget(Label(text="Change App Code", bold=True, size_hint_y=None, height=dp(28)))
        code_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.new_code = TextInput(hint_text="New app code", multiline=False)
        code_btn = RoundedButton(text="Save", size_hint_x=0.3)
        code_btn.bind(on_release=self.change_app_code)
        code_row.add_widget(self.new_code)
        code_row.add_widget(code_btn)
        content.add_widget(code_row)

        self.status_label = Label(text="", color=(0.4, 1, 0.4, 1), size_hint_y=None, height=dp(24))
        content.add_widget(self.status_label)

        # --- Users summary ---
        self.summary_label = Label(text="", bold=True, size_hint_y=None, height=dp(28))
        content.add_widget(self.summary_label)

        # --- Users table header ---
        header = GridLayout(cols=4, size_hint_y=None, height=dp(30))
        for h in ["ID", "Username", "Password", "Active"]:
            header.add_widget(Label(text=h, bold=True, font_size="13sp"))
        content.add_widget(header)

        self.users_table = GridLayout(cols=4, size_hint_y=None, spacing=dp(2))
        self.users_table.bind(minimum_height=self.users_table.setter("height"))
        content.add_widget(self.users_table)

        scroll.add_widget(content)
        self.root_layout.add_widget(scroll)

    def change_admin_password(self, *args):
        new_pw = self.new_admin_pw.text.strip()
        if not new_pw:
            self.status_label.text = "Password khali nahi ho sakta."
            self.status_label.color = (1, 0.4, 0.4, 1)
            return
        config = load_json(CONFIG_FILE)
        config["admin_password"] = new_pw
        save_json(CONFIG_FILE, config)
        self.new_admin_pw.text = ""
        self.status_label.text = "Admin password update ho gaya."
        self.status_label.color = (0.4, 1, 0.4, 1)

    def change_app_code(self, *args):
        new_code = self.new_code.text.strip()
        if not new_code:
            self.status_label.text = "Code khali nahi ho sakta."
            self.status_label.color = (1, 0.4, 0.4, 1)
            return
        config = load_json(CONFIG_FILE)
        config["app_code"] = new_code
        save_json(CONFIG_FILE, config)
        self.new_code.text = ""
        self.status_label.text = "App code update ho gaya."
        self.status_label.color = (0.4, 1, 0.4, 1)

    def refresh(self):
        users = load_json(USERS_FILE)
        active_count = sum(1 for u in users if u.get("active"))
        self.summary_label.text = f"Total Users: {len(users)}   |   Active Users: {active_count}"

        self.users_table.clear_widgets()
        for u in users:
            self.users_table.add_widget(Label(text=str(u["id"]), size_hint_y=None, height=dp(34)))
            self.users_table.add_widget(Label(text=u["username"], size_hint_y=None, height=dp(34)))
            self.users_table.add_widget(Label(text=u["password"], size_hint_y=None, height=dp(34)))
            toggle_btn = RoundedButton(
                text="Yes" if u.get("active") else "No",
                size_hint_y=None,
                height=dp(30),
                bg_color=(0.2, 0.7, 0.3, 1) if u.get("active") else (0.7, 0.2, 0.2, 1),
            )
            toggle_btn.bind(on_release=lambda inst, uid=u["id"]: self.toggle_active(uid))
            self.users_table.add_widget(toggle_btn)

    def toggle_active(self, user_id):
        users = load_json(USERS_FILE)
        for u in users:
            if u["id"] == user_id:
                u["active"] = not u.get("active", False)
        save_json(USERS_FILE, users)
        self.refresh()


# ---------------------------------------------------------------------------
# APP
# ---------------------------------------------------------------------------
class HamzaAIApp(App):
    def build(self):
        ensure_data()
        # seed one demo user so the admin panel isn't empty on first run
        users = load_json(USERS_FILE)
        if not users:
            users.append({"id": 1, "username": "demo_user", "password": "demo123", "active": True})
            save_json(USERS_FILE, users)

        Window.clearcolor = (0.05, 0.05, 0.08, 1)
        sm = ScreenManager(transition=SlideTransition())
        sm.add_widget(ChatScreen(name="chat"))
        sm.add_widget(AdminLoginScreen(name="admin_login"))
        sm.add_widget(AdminPanelScreen(name="admin_panel"))
        sm.current = "chat"
        return sm


if __name__ == "__main__":
    HamzaAIApp().run()