#!/usr/bin/env python3
"""
사용자 정의 예외 클래스들
일관된 에러 처리를 위한 예외 정의
"""

from typing import Optional, Dict, Any

class InterviewSystemError(Exception):
    """면접 시스템 기본 예외 클래스"""
    
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """예외 정보를 딕셔너리로 변환"""
        return {
            'error': self.message,
            'error_code': self.error_code,
            'details': self.details
        }

class DocumentProcessingError(InterviewSystemError):
    """문서 처리 관련 예외"""
    
    def __init__(self, message: str, file_type: str = None, file_size: int = None):
        super().__init__(message, 'DOCUMENT_PROCESSING_ERROR')
        self.details.update({
            'file_type': file_type,
            'file_size': file_size
        })

class UnsupportedFileFormatError(DocumentProcessingError):
    """지원하지 않는 파일 형식 예외"""
    
    def __init__(self, file_type: str, supported_formats: list):
        message = f"지원하지 않는 파일 형식입니다: {file_type}"
        super().__init__(message, file_type=file_type)
        self.details['supported_formats'] = supported_formats

class FileSizeExceededError(DocumentProcessingError):
    """파일 크기 초과 예외"""
    
    def __init__(self, file_size: int, max_size: int):
        message = f"파일 크기가 제한을 초과합니다: {file_size/1024/1024:.1f}MB (최대: {max_size/1024/1024:.1f}MB)"
        super().__init__(message, file_size=file_size)
        self.details['max_size'] = max_size

class TextExtractionError(DocumentProcessingError):
    """텍스트 추출 실패 예외"""
    
    def __init__(self, file_type: str, original_error: str = None):
        message = f"{file_type} 파일에서 텍스트를 추출할 수 없습니다"
        super().__init__(message, file_type=file_type)
        self.details['original_error'] = original_error

class SessionError(InterviewSystemError):
    """세션 관련 예외"""
    
    def __init__(self, message: str, session_id: str = None):
        super().__init__(message, 'SESSION_ERROR')
        self.details['session_id'] = session_id

class SessionNotFoundError(SessionError):
    """세션을 찾을 수 없는 예외"""
    
    def __init__(self, session_id: str):
        message = f"세션을 찾을 수 없습니다: {session_id}"
        super().__init__(message, session_id=session_id)

class SessionExpiredError(SessionError):
    """세션 만료 예외"""
    
    def __init__(self, session_id: str):
        message = f"세션이 만료되었습니다: {session_id}"
        super().__init__(message, session_id=session_id)

class InterviewError(InterviewSystemError):
    """면접 진행 관련 예외"""
    
    def __init__(self, message: str, session_id: str = None, question_number: int = None):
        super().__init__(message, 'INTERVIEW_ERROR')
        self.details.update({
            'session_id': session_id,
            'question_number': question_number
        })

class QuestionGenerationError(InterviewError):
    """질문 생성 실패 예외"""
    
    def __init__(self, question_type: str, company: str = None, attempt: int = None):
        message = f"질문 생성에 실패했습니다: {question_type}"
        super().__init__(message)
        self.details.update({
            'question_type': question_type,
            'company': company,
            'attempt': attempt
        })

class DuplicateQuestionError(InterviewError):
    """중복 질문 감지 예외"""
    
    def __init__(self, similarity_score: float, threshold: float):
        message = f"중복 질문이 감지되었습니다 (유사도: {similarity_score:.2f}, 임계값: {threshold:.2f})"
        super().__init__(message)
        self.details.update({
            'similarity_score': similarity_score,
            'threshold': threshold
        })

class EvaluationError(InterviewError):
    """평가 시스템 관련 예외"""
    
    def __init__(self, message: str, question_id: str = None, answer_content: str = None):
        super().__init__(message)
        self.details.update({
            'question_id': question_id,
            'answer_content': answer_content[:100] if answer_content else None
        })

class AIError(InterviewSystemError):
    """AI 관련 예외"""
    
    def __init__(self, message: str, model: str = None, prompt: str = None):
        super().__init__(message, 'AI_ERROR')
        self.details.update({
            'model': model,
            'prompt': prompt[:200] if prompt else None
        })

