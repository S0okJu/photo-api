# GitHub Actions Setup Guide

이 문서는 NHN Cloud 인스턴스 이미지 빌드 및 테스트를 위한 GitHub Actions 워크플로우 설정 방법을 설명합니다.

## 개요

`build-and-test-image.yml` 워크플로우는 다음 작업을 자동으로 수행합니다:

1. **빌드 인스턴스 생성**: NHN Cloud에 Ubuntu 인스턴스를 생성합니다
2. **오프라인 패키지 준비**: Python 패키지, Promtail 바이너리를 미리 다운로드합니다
3. **인스턴스 빌드**: 소스 코드와 패키지를 업로드하고 오프라인 환경에서 설치합니다
4. **이미지 생성**: 빌드된 인스턴스를 이미지로 스냅샷합니다
5. **테스트 인스턴스 실행**: 생성된 이미지로 새 인스턴스를 시작합니다
6. **동작 검증**: curl로 API health check 및 metrics 확인
7. **리소스 정리**: 테스트 후 생성된 리소스를 자동 삭제합니다

## 필수 GitHub Secrets 설정

GitHub 저장소 Settings > Secrets and variables > Actions에서 다음 secrets를 설정해야 합니다.

### 1. NHN Cloud 인증 정보

| Secret 이름 | 설명 | 예시 |
|-------------|------|------|
| `NHN_AUTH_URL` | NHN Cloud Identity API URL | `https://api-identity-infrastructure.nhncloudservice.com/v2.0` |
| `NHN_TENANT_ID` | 테넌트 ID (프로젝트 ID) | `a1b2c3d4e5f6...` |
| `NHN_USERNAME` | NHN Cloud API 사용자 이름 | `user@example.com` |
| `NHN_PASSWORD` | NHN Cloud API 비밀번호 | `your-password` |
| `NHN_REGION` | 리전 이름 | `KR1`, `KR2`, `JP1` 등 |

### 2. NHN Cloud 인스턴스 설정

| Secret 이름 | 설명 | 예시 | 확인 방법 |
|-------------|------|------|----------|
| `NHN_FLAVOR_ID` | 인스턴스 타입 ID | `u2.c2m4` | Console > Compute > Instance > 인스턴스 생성 시 표시 |
| `NHN_IMAGE_ID` | 베이스 이미지 ID (Ubuntu 22.04 권장) | `12345678-1234-...` | Console > Compute > Image에서 Ubuntu 이미지 ID 확인 |
| `NHN_NETWORK_ID` | VPC 네트워크 ID | `87654321-4321-...` | Console > Network > VPC > 서브넷 ID 확인 |
| `NHN_SECURITY_GROUP_ID` | 보안 그룹 이름 또는 ID | `default` 또는 UUID | Console > Network > Security Group |

**보안 그룹 설정 필수 사항:**
- 인바운드: SSH (22), HTTP (8000) 허용
- 아웃바운드: 모든 트래픽 허용 (패키지 다운로드용)

### 3. Observability 설정

| Secret 이름 | 설명 | 예시 |
|-------------|------|------|
| `LOKI_URL` | Loki 서버 URL (Promtail이 로그 전송) | `http://192.168.4.73:3100` |

**메트릭**: Photo API는 `/metrics` 엔드포인트로 Prometheus 메트릭을 노출합니다. Prometheus 서버에서 해당 인스턴스(예: `http://인스턴스IP:8000/metrics`)를 스크래핑 대상으로 등록하면 됩니다. InfluxDB/Telegraf는 사용하지 않습니다.

### 4. Photo API 애플리케이션 설정

| Secret 이름 | 설명 | 예시 |
|-------------|------|------|
| `DATABASE_URL` | 데이터베이스 연결 URL | `postgresql://user:pass@host:5432/db` |
| `JWT_SECRET_KEY` | JWT 토큰 서명 키 | `your-secret-key-min-32-chars` |
| `NHN_OBJECT_STORAGE_ENDPOINT` | NHN Object Storage endpoint | `https://kr1-api-object-storage.nhncloudservice.com` |
| `NHN_OBJECT_STORAGE_ACCESS_KEY` | Object Storage Access Key | `your-access-key` |
| `NHN_OBJECT_STORAGE_SECRET_KEY` | Object Storage Secret Key | `your-secret-key` |
| `NHN_CDN_DOMAIN` | NHN CDN 도메인 | `https://your-cdn.toastcdn.net` |
| `NHN_CDN_AUTH_KEY` | CDN 인증 키 | `your-cdn-auth-key` |

## NHN Cloud API 인증 정보 확인 방법

### 1. API 비밀번호 설정

1. NHN Cloud Console에 로그인
2. 우측 상단 사용자 아이콘 클릭
3. **API 보안 설정** 메뉴 선택
4. **API 비밀번호 설정**에서 비밀번호 생성

### 2. 테넌트 ID 확인

1. Console > 프로젝트 설정
2. **API Endpoint** 탭에서 Tenant ID 확인

### 3. 리전 확인

- **KR1**: 한국(판교) 리전
- **KR2**: 한국(평촌) 리전  
- **JP1**: 일본(도쿄) 리전

## 워크플로우 실행 방법

### 자동 실행

