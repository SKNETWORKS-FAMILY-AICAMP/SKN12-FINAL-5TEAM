from flask import Flask, render_template, Response, jsonify, request, redirect
import cv2
import mediapipe as mp
import numpy as np
import time
from collections import deque
import threading

app = Flask(__name__)

# MediaPipe 초기화
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    refine_landmarks=True,
    max_num_faces=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# 전역 변수
camera = None
gaze_data = []  
is_setting = False
setting_phase = 'top_left'  # 'top_left', 'bottom_left', 'top_right', 'bottom_right'
setting_start_time = 0

# 4포인트 시선 데이터
top_left_gaze_data = []
bottom_left_gaze_data = []
top_right_gaze_data = []
bottom_right_gaze_data = []

final_jitter_score = 0
calibration_completed = False

# 면접 관련 변수들
is_interview = False
interview_start_time = 0
interview_duration = 20
interview_gaze_data = []
interview_jitter_score = 0

# 허용 시선 범위 (4포인트 환경 설정에서 계산됨)
allowed_gaze_range = {
    'left_bound': None,
    'right_bound': None,
    'top_bound': None,
    'bottom_bound': None
}  

def get_gaze_point_3d(landmarks, w, h):
    """MediaPipe를 사용한 개별 동공 인식 및 3D 시선 포인트 계산"""
    # 동공의 3D 랜드마크 인덱스
    left_iris_3d = [468, 469, 470, 471, 472]   # 왼쪽 동공
    right_iris_3d = [473, 474, 475, 476, 477]  # 오른쪽 동공
    
    # 왼쪽 동공 3D 중심점
    left_iris_points = np.array([(landmarks[i].x * w, landmarks[i].y * h, landmarks[i].z) for i in left_iris_3d])
    left_center = np.mean(left_iris_points, axis=0)
    
    # 오른쪽 동공 3D 중심점
    right_iris_points = np.array([(landmarks[i].x * w, landmarks[i].y * h, landmarks[i].z) for i in right_iris_3d])
    right_center = np.mean(right_iris_points, axis=0)
    
    # 개별 동공 정보 반환 (양쪽 동공을 따로 추적)
    left_gaze_2d = ((left_center[0] - w/2) / (w/2), (left_center[1] - h/2) / (h/2))
    right_gaze_2d = ((right_center[0] - w/2) / (w/2), (right_center[1] - h/2) / (h/2))
    
    return left_center, right_center, left_gaze_2d, right_gaze_2d

def calculate_jitter_score(gaze_points):
    """시선 흔들림(jitter) 기반 점수 계산"""
    if len(gaze_points) < 10:
        return 0
    
    # 3D 포인트들의 표준편차 계산 (jitter)
    arr = np.array(gaze_points)
    
    # 각 축(x, y, z)별로 표준편차 계산 후 평균
    jitter_x = np.std(arr[:, 0])
    jitter_y = np.std(arr[:, 1])
    jitter_z = np.std(arr[:, 2]) if arr.shape[1] > 2 else 0
    
    # 전체 jitter는 x, y축의 평균 (z축은 덜 중요)
    jitter = (jitter_x + jitter_y) / 2
    
    print(f"Jitter 값: X={jitter_x:.4f}, Y={jitter_y:.4f}, Z={jitter_z:.4f}, 평균={jitter:.4f}")
    
    # 실제 동공 움직임에 맞는 jitter 범위로 조정
    # 픽셀 단위에서 일반적인 범위: 0~50 픽셀
    max_jitter = 50.0  # 매우 불안정한 시선
    min_jitter = 0.5   # 매우 안정적인 시선
    
    if jitter <= min_jitter:
        score = 100
    elif jitter >= max_jitter:
        score = 0
    else:
        # 선형 변환: jitter가 낮을수록 높은 점수
        score = int(100 * (1 - (jitter - min_jitter) / (max_jitter - min_jitter)))
    
    print(f"최종 Jitter 점수 계산: {jitter:.4f} -> {score}점")
    return max(0, min(100, score))

