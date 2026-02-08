#!/usr/bin/env python3
"""
구조화된 로깅 시스템 테스트 스크립트.

실행 방법:
    python test_logging.py
"""
import logging
import sys
import json
from io import StringIO

# 테스트를 위해 경로 추가
sys.path.insert(0, '.')

from app.utils.logger import (
    setup_logging,
    log_info,
    log_warning,
    log_error,
    log_debug,
    log_with_context,
    set_request_id,
)


def test_logging_system():
    """구조화된 로깅 시스템 테스트."""
    print("=" * 70)
    print("구조화된 로깅 시스템 테스트")
    print("=" * 70)
    print()
    
    # 로깅 시스템 초기화
    setup_logging()
    
    # Request ID 설정
    request_id = set_request_id()
    print(f"✓ Request ID 생성: {request_id}")
    print()
    
    # 1. INFO 레벨 테스트
    print("1. INFO 레벨 로깅 (주요 비즈니스 이벤트)")
    print("-" * 70)
    log_info(
        "User registration completed",
        event="user_registration",
        user_id=12345,
    )
    print("✓ log_info() 호출 완료")
    print()
    
    # 2. WARNING 레벨 테스트
    print("2. WARNING 레벨 로깅 (잠재적 문제)")
    print("-" * 70)
    log_warning(
        "API rate limit approaching",
        current_rate=950,
        limit=1000,
        retry_count=2,
    )
    print("✓ log_warning() 호출 완료")
    print()
    
    # 3. ERROR 레벨 테스트
    print("3. ERROR 레벨 로깅 (즉시 대응 필요)")
    print("-" * 70)
    try:
        # 의도적으로 예외 발생
        raise ValueError("Test error for logging demonstration")
    except Exception as e:
        log_error(
            "Database connection failed",
            error_type="DatabaseError",
            error_code="DB_001",
            upstream_service="postgresql",
            retry_count=3,
            exc_info=True,
        )
        print("✓ log_error() 호출 완료 (예외 정보 포함)")
    print()
    
    # 4. DEBUG 레벨 테스트
    print("4. DEBUG 레벨 로깅 (개발/디버깅)")
    print("-" * 70)
    log_debug(
        "Function entry",
        function="process_image",
        params={"width": 800, "height": 600},
    )
    print("✓ log_debug() 호출 완료")
    print()
    
    # 5. 고급 로깅 테스트 (log_with_context)
    print("5. 고급 로깅 (모든 컨텍스트 포함)")
    print("-" * 70)
    log_with_context(
        logging.INFO,
        "Order completed successfully",
        # 요청 컨텍스트
        http_method="POST",
        http_path="/api/orders",
        http_status=201,
        duration_ms=456.78,
        client_ip="192.168.1.100",
        user_agent="Mozilla/5.0 (Test Browser)",
        # 비즈니스 컨텍스트
        event="order_complete",
        order_id=67890,
        amount=150000,
    )
    print("✓ log_with_context() 호출 완료")
    print()
    
    # 6. 재시도 로직 시뮬레이션
    print("6. 재시도 로직 시뮬레이션")
    print("-" * 70)
    max_retries = 3
    for retry_count in range(1, max_retries + 1):
        if retry_count < max_retries:
            log_warning(
                "External API call failed, retrying",
                error_type="TimeoutError",
                upstream_service="nhn_storage_iam",
                retry_count=retry_count,
            )
            print(f"  ✓ 재시도 {retry_count}/{max_retries} - WARNING 로그")
        else:
            log_error(
                "External API call failed after retries",
                error_type="TimeoutError",
                error_code="API_001",
                upstream_service="nhn_storage_iam",
                retry_count=retry_count,
                exc_info=False,
            )
            print(f"  ✓ 최종 실패 - ERROR 로그")
    print()
    
    print("=" * 70)
    print("테스트 완료!")
    print("=" * 70)
    print()
    print("로그 파일 확인:")
    print("  - stdout: 콘솔 출력 (텍스트 포맷)")
    print("  - /var/log/photo-api/app.log: INFO 이상 (JSON 포맷)")
    print("  - /var/log/photo-api/error.log: ERROR만 (JSON 포맷)")
    print()
    print("참고: /var/log/photo-api 디렉토리가 없으면 파일 로깅이 비활성화됩니다.")
    print()


def test_json_format():
    """JSON 포맷 예시 출력."""
    print("=" * 70)
    print("JSON 로그 포맷 예시")
    print("=" * 70)
    print()
    
    example_log = {
        "timestamp": "2024-01-15T09:23:45.123Z",
        "level": "ERROR",
        "service": "Photo API",
        "message": "Database connection failed",
        "host": "192.168.1.10",
        "instance_id": "i-1234567890",
        "environment": "production",
        "region": "kr1",
        "version": "1.0.0",
        "request_id": "abc123def456",
        "http_method": "POST",
        "http_path": "/api/photos",
        "http_status": 500,
        "duration_ms": 1234.56,
        "client_ip": "203.0.113.1",
        "user_agent": "Mozilla/5.0...",
        "error_type": "DatabaseError",
        "error_message": "Connection refused",
        "error_code": "DB_001",
        "upstream_service": "postgresql",
        "retry_count": 3,
        "stack_trace": "Traceback (most recent call last):...",
        "event": "request",
    }
    
    print(json.dumps(example_log, indent=2, ensure_ascii=False))
    print()


if __name__ == "__main__":
    # JSON 포맷 예시 출력
    test_json_format()
    
    # 로깅 시스템 테스트
    test_logging_system()
