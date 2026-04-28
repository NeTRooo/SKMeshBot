import asyncio
import logging
import os
from typing import Any

from meshcore import MeshCore, EventType

SERIAL_PORT = os.environ.get("SERIAL_PORT", "COM8")
CHANNEL_IDX = int(os.environ.get("CHANNEL_IDX", "1"))

TRIGGER_WORDS = ["ping", "пинг", "test", "тест"]

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger("serial_pingbot")

latest_pathinfo_str = "(? hops, ?)"
latest_log_data: dict[str, Any] = {}


def format_pathinfo(log_data: dict[str, Any]) -> str:
    path_len = log_data.get("path_len")
    path_hex = log_data.get("path", "")
    hash_size = log_data.get("path_hash_size", 1)

    if path_len is None:
        return "(? hops, ?)"
    if path_len == 0:
        return "(0 hops, direct)"

    node_hex_len = hash_size * 2
    nodes = [path_hex[i:i + node_hex_len] for i in range(0, len(path_hex), node_hex_len) if path_hex[i:i + node_hex_len]]
    path_str = ":".join(nodes) if nodes else "?"
    return f"({path_len} hops, {path_str})"


def resolve_path_names(log_data: dict[str, Any], mc: MeshCore) -> str | None:
    """Map each path hop hash to a contact name; return ':'-joined string or None if no hops."""
    path_len = log_data.get("path_len")
    path_hex = log_data.get("path", "")
    hash_size = log_data.get("path_hash_size", 1)

    if not path_len:
        return None

    node_hex_len = hash_size * 2
    nodes = [path_hex[i:i + node_hex_len] for i in range(0, len(path_hex), node_hex_len) if path_hex[i:i + node_hex_len]]

    names = []
    for node_hash in nodes:
        contact = mc.get_contact_by_key_prefix(node_hash)
        names.append(contact["adv_name"] if contact else node_hash)

    return ":".join(names) if names else None


async def main():
    global latest_pathinfo_str, latest_log_data

    meshcore = await MeshCore.create_serial(SERIAL_PORT, debug=True)
    print(f"Connected on {SERIAL_PORT}")

    await meshcore.ensure_contacts()
    meshcore.auto_update_contacts = True

    await meshcore.start_auto_message_fetching()

    async def handle_rx_log_data(event):
        global latest_pathinfo_str, latest_log_data

        log_data = event.payload or {}
        if "path_len" not in log_data:
            return

        latest_log_data = log_data
        latest_pathinfo_str = format_pathinfo(log_data)

    async def handle_channel_message(event):
        msg = event.payload or {}

        pathinfo = latest_pathinfo_str
        log_data = latest_log_data

        chan = msg.get("channel_idx")
        text = msg.get("text", "")
        path_len = msg.get("path_len")
        sender = text.split(":", 1)[0].strip()

        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        print(pathinfo)
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        print(f"Received on channel {chan} from {sender}: {text} | path_len={path_len}")

        if chan == CHANNEL_IDX and any(w in text.lower() for w in TRIGGER_WORDS):
            reply = f"@[{sender}] Pong 🏓{pathinfo}"
            print(f"Replying in channel {CHANNEL_IDX} with:\n{reply}")

            result = await meshcore.commands.send_chan_msg(CHANNEL_IDX, reply)
            if result.type == EventType.ERROR:
                print(f"Error sending reply: {result.payload}")
                return
            print("Reply sent")

            path_names = resolve_path_names(log_data, meshcore)
            if path_names:
                names_msg = f"@[{sender}] Path: {path_names}"
                print(f"Sending path names:\n{names_msg}")
                result2 = await meshcore.commands.send_chan_msg(CHANNEL_IDX, names_msg)
                if result2.type == EventType.ERROR:
                    print(f"Error sending path names: {result2.payload}")
                else:
                    print("Path names sent")

    sub_chan = meshcore.subscribe(
        EventType.CHANNEL_MSG_RECV,
        handle_channel_message,
        attribute_filters={"channel_idx": CHANNEL_IDX},
    )

    sub_rx = meshcore.subscribe(
        EventType.RX_LOG_DATA,
        handle_rx_log_data,
    )

    try:
        print(f"Listening for 'Ping' on channel {CHANNEL_IDX} and RX_LOG_DATA...")
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        print("Stopping listener...")
    finally:
        meshcore.unsubscribe(sub_chan)
        meshcore.unsubscribe(sub_rx)
        await meshcore.stop_auto_message_fetching()
        await meshcore.disconnect()
        print("Disconnected")


if __name__ == "__main__":
    asyncio.run(main())