def calculate_allowed_gaze_range():
    """4포인트 환경 설정에서 수집한 시선 데이터를 기반으로 허용 시선 범위 계산"""
    global allowed_gaze_range
    
    if not all([top_left_gaze_data, bottom_left_gaze_data, top_right_gaze_data, bottom_right_gaze_data]):
        print("4포인트 시선 데이터가 부족합니다.")
        return
    
    # 모든 4포인트 데이터를 합쳐서 전체 범위 계산
    all_data = top_left_gaze_data + bottom_left_gaze_data + top_right_gaze_data + bottom_right_gaze_data
    all_data = np.array(all_data)
    
    # X축 (좌우) 범위
    min_x = np.min(all_data[:, 0])
    max_x = np.max(all_data[:, 0])
    x_range = max_x - min_x
    x_margin = x_range * 0.05
    
    # Y축 (상하) 범위  
    min_y = np.min(all_data[:, 1])
    max_y = np.max(all_data[:, 1])
    y_range = max_y - min_y
    y_margin = y_range * 0.05
    
    # 허용 범위 설정 (마진 적용)
    allowed_gaze_range['left_bound'] = min_x - x_margin    # 왼쪽으로 여유 공간
    allowed_gaze_range['right_bound'] = max_x + x_margin   # 오른쪽으로 여유 공간
    allowed_gaze_range['top_bound'] = min_y - y_margin     # 위쪽으로 여유 공간
    allowed_gaze_range['bottom_bound'] = max_y + y_margin  # 아래쪽으로 여유 공간
    
    print(f"4포인트 기반 허용 시선 범위 설정:")
    print(f"  X축 (L-R): {allowed_gaze_range['left_bound']:.2f} ~ {allowed_gaze_range['right_bound']:.2f}")
    print(f"  Y축 (T-B): {allowed_gaze_range['top_bound']:.2f} ~ {allowed_gaze_range['bottom_bound']:.2f}")

def calculate_gaze_compliance_score(interview_gaze_data):
    """
    면접 중 시선 범위 준수 기반 점수 계산 (면접 시간/프레임 수에 무관하게 비율 기반 점수)
    """
    if not interview_gaze_data or not all(allowed_gaze_range.values()):
        return 50  # 기본 점수

    total_points = len(interview_gaze_data)
    if total_points < 10:
        return 50

    in_range_count = 0
    total_violation_severity = 0  # 전체 이탈 정도 합산

    for gaze_point in interview_gaze_data:
        x, y = gaze_point[0], gaze_point[1]
        x_in_range = allowed_gaze_range['left_bound'] <= x <= allowed_gaze_range['right_bound']
        y_in_range = allowed_gaze_range['top_bound'] <= y <= allowed_gaze_range['bottom_bound']

        if x_in_range and y_in_range:
            in_range_count += 1
        else:
            x_violation = 0
            y_violation = 0
            if not x_in_range:
                if x < allowed_gaze_range['left_bound']:
                    x_violation = allowed_gaze_range['left_bound'] - x
                else:
                    x_violation = x - allowed_gaze_range['right_bound']
            if not y_in_range:
                if y < allowed_gaze_range['top_bound']:
                    y_violation = allowed_gaze_range['top_bound'] - y
                else:
                    y_violation = y - allowed_gaze_range['bottom_bound']
            violation_severity = np.sqrt(x_violation**2 + y_violation**2)
            total_violation_severity += min(violation_severity * 5, 5)  # 최대 5점 누적

    compliance_ratio = in_range_count / total_points              # 범위 내 비율
    violation_ratio = (total_points - in_range_count) / total_points  # 범위 밖 비율
    avg_violation_severity = total_violation_severity / max(1, total_points)  # **프레임 수로 나누어 평균화**

    # 기본 점수: 준수율 90% 이상 → 90점, 이하 구간별 차등 (이전과 동일)
    if compliance_ratio >= 0.9:
        base_score = 90 + int((compliance_ratio - 0.9) * 100)
    elif compliance_ratio >= 0.7:
        base_score = 70 + int((compliance_ratio - 0.7) * 100)
    elif compliance_ratio >= 0.5:
        base_score = 50 + int((compliance_ratio - 0.5) * 100)
    elif compliance_ratio >= 0.3:
        base_score = 30 + int((compliance_ratio - 0.3) * 100)
    else:
        base_score = int(compliance_ratio * 100)

    # **이탈 페널티: 전체 프레임 수로 평균화한 이탈 심각도를 기반으로**
    penalty_by_severity = min(int(avg_violation_severity), 10)  # 평균이 10점 이상일 땐 10점만 감점

    # 최종 점수 산출
    final_score = max(0, base_score - penalty_by_severity)

    print(f"시선 범위 준수 분석:")
    print(f"  전체 데이터: {total_points}개")
    print(f"  범위 내: {in_range_count}개 ({compliance_ratio:.1%})")
    print(f"  기본 점수: {base_score}점")
    print(f"  평균 이탈 정도: {avg_violation_severity:.2f}")
    print(f"  평균 이탈 기반 감점: {penalty_by_severity}점")
    print(f"  최종 점수: {final_score}점")

    return final_score