다음 이벤트에서 자동으로 실행됩니다:

- `main` 또는 `develop` 브랜치에 push
- `main` 또는 `develop` 브랜치로 Pull Request 생성

### 수동 실행

1. GitHub 저장소 > Actions 탭
2. "Build and Test NHN Cloud Instance Image" 워크플로우 선택
3. "Run workflow" 버튼 클릭
4. 옵션 설정:
   - **Skip resource cleanup**: 디버깅을 위해 리소스를 삭제하지 않으려면 `true` 선택

## 워크플로우 출력

### GitHub Actions Summary

워크플로우 실행 후 Summary 탭에서 다음 정보를 확인할 수 있습니다:

- 빌드 인스턴스 ID 및 IP
- 생성된 이미지 ID 및 이름
- 테스트 인스턴스 ID 및 IP
- Git commit SHA
- 빌드 시간

### 생성된 이미지 사용

워크플로우가 성공적으로 완료되면 NHN Cloud Console에서 생성된 이미지를 확인할 수 있습니다:

1. Console > Compute > Image
2. 이름 패턴: `photo-api-YYYYMMDD-HHMMSS`
3. 메타데이터:
   - `purpose`: `github-actions-build`
   - `app`: `photo-api`
   - `git_sha`: Git commit hash

이 이미지로 프로덕션 인스턴스를 생성할 수 있습니다.

## 트러블슈팅

### SSH 연결 실패

**증상**: "Wait for SSH to be ready" 단계에서 타임아웃

**해결 방법**:
1. 보안 그룹에 SSH (포트 22) 인바운드 규칙 확인
2. 네트워크 설정 확인 (공인 IP 할당 여부)
3. 인스턴스 플레이버가 충분한지 확인

### 패키지 설치 실패

**증상**: "Download dependencies offline" 단계에서 실패

**해결 방법**:
1. requirements.txt의 패키지 버전이 올바른지 확인
2. Promtail 버전이 존재하는지 확인
3. GitHub Actions runner에서 외부 네트워크 접근 가능한지 확인

### 이미지 생성 실패

**증상**: "Create instance image" 단계에서 타임아웃

**해결 방법**:
1. 인스턴스가 SHUTOFF 상태인지 확인
2. NHN Cloud 콘솔에서 이미지 생성 상태 확인
3. 디스크 용량이 충분한지 확인

### Health Check 실패

**증상**: "Test image with curl" 단계에서 실패

**해결 방법**:
1. 워크플로우 로그에서 디버깅 정보 확인
2. systemd 서비스 상태 확인:
   ```bash
   sudo systemctl status photo-api.service
   sudo systemctl status promtail.service
   ```
   메트릭은 앱의 `/metrics` 엔드포인트로 제공되며, Prometheus에서 스크래핑합니다.
3. 환경 변수 설정 확인: `/opt/photo-api/.env`
4. 수동 실행 시 `skip_cleanup: true`로 설정하여 인스턴스를 유지하고 직접 SSH 접속하여 디버깅

## 오프라인 환경 동작 원리

이 워크플로우는 인터넷 격리 환경에서 동작하도록 설계되었습니다:

1. **사전 다운로드**: 
   - GitHub Actions runner (인터넷 접근 가능)에서 모든 패키지를 미리 다운로드
   - Python wheels, Promtail 바이너리

2. **오프라인 설치**:
   - `pip install --no-index --find-links=/tmp/offline-packages`
   - 모든 의존성을 로컬 디렉토리에서 설치

3. **바이너리 포함**:
   - Promtail: GitHub releases에서 다운로드한 바이너리 (Loki 로그 전송)
   - Prometheus 메트릭: 앱 내장 `/metrics` 엔드포인트 (별도 에이전트 없음)
   - 런타임에 외부 네트워크 불필요

## 비용 절감 팁

1. **워크플로우 트리거 최적화**:
   - 개발 중에는 수동 실행 사용
   - PR/Push 자동 실행은 중요한 브랜치만 설정

2. **리소스 크기 조정**:
   - 빌드용으로는 작은 플레이버 사용 가능 (u2.c2m4)
   - 테스트는 최소 사양으로 충분

3. **정리 자동화**:
   - 워크플로우 종료 시 자동으로 리소스 삭제
   - 실패 시에도 cleanup 단계 실행 (`if: always()`)

## 보안 고려사항

1. **Secrets 관리**:
   - GitHub Secrets로 민감 정보 관리
   - 로그에 비밀번호나 토큰이 노출되지 않도록 주의

2. **SSH 키**:
   - 워크플로우 실행 시마다 새로운 임시 키 생성
   - 워크플로우 종료 시 키페어 자동 삭제

3. **네트워크 격리**:
   - 프로덕션 환경에서는 인터넷 차단된 VPC 사용
   - 이미지 빌드 시에만 임시로 인터넷 접근 허용

## 참고 자료

- [NHN Cloud API 가이드](https://docs.toast.com/ko/Compute/Instance/ko/api-guide/)
- [GitHub Actions 문서](https://docs.github.com/en/actions)
- [Promtail 문서](https://grafana.com/docs/loki/latest/send-data/promtail/)
- [Prometheus 문서](https://prometheus.io/docs/)
