#!/usr/bin/env python3
"""
로깅 설정 모듈
구조화된 로깅 시스템 제공
"""

import logging
import logging.handlers
import os
from datetime import datetime
from functools import wraps
from typing import Any, Callable
import json

from .config import config

class JSONFormatter(logging.Formatter):
    """JSON 형식의 로그 포맷터"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # 추가 정보가 있으면 포함
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'session_id'):
            log_entry['session_id'] = record.session_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'execution_time'):
            log_entry['execution_time'] = record.execution_time
        
        return json.dumps(log_entry, ensure_ascii=False)

class InterviewLogger:
    """면접 시스템 전용 로거"""
    
    def __init__(self, name: str = 'interview_system'):
        self.logger = logging.getLogger(name)
        self.setup_logger()
    
    def setup_logger(self):
        """로거 설정"""
        # 로그 레벨 설정
        log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
        self.logger.setLevel(log_level)
        
        # 기존 핸들러 제거
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(log_level)
        self.logger.addHandler(console_handler)
        
        # 파일 핸들러 (로테이션)
        if config.LOG_FILE:
            # 로그 디렉토리 생성
            log_dir = os.path.dirname(config.LOG_FILE)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            
            # 일반 로그 파일 (텍스트)
            file_handler = logging.handlers.RotatingFileHandler(
                config.LOG_FILE,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(log_level)
            self.logger.addHandler(file_handler)
            
            # JSON 로그 파일 (구조화된 데이터)
            json_log_file = config.LOG_FILE.replace('.log', '.json')
            json_handler = logging.handlers.RotatingFileHandler(
                json_log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            json_handler.setFormatter(JSONFormatter())
            json_handler.setLevel(log_level)
            self.logger.addHandler(json_handler)
    
    def info(self, message: str, **kwargs):
        """정보 레벨 로그"""
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """경고 레벨 로그"""
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """에러 레벨 로그"""
        self._log_with_context(logging.ERROR, message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """디버그 레벨 로그"""
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def _log_with_context(self, level: int, message: str, **kwargs):
        """컨텍스트 정보와 함께 로그 기록"""
        record = self.logger.makeRecord(
            self.logger.name, level, '', 0, message, (), None
        )
        
        # 추가 컨텍스트 정보 설정
        for key, value in kwargs.items():
            setattr(record, key, value)
        
        self.logger.handle(record)

class PerformanceLogger:
    """성능 모니터링 전용 로거"""
    
    def __init__(self):
        self.logger = logging.getLogger('performance')
        self.setup_logger()
    
    def setup_logger(self):
        """성능 로거 설정"""
        self.logger.setLevel(logging.INFO)
        
        # 성능 로그 파일
        if config.LOG_FILE:
            log_dir = os.path.dirname(config.LOG_FILE)
            if not log_dir:
                log_dir = 'logs'
        else:
            log_dir = 'logs'
            
        perf_log_file = os.path.join(log_dir, 'performance.log')
        
        # 디렉토리 생성
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        handler = logging.handlers.RotatingFileHandler(
            perf_log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        
        formatter = logging.Formatter(
            '%(asctime)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_request(self, endpoint: str, method: str, execution_time: float, 
                   status_code: int, user_id: str = None, session_id: str = None):
        """API 요청 성능 로그"""
        log_data = {
            'endpoint': endpoint,
            'method': method,
            'execution_time': execution_time,
            'status_code': status_code,
            'user_id': user_id,
            'session_id': session_id
        }
        
        self.logger.info(json.dumps(log_data, ensure_ascii=False))
    
    def log_ai_request(self, model: str, prompt_tokens: int, completion_tokens: int,
                      execution_time: float, success: bool, error: str = None):
        """AI API 요청 성능 로그"""
        log_data = {
            'type': 'ai_request',
            'model': model,
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': prompt_tokens + completion_tokens,
            'execution_time': execution_time,
            'success': success,
            'error': error
        }
        
        self.logger.info(json.dumps(log_data, ensure_ascii=False))

# 데코레이터 함수들
def log_function_call(logger: InterviewLogger = None):
    """함수 호출 로깅 데코레이터"""
    if logger is None:
        logger = InterviewLogger()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            function_name = f"{func.__module__}.{func.__name__}"
            
            logger.debug(f"함수 호출 시작: {function_name}", 
                        args=str(args)[:200], kwargs=str(kwargs)[:200])
            
            try:
                result = func(*args, **kwargs)
                execution_time = (datetime.now() - start_time).total_seconds()
                
                logger.debug(f"함수 호출 완료: {function_name}", 
                           execution_time=execution_time)
                
                return result
                
            except Exception as e:
                execution_time = (datetime.now() - start_time).total_seconds()
                
                logger.error(f"함수 호출 에러: {function_name} - {str(e)}", 
                           execution_time=execution_time, error=str(e))
                raise
        
        return wrapper
    return decorator

def log_api_performance(perf_logger: PerformanceLogger = None):
    """API 성능 로깅 데코레이터"""
    if perf_logger is None:
        perf_logger = PerformanceLogger()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            
            try:
                result = func(*args, **kwargs)
                execution_time = (datetime.now() - start_time).total_seconds()
                
                # Flask 요청 정보 추출 (가능한 경우)
                try:
                    from flask import request
                    endpoint = request.endpoint or func.__name__
                    method = request.method
                    
                    perf_logger.log_request(
                        endpoint=endpoint,
                        method=method,
                        execution_time=execution_time,
                        status_code=200  # 성공 가정
                    )
                except:
                    # Flask 컨텍스트가 없는 경우
                    perf_logger.log_request(
                        endpoint=func.__name__,
                        method='UNKNOWN',
                        execution_time=execution_time,
                        status_code=200
                    )
                
                return result
                
            except Exception as e:
                execution_time = (datetime.now() - start_time).total_seconds()
                
                try:
                    from flask import request
                    endpoint = request.endpoint or func.__name__
                    method = request.method
                    
                    perf_logger.log_request(
                        endpoint=endpoint,
                        method=method,
                        execution_time=execution_time,
                        status_code=500
                    )
                except:
                    perf_logger.log_request(
                        endpoint=func.__name__,
                        method='UNKNOWN',
                        execution_time=execution_time,
                        status_code=500
                    )
                
                raise
        
        return wrapper
    return decorator

# 전역 로거 인스턴스
interview_logger = InterviewLogger()
performance_logger = PerformanceLogger()

# 편의 함수들
def log_info(message: str, **kwargs):
    """정보 로그 편의 함수"""
    interview_logger.info(message, **kwargs)

def log_warning(message: str, **kwargs):
    """경고 로그 편의 함수"""
    interview_logger.warning(message, **kwargs)

def log_error(message: str, **kwargs):
    """에러 로그 편의 함수"""
    interview_logger.error(message, **kwargs)

def log_debug(message: str, **kwargs):
    """디버그 로그 편의 함수"""
    interview_logger.debug(message, **kwargs)

def log_performance(endpoint: str, method: str, execution_time: float, 
                   status_code: int, **kwargs):
    """성능 로그 편의 함수"""
    performance_logger.log_request(endpoint, method, execution_time, status_code, **kwargs)

def log_ai_performance(model: str, prompt_tokens: int, completion_tokens: int,
                      execution_time: float, success: bool, error: str = None):
    """AI 성능 로그 편의 함수"""
    performance_logger.log_ai_request(model, prompt_tokens, completion_tokens, 
                                     execution_time, success, error)