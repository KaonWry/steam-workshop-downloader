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

parser = argparse.ArgumentParser(description="Steam Workshop Downloader")
parser.add_argument("workshop_id", type=str, help="Steam Workshop Item ID or workshop URL")

args = parser.parse_args()
raw_workshop = args.workshop_id


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

    print(f"Could not extract workshop id from '{value}'", file=sys.stderr)
    sys.exit(1)


workshop_id = extract_workshop_id(raw_workshop)

def sanitize_name(name: str) -> str:
    """Remove or replace characters that are unsafe for directory names."""
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    return name.strip().rstrip('.')


def get_appid_from_workshop(wid: str) -> tuple[str, str]:
    url = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
    data = {"itemcount": "1", "publishedfileids[0]": wid}
    encoded = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=encoded, headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode()
    except Exception as e:
        print(f"Failed to contact Steam API: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        obj = json.loads(body)
        details = obj["response"]["publishedfiledetails"][0]
        appid = details["consumer_app_id"]
        if not appid:
            raise KeyError("consumer_app_id not found")
        title = details.get("title", wid)
        return str(appid), title
    except Exception as e:
        print(f"Failed to parse Steam API response: {e}", file=sys.stderr)
        sys.exit(1)


def get_game_name(appid: str) -> str:
    url = f"https://store.steampowered.com/api/appdetails?appids={urllib.parse.quote(appid)}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode()
    except Exception as e:
        print(f"Failed to contact Steam Store API: {e}", file=sys.stderr)
        return appid

    try:
        obj = json.loads(body)
        return obj[appid]["data"]["name"]
    except Exception:
        return appid


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
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"steamcmd failed: {e}", file=sys.stderr)
        sys.exit(1)

    src = tmp_path / "steamapps" / "workshop" / "content" / appid / workshop_id
    if not src.exists():
        print(f"Downloaded item not found at {src}", file=sys.stderr)
        sys.exit(1)

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
