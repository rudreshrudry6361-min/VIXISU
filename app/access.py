"""Write authorization for the local, single-owner workspace."""
import hmac
import ipaddress
import os
import secrets
from urllib.parse import urlsplit

from fastapi import HTTPException, Request


OWNER_COOKIE = "vixisu_owner"


def owner_session(token):
    return hmac.digest(token.encode(), b"vixisu-local-owner", "sha256").hex()


def require_owner(request: Request):
    host = request.headers.get("host", "")
    origin = request.headers.get("origin")
    if origin:
        try:
            origin_url = urlsplit(origin)
        except ValueError as exc:
            raise HTTPException(403, "Workspace changes require the application origin.") from exc
        if origin_url.scheme not in {"http", "https"} or origin_url.netloc.lower() != host.lower():
            raise HTTPException(403, "Workspace changes require the application origin.")

    token = os.environ.get("VIXISU_OWNER_TOKEN")
    if token:
        scheme, _, value = request.headers.get("authorization", "").partition(" ")
        if scheme.lower() == "bearer" and secrets.compare_digest(value.encode(), token.encode()):
            return
        if secrets.compare_digest(request.cookies.get(OWNER_COOKIE, "").encode(), owner_session(token).encode()):
            return
        raise HTTPException(401, "Enter the workspace owner token.", headers={"WWW-Authenticate": "Bearer"})

    local = False
    try:
        local = ipaddress.ip_address(request.client.host).is_loopback if request.client else False
        hostname = urlsplit("//" + host).hostname or ""
        local_origin = hostname == "localhost" or ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        local_origin = False
    if not local or not local_origin:
        raise HTTPException(403, "Profile changes require local access or a configured workspace owner token.")
