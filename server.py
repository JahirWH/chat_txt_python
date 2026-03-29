import asyncio
import websockets
import json
import sqlite3
from datetime import datetime

# ─────────────────────────────────────────
#  CONFIGURACIÓN
# ─────────────────────────────────────────
HOST = "0.0.0.0"
PORT = 8765
DB_FILE = "chat.db"

# Nombres fijos de los dos usuarios
VALID_USERS = {"fatima", "jahir"}   # 

# ─────────────────────────────────────────
#  BASE DE DATOS
# ─────────────────────────────────────────
def init_db():
    con = sqlite3.connect(DB_FILE)
    con.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            sender    TEXT NOT NULL,
            content   TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    con.commit()
    con.close()

def save_message(sender, content, timestamp):
    con = sqlite3.connect(DB_FILE)
    con.execute(
        "INSERT INTO messages (sender, content, timestamp) VALUES (?, ?, ?)",
        (sender, content, timestamp)
    )
    con.commit()
    con.close()

def get_history(limit=30):
    con = sqlite3.connect(DB_FILE)
    rows = con.execute(
        "SELECT sender, content, timestamp FROM messages ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    con.close()
    return list(reversed(rows))

# ─────────────────────────────────────────
#  ESTADO GLOBAL
# ─────────────────────────────────────────
connected_clients: dict[str, websockets.WebSocketServerProtocol] = {}

async def broadcast_status():
    """Avisa a todos quién está conectado."""
    online = list(connected_clients.keys())
    msg = json.dumps({"type": "status", "online": online})
    for ws in connected_clients.values():
        try:
            await ws.send(msg)
        except Exception:
            pass

async def broadcast_message(sender, content, timestamp):
    """Envía el mensaje a todos los conectados."""
    msg = json.dumps({
        "type": "message",
        "sender": sender,
        "content": content,
        "timestamp": timestamp
    })
    for ws in connected_clients.values():
        try:
            await ws.send(msg)
        except Exception:
            pass

# ─────────────────────────────────────────
#  HANDLER PRINCIPAL
# ─────────────────────────────────────────
async def handler(websocket):
    username = None
    try:
        # Primer mensaje debe ser identificación
        raw = await asyncio.wait_for(websocket.recv(), timeout=10)
        data = json.loads(raw)

        if data.get("type") != "join" or data.get("username") not in VALID_USERS:
            await websocket.send(json.dumps({"type": "error", "msg": "Usuario no válido."}))
            return

        username = data["username"]

        if username in connected_clients:
            await websocket.send(json.dumps({"type": "error", "msg": "Ya hay una sesión activa con ese nombre."}))
            return

        connected_clients[username] = websocket
        print(f"[+] {username} conectado  ({datetime.now().strftime('%H:%M:%S')})")

        # Enviar historial al recién conectado
        history = get_history()
        await websocket.send(json.dumps({"type": "history", "messages": [
            {"sender": s, "content": c, "timestamp": t} for s, c, t in history
        ]}))

        # Avisar a todos sobre el nuevo estado
        await broadcast_status()

        # Escuchar mensajes
        async for raw_msg in websocket:
            data = json.loads(raw_msg)
            if data.get("type") == "message":
                content = data.get("content", "").strip()
                if not content:
                    continue
                timestamp = datetime.now().strftime("%H:%M")
                save_message(username, content, timestamp)
                await broadcast_message(username, content, timestamp)

    except asyncio.TimeoutError:
        print("[-] Timeout esperando identificación.")
    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        if username and username in connected_clients:
            del connected_clients[username]
            print(f"[-] {username} desconectado ({datetime.now().strftime('%H:%M:%S')})")
            await broadcast_status()

# ─────────────────────────────────────────
#  INICIO
# ─────────────────────────────────────────
async def main():
    init_db()
    print(f"[*] Servidor corriendo en {HOST}:{PORT}")
    async with websockets.serve(handler, HOST, PORT):
        await asyncio.Future()  # correr para siempre

if __name__ == "__main__":
    asyncio.run(main())