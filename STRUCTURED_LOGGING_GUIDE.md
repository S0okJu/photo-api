# 구조화된 로깅 가이드 (Structured Logging Guide)

이 문서는 Photo API의 구조화된 로깅 시스템 사용 방법을 설명합니다.

## 목차

- [개요](#개요)
- [로그 레벨 전략](#로그-레벨-전략)
- [로그 포맷](#로그-포맷)
- [사용 방법](#사용-방법)
- [예시](#예시)
- [모범 사례](#모범-사례)

## 개요

Photo API는 JSON 형식의 구조화된 로깅을 사용합니다. 이를 통해:
- 로그 집계 및 분석이 용이함
- 장애 추적 및 디버깅 효율성 향상
- Loki, Elasticsearch 등 로그 분석 도구와 통합 가능

## 로그 레벨 전략

각 레벨의 용도를 명확히 정의하여 효과적인 로그 관리를 지원합니다.

| **레벨** | **용도** | **예시** |
|:-------:|:---------|:---------|
| **ERROR** | 즉시 대응 필요한 오류 | DB 연결 실패, 외부 API 장애 |
| **WARN** | 잠재적 문제, 곧 이슈가 될 수 있음 | 재시도 발생, 임계치 근접 |
| **INFO** | 주요 비즈니스 이벤트 | 사용자 로그인, 사진 업로드 완료 |
| **DEBUG** | 개발/디버깅용 상세 정보 | 함수 진입/종료, 변수 값 |

## 로그 포맷

### 필수 필드

모든 로그에는 다음 필드가 포함됩니다:

| **필드명** | **타입** | **설명** | **예시** |
|:----------:|:--------:|:---------|:---------|
| `timestamp` | ISO 8601 | 이벤트 발생 시각 (UTC) | `2024-01-15T09:23:45.123Z` |
| `level` | string | 로그 심각도 | `ERROR`, `WARN`, `INFO`, `DEBUG` |
| `service` | string | 서비스/애플리케이션 이름 | `Photo API` |
| `message` | string | 사람이 읽을 수 있는 설명 | `User login successful` |

### 인프라 컨텍스트

서버 및 배포 환경 정보:

| **필드명** | **설명** | **예시** |
|:----------:|:---------|:---------|
| `host` | 서버 호스트명 또는 IP | `192.168.1.10` |
| `instance_id` | 클라우드 인스턴스 ID | `i-1234567890abcdef0` |
| `environment` | 환경 구분 | `prod`, `staging`, `dev` |
| `region` | 배포 리전 | `kr1`, `us-east-1` |
| `version` | 애플리케이션 버전 | `1.0.0` |

### 요청 컨텍스트

HTTP 요청 관련 정보:

| **필드명** | **설명** | **예시** |
|:----------:|:---------|:---------|
| `http_method` | HTTP 메서드 | `GET`, `POST` |
| `http_path` | 요청 경로 (개인정보 제외) | `/api/photos` |
| `http_status` | 응답 상태 코드 | `200`, `404`, `500` |
| `duration_ms` | 처리 소요 시간 (밀리초) | `123.45` |
| `client_ip` | 클라이언트 IP | `203.0.113.1` |
| `user_agent` | 브라우저/클라이언트 정보 | `Mozilla/5.0...` |
| `request_id` | 요청 추적 ID | `abc123def456` |

### 오류 로그 추가 필드

에러 발생 시 디버깅을 위한 추가 정보:

| **필드명** | **설명** | **예시** |
|:----------:|:---------|:---------|
| `error_type` | 예외 클래스명 또는 에러 코드 | `DatabaseError`, `TimeoutError` |
| `error_message` | 오류 메시지 | `Connection refused` |
| `stack_trace` | 스택 트레이스 | `Traceback (most recent call last):...` |
| `error_code` | 내부 정의 에러 코드 | `DB_001`, `API_502` |
| `retry_count` | 재시도 횟수 | `3` |
| `upstream_service` | 오류 발생한 외부 서비스명 | `nhn_storage`, `postgresql` |

## 사용 방법

### 1. 기본 로깅 함수

Photo API는 다음의 헬퍼 함수를 제공합니다:

```python
from app.utils.logger import log_info, log_warning, log_error, log_debug

# INFO 레벨 로깅 (주요 비즈니스 이벤트)
log_info("User registration completed", event="user_registration", user_id=12345)

# WARNING 레벨 로깅 (잠재적 문제)
log_warning("API rate limit approaching", current_rate=950, limit=1000)

# ERROR 레벨 로깅 (즉시 대응 필요)
log_error(
    "Database connection failed",
    error_type="DatabaseError",
    error_code="DB_001",
    upstream_service="postgresql",
    exc_info=True
)

# DEBUG 레벨 로깅 (개발/디버깅)
log_debug("Function entry", function="process_image", params={"width": 800})
```

### 2. 고급 로깅 (log_with_context)

모든 필드를 직접 제어하려면 `log_with_context`를 사용합니다:

```python
from app.utils.logger import log_with_context
import logging

log_with_context(
    logging.INFO,
    "Order completed successfully",
    # 요청 컨텍스트
    http_method="POST",
    http_path="/api/orders",
    http_status=201,
    duration_ms=456.78,
    client_ip="192.168.1.100",
    user_agent="Mozilla/5.0...",
    # 비즈니스 컨텍스트
    event="order_complete",
    order_id=67890,
    amount=150000,
)
```

### 3. 자동 요청 로깅

`LoggingMiddleware`가 모든 HTTP 요청에 대해 자동으로 로깅합니다:

- **5xx 에러**: ERROR 레벨로 로깅
- **4xx 에러**: WARNING 레벨로 로깅
- **느린 요청 (3초 이상)**: WARNING 레벨로 로깅
- **정상 요청**: 로깅하지 않음 (운영 노이즈 최소화)

필요시 모든 요청을 로깅하도록 설정 변경 가능합니다.

## 예시

### 예시 1: 사용자 로그인

```python
from app.utils.logger import log_info, log_warning

# 성공 케이스
log_info(
    "User login successful",
    event="user_login",
)

# 실패 케이스
log_warning(
    "Login failed - invalid credentials",
    event="user_login",
)
```

**출력 (JSON):**

```json
{
  "timestamp": "2024-01-15T09:23:45.123Z",
  "level": "INFO",
  "service": "Photo API",
  "message": "User login successful",
  "host": "192.168.1.10",
  "instance_id": "192.168.1.10",
  "environment": "production",
  "region": "kr1",
  "version": "1.0.0",
  "request_id": "abc123def456",
  "event": "user_login"
}
```

### 예시 2: 외부 API 오류 (재시도 포함)

```python
from app.utils.logger import log_error, log_warning

retry_count = 0
max_retries = 3

while retry_count < max_retries:
    try:
        # 외부 API 호출
        result = await external_api.call()
        break
    except Exception as e:
        retry_count += 1
        
        if retry_count >= max_retries:
            # 최종 실패 -> ERROR
            log_error(
                "External API call failed after retries",
                error_type=type(e).__name__,
                error_message=str(e),
                error_code="API_001",
                upstream_service="nhn_storage_iam",
                retry_count=retry_count,
                exc_info=True,
            )
            raise
        else:
            # 재시도 중 -> WARNING
            log_warning(
                "External API call failed, retrying",
                error_type=type(e).__name__,
                upstream_service="nhn_storage_iam",
                retry_count=retry_count,
            )
            await asyncio.sleep(1 ** retry_count)
```

**출력 (JSON):**

```json
{
  "timestamp": "2024-01-15T09:25:30.456Z",
  "level": "ERROR",
  "service": "Photo API",
  "message": "External API call failed after retries",
  "host": "192.168.1.10",
  "instance_id": "192.168.1.10",
  "environment": "production",
  "region": "kr1",
  "version": "1.0.0",
  "error_type": "HTTPStatusError",
  "error_message": "401 Unauthorized",
  "error_code": "API_001",
  "upstream_service": "nhn_storage_iam",
  "retry_count": 3,
  "stack_trace": "Traceback (most recent call last):..."
}
```

### 예시 3: 데이터베이스 연결 실패

```python
from app.utils.logger import log_error

try:
    await db.connect()
except Exception as e:
    log_error(
        "Database connection failed",
        error_type="DatabaseError",
        error_code="DB_001",
        upstream_service="postgresql",
        database_host="db.example.com",
        database_port=5432,
        exc_info=True,
    )
    raise
```

**출력 (JSON):**

```json
{
  "timestamp": "2024-01-15T09:30:12.789Z",
  "level": "ERROR",
  "service": "Photo API",
  "message": "Database connection failed",
  "host": "192.168.1.10",
  "instance_id": "192.168.1.10",
  "environment": "production",
  "region": "kr1",
  "version": "1.0.0",
  "error_type": "DatabaseError",
  "error_message": "could not connect to server",
  "error_code": "DB_001",
  "upstream_service": "postgresql",
  "stack_trace": "Traceback (most recent call last):...",
  "context": {
    "database_host": "db.example.com",
    "database_port": 5432
  }
}
```

### 예시 4: 성능 모니터링 (느린 쿼리)

```python
from app.utils.logger import log_warning
import time

start = time.perf_counter()
result = await db.execute(complex_query)
duration_ms = round((time.perf_counter() - start) * 1000, 2)

# 임계치 (예: 1초) 초과 시 로깅
if duration_ms > 1000:
    log_warning(
        "Slow query detected",
        event="database",
        duration_ms=duration_ms,
        query_type="SELECT",
        table="photos",
    )
```

**출력 (JSON):**

```json
{
  "timestamp": "2024-01-15T09:35:45.234Z",
  "level": "WARN",
  "service": "Photo API",
  "message": "Slow query detected",
  "host": "192.168.1.10",
  "instance_id": "192.168.1.10",
  "environment": "production",
  "region": "kr1",
  "version": "1.0.0",
  "duration_ms": 1523.45,
  "event": "database",
  "context": {
    "query_type": "SELECT",
    "table": "photos"
  }
}
```

## 모범 사례

### 1. 개인정보 제외

**절대 로깅하지 말 것:**
- 이메일, 사용자명, 비밀번호
- 인증 토큰, API 키
- 신용카드 번호, 주민등록번호

```python
# ❌ 나쁜 예
log_info("User logged in", email="user@example.com", password="secret123")

# ✅ 좋은 예
log_info("User logged in", user_id=12345)
```

### 2. 적절한 로그 레벨 사용

```python
# ✅ ERROR: 즉시 대응 필요
log_error("Payment gateway unavailable", upstream_service="payment_api")

# ✅ WARN: 잠재적 문제
log_warning("Cache miss rate high", miss_rate=0.75, threshold=0.5)

# ✅ INFO: 주요 비즈니스 이벤트
log_info("Order completed", event="order_complete", order_id=123)

# ✅ DEBUG: 디버깅 정보 (개발 환경에서만)
log_debug("Function entry", function="calculate_total")
```

### 3. 구조화된 데이터 활용

```python
# ❌ 나쁜 예: 문자열에 데이터 포함
log_info(f"Order {order_id} completed with amount {amount}")

# ✅ 좋은 예: 별도 필드로 구조화
log_info(
    "Order completed",
    event="order_complete",
    order_id=order_id,
    amount=amount,
)
```

### 4. 에러 컨텍스트 충분히 제공

```python
# ❌ 나쁜 예
log_error("API call failed")

# ✅ 좋은 예
log_error(
    "API call failed",
    error_type="HTTPStatusError",
    error_code="API_502",
    upstream_service="nhn_storage",
    retry_count=3,
    exc_info=True,
)
```

### 5. Request ID 활용

Request ID는 자동으로 생성되어 모든 로그에 포함됩니다. 이를 통해:
- 단일 요청의 모든 로그 추적 가능
- 장애 발생 시 사용자에게 Request ID 제공하여 문의 처리 용이

```python
from app.utils.logger import get_request_id

# 현재 요청의 Request ID 조회
request_id = get_request_id()
```

### 6. 이벤트 타입 활용

이벤트 타입을 사용하여 로그를 카테고리화하면 검색 및 분석이 용이합니다:

```python
# 인증 관련
log_info("...", event="user_login")
log_info("...", event="user_registration")

# 사진 관련
log_info("...", event="photo_upload")
log_info("...", event="photo_delete")

# 주문 관련
log_info("...", event="order_complete")
log_info("...", event="payment_success")
```

### 7. 운영 노이즈 최소화

정상 동작은 로깅하지 않아 로그 볼륨을 줄이고 중요한 이벤트에 집중합니다:

```python
# ✅ 정상 응답: 로깅하지 않음
# ✅ 에러 응답: 자동으로 로깅됨 (미들웨어)
# ✅ 주요 비즈니스 이벤트: 명시적으로 로깅
log_info("Photo upload completed", event="photo_upload", photo_id=123)
```

## 로그 조회 및 분석

### Loki 쿼리 예시

```logql
# 특정 Request ID의 모든 로그
{service="Photo API"} |= "abc123def456"

# ERROR 레벨 로그만 조회
{service="Photo API"} | json | level="ERROR"

# 특정 이벤트 타입 조회
{service="Photo API"} | json | event="user_login"

# 느린 요청 조회 (3초 이상)
{service="Photo API"} | json | duration_ms > 3000

# 특정 에러 코드 조회
{service="Photo API"} | json | error_code="DB_001"

# 외부 서비스별 에러 집계
sum by (upstream_service) (rate({service="Photo API"} | json | level="ERROR" [5m]))
```

## 참고

- 로그 파일 위치: `/var/log/photo-api/`
  - `app.log`: INFO 이상 모든 로그
  - `error.log`: ERROR 로그만
- 로그 포맷: NDJSON (Newline Delimited JSON)
- 로그 수집: Promtail → Loki
- 로그 보존 기간: 설정에 따라 다름 (기본 30일 권장)

## 문의

로깅 시스템 관련 문의사항이나 개선 제안은 개발팀에 문의하세요.
