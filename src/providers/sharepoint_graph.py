from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterator, Optional

import msal
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

GRAPH = "https://graph.microsoft.com/v1.0"


@dataclass(frozen=True)
class SPConfig:
    tenant_id: str
    client_id: str
    client_secret: str
    hostname: str
    site_path: str
    drive_name: str
    root_folder: str


def load_sp_config() -> SPConfig:
    def req(name: str) -> str:
        v = os.environ.get(name, "").strip()
        if not v:
            raise RuntimeError(f"Missing env var: {name}")
        return v

    return SPConfig(
        tenant_id=req("GRAPH_TENANT_ID"),
        client_id=req("GRAPH_CLIENT_ID"),
        client_secret=req("GRAPH_CLIENT_SECRET"),
        hostname=req("SP_HOSTNAME"),
        site_path=req("SP_SITE_PATH"),
        drive_name=(os.environ.get("SP_DRIVE_NAME", "Documents").strip() or "Documents"),
        root_folder=os.environ.get("SP_ROOT_FOLDER", "").strip(),
    )


class SharePointGraphClient:
    def __init__(self, cfg: SPConfig) -> None:
        self.cfg = cfg
        self._app = msal.ConfidentialClientApplication(
            client_id=cfg.client_id,
            authority=f"https://login.microsoftonline.com/{cfg.tenant_id}",
            client_credential=cfg.client_secret,
        )
        self._token: Optional[str] = None

    def get_token(self) -> str:
        scopes = ["https://graph.microsoft.com/.default"]
        result = self._app.acquire_token_silent(scopes, account=None)
        if not result:
            result = self._app.acquire_token_for_client(scopes=scopes)
        token = result.get("access_token")
        if not token:
            raise RuntimeError(
                f"Could not get access token: {result.get('error')} {result.get('error_description')}"
            )
        self._token = token
        return token

    def _headers(self) -> Dict[str, str]:
        if not self._token:
            self.get_token()
        assert self._token
        return {"Authorization": f"Bearer {self._token}"}

    def get_json(
        self,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 8,
    ) -> Dict[str, Any]:
        for attempt in range(1, max_retries + 1):
            r = requests.get(url, headers=self._headers(), params=params, timeout=60)

            # For app-only, 401 should not loop forever: refresh once then raise.
            if r.status_code == 401:
                if attempt == 1:
                    self.get_token()
                    continue
                try:
                    detail = r.json()
                except Exception:
                    detail = r.text
                raise RuntimeError(f"Graph 401 Unauthorized on {url}: {detail}")

            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", "5"))
                time.sleep(wait)
                continue

            if 500 <= r.status_code < 600:
                time.sleep(min(2 * attempt, 10))
                continue

            if r.status_code >= 400:
                try:
                    detail = r.json()
                except Exception:
                    detail = r.text
                raise RuntimeError(f"Graph error {r.status_code} on {url}: {detail}")

            return r.json()

        raise RuntimeError(f"GET failed after retries: {url}")

    def resolve_site_id(self) -> str:
        url = f"{GRAPH}/sites/{self.cfg.hostname}:/{self.cfg.site_path.lstrip('/')}"
        data = self.get_json(url)
        return data["id"]

    def list_drives(self, site_id: str) -> Dict[str, str]:
        url = f"{GRAPH}/sites/{site_id}/drives"
        data = self.get_json(url)
        drives: Dict[str, str] = {}
        for d in data.get("value", []):
            name = d.get("name")
            did = d.get("id")
            if name and did:
                drives[name] = did
        return drives

    def resolve_root_item(self, drive_id: str) -> Dict[str, Any]:
        if not self.cfg.root_folder:
            url = f"{GRAPH}/drives/{drive_id}/root"
        else:
            url = f"{GRAPH}/drives/{drive_id}/root:/{self.cfg.root_folder.strip('/')}"
        return self.get_json(url)

    def iter_children(self, drive_id: str, folder_item_id: str) -> Iterator[Dict[str, Any]]:
        url = f"{GRAPH}/drives/{drive_id}/items/{folder_item_id}/children"
        while url:
            page = self.get_json(url)
            for item in page.get("value", []):
                yield item
            url = page.get("@odata.nextLink")


def quick_test() -> None:
    cfg = load_sp_config()
    client = SharePointGraphClient(cfg)

    print("Auth…")
    client.get_token()
    print("OK token")

    print("Resolve site…")
    site_id = client.resolve_site_id()
    print("OK site_id:", site_id)

    print("List drives…")
    drives = client.list_drives(site_id)
    if not drives:
        raise SystemExit("No drives found for this site (permissions issue or wrong site).")

    print("Found drives:", ", ".join(sorted(drives.keys())))

    drive_id = drives.get(cfg.drive_name)
    if not drive_id:
        raise SystemExit(
            f"Drive '{cfg.drive_name}' not found. Set SP_DRIVE_NAME to one of: {sorted(drives.keys())}"
        )

    print("Resolve root folder…")
    root_item = client.resolve_root_item(drive_id)
    root_id = root_item["id"]
    print("OK root item:", root_item.get("name"), "id=", root_id)

    print("List children (first 20):")
    for i, item in enumerate(client.iter_children(drive_id, root_id)):
        print(" -", item.get("name"))
        if i >= 19:
            break


if __name__ == "__main__":
    quick_test()
