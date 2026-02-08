#!/usr/bin/env python3
"""
NHN Cloud에 빌드용 인스턴스를 생성하고 ACTIVE 될 때까지 대기.
환경 변수로 입력받고, GITHUB_OUTPUT에 결과를 쓴다.
"""
import os
import sys
import time
from datetime import datetime

import requests

from nhn_api import get_headers, get_server_ip, get_token_and_compute_url


def main() -> None:
    auth_url = os.environ["NHN_AUTH_URL"]
    tenant_id = os.environ["NHN_TENANT_ID"]
    username = os.environ["NHN_USERNAME"]
    password = os.environ["NHN_PASSWORD"]
    region = os.environ["NHN_REGION"]
    flavor_id = os.environ["NHN_FLAVOR_ID"]
    image_id = os.environ["NHN_IMAGE_ID"]
    network_id = os.environ["NHN_NETWORK_ID"]
    security_group_id = os.environ.get("NHN_SECURITY_GROUP_ID", "")
    ssh_public_key_path = os.environ["SSH_PUBLIC_KEY"]

    with open(ssh_public_key_path, "r") as f:
        ssh_public_key = f.read().strip()

    print("🔐 NHN Cloud 인증 중...")
    token, compute_url = get_token_and_compute_url(
        auth_url, tenant_id, username, password, region
    )
    headers = get_headers(token)

    keypair_name = f"github-actions-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    print(f"🔑 키페어 등록 중: {keypair_name}")
    keypair_payload = {
        "keypair": {"name": keypair_name, "public_key": ssh_public_key}
    }
    try:
        r = requests.post(
            f"{compute_url}/os-keypairs",
            headers=headers,
            json=keypair_payload,
        )
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"⚠️  키페어 등록 실패 (이미 존재할 수 있음): {e}")

    instance_name = f"photo-api-build-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    print(f"🚀 빌드 인스턴스 생성 중: {instance_name}")
    server_payload = {
        "server": {
            "name": instance_name,
            "flavorRef": flavor_id,
            "imageRef": image_id,
            "networks": [{"uuid": network_id}],
            "key_name": keypair_name,
            "metadata": {"purpose": "github-actions-build", "app": "photo-api"},
        }
    }
    if security_group_id:
        server_payload["server"]["security_groups"] = [
            {"name": security_group_id}
        ]

    r = requests.post(f"{compute_url}/servers", headers=headers, json=server_payload)
    if not r.ok:
        print(f"❌ 인스턴스 생성 API 응답: {r.status_code}", file=sys.stderr)
        print(r.text[:500] if r.text else "(empty body)", file=sys.stderr)
    r.raise_for_status()
    server_id = r.json()["server"]["id"]
    print(f"✅ 인스턴스 생성 요청 완료: {server_id}")

    print("⏳ 인스턴스가 ACTIVE 상태가 될 때까지 대기 중...")
    max_wait = 600
    start = time.time()
    while time.time() - start < max_wait:
        detail = requests.get(
            f"{compute_url}/servers/{server_id}",
            headers=headers,
        )
        detail.raise_for_status()
        server_data = detail.json()["server"]
        status = server_data["status"]

        if status == "ACTIVE":
            ip_address = get_server_ip(server_data)
            if not ip_address:
                print("❌ IP 주소를 찾을 수 없습니다", file=sys.stderr)
                sys.exit(1)
            print(f"✅ 인스턴스 ACTIVE: IP={ip_address}")
            out = os.environ.get("GITHUB_OUTPUT")
            if out:
                with open(out, "a") as f:
                    f.write(f"instance_id={server_id}\n")
                    f.write(f"instance_ip={ip_address}\n")
                    f.write(f"instance_name={instance_name}\n")
                    f.write(f"keypair_name={keypair_name}\n")
                    f.write(f"token={token}\n")
                    f.write(f"compute_url={compute_url}\n")
            return
        if status == "ERROR":
            print(f"❌ 인스턴스 생성 실패: {status}", file=sys.stderr)
            sys.exit(1)
        print(f"  상태: {status}, 대기 중...")
        time.sleep(10)

    print("❌ 타임아웃: 인스턴스가 ACTIVE 상태가 되지 않았습니다", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
