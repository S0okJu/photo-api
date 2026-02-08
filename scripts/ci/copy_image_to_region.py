#!/usr/bin/env python3
"""
KR1에서 생성한 이미지를 다른 리전(KR2 등) Image API로 복사.
인스턴스는 생성하지 않고, Image API만 사용 (GET image file from source → POST+PUT to target).
환경 변수: TOKEN, SOURCE_IMAGE_ID, SOURCE_IMAGE_NAME, TARGET_REGION
  SOURCE_IMAGE_BASE_URL 또는 COMPUTE_URL(KR1) 중 하나 필요.
  COMPUTE_URL이 있으면 kr1-api-instance → kr1-api-image 로 추론.
"""
import os
import sys
import time

import requests


def _image_base_from_compute_url(compute_url: str) -> str:
    """Compute URL에서 Image API 베이스 URL 추론 (NHN: kr1-api-instance → kr1-api-image)."""
    base = compute_url.split("/v2/")[0]
    return base.replace("-instance-", "-image-")


def _image_base_for_region(region: str) -> str:
    """리전 코드로 NHN Image API 베이스 URL 반환."""
    r = (region or "kr1").strip().lower()
    return f"https://{r}-api-image-infrastructure.nhncloudservice.com"


def main() -> None:
    token = os.environ.get("TOKEN", "").strip()
    source_base = os.environ.get("SOURCE_IMAGE_BASE_URL", "").strip()
    if not source_base:
        compute_url = os.environ.get("COMPUTE_URL", "").strip()
        if compute_url:
            source_base = _image_base_from_compute_url(compute_url)
    source_id = os.environ.get("SOURCE_IMAGE_ID", "").strip()
    source_name = os.environ.get("SOURCE_IMAGE_NAME", "").strip()
    target_region = os.environ.get("TARGET_REGION", "KR2").strip()

    if not all([token, source_base, source_id, source_name]):
        print("❌ TOKEN, (SOURCE_IMAGE_BASE_URL 또는 COMPUTE_URL), SOURCE_IMAGE_ID, SOURCE_IMAGE_NAME 필요", file=sys.stderr)
        sys.exit(1)

    target_base = _image_base_for_region(target_region)
    headers = {"X-Auth-Token": token}
    headers_json = {**headers, "Content-Type": "application/json"}

    # 1) 소스 이미지 상세 조회 (disk_format, container_format 등)
    r = requests.get(f"{source_base}/v2/images/{source_id}", headers=headers_json)
    if r.status_code == 404:
        print(f"❌ 소스 이미지를 찾을 수 없음: {source_id}", file=sys.stderr)
        sys.exit(1)
    r.raise_for_status()
    image_meta = r.json().get("image") or r.json()
    container_format = image_meta.get("container_format") or "bare"
    disk_format = image_meta.get("disk_format") or "raw"

    # 2) 소스 이미지 파일 스트림
    print(f"📥 소스 리전에서 이미지 다운로드 중: {source_id}")
    get_file = requests.get(
        f"{source_base}/v2/images/{source_id}/file",
        headers=headers,
        stream=True,
    )
    get_file.raise_for_status()

    # 3) 타겟 리전에 이미지 생성 (메타데이터만)
    create_body = {
        "name": source_name,
        "container_format": container_format,
        "disk_format": disk_format,
        "visibility": "private",
    }
    create = requests.post(
        f"{target_base}/v2/images",
        headers=headers_json,
        json=create_body,
    )
    if not create.ok:
        print(f"❌ 타겟 리전 이미지 생성 실패: {create.status_code}", file=sys.stderr)
        print(create.text[:500], file=sys.stderr)
        sys.exit(1)
    target_image = create.json().get("image") or create.json()
    target_id = target_image.get("id")
    if not target_id:
        print("❌ 타겟 이미지 ID를 찾을 수 없음", file=sys.stderr)
        sys.exit(1)
    print(f"📤 타겟 리전({target_region}) 이미지 생성됨: {target_id}, 업로드 중...")

    # 4) 타겟에 이미지 데이터 업로드 (PUT /file)
    put_headers = {"X-Auth-Token": token, "Content-Type": "application/octet-stream"}
    content_length = get_file.headers.get("Content-Length")
    if content_length:
        put_headers["Content-Length"] = content_length
    upload = requests.put(
        f"{target_base}/v2/images/{target_id}/file",
        headers=put_headers,
        data=get_file.raw,
        timeout=3600,
    )
    if not upload.ok:
        print(f"❌ 타겟 리전 이미지 업로드 실패: {upload.status_code}", file=sys.stderr)
        print(upload.text[:500], file=sys.stderr)
        sys.exit(1)

    # 5) active 될 때까지 대기
    max_wait = 900
    start = time.time()
    while time.time() - start < max_wait:
        r = requests.get(f"{target_base}/v2/images/{target_id}", headers=headers_json)
        r.raise_for_status()
        img = r.json().get("image") or r.json()
        status = img.get("status", "")
        if status == "active":
            print(f"✅ 이미지 복사 완료: {target_region} image_id={target_id}")
            out = os.environ.get("GITHUB_OUTPUT")
            if out:
                with open(out, "a") as f:
                    f.write(f"target_image_id={target_id}\n")
                    f.write(f"target_region={target_region}\n")
            return
        if status == "killed" or status == "deleted":
            print(f"❌ 이미지 상태: {status}", file=sys.stderr)
            sys.exit(1)
        print(f"  타겟 이미지 상태: {status}, 대기 중...")
        time.sleep(15)

    print("❌ 타겟 이미지 active 대기 타임아웃", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
