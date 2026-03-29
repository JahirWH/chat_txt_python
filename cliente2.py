"""
chat_gui.py  —  jahir & fatima ✦
pip install customtkinter websockets pillow
pyinstaller --onefile --windowed --name "fatima" chat_gui.py
"""

import customtkinter as ctk
import tkinter as tk
import asyncio
import websockets
import json
import threading
import platform
import math
import random
import os
import sys
from datetime import datetime
from PIL import Image, ImageTk, ImageFilter, ImageDraw

# ══════════════════════════════════════════════
#  VAriables de configuracion
# ══════════════════════════════════════════════
SERVER_IP   = "66.179.137.254"
SERVER_PORT = 8765
MY_NAME     = "fatima"           # "ahir" o "fatilov"

# Rutas de fotos — déjalas en "" si no tienes aún
PHOTO_ME    = "jahir.jpg"      # tu foto
PHOTO_HER   = "fati.jpg"   # foto de ella
PHOTO_BG    = "juntos.jpg"    # foto de fondo difuminada
# ══════════════════════════════════════════════

OTHER_NAME = "jahir" if MY_NAME == "fatima" else "fatima"
WS_URL     = f"ws://{SERVER_IP}:{SERVER_PORT}"

# ── Paleta ───────────────────────────────────
BG_BASE   = "#120a0e"
BG_SIDE   = "#170d12"
BG_CHAT   = "#130c10"
BG_INPUT  = "#1e1118"
BG_ME     = "#3d1a28"
BG_OTHER  = "#1e1118"
ROSE      = "#f9a8c9"
ROSE_DIM  = "#7a3a52"
ROSE_DARK = "#2a1020"
TEXT_PRI  = "#fce8f0"
TEXT_MUT  = "#6b4555"
TEXT_TS   = "#3a1f2e"
BORDER    = "#2a1520"

FONT_MSG   = ("Georgia", 13)
FONT_SMALL = ("Georgia", 10)
FONT_NAME  = ("Georgia", 11, "bold")
FONT_MATH  = ("Courier New", 9)

WIN_W, WIN_H = 860, 640
SIDE_W       = 218
AV_SIZE      = 38

MATH_GLYPHS = [
    "∫₀^∞ e^{-x²}dx", "∑ 1/n²", "∂f/∂x", "∇·E = ρ/ε",
    "lim_{x→0}", "π≈3.14159", "e^{iπ}+1=0", "∀ε>0 ∃δ>0",
    "det(A-λI)=0", "dx/dt", "sin²+cos²=1", "∆x·∆p≥ℏ/2",
    "∞", "√-1 = i", "∮ B·dl", "ℝ³→ℝ", "P(A|B)",
]

# ── Helpers ──────────────────────────────────
def res(path):
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, path)

def beep():
    if platform.system() == "Windows":
        import winsound
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
    else:
        os.system("paplay /usr/share/sounds/freedesktop/stereo/message.oga 2>/dev/null &")

def ts_now():
    return datetime.now().strftime("%H:%M")