class APIError(AIError):
    """외부 API 호출 관련 예외"""
    
    def __init__(self, message: str, status_code: int = None, api_provider: str = None):
        super().__init__(message, api_provider)
        self.details.update({
            'status_code': status_code,
            'api_provider': api_provider
        })

class RateLimitError(APIError):
    """API 요청 제한 초과 예외"""
    
    def __init__(self, retry_after: int = None, api_provider: str = None):
        message = f"API 요청 제한을 초과했습니다"
        if retry_after:
            message += f" (재시도 가능: {retry_after}초 후)"
        super().__init__(message, status_code=429, api_provider=api_provider)
        self.details['retry_after'] = retry_after

class APITimeoutError(APIError):
    """API 응답 시간 초과 예외"""
    
    def __init__(self, timeout: int, api_provider: str = None):
        message = f"API 응답 시간이 초과되었습니다: {timeout}초"
        super().__init__(message, status_code=408, api_provider=api_provider)
        self.details['timeout'] = timeout

class TokenLimitError(AIError):
    """토큰 제한 초과 예외"""
    
    def __init__(self, used_tokens: int, max_tokens: int, model: str = None):
        message = f"토큰 제한을 초과했습니다: {used_tokens}/{max_tokens}"
        super().__init__(message, model=model)
        self.details.update({
            'used_tokens': used_tokens,
            'max_tokens': max_tokens
        })

class ConfigurationError(InterviewSystemError):
    """설정 관련 예외"""
    
    def __init__(self, message: str, config_key: str = None):
        super().__init__(message, 'CONFIGURATION_ERROR')
        self.details['config_key'] = config_key

class MissingAPIKeyError(ConfigurationError):
    """API 키 누락 예외"""
    
    def __init__(self, api_provider: str):
        message = f"{api_provider} API 키가 설정되지 않았습니다"
        super().__init__(message, config_key=f"{api_provider}_API_KEY")

class ValidationError(InterviewSystemError):
    """입력 검증 실패 예외"""
    
    def __init__(self, message: str, field: str = None, value: Any = None):
        super().__init__(message, 'VALIDATION_ERROR')
        self.details.update({
            'field': field,
            'value': str(value) if value is not None else None
        })

class CompanyNotSupportedError(ValidationError):
    """지원하지 않는 회사 예외"""
    
    def __init__(self, company: str, supported_companies: list):
        message = f"지원하지 않는 회사입니다: {company}"
        super().__init__(message, field='company', value=company)
        self.details['supported_companies'] = supported_companies

class InvalidInputError(ValidationError):
    """잘못된 입력 예외"""
    
    def __init__(self, field: str, value: Any, expected_type: str = None):
        message = f"잘못된 입력값입니다: {field} = {value}"
        if expected_type:
            message += f" (예상 타입: {expected_type})"
        super().__init__(message, field=field, value=value)

# 예외 처리 유틸리티 함수들
def handle_api_error(error: Exception) -> APIError:
    """API 에러를 적절한 예외로 변환"""
    error_msg = str(error)
    
    if 'rate_limit' in error_msg.lower() or 'too many requests' in error_msg.lower():
        return RateLimitError(api_provider='OpenAI')
    elif 'timeout' in error_msg.lower():
        return APITimeoutError(timeout=30, api_provider='OpenAI')
    elif 'token' in error_msg.lower() and 'limit' in error_msg.lower():
        return TokenLimitError(used_tokens=0, max_tokens=4000, model='gpt-4o-mini')
    else:
        return APIError(error_msg, api_provider='OpenAI')

def safe_execute(func, *args, **kwargs):
    """안전한 함수 실행 (예외 처리 포함)"""
    try:
        return func(*args, **kwargs)
    except InterviewSystemError:
        # 이미 우리가 정의한 예외는 그대로 전달
        raise
    except Exception as e:
        # 일반 예외는 InterviewSystemError로 변환
        raise InterviewSystemError(f"예상치 못한 오류가 발생했습니다: {str(e)}")

def format_error_response(error: InterviewSystemError) -> dict:
    """에러 응답을 표준 형식으로 포맷"""
    return {
        'success': False,
        'error': error.message,
        'error_code': error.error_code,
        'details': error.details,
        'timestamp': None  # 실제 사용 시 datetime.now().isoformat() 추가
    }