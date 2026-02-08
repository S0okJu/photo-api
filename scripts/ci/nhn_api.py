"""
NHN Cloud Compute API 공통 모듈.
GitHub Actions 인스턴스 이미지 빌드에서 사용.
"""
import re
import sys
from typing import Optional

import requests

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def _is_uuid(value: str) -> bool:
    return bool(value and _UUID_RE.match(value.strip()))


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
    # NHN Cloud Compute API: /v2/{tenantId}/... 사용 (https://docs.nhncloud.com/ko/Compute/Instance/ko/public-api/)
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


def resolve_flavor_uuid(compute_url: str, headers: dict, flavor_ref: str) -> str:
    """flavor_ref가 UUID면 그대로, 아니면 이름으로 조회해 UUID 반환."""
    if _is_uuid(flavor_ref):
        return flavor_ref.strip()
    r = requests.get(f"{compute_url}/flavors/detail", headers=headers)
    r.raise_for_status()
    name_lower = flavor_ref.strip().lower()
    for f in r.json().get("flavors", []):
        if f.get("name", "").lower() == name_lower:
            return f["id"]
    for f in r.json().get("flavors", []):
        if name_lower in f.get("name", "").lower():
            return f["id"]
    print(f"❌ Flavor를 찾을 수 없음: {flavor_ref}", file=sys.stderr)
    sys.exit(1)


def resolve_image_uuid(region: str, token: str, image_ref: str) -> str:
    """image_ref가 UUID면 그대로, 아니면 이름으로 Public 이미지 조회해 UUID 반환.
    동일 이름이 여러 개면 created_at 최신 순으로 하나 선택."""
    if _is_uuid(image_ref):
        return image_ref.strip()
    region_lower = region.strip().lower()
    image_url = f"https://{region_lower}-api-image-infrastructure.nhncloudservice.com"
    headers = {"X-Auth-Token": token}
    r = requests.get(
        f"{image_url}/v2/images",
        headers=headers,
        params={"visibility": "public", "limit": 100},
    )
    r.raise_for_status()
    body = r.json()
    images = body.get("images") or []
    name_lower = image_ref.strip().lower()
    exact = [img for img in images if (img.get("name") or "").lower() == name_lower]
    if exact:
        candidates = exact
    else:
        candidates = [
            img for img in images
            if name_lower in (img.get("name") or "").lower()
        ]
    if not candidates:
        print(f"❌ 이미지를 찾을 수 없음: {image_ref}", file=sys.stderr)
        sys.exit(1)
    # 여러 개면 created_at 최신 순 (없으면 맨 뒤)
    candidates.sort(key=lambda img: img.get("created_at") or "", reverse=True)
    chosen = candidates[0]
    if len(candidates) > 1:
        print(f"ℹ️  이미지 이름 '{image_ref}' 후보 {len(candidates)}개 중 최신 사용: {chosen['id']} (created_at={chosen.get('created_at', '?')})")
    return chosen["id"]