# ── Procesamiento de imágenes ─────────────────
def circle_photo(path, size):
    try:
        img = Image.open(res(path)).convert("RGBA").resize((size, size), Image.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        img.putalpha(mask)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None

def blurred_bg(path, w, h):
    try:
        img = Image.open(res(path)).convert("RGBA").resize((w, h), Image.LANCZOS)
        img = img.filter(ImageFilter.GaussianBlur(radius=22))
        overlay = Image.new("RGBA", (w, h), (18, 8, 14, 215))
        return ImageTk.PhotoImage(Image.alpha_composite(img, overlay))
    except Exception:
        return None

def initials_img(letter, size, bg_hex, fg_hex):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    br, bg2, bb = int(bg_hex[1:3],16), int(bg_hex[3:5],16), int(bg_hex[5:7],16)
    fr, fg2, fb = int(fg_hex[1:3],16), int(fg_hex[3:5],16), int(fg_hex[5:7],16)
    draw.ellipse((2,2,size-2,size-2), fill=(br,bg2,bb,255))
    draw.text((size//2-5, size//2-8), letter, fill=(fr,fg2,fb,255))
    return ImageTk.PhotoImage(img)

# ══════════════════════════════════════════════
#  BURBUJA Anim
# ══════════════════════════════════════════════
class Bubble(tk.Frame):
    def __init__(self, parent, sender, content, timestamp, avatars, **kw):
        is_me = sender == MY_NAME
        super().__init__(parent, bg=BG_CHAT, **kw)
        self.columnconfigure(1, weight=1)

        av_img = avatars.get(sender)
        av_col = 2 if is_me else 0
        pad_l  = 55 if not is_me else 4
        pad_r  = 4  if not is_me else 55
        side   = "e" if is_me else "w"
        bub_bg = BG_ME if is_me else BG_OTHER
        bub_bd = ROSE_DIM if is_me else "#2a1a22"

        # Avatar
        if av_img:
            av_w = tk.Label(self, image=av_img, bg=BG_CHAT)
            av_w.image = av_img
        else:
            av_w = tk.Label(self,
                text=sender[0].upper(),
                bg=ROSE_DIM if is_me else "#2a0f20",
                fg=ROSE, font=("Georgia",12,"bold"),
                width=2, padx=4, pady=2)
        av_w.grid(row=0, column=av_col, padx=5, pady=(5,0), sticky="n")

        # Burbuja
        bub = tk.Frame(self, bg=bub_bg,
                       highlightbackground=bub_bd, highlightthickness=1,
                       padx=12, pady=8)
        bub.grid(row=0, column=1, padx=(pad_l,pad_r), pady=(6,0), sticky=side)
        tk.Label(bub, text=content, bg=bub_bg, fg=TEXT_PRI,
                 font=FONT_MSG, wraplength=340,
                 justify="left", anchor="w").pack()

        # Timestamp
        tk.Label(self, text=timestamp, bg=BG_CHAT,
                 fg=TEXT_TS, font=FONT_SMALL).grid(
            row=1, column=1, padx=(pad_l,pad_r), pady=(0,4), sticky=side)


class SysMsg(tk.Frame):
    def __init__(self, parent, text, **kw):
        super().__init__(parent, bg=BG_CHAT, **kw)
        inner = tk.Frame(self, bg=ROSE_DARK, padx=14, pady=3)
        inner.pack(pady=5)
        tk.Label(inner, text=text, bg=ROSE_DARK,
                 fg=TEXT_MUT, font=FONT_MATH).pack()

# ══════════════════════════════════════════════
#  APP
# ══════════════════════════════════════════════
class ChatApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.title("ahir & fatilov  ✦")
        self.geometry(f"{WIN_W}x{WIN_H}")
        self.minsize(620, 440)
        self.configure(fg_color=BG_BASE)

        self._ws      = None
        self._loop    = asyncio.new_event_loop()
        self._avatars = {}
        self._bg_photo = None

        self._load_images()
        self._build_ui()
        self._start_ws()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Imágenes ──────────────────────────────
    def _load_images(self):
        map_ = {"ahir": (PHOTO_ME, ROSE_DIM, ROSE),
                "fatilov": (PHOTO_HER, "#2a0f20", ROSE)}
        for name, (path, bg, fg) in map_.items():
            img = circle_photo(path, AV_SIZE) if os.path.exists(res(path)) else None
            self._avatars[name] = img or initials_img(name[0].upper(), AV_SIZE, bg, fg)

        if os.path.exists(res(PHOTO_BG)):
            self._bg_photo = blurred_bg(PHOTO_BG, WIN_W - SIDE_W, WIN_H - 50)

    # ── UI ────────────────────────────────────
    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_chat()

    # ── Sidebar ───────────────────────────────
    def _build_sidebar(self):
        sb = tk.Frame(self, bg=BG_SIDE, width=SIDE_W)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)

        tk.Frame(sb, bg=ROSE, height=2).pack(fill="x")

        # Título
        hdr = tk.Frame(sb, bg=BG_SIDE, pady=18)
        hdr.pack(fill="x")
        tk.Label(hdr, text="✦  ahir & fatilov  ✦",
                 bg=BG_SIDE, fg=ROSE,
                 font=("Georgia", 12, "bold")).pack()
        tk.Label(hdr, text="chat privado",
                 bg=BG_SIDE, fg=TEXT_MUT,
                 font=("Courier New", 9)).pack(pady=(2,0))
        tk.Label(hdr, text="e^{iπ} + 1 = 0  ♡",
                 bg=BG_SIDE, fg=ROSE_DIM,
                 font=("Courier New", 9, "italic")).pack(pady=(5,0))

        tk.Frame(sb, bg=BORDER, height=1).pack(fill="x", padx=16, pady=10)

        # Card contacto
        self._contact_card(sb, OTHER_NAME)
        tk.Frame(sb, bg=BORDER, height=1).pack(fill="x", padx=16, pady=10)
        tk.Frame(sb, bg=BG_SIDE).pack(fill="both", expand=True)

        # Mi perfil (abajo)
        bot = tk.Frame(sb, bg=BG_SIDE, pady=10)
        bot.pack(fill="x", side="bottom")
        tk.Frame(bot, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(0,10))
        self._me_card(bot)

        self._conn_lbl = tk.Label(sb, text="● conectando...",
                                   bg=BG_SIDE, fg=TEXT_MUT,
                                   font=("Courier New", 9))
        self._conn_lbl.pack(pady=(2,8), side="bottom")

    def _contact_card(self, parent, name):
        card = tk.Frame(parent, bg=BG_INPUT, padx=12, pady=10)
        card.pack(fill="x", padx=14)
        row = tk.Frame(card, bg=BG_INPUT)
        row.pack(fill="x")

        av = self._avatars.get(name)
        if av:
            lbl = tk.Label(row, image=av, bg=BG_INPUT)
            lbl.image = av
            lbl.pack(side="left")
        else:
            tk.Label(row, text=name[0].upper(), bg="#2a0f20", fg=ROSE,
                     font=("Georgia",13,"bold"),
                     width=2, padx=5, pady=3).pack(side="left")

        info = tk.Frame(row, bg=BG_INPUT)
        info.pack(side="left", padx=10)
        tk.Label(info, text=name, bg=BG_INPUT,
                 fg=TEXT_PRI, font=FONT_NAME).pack(anchor="w")

        sr = tk.Frame(info, bg=BG_INPUT)
        sr.pack(anchor="w", pady=(3,0))
        self._dot = tk.Canvas(sr, width=8, height=8,
                               bg=BG_INPUT, highlightthickness=0)
        self._dot_id = self._dot.create_oval(1,1,7,7, fill="#2a2a2a", outline="")
        self._dot.pack(side="left")
        self._stat_lbl = tk.Label(sr, text="desconectada",
                                   bg=BG_INPUT, fg=TEXT_MUT,
                                   font=("Courier New", 9))
        self._stat_lbl.pack(side="left", padx=4)

    def _me_card(self, parent):
        row = tk.Frame(parent, bg=BG_SIDE)
        row.pack(fill="x", padx=14)
        av = self._avatars.get(MY_NAME)
        if av:
            lbl = tk.Label(row, image=av, bg=BG_SIDE)
            lbl.image = av
            lbl.pack(side="left")
        else:
            tk.Label(row, text=MY_NAME[0].upper(), bg=ROSE_DIM, fg=ROSE,
                     font=("Georgia",12,"bold"),
                     width=2, padx=4, pady=2).pack(side="left")
        info = tk.Frame(row, bg=BG_SIDE)
        info.pack(side="left", padx=9)
        tk.Label(info, text=MY_NAME, bg=BG_SIDE,
                 fg=TEXT_PRI, font=FONT_NAME).pack(anchor="w")
        tk.Label(info, text="tú", bg=BG_SIDE,
                 fg=TEXT_MUT, font=("Courier New", 9)).pack(anchor="w")

    # ── Chat ──────────────────────────────────
    def _build_chat(self):
        chat = tk.Frame(self, bg=BG_CHAT)
        chat.grid(row=0, column=1, sticky="nsew")
        chat.grid_rowconfigure(0, weight=1)
        chat.grid_columnconfigure(0, weight=1)

        # Canvas scrollable
        self._canvas = tk.Canvas(chat, bg=BG_CHAT,
                                  highlightthickness=0, bd=0)
        vsb = tk.Scrollbar(chat, orient="vertical",
                            command=self._canvas.yview,
                            bg=BG_CHAT, troughcolor=BG_CHAT,
                            activebackground=BG_INPUT, width=5)
        self._canvas.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns")
        self._canvas.grid(row=0, column=0, sticky="nsew")

        # Fondo de foto difuminada
        if self._bg_photo:
            self._canvas.create_image(0, 0, image=self._bg_photo,
                                       anchor="nw", tags="bg")

        # Símbolos matemáticos de fondo
        random.seed(42)
        for g in random.choices(MATH_GLYPHS, k=24):
            self._canvas.create_text(
                random.randint(20, WIN_W-SIDE_W-20),
                random.randint(20, WIN_H-20),
                text=g, fill=TEXT_TS,
                font=("Courier New", random.choice([9,10,11])),
                angle=random.randint(-20,20),
                tags="mathbg")
        self._canvas.tag_lower("mathbg")
        if self._bg_photo:
            self._canvas.tag_lower("bg")

        # Frame de mensajes
        self._msgs = tk.Frame(self._canvas, bg=BG_CHAT)
        self._cwin = self._canvas.create_window(
            (0,0), window=self._msgs, anchor="nw")

        self._msgs.bind("<Configure>",
            lambda e: self._canvas.configure(
                scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>",
            lambda e: self._canvas.itemconfig(self._cwin, width=e.width))
        self._canvas.bind_all("<MouseWheel>",
            lambda e: self._canvas.yview_scroll(
                int(-1*(e.delta/120)), "units"))

        # Barra input
        bar = tk.Frame(chat, bg=BG_SIDE, pady=10)
        bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        tk.Frame(bar, bg=ROSE_DIM, height=1).pack(fill="x", pady=(0,8))

        inp_row = tk.Frame(bar, bg=BG_SIDE)
        inp_row.pack(fill="x", padx=12)

        self._input = tk.Text(inp_row, height=2, bg=BG_INPUT,
                               fg=TEXT_MUT, font=FONT_MSG,
                               insertbackground=ROSE,
                               relief="flat", padx=12, pady=7,
                               wrap="word", bd=0,
                               highlightbackground=ROSE_DIM,
                               highlightthickness=1)
        self._input.insert("1.0", "escribe algo bonito...")
        self._input.pack(side="left", fill="both", expand=True)
        self._input.bind("<Return>", self._on_enter)
        self._input.bind("<FocusIn>",  self._clear_ph)
        self._input.bind("<FocusOut>", self._set_ph)

        tk.Button(inp_row, text="✦ enviar",
                  bg=ROSE_DIM, fg=ROSE,
                  activebackground=ROSE, activeforeground=BG_BASE,
                  font=("Georgia",11,"bold"),
                  relief="flat", padx=16, pady=8,
                  cursor="hand2", bd=0,
                  command=self._send).pack(side="right", padx=(8,0))

    def _clear_ph(self, e=None):
        if self._input.get("1.0","end").strip() == "escribe algo bonito...":
            self._input.delete("1.0","end")
            self._input.config(fg=TEXT_PRI)

    def _set_ph(self, e=None):
        if not self._input.get("1.0","end").strip():
            self._input.insert("1.0","escribe algo bonito...")
            self._input.config(fg=TEXT_MUT)

    # ── Mensajes ──────────────────────────────
    def _add_bubble(self, sender, content, ts):
        Bubble(self._msgs, sender, content, ts, self._avatars).pack(
            fill="x", pady=1)
        self._scroll_bottom()

    def _add_sys(self, text):
        SysMsg(self._msgs, text).pack(fill="x")
        self._scroll_bottom()

    def _add_history(self, msgs):
        if msgs:
            self._add_sys("── historial ──")
        for m in msgs:
            self._add_bubble(m["sender"], m["content"], m["timestamp"])
        if msgs:
            self._add_sys("── ahora ──")

    def _scroll_bottom(self):
        self._canvas.update_idletasks()
        self._canvas.yview_moveto(1.0)

    # ── Estado ────────────────────────────────
    def _set_connected(self, ok):
        self._conn_lbl.config(
            text="● conectado" if ok else "● desconectado",
            fg=ROSE if ok else TEXT_MUT)

    def _set_other_online(self, online):
        self._dot.itemconfig(self._dot_id,
            fill=ROSE if online else "#2a2a2a")
        self._stat_lbl.config(
            text="en línea  ♡" if online else "desconectada",
            fg=ROSE if online else TEXT_MUT)

    # ── Envío ─────────────────────────────────
    def _on_enter(self, e):
        if not (e.state & 1):
            self._send()
            return "break"

    def _send(self):
        txt = self._input.get("1.0","end").strip()
        if not txt or txt == "escribe algo bonito..." or not self._ws:
            return
        self._input.delete("1.0","end")
        self._set_ph()
        asyncio.run_coroutine_threadsafe(
            self._ws.send(json.dumps({"type":"message","content":txt})),
            self._loop)

    # ── WebSocket ─────────────────────────────
    def _start_ws(self):
        threading.Thread(target=self._run_loop, daemon=True).start()

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._ws_loop())

    async def _ws_loop(self):
        while True:
            try:
                async with websockets.connect(WS_URL) as ws:
                    self._ws = ws
                    self.after(0, self._set_connected, True)
                    await ws.send(json.dumps({"type":"join","username":MY_NAME}))
                    async for raw in ws:
                        self.after(0, self._handle, json.loads(raw))
            except Exception:
                self._ws = None
                self.after(0, self._set_connected, False)
                self.after(0, self._set_other_online, False)
                await asyncio.sleep(5)

    def _handle(self, data):
        t = data.get("type")
        if   t == "history": self._add_history(data.get("messages", []))
        elif t == "message":
            self._add_bubble(data["sender"], data["content"], data["timestamp"])
            if data["sender"] != MY_NAME:
                beep(); self.lift(); self.focus_force()
        elif t == "status":
            self._set_other_online(OTHER_NAME in data.get("online",[]))
        elif t == "error":
            self._add_sys(f"error: {data.get('msg')}")

    def _on_close(self):
        if self._ws:
            asyncio.run_coroutine_threadsafe(self._ws.close(), self._loop)
        self.destroy()


if __name__ == "__main__":
    app = ChatApp()
    app.mainloop()