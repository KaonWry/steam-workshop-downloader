import argparse
import pathlib
import subprocess
import tempfile
import shutil
import sys
import urllib.request
import urllib.parse
import json
import re

project_root = pathlib.Path(__file__).parent.resolve()
downloads_dir = project_root / "Downloads"
downloads_dir.mkdir(exist_ok=True)


def extract_workshop_id(value: str) -> str:
    if value.isdigit():
        return value

    try:
        p = urllib.parse.urlparse(value)
        qs = urllib.parse.parse_qs(p.query)
        if "id" in qs and qs["id"]:
            return qs["id"][0]
    except Exception:
        pass

    m = re.search(r"(\d{5,})", value)
    if m:
        return m.group(1)

    raise ValueError(f"Could not extract workshop id from '{value}'")


def sanitize_name(name: str) -> str:
    """Remove or replace characters that are unsafe for directory names."""
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    return name.strip().rstrip('.')


def get_appid_from_workshop(wid: str) -> tuple[str, str]:
    url = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
    data = {"itemcount": "1", "publishedfileids[0]": wid}
    encoded = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=encoded, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode()

    obj = json.loads(body)
    details = obj["response"]["publishedfiledetails"][0]
    appid = details["consumer_app_id"]
    if not appid:
        raise KeyError("consumer_app_id not found")
    title = details.get("title", wid)
    return str(appid), title


def get_game_name(appid: str) -> str:
    url = f"https://store.steampowered.com/api/appdetails?appids={urllib.parse.quote(appid)}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode()
        obj = json.loads(body)
        return obj[appid]["data"]["name"]
    except Exception:
        return appid


def download_workshop_item(raw_workshop: str) -> dict:
    """Download a workshop item. Returns a dict with details about the result.

    Raises on failure so callers (CLI / server) can handle errors.
    """
    workshop_id = extract_workshop_id(raw_workshop)
    appid, workshop_title = get_appid_from_workshop(workshop_id)
    game_name = get_game_name(appid)

    print(f"Downloading workshop item '{workshop_title}' ({workshop_id}) for {game_name} ({appid})")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = pathlib.Path(tmpdir)
        cmd = [
            "steamcmd",
            "+force_install_dir",
            str(tmp_path),
            "+login",
            "anonymous",
            "+workshop_download_item",
            appid,
            workshop_id,
            "+quit",
        ]
        subprocess.run(cmd, check=True)

        src = tmp_path / "steamapps" / "workshop" / "content" / appid / workshop_id
        if not src.exists():
            raise FileNotFoundError(f"Downloaded item not found at {src}")

        app_dir = downloads_dir / sanitize_name(game_name)
        app_dir.mkdir(exist_ok=True)
        dest = app_dir / sanitize_name(workshop_title)
        if dest.exists():
            print(f"Destination {dest} already exists, removing it")
            if dest.is_dir():
                shutil.rmtree(dest)
            else:
                dest.unlink()

        shutil.move(str(src), str(dest))
        print(f"Moved downloaded item to {dest}")

    return {
        "workshop_id": workshop_id,
        "workshop_title": workshop_title,
        "appid": appid,
        "game_name": game_name,
        "destination": str(dest),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Steam Workshop Downloader")
    parser.add_argument("workshop_id", type=str, help="Steam Workshop Item ID or workshop URL")
    args = parser.parse_args()

    try:
        result = download_workshop_item(args.workshop_id)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
