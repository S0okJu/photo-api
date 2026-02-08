# GitHub Actions Workflows

이 디렉토리는 photo-api의 CI/CD 워크플로우를 포함합니다.

## 워크플로우 목록

### 🏗️ build-and-test-image.yml

**목적**: NHN Cloud 인스턴스 이미지를 빌드하고 테스트합니다.

**주요 기능**:
- ✅ 인터넷 격리 환경을 위한 오프라인 패키지 준비
- ✅ Python 3.11 + FastAPI + 의존성 패키지 설치
- ✅ Promtail 바이너리 포함 (Loki 로깅)
- ✅ Prometheus 메트릭 (/metrics 엔드포인트, 앱 내장)
- ✅ systemd 서비스 자동 등록 및 활성화
- ✅ 이미지 생성 및 테스트 인스턴스 검증
- ✅ Health check 및 Prometheus metrics 확인
- ✅ 자동 리소스 정리

**트리거**:
- `main`, `develop` 브랜치 push
- `main`, `develop` 브랜치 대상 Pull Request
- 수동 실행 (workflow_dispatch)

**실행 시간**: 약 20-30분

**필수 Secrets**: 
- NHN Cloud 인증 (7개)
- Observability (1개: LOKI_URL)
- Application 설정 (7개)

자세한 설정 방법은 [GITHUB_ACTIONS_SETUP.md](../GITHUB_ACTIONS_SETUP.md)를 참조하세요.

## 빠른 시작

### 1. Secrets 설정

```bash
# GitHub CLI 사용 예시
gh secret set NHN_AUTH_URL -b"https://api-identity-infrastructure.nhncloudservice.com/v2.0"
gh secret set NHN_TENANT_ID -b"your-tenant-id"
gh secret set NHN_USERNAME -b"your-username"
gh secret set NHN_PASSWORD -b"your-password"
# ... (나머지 secrets)
```

또는 GitHub 웹 인터페이스에서:
1. Repository > Settings > Secrets and variables > Actions
2. "New repository secret" 클릭
3. 필요한 모든 secrets 추가

### 2. 워크플로우 수동 실행

```bash
# GitHub CLI 사용
gh workflow run build-and-test-image.yml

# 디버깅 모드 (리소스 정리 건너뛰기)
gh workflow run build-and-test-image.yml -f skip_cleanup=true
```

또는 GitHub 웹 인터페이스에서:
1. Actions 탭 이동
2. "Build and Test NHN Cloud Instance Image" 선택
3. "Run workflow" 버튼 클릭

### 3. 실행 결과 확인

워크플로우가 성공하면:

1. **Summary 탭**에서 생성된 이미지 정보 확인
2. **NHN Cloud Console**에서 이미지 확인:
   - Console > Compute > Image
   - 이름: `photo-api-YYYYMMDD-HHMMSS`

## 워크플로우 단계 설명

| 단계 | 설명 | 소요 시간 |
|------|------|----------|
| 1. Checkout code | 소스 코드 체크아웃 | ~10초 |
| 2. Create build instance | NHN Cloud에 빌드용 인스턴스 생성 | ~3분 |
| 3. Download dependencies | Python 패키지, Promtail 다운로드 | ~2분 |
| 4. Upload packages | 패키지를 빌드 인스턴스에 업로드 | ~1분 |
| 5. Build image | 오프라인 설치 및 systemd 설정 | ~5분 |
| 6. Create image snapshot | 인스턴스를 이미지로 스냅샷 | ~5분 |
| 7. Create test instance | 생성된 이미지로 테스트 인스턴스 시작 | ~3분 |
| 8. Test with curl | Health check 및 metrics 확인 | ~1분 |
| 9. Cleanup | 리소스 정리 (인스턴스, 키페어 삭제) | ~1분 |

## 생성된 이미지 구조

이미지에는 다음이 포함됩니다:

```
/opt/photo-api/
├── app/                    # FastAPI 애플리케이션 (Prometheus /metrics 내장)
├── venv/                   # Python 가상환경 (모든 의존성 포함)
├── requirements.txt
├── conf/
│   └── promtail-config.yaml
└── .env                    # 환경 변수

/opt/promtail/
├── promtail                # 바이너리
└── promtail-config.yaml

/var/log/photo-api/         # 로그 디렉토리
├── app.log
└── error.log

/etc/systemd/system/
├── photo-api.service       # 자동 시작 설정됨
└── promtail.service        # 자동 시작 설정됨
```

**메트릭**: Photo API는 `/metrics` 엔드포인트로 Prometheus 메트릭을 노출합니다. Prometheus 서버에서 해당 인스턴스를 스크래핑 대상으로 등록하면 됩니다. (Telegraf/InfluxDB 미사용)

## 트러블슈팅

### ❌ "SSH 연결 실패"

**해결**: 
- 보안 그룹에 SSH (22번 포트) 인바운드 규칙 추가
- 인스턴스에 공인 IP 할당 확인

### ❌ "Health check 실패"

**해결**:
1. 수동 실행 시 `skip_cleanup: true` 설정
2. 테스트 인스턴스에 SSH 접속:
   ```bash
   ssh ubuntu@<test_instance_ip>
   sudo systemctl status photo-api
   sudo journalctl -u photo-api -f
   ```
3. 환경 변수 확인: `cat /opt/photo-api/.env`

### ❌ "패키지 다운로드 실패"

**해결**:
- requirements.txt의 패키지 버전 확인
- Promtail 버전이 유효한지 확인

### 🔍 디버깅 모드

리소스를 유지하고 직접 접속하려면:

```bash
gh workflow run build-and-test-image.yml -f skip_cleanup=true
```

워크플로우 완료 후:
1. Actions 로그에서 인스턴스 IP 확인
2. SSH 키는 GitHub Actions runner에만 존재하므로 별도 키페어 등록 필요
3. NHN Cloud Console에서 키페어 추가 후 접속

## 환경별 설정

### 개발 환경

```yaml
# .github/workflows/build-and-test-image-dev.yml
on:
  push:
    branches:
      - develop
```

### 프로덕션 환경

```yaml
# .github/workflows/build-and-test-image-prod.yml
on:
  push:
    branches:
      - main
    tags:
      - 'v*'
```

환경별로 다른 secrets를 사용하려면 GitHub Environments를 활용하세요:
1. Settings > Environments
2. 환경 생성 (예: `development`, `production`)
3. 환경별 secrets 설정
4. 워크플로우에서 `environment` 지정

```yaml
jobs:
  build-and-test:
    environment: production
    steps:
      # ...
```

## 비용 최적화

### 워크플로우 실행 횟수 줄이기

```yaml
# 특정 파일 변경 시에만 실행
on:
  push:
    paths:
      - 'app/**'
      - 'requirements.txt'
      - 'scripts/**'
      - 'conf/**'
```

### 작은 플레이버 사용

빌드 및 테스트용으로는 최소 사양으로 충분합니다:
- `u2.c2m4`: vCPU 2개, RAM 4GB

### 병렬 실행 제한

```yaml
concurrency:
  group: build-image-${{ github.ref }}
  cancel-in-progress: true
```

## 참고 자료

- 📚 [전체 설정 가이드](../GITHUB_ACTIONS_SETUP.md)
- 🏗️ [빌드 스크립트 문서](../../scripts/README.md)
- 🌐 [NHN Cloud API 문서](https://docs.toast.com/ko/Compute/Instance/ko/api-guide/)
