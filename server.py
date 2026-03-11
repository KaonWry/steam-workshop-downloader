import shutil
import sqlite3
import tempfile
import pathlib
from flask import Flask, request, jsonify, send_file
from main import (
    download_workshop_item,
    extract_workshop_id,
    get_appid_from_workshop,
    get_game_name,
)

app = Flask(__name__)

DB_PATH = pathlib.Path(__file__).parent.resolve() / "queue.db"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE IF NOT EXISTS queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workshop_id TEXT NOT NULL,
            workshop_title TEXT NOT NULL,
            appid TEXT NOT NULL,
            game_name TEXT NOT NULL,
            workshop_link TEXT NOT NULL
        )"""
    )
    conn.commit()
    return conn


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
    response.headers["Access-Control-Expose-Headers"] = "Content-Disposition, X-Remaining"
    return response


# ── Queue endpoints ──────────────────────────────────────────────


@app.route("/queue", methods=["GET", "OPTIONS"])
def list_queue():
    if request.method == "OPTIONS":
        return "", 204
    conn = get_db()
    rows = conn.execute("SELECT * FROM queue ORDER BY id").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/queue", methods=["POST"])
def add_to_queue():
    body = request.get_json(silent=True)
    if not body or "workshop_id" not in body:
        return jsonify({"error": "Missing workshop_id"}), 400

    raw = str(body["workshop_id"]).strip()
    if not raw:
        return jsonify({"error": "Empty workshop_id"}), 400

    try:
        wid = extract_workshop_id(raw)
        appid, workshop_title = get_appid_from_workshop(wid)
        game_name = get_game_name(appid)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    link = f"https://steamcommunity.com/sharedfiles/filedetails/?id={wid}"

    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM queue WHERE workshop_id = ?", (wid,)
    ).fetchone()
    if existing:
        conn.close()
        return jsonify({"error": f"Workshop item {wid} is already in the queue"}), 409

    conn.execute(
        "INSERT INTO queue (workshop_id, workshop_title, appid, game_name, workshop_link) VALUES (?, ?, ?, ?, ?)",
        (wid, workshop_title, appid, game_name, link),
    )
    conn.commit()
    conn.close()

    return jsonify({
        "workshop_id": wid,
        "workshop_title": workshop_title,
        "appid": appid,
        "game_name": game_name,
        "workshop_link": link,
    }), 201


@app.route("/queue/<int:item_id>", methods=["DELETE", "OPTIONS"])
def remove_from_queue(item_id):
    if request.method == "OPTIONS":
        return "", 204
    conn = get_db()
    conn.execute("DELETE FROM queue WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return "", 204


# ── Download endpoints ───────────────────────────────────────────


@app.route("/download", methods=["POST", "OPTIONS"])
def download():
    if request.method == "OPTIONS":
        return "", 204

    body = request.get_json(silent=True)
    if not body or "workshop_id" not in body:
        return jsonify({"error": "Missing workshop_id"}), 400

    workshop_id = str(body["workshop_id"])
    if not workshop_id.strip():
        return jsonify({"error": "Empty workshop_id"}), 400

    try:
        result = download_workshop_item(workshop_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    dest = result["destination"]
    zip_name = f"{result['game_name']} - {result['workshop_title']}"
    tmp_zip = tempfile.mktemp(suffix=".zip")
    shutil.make_archive(tmp_zip.removesuffix(".zip"), "zip", dest)

    return send_file(
        tmp_zip,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"{zip_name}.zip",
    )


@app.route("/download-next", methods=["POST", "OPTIONS"])
def download_next():
    """Download the first item in the queue and remove it. Returns JSON with item info."""
    if request.method == "OPTIONS":
        return "", 204

    conn = get_db()
    row = conn.execute("SELECT * FROM queue ORDER BY id LIMIT 1").fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Queue is empty"}), 400

    item = dict(row)
    conn.execute("DELETE FROM queue WHERE id = ?", (item["id"],))
    conn.commit()
    conn.close()

    try:
        result = download_workshop_item(item["workshop_id"])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify(result), 200


@app.route("/download-file/<wid>", methods=["GET", "OPTIONS"])
def download_file(wid):
    """Serve an already-downloaded workshop item as a zip."""
    if request.method == "OPTIONS":
        return "", 204

    try:
        wid = extract_workshop_id(wid)
        appid, workshop_title = get_appid_from_workshop(wid)
        game_name = get_game_name(appid)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    from main import sanitize_name, downloads_dir
    dest = downloads_dir / sanitize_name(game_name) / sanitize_name(workshop_title)
    if not dest.exists():
        return jsonify({"error": "Item not found on disk"}), 404

    zip_name = f"{game_name} - {workshop_title}"
    tmp_zip = tempfile.mktemp(suffix=".zip")
    shutil.make_archive(tmp_zip.removesuffix(".zip"), "zip", dest)

    return send_file(
        tmp_zip,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"{zip_name}.zip",
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, threaded=True)
