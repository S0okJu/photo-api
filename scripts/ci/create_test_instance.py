#!/usr/bin/env python3
"""
생성된 이미지로 테스트 인스턴스를 띄우고 ACTIVE 될 때까지 대기.
환경 변수: TOKEN, COMPUTE_URL, IMAGE_ID, NHN_NETWORK_ID, NHN_FLAVOR_ID,
  NHN_SECURITY_GROUP_ID(선택), KEYPAIR_NAME
GITHUB_OUTPUT에 test_instance_id, test_instance_ip 기록.
"""
import os
import sys
import time
from datetime import datetime

import requests

from nhn_api import get_headers, get_server_ip


def main() -> None:
    token = os.environ["TOKEN"]
    compute_url = os.environ["COMPUTE_URL"]
    image_id = os.environ["IMAGE_ID"]
    network_id = os.environ["NHN_NETWORK_ID"]
    flavor_id = os.environ["NHN_FLAVOR_ID"]
    keypair_name = os.environ["KEYPAIR_NAME"]
    security_group_id = os.environ.get("NHN_SECURITY_GROUP_ID", "")
    headers = get_headers(token)

    instance_name = f"photo-api-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    server_payload = {
        "server": {
            "name": instance_name,
            "flavorRef": flavor_id,
            "imageRef": image_id,
            "networks": [{"uuid": network_id}],
            "key_name": keypair_name,
            "metadata": {"purpose": "github-actions-test", "app": "photo-api"},
        }
    }
    if security_group_id:
        server_payload["server"]["security_groups"] = [
            {"name": security_group_id}
        ]

    r = requests.post(f"{compute_url}/servers", headers=headers, json=server_payload)
    r.raise_for_status()
    test_server_id = r.json()["server"]["id"]
    print(f"⏳ 테스트 인스턴스 ACTIVE 대기 중: {test_server_id}")

    max_wait = 600
    start = time.time()
    while time.time() - start < max_wait:
        detail = requests.get(
            f"{compute_url}/servers/{test_server_id}",
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
            print(f"✅ 테스트 인스턴스 ACTIVE: {ip_address}")
            out = os.environ.get("GITHUB_OUTPUT")
            if out:
                with open(out, "a") as f:
                    f.write(f"test_instance_id={test_server_id}\n")
                    f.write(f"test_instance_ip={ip_address}\n")
            return
        if status == "ERROR":
            print("❌ 테스트 인스턴스 생성 실패", file=sys.stderr)
            sys.exit(1)
        print(f"  상태: {status}, 대기 중...")
        time.sleep(10)

    print("❌ 타임아웃: 테스트 인스턴스가 시작되지 않았습니다", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
