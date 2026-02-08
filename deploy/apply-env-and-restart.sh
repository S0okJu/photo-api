#!/usr/bin/env bash
#
# NHN Deploy User Command용: 환경 변수 반영 후 photo-api 서비스 재시작.
# - 인자로 .env 파일 경로 지정 가능.
# - DEPLOY_ENV_FILE 환경 변수로 파일 경로 지정 가능.
# - --stdin 이면 표준입력 내용을 .env로 저장.
# - 그 외에는 현재 셸 환경 변수 중 앱 관련만 골라 .env에 씀.
#
set -euo pipefail

SERVICE_NAME="${SERVICE_NAME:-photo-api}"
ENV_FILE="${ENV_FILE:-/opt/photo-api/.env}"
APP_HOME="$(dirname "$(dirname "$(realpath "$0")")")"

# 앱에서 참조하는 환경 변수 이름 (필요 시 추가)
ENV_KEYS=(
  ENVIRONMENT
  APP_NAME
  APP_VERSION
  DEBUG
  DATABASE_URL
  JWT_SECRET_KEY
  JWT_ALGORITHM
  ACCESS_TOKEN_EXPIRE_MINUTES
  INSTANCE_IP
  LOKI_URL
  PROMETHEUS_PUSHGATEWAY_URL
  PROMETHEUS_PUSH_INTERVAL_SECONDS
  NHN_STORAGE_IAM_USER
  NHN_STORAGE_IAM_PASSWORD
  NHN_STORAGE_PROJECT_ID
  NHN_STORAGE_TENANT_ID
  NHN_STORAGE_AUTH_URL
  NHN_STORAGE_CONTAINER
  NHN_STORAGE_URL
  NHN_S3_ACCESS_KEY
  NHN_S3_SECRET_KEY
  NHN_S3_ENDPOINT_URL
  NHN_S3_REGION_NAME
  NHN_S3_PRESIGNED_URL_EXPIRE_SECONDS
  NHN_CDN_DOMAIN
  NHN_CDN_APP_KEY
  NHN_CDN_AUTH_KEY
  NHN_OBJECT_STORAGE_ENDPOINT
  NHN_OBJECT_STORAGE_ACCESS_KEY
  NHN_OBJECT_STORAGE_SECRET_KEY
)

usage() {
  echo "Usage: $0 [PATH_TO_ENV_FILE]"
  echo "       DEPLOY_ENV_FILE=/path/to/.env $0"
  echo "       $0 --stdin   # read env content from stdin"
  exit 0
}

if [[ "${1:-}" == "--stdin" ]]; then
  sudo tee "$ENV_FILE" > /dev/null
  echo "Written .env from stdin to $ENV_FILE"
elif [[ -n "${DEPLOY_ENV_FILE:-}" ]] && [[ -f "${DEPLOY_ENV_FILE}" ]]; then
  sudo cp -f "$DEPLOY_ENV_FILE" "$ENV_FILE"
  echo "Copied $DEPLOY_ENV_FILE to $ENV_FILE"
elif [[ -n "${1:-}" ]] && [[ "$1" != "--help" && "$1" != "-h" ]]; then
  if [[ -f "$1" ]]; then
    sudo cp -f "$1" "$ENV_FILE"
    echo "Copied $1 to $ENV_FILE"
  else
    echo "File not found: $1" >&2
    exit 1
  fi
else
  # 현재 환경 변수에서 앱 관련만 골라 .env 형식으로 출력 (값 내 줄바꿈·따옴표 주의)
  tmp=$(mktemp)
  for key in "${ENV_KEYS[@]}"; do
    val="${!key:-}"
    if [[ -n "$val" ]]; then
      # 한 줄로 만들고, 쌍따옴표는 이스케이프
      val_escaped="${val//$'\n'/ }"
      val_escaped="${val_escaped//\"/\\\"}"
      echo "${key}=\"${val_escaped}\"" >> "$tmp"
    fi
  done
  if [[ -s "$tmp" ]]; then
    sudo cp -f "$tmp" "$ENV_FILE"
    echo "Written env vars to $ENV_FILE"
  else
    echo "No env vars to write. Set vars in NHN Deploy or pass a .env file." >&2
    rm -f "$tmp"
    exit 1
  fi
  rm -f "$tmp"
fi

sudo systemctl restart "$SERVICE_NAME"
echo "Restarted $SERVICE_NAME"
sudo systemctl status "$SERVICE_NAME" --no-pager || true
