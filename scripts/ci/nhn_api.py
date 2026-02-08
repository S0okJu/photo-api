"""
NHN Cloud Compute API 공통 모듈.
GitHub Actions 인스턴스 이미지 빌드에서 사용.
"""
import os
import sys
from typing import Optional

import requests


def get_token_and_compute_url(
    auth_url: str,
    tenant_id: str,
    username: str,
    password: str,
    region: str,
) -> tuple[str, str]:
    """토큰 발급 후 Compute API URL 반환."""
    auth_payload = {
        "auth": {
            "tenantId": tenant_id,
            "passwordCredentials": {
                "username": username,
                "password": password,
            },
        }
    }
    auth_response = requests.post(f"{auth_url.rstrip('/')}/tokens", json=auth_payload)
    auth_response.raise_for_status()
    data = auth_response.json()
    token = data["access"]["token"]["id"]
    compute_url = None
    for service in data["access"].get("serviceCatalog", []):
        if service.get("type") == "compute":
            for endpoint in service.get("endpoints", []):
                if endpoint.get("region") == region:
                    compute_url = endpoint.get("publicURL")
                    break
            break
    if not compute_url:
        print(f"❌ Compute endpoint not found for region: {region}", file=sys.stderr)
        sys.exit(1)
    return token, compute_url


def get_headers(token: str) -> dict:
    return {
        "X-Auth-Token": token,
        "Content-Type": "application/json",
    }


def get_server_ip(server_data: dict) -> Optional[str]:
    """server 상세 응답에서 IPv4 주소 추출."""
    for addresses in server_data.get("addresses", {}).values():
        for addr in addresses:
            if addr.get("version") == 4:
                return addr.get("addr")
    return None