def generate_frames():
    """카메라 프레임 생성 - 환경 설정 및 면접 진행 모드 지원"""
    global camera, gaze_data, is_setting, setting_phase, setting_start_time
    global left_gaze_data, right_gaze_data, final_jitter_score, calibration_completed
    global is_interview, interview_start_time, interview_gaze_data, interview_jitter_score
    
    if camera is None:
        camera = cv2.VideoCapture(0)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    while True:
        success, frame = camera.read()
        if not success:
            break
        
        # 카메라 좌우반전 (수평 뒤집기)
        frame = cv2.flip(frame, 1)
        
        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 화면 중앙에 점선 원형 프레임 그리기 (가로 길이의 1/5 반지름)
        center_x = w // 2
        center_y = h // 2
        radius = w // 5
        
        # 점선 원 그리기
        for i in range(0, 360, 10):
            if i % 20 == 0:  # 점선 효과
                x1 = int(center_x + radius * np.cos(np.radians(i)))
                y1 = int(center_y + radius * np.sin(np.radians(i)))
                x2 = int(center_x + radius * np.cos(np.radians(i + 8)))
                y2 = int(center_y + radius * np.sin(np.radians(i + 8)))
                cv2.line(frame, (x1, y1), (x2, y2), (255, 255, 255), 2)
        
        # MediaPipe 얼굴 처리
        results = face_mesh.process(rgb_frame)
        
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                # 개별 동공 포인트 계산
                left_center, right_center, left_gaze_2d, right_gaze_2d = get_gaze_point_3d(face_landmarks.landmark, w, h)
                
                if is_setting:
                    # 4포인트 환경 설정 단계에 따라 데이터 수집
                    current_time = time.time()
                    elapsed = current_time - setting_start_time
                    
                    if setting_phase == 'top_left':
                        if elapsed >= 3:  # 3초 후부터 데이터 수집
                            # 양쪽 동공의 평균 위치를 데이터로 사용
                            avg_gaze = ((left_center + right_center) / 2)
                            top_left_gaze_data.append(avg_gaze)
                            # 시선 위치 표시 (좌상단 - 초록색)
                            # cv2.circle(frame, (int(avg_gaze[0]), int(avg_gaze[1])), 5, (0, 255, 0), -1)
                    elif setting_phase == 'bottom_left':
                        if elapsed >= 3:  # 3초 후부터 데이터 수집
                            avg_gaze = ((left_center + right_center) / 2)
                            bottom_left_gaze_data.append(avg_gaze)
                            # 시선 위치 표시 (좌하단 - 파란색)
                            # cv2.circle(frame, (int(avg_gaze[0]), int(avg_gaze[1])), 5, (255, 0, 0), -1)
                    elif setting_phase == 'top_right':
                        if elapsed >= 3:  # 3초 후부터 데이터 수집
                            avg_gaze = ((left_center + right_center) / 2)
                            top_right_gaze_data.append(avg_gaze)
                            # 시선 위치 표시 (우상단 - 빨간색)
                            # cv2.circle(frame, (int(avg_gaze[0]), int(avg_gaze[1])), 5, (0, 0, 255), -1)
                    elif setting_phase == 'bottom_right':
                        if elapsed >= 3:  # 3초 후부터 데이터 수집
                            avg_gaze = ((left_center + right_center) / 2)
                            bottom_right_gaze_data.append(avg_gaze)
                            # 시선 위치 표시 (우하단 - 노란색)
                            # cv2.circle(frame, (int(avg_gaze[0]), int(avg_gaze[1])), 5, (0, 255, 255), -1)
                
                # 면접 진행 중 데이터 수집
                elif is_interview:
                    current_time = time.time()
                    elapsed = current_time - interview_start_time

                    if elapsed < interview_duration:
                        # 면접 중 동공 움직임 데이터 수집
                        avg_gaze = ((left_center + right_center) / 2)

                        # ★ 동공 인식 정상일 때만 데이터 저장 (깜빡임 등은 제외)
                        if (
                            not np.any(np.isnan(avg_gaze)) and
                            not np.any(np.isinf(avg_gaze)) and
                            not np.allclose(avg_gaze, 0)
                        ):
                            interview_gaze_data.append(avg_gaze)

                            # 시선 범위 준수 확인 및 시각적 피드백
                            if all(allowed_gaze_range.values()):
                                x, y = avg_gaze[0], avg_gaze[1]
                                x_in_range = allowed_gaze_range['left_bound'] <= x <= allowed_gaze_range['right_bound']
                                y_in_range = allowed_gaze_range['top_bound'] <= y <= allowed_gaze_range['bottom_bound']

                                if x_in_range and y_in_range:
                                    # 범위 내: 초록색 테두리
                                    cv2.rectangle(frame, (10, 10), (w-10, h-10), (0, 255, 0), 3)
                                    status_text = "Good! Gaze within range"
                                    text_color = (0, 255, 0)
                                else:
                                    # 범위 밖: 빨간색 테두리 및 경고
                                    cv2.rectangle(frame, (10, 10), (w-10, h-10), (0, 0, 255), 3)
                                    status_text = "Warning! Gaze out of range!"
                                    text_color = (0, 0, 255)

                                    # 경고 메시지 깜빡임 효과
                                    if int(elapsed * 2) % 2:  # 0.5초마다 깜빡임
                                        cv2.putText(frame, status_text, (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, text_color, 2)
                        # else: 인식 실패(깜빡임 등) 프레임은 아무것도 저장하지 않음

                        # 남은 시간 표시
                        remaining = interview_duration - elapsed
                        cv2.putText(frame, f"면접 진행 중... 남은 시간: {int(remaining)}초", 
                                    (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                        # 진행률 바 표시
                        progress = elapsed / interview_duration
                        bar_width = int(w * 0.6)
                        bar_x = (w - bar_width) // 2
                        bar_y = h - 50
                        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + 20), (100, 100, 100), -1)
                        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + int(bar_width * progress), bar_y + 20), (0, 255, 0), -1)
                    else:
                        # 면접 완료
                        is_interview = False

                        # 새로운 점수 계산 방식: 시선 범위 준수 기반
                        interview_jitter_score = calculate_gaze_compliance_score(interview_gaze_data)

                        print(f"면접 완료! 수집된 데이터: {len(interview_gaze_data)}개")
                        print(f"면접 중 시선 범위 준수 점수: {interview_jitter_score}")

        # 4포인트 설정 단계별 메시지 표시
        if is_setting:
            current_time = time.time()
            elapsed = current_time - setting_start_time
            
            if setting_phase == 'top_left':
                if elapsed < 3:
                    message = "Look at TOP LEFT corner of screen"
                    countdown = 3 - int(elapsed)
                    cv2.putText(frame, message, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    cv2.putText(frame, f"Ready: {countdown}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                elif elapsed < 6:
                    message = "Keep looking at TOP LEFT!"
                    countdown = 6 - int(elapsed)
                    cv2.putText(frame, message, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    # 원형 진행바
                    progress = (elapsed - 3) / 3
                    cv2.ellipse(frame, (w-100, 100), (30, 30), 0, 0, int(360 * progress), (0, 255, 0), 3)
                    cv2.putText(frame, f"{countdown}", (w-110, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                else:
                    # 좌하단 단계로 전환
                    setting_phase = 'bottom_left'
                    setting_start_time = current_time
                    
            elif setting_phase == 'bottom_left':
                if elapsed < 3:
                    message = "Look at BOTTOM LEFT corner of screen"
                    countdown = 3 - int(elapsed)
                    cv2.putText(frame, message, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    cv2.putText(frame, f"Ready: {countdown}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                elif elapsed < 6:
                    message = "Keep looking at BOTTOM LEFT!"
                    countdown = 6 - int(elapsed)
                    cv2.putText(frame, message, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                    # 원형 진행바
                    progress = (elapsed - 3) / 3
                    cv2.ellipse(frame, (w-100, 100), (30, 30), 0, 0, int(360 * progress), (255, 0, 0), 3)
                    cv2.putText(frame, f"{countdown}", (w-110, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
                else:
                    # 우상단 단계로 전환
                    setting_phase = 'top_right'
                    setting_start_time = current_time
                    
            elif setting_phase == 'top_right':
                if elapsed < 3:
                    message = "Look at TOP RIGHT corner of screen"
                    countdown = 3 - int(elapsed)
                    cv2.putText(frame, message, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    cv2.putText(frame, f"Ready: {countdown}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                elif elapsed < 6:
                    message = "Keep looking at TOP RIGHT!"
                    countdown = 6 - int(elapsed)
                    cv2.putText(frame, message, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    # 원형 진행바
                    progress = (elapsed - 3) / 3
                    cv2.ellipse(frame, (w-100, 100), (30, 30), 0, 0, int(360 * progress), (0, 0, 255), 3)
                    cv2.putText(frame, f"{countdown}", (w-110, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                else:
                    # 우하단 단계로 전환
                    setting_phase = 'bottom_right'
                    setting_start_time = current_time
                    
            elif setting_phase == 'bottom_right':
                if elapsed < 3:
                    message = "Look at BOTTOM RIGHT corner of screen"
                    countdown = 3 - int(elapsed)
                    cv2.putText(frame, message, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    cv2.putText(frame, f"Ready: {countdown}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                elif elapsed < 6:
                    message = "Keep looking at BOTTOM RIGHT!"
                    countdown = 6 - int(elapsed)
                    cv2.putText(frame, message, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    # 원형 진행바
                    progress = (elapsed - 3) / 3
                    cv2.ellipse(frame, (w-100, 100), (30, 30), 0, 0, int(360 * progress), (0, 255, 255), 3)
                    cv2.putText(frame, f"{countdown}", (w-110, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                else:
                    # 4포인트 설정 완료
                    setting_phase = 'completed'
                    is_setting = False
                    calibration_completed = True
                    
                    # 4포인트 기반 허용 시선 범위 계산
                    calculate_allowed_gaze_range()
                    
                    # Jitter 점수 계산 (모든 4포인트 데이터 사용)
                    all_gaze_data = top_left_gaze_data + bottom_left_gaze_data + top_right_gaze_data + bottom_right_gaze_data
                    final_jitter_score = calculate_jitter_score(all_gaze_data)
                    print(f"4포인트 환경 설정 완료!")
                    print(f"  좌상단: {len(top_left_gaze_data)}개, 좌하단: {len(bottom_left_gaze_data)}개")
                    print(f"  우상단: {len(top_right_gaze_data)}개, 우하단: {len(bottom_right_gaze_data)}개")
                    print(f"환경 설정 Jitter 점수: {final_jitter_score}")
        
        # JPEG 인코딩
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    """첫 번째 페이지 - 환경 설정"""
    return render_template('setup.html')

@app.route('/interview')
def interview():
    """두 번째 페이지 - 면접 진행"""
    global calibration_completed
    if not calibration_completed:
        return redirect('/')  # 환경 설정이 완료되지 않았으면 첫 페이지로 리다이렉트
    return render_template('interview.html')

@app.route('/result')
def result():
    """세 번째 페이지 - 결과 (시각화 데이터 포함)"""
    global interview_jitter_score, interview_gaze_data
    global top_left_gaze_data, bottom_left_gaze_data, top_right_gaze_data, bottom_right_gaze_data
    
    # 면접 점수가 0이면 환경 설정 점수를 사용 (하위 호환성)
    display_score = interview_jitter_score if interview_jitter_score > 0 else final_jitter_score
    
    # 4포인트 보정 데이터 준비 (대표값 사용)
    calibration_points = []
    if top_left_gaze_data:
        avg_point = np.mean(top_left_gaze_data, axis=0)
        calibration_points.append({'x': float(avg_point[0]), 'y': float(avg_point[1]), 'label': '좌상단'})
    if bottom_left_gaze_data:
        avg_point = np.mean(bottom_left_gaze_data, axis=0)
        calibration_points.append({'x': float(avg_point[0]), 'y': float(avg_point[1]), 'label': '좌하단'})
    if top_right_gaze_data:
        avg_point = np.mean(top_right_gaze_data, axis=0)
        calibration_points.append({'x': float(avg_point[0]), 'y': float(avg_point[1]), 'label': '우상단'})
    if bottom_right_gaze_data:
        avg_point = np.mean(bottom_right_gaze_data, axis=0)
        calibration_points.append({'x': float(avg_point[0]), 'y': float(avg_point[1]), 'label': '우하단'})
    
    # 면접 시선 데이터 준비 (대표적인 20개 선택)
    interview_sample_points = []
    if interview_gaze_data and len(interview_gaze_data) > 0:
        # 전체 데이터에서 20개 균등 샘플링
        step = max(1, len(interview_gaze_data) // 20)
        for i in range(0, len(interview_gaze_data), step):
            if len(interview_sample_points) >= 20:
                break
            point = interview_gaze_data[i]
            interview_sample_points.append({'x': float(point[0]), 'y': float(point[1])})
    
    # 실제 허용 범위 좌표 전달 (축척 문제 해결)
    allowed_range = {
        'left_bound': float(allowed_gaze_range['left_bound']),
        'right_bound': float(allowed_gaze_range['right_bound']),
        'top_bound': float(allowed_gaze_range['top_bound']),
        'bottom_bound': float(allowed_gaze_range['bottom_bound'])
    } if all(allowed_gaze_range.values()) else None
    
    return render_template('result.html', 
                         jitter_score=display_score,
                         calibration_score=final_jitter_score,
                         interview_score=interview_jitter_score,
                         calibration_points=calibration_points,
                         interview_points=interview_sample_points,
                         allowed_range=allowed_range)

@app.route('/video_feed')
def video_feed():
    """비디오 스트림"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start_setting', methods=['POST'])
def start_setting():
    """4포인트 환경 설정 시작"""
    global is_setting, setting_phase, setting_start_time
    global top_left_gaze_data, bottom_left_gaze_data, top_right_gaze_data, bottom_right_gaze_data
    is_setting = True
    setting_phase = 'top_left'
    setting_start_time = time.time()
    # 4포인트 데이터 초기화
    top_left_gaze_data = []
    bottom_left_gaze_data = []
    top_right_gaze_data = []
    bottom_right_gaze_data = []
    return jsonify({'status': 'success'})

@app.route('/get_setting_status', methods=['GET'])
def get_setting_status():
    """설정 상태 확인"""
    return jsonify({
        'phase': setting_phase,
        'is_setting': is_setting,
        'calibration_completed': calibration_completed
    })

@app.route('/start_interview', methods=['POST'])
def start_interview():
    """면접 시작"""
    global is_interview, interview_start_time, interview_gaze_data, calibration_completed
    
    if not calibration_completed:
        return jsonify({'status': 'error', 'message': '환경 설정을 먼저 완료해주세요.'})
    
    is_interview = True
    interview_start_time = time.time()
    interview_gaze_data = []
    return jsonify({'status': 'success', 'message': '면접이 시작되었습니다.'})

@app.route('/get_interview_status', methods=['GET'])
def get_interview_status():
    """면접 상태 확인"""
    global is_interview, interview_start_time, interview_duration
    
    if not is_interview and interview_start_time > 0:
        # 면접 완료된 상태
        return jsonify({
            'is_interview': False,
            'completed': True,
            'remaining_time': 0,
            'data_count': len(interview_gaze_data)
        })
    elif is_interview:
        # 면접 진행 중
        elapsed = time.time() - interview_start_time
        remaining = max(0, interview_duration - elapsed)
        return jsonify({
            'is_interview': True,
            'completed': False,
            'remaining_time': int(remaining),
            'data_count': len(interview_gaze_data)
        })
    else:
        # 면접 시작 전
        return jsonify({
            'is_interview': False,
            'completed': False,
            'remaining_time': interview_duration,
            'data_count': 0
        })

if __name__ == '__main__':
    # 템플릿 디렉토리 생성
    import os
    os.makedirs('templates', exist_ok=True)
    
    print("면접 환경 설정 시스템을 시작합니다...")
    print("웹 브라우저에서 http://localhost:5000 으로 접속하세요.")
    app.run(debug=True, host='0.0.0.0', port=5000)
