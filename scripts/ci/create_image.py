#!/usr/bin/env python3
"""
중지된 NHN Cloud 인스턴스로부터 이미지를 생성하고 active 될 때까지 대기.
환경 변수: TOKEN, COMPUTE_URL, INSTANCE_ID, GIT_SHA(선택)
GITHUB_OUTPUT에 image_id, image_name 기록.
"""
import os
import sys
import time
from datetime import datetime

import requests


def main() -> None:
    token = os.environ["TOKEN"]
    compute_url = os.environ["COMPUTE_URL"]
    server_id = os.environ["INSTANCE_ID"]
    git_sha = os.environ.get("GIT_SHA", "")
    headers = {
        "X-Auth-Token": token,
        "Content-Type": "application/json",
    }

    image_name = f"photo-api-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    create_image_payload = {
        "createImage": {
            "name": image_name,
            "metadata": {
                "purpose": "github-actions-build",
                "app": "photo-api",
                "git_sha": git_sha,
            },
        }
    }

    r = requests.post(
        f"{compute_url}/servers/{server_id}/action",
        headers=headers,
        json=create_image_payload,
    )
    r.raise_for_status()

    image_url = compute_url.replace("/compute/", "/image/")
    print(f"⏳ 이미지 생성 대기 중: {image_name}")
    max_wait = 900
    start = time.time()
    while time.time() - start < max_wait:
        r = requests.get(
            f"{image_url}/v2/images?name={image_name}",
            headers=headers,
        )
        r.raise_for_status()
        images = r.json().get("images", [])
        if images:
            image = images[0]
            image_id = image["id"]
            status = image["status"]
            if status == "active":
                print(f"✅ 이미지 생성 완료: {image_id}")
                out = os.environ.get("GITHUB_OUTPUT")
                if out:
                    with open(out, "a") as f:
                        f.write(f"image_id={image_id}\n")
                        f.write(f"image_name={image_name}\n")
                return
            print(f"  상태: {status}, 대기 중...")
        time.sleep(15)

    print("❌ 타임아웃: 이미지가 생성되지 않았습니다", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
