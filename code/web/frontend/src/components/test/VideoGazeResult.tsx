import React, { useEffect, useRef } from 'react';
import { GazeResultProps } from './types';

const VideoGazeResult: React.FC<GazeResultProps> = ({ result, onRestart }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // 시선 궤적 시각화
  useEffect(() => {
    console.log('🎯 [DEBUG] VideoGazeResult rendering started');
    console.log('🎯 [DEBUG] result.allowed_range:', result.allowed_range);
    console.log('🎯 [DEBUG] result.gaze_points length:', result.gaze_points?.length);
    console.log('🎯 [DEBUG] result.calibration_points:', result.calibration_points);
    
    if (!canvasRef.current || !result.gaze_points || result.gaze_points.length === 0) {
      console.log('🎯 [DEBUG] Early return - missing canvas or gaze_points');
      return;
    }

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // 캔버스 크기 설정
    const canvasWidth = canvas.width;
    const canvasHeight = canvas.height;

    // 캔버스 초기화
    ctx.clearRect(0, 0, canvasWidth, canvasHeight);

    // 좌표 정규화를 위한 범위 계산 (시선 포인트 + 허용 범위)
    const xCoords = result.gaze_points.map(point => point[0]);
    const yCoords = result.gaze_points.map(point => point[1]);
    
    // 허용 범위도 좌표 범위 계산에 포함
    if (result.allowed_range) {
      xCoords.push(result.allowed_range.left_bound, result.allowed_range.right_bound);
      yCoords.push(result.allowed_range.top_bound, result.allowed_range.bottom_bound);
    }
    
    const minX = Math.min(...xCoords);
    const maxX = Math.max(...xCoords);
    const minY = Math.min(...yCoords);
    const maxY = Math.max(...yCoords);
    
    console.log('🎯 [DEBUG] Coordinate bounds:', { minX, maxX, minY, maxY });

    // 좌표 변환 함수 (여유 공간 확보)
    const margin = 60; // 더 큰 마진으로 변경
    const transformX = (x: number) => {
      const normalized = (x - minX) / (maxX - minX || 1);
      return normalized * (canvasWidth - margin * 2) + margin;
    };

    const transformY = (y: number) => {
      const normalized = (y - minY) / (maxY - minY || 1);
      return normalized * (canvasHeight - margin * 2) + margin;
    };

    // 배경 그리기
    ctx.fillStyle = '#f9fafb';
    ctx.fillRect(0, 0, canvasWidth, canvasHeight);

    // 허용 범위 시각화 (캘리브레이션 기반)
    if (result.allowed_range) {
      console.log('🎯 [DEBUG] Drawing allowed range');
      const allowedRange = result.allowed_range;
      console.log('🎯 [DEBUG] Raw allowed range:', allowedRange);
      
      // 허용 범위 좌표 변환
      const allowedLeft = transformX(allowedRange.left_bound);
      const allowedRight = transformX(allowedRange.right_bound);
      const allowedTop = transformY(allowedRange.top_bound);
      const allowedBottom = transformY(allowedRange.bottom_bound);
      
      console.log('🎯 [DEBUG] Transformed coordinates:', {
        left: allowedLeft, right: allowedRight, 
        top: allowedTop, bottom: allowedBottom,
        width: allowedRight - allowedLeft,
        height: allowedBottom - allowedTop
      });
      
      // 허용 범위 영역 (반투명 녹색)
      ctx.fillStyle = 'rgba(34, 197, 94, 0.3)'; // 더 진하게 변경
      ctx.fillRect(
        allowedLeft,
        allowedTop,
        allowedRight - allowedLeft,
        allowedBottom - allowedTop
      );
      console.log('🎯 [DEBUG] Filled allowed range rectangle');
      
      // 허용 범위 테두리 (녹색 점선)
      ctx.strokeStyle = '#22c55e';
      ctx.lineWidth = 3; // 더 두껍게
      ctx.setLineDash([8, 4]);
      ctx.strokeRect(
        allowedLeft,
        allowedTop,
        allowedRight - allowedLeft,
        allowedBottom - allowedTop
      );
      ctx.setLineDash([]);
      console.log('🎯 [DEBUG] Drew allowed range border');
      
      // 허용 범위 라벨
      ctx.fillStyle = '#16a34a';
      ctx.font = 'bold 14px -apple-system, BlinkMacSystemFont, sans-serif'; // 더 크고 굵게
      ctx.fillText('허용 범위', allowedLeft + 5, allowedTop - 5);
      console.log('🎯 [DEBUG] Drew allowed range label');
    } else {
      console.log('🎯 [DEBUG] No allowed_range found in result');
    }



    // 시선 포인트들 그리기 (범위 내/외 구분)
    console.log('🎯 [DEBUG] Drawing gaze points, total:', result.gaze_points.length);
    let inRangeCount = 0;
    let outOfRangeCount = 0;
    
    result.gaze_points.forEach((point, index) => {
      const x = transformX(point[0]);
      const y = transformY(point[1]);
      
      // 허용 범위 내에 있는지 확인
      let isInRange = true;
      if (result.allowed_range) {
        const allowedRange = result.allowed_range;
        isInRange = 
          point[0] >= allowedRange.left_bound && 
          point[0] <= allowedRange.right_bound &&
          point[1] >= allowedRange.top_bound && 
          point[1] <= allowedRange.bottom_bound;
        
        if (isInRange) {
          inRangeCount++;
        } else {
          outOfRangeCount++;
        }
      }
      
      // 색상 결정: 범위 내(파란색 계열) vs 범위 외(빨간색 계열)
      if (isInRange) {
        // 범위 내: 시간 순서에 따라 연파란색 → 진파란색
        const ratio = index / (result.gaze_points.length - 1);
        const intensity = Math.round(100 + 155 * ratio); // 100~255
        ctx.fillStyle = `rgb(59, 130, ${intensity})`;
      } else {
        // 범위 외: 빨간색 계열
        const ratio = index / (result.gaze_points.length - 1);
        const intensity = Math.round(150 + 105 * ratio); // 150~255
        ctx.fillStyle = `rgb(${intensity}, 68, 68)`;
      }
      
      ctx.beginPath();
      ctx.arc(x, y, isInRange ? 4 : 5, 0, 2 * Math.PI); // 범위 외는 약간 더 크게
      ctx.fill();
      
      // 테두리 색상도 다르게
      ctx.strokeStyle = isInRange ? '#ffffff' : '#fee2e2';
      ctx.lineWidth = 1;
      ctx.stroke();
    });
    
    console.log('🎯 [DEBUG] Gaze points drawn - In range:', inRangeCount, 'Out of range:', outOfRangeCount);

    // 시작점과 끝점 표시
    if (result.gaze_points.length > 0) {
      const startPoint = result.gaze_points[0];
      const endPoint = result.gaze_points[result.gaze_points.length - 1];
      
      // 시작점 (초록색)
      ctx.fillStyle = '#10b981';
      ctx.beginPath();
      ctx.arc(transformX(startPoint[0]), transformY(startPoint[1]), 6, 0, 2 * Math.PI);
      ctx.fill();
      
      // 끝점 (빨간색)
      ctx.fillStyle = '#ef4444';
      ctx.beginPath();
      ctx.arc(transformX(endPoint[0]), transformY(endPoint[1]), 6, 0, 2 * Math.PI);
      ctx.fill();
    }

    // 범례 추가
    ctx.fillStyle = '#374151';
    ctx.font = '12px -apple-system, BlinkMacSystemFont, sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText('🟢 시작점', 10, canvasHeight - 35);
    ctx.fillText('🔴 끝점', 10, canvasHeight - 20);
    ctx.fillText(`${result.gaze_points.length}개 포인트`, 100, canvasHeight - 35);
    
    // 허용 범위 범례
    if (result.allowed_range) {
      ctx.fillStyle = '#22c55e';
      ctx.fillText('🟩 허용 범위', 200, canvasHeight - 35);
      ctx.fillStyle = '#3b82f6';
      ctx.fillText('🔵 범위 내', 200, canvasHeight - 20);
      ctx.fillStyle = '#ef4444';
      ctx.fillText('🔴 범위 외', 300, canvasHeight - 35);
      
      // 통계 정보 추가
      ctx.fillStyle = '#374151';
      ctx.fillText(`${inRangeCount}개`, 300, canvasHeight - 20);
      ctx.fillText(`${outOfRangeCount}개`, 400, canvasHeight - 35);
    } else {
      ctx.fillStyle = '#ef4444';
      ctx.fillText('⚠️ 허용 범위 없음', 200, canvasHeight - 35);
    }

  }, [result]);

  // 점수에 따른 색상 및 메시지 결정
  const getScoreStyle = (score: number) => {
    if (score >= 85) {
      return {
        bgColor: 'bg-green-50 border-green-200',
        textColor: 'text-green-800',
        barColor: 'bg-green-500',
        emoji: '🌟'
      };
    } else if (score >= 70) {
      return {
        bgColor: 'bg-blue-50 border-blue-200',
        textColor: 'text-blue-800',
        barColor: 'bg-blue-500',
        emoji: '👍'
      };
    } else if (score >= 50) {
      return {
        bgColor: 'bg-yellow-50 border-yellow-200',
        textColor: 'text-yellow-800',
        barColor: 'bg-yellow-500',
        emoji: '⚠️'
      };
    } else {
      return {
        bgColor: 'bg-red-50 border-red-200',
        textColor: 'text-red-800',
        barColor: 'bg-red-500',
        emoji: '📈'
      };
    }
  };

  const scoreStyle = getScoreStyle(result.gaze_score);

  // 허용 범위 내/외 시선 포인트 통계 계산
  const getRangeStatistics = () => {
    if (!result.allowed_range || !result.gaze_points || result.gaze_points.length === 0) {
      return { inRangePoints: 0, outOfRangePoints: 0, totalPoints: 0, rangeCompliancePercent: 0 };
    }

    const allowedRange = result.allowed_range;
    let inRangePoints = 0;
    let outOfRangePoints = 0;

    result.gaze_points.forEach(point => {
      const isInRange = 
        point[0] >= allowedRange.left_bound && 
        point[0] <= allowedRange.right_bound &&
        point[1] >= allowedRange.top_bound && 
        point[1] <= allowedRange.bottom_bound;
      
      if (isInRange) {
        inRangePoints++;
      } else {
        outOfRangePoints++;
      }
    });

    return {
      inRangePoints,
      outOfRangePoints,
      totalPoints: result.gaze_points.length,
      rangeCompliancePercent: Math.round((inRangePoints / result.gaze_points.length) * 100)
    };
  };

  const rangeStats = getRangeStatistics();

  return (
    <div className="space-y-6">
      {/* 메인 점수 표시 */}
      <div className={`${scoreStyle.bgColor} border rounded-lg p-6 text-center`}>
        <div className="text-4xl mb-2">{scoreStyle.emoji}</div>
        <h3 className={`text-2xl font-bold ${scoreStyle.textColor} mb-2`}>
          시선 안정성 점수
        </h3>
        <div className="text-6xl font-bold text-gray-900 mb-4">
          {result.gaze_score}
        </div>
        
        {/* 점수 바 */}
        <div className="w-full bg-gray-200 rounded-full h-4 mb-4">
          <div 
            className={`${scoreStyle.barColor} h-4 rounded-full transition-all duration-1000 ease-out`}
            style={{ width: `${result.gaze_score}%` }}
          />
        </div>
        
        <div className={`${scoreStyle.textColor} font-medium text-lg`}>
          {result.stability_rating}
        </div>
      </div>

      {/* 상세 분석 결과 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 mb-3">📊 분석 통계</h4>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span>총 프레임:</span>
              <span className="font-bold">{result.total_frames.toLocaleString()}개</span>
            </div>
            <div className="flex justify-between">
              <span>분석된 프레임:</span>
              <span className="font-bold">{result.analyzed_frames.toLocaleString()}개</span>
            </div>
            <div className="flex justify-between">
              <span>범위 내 프레임:</span>
              <span className="font-bold">{result.in_range_frames.toLocaleString()}개</span>
            </div>
            <div className="flex justify-between">
              <span>범위 준수율:</span>
              <span className="font-bold">{Math.round(result.in_range_ratio * 100)}%</span>
            </div>
            {result.allowed_range && rangeStats.totalPoints > 0 && (
              <>
                <div className="flex justify-between">
                  <span>시선 포인트 (범위 내):</span>
                  <span className="font-bold text-blue-600">{rangeStats.inRangePoints.toLocaleString()}개</span>
                </div>
                <div className="flex justify-between">
                  <span>시선 포인트 (범위 외):</span>
                  <span className="font-bold text-red-600">{rangeStats.outOfRangePoints.toLocaleString()}개</span>
                </div>
              </>
            )}
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 mb-3">🎯 세부 점수</h4>
          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>시선 흔들림 점수:</span>
                <span className="font-bold">{result.jitter_score}점</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-purple-500 h-2 rounded-full"
                  style={{ width: `${result.jitter_score}%` }}
                />
              </div>
            </div>
            
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>범위 준수 점수:</span>
                <span className="font-bold">{Math.round(result.in_range_ratio * 100)}점</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-green-500 h-2 rounded-full"
                  style={{ width: `${result.in_range_ratio * 100}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 피드백 메시지 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="font-medium text-blue-900 mb-2">💬 AI 피드백</h4>
        <p className="text-blue-800">{result.feedback}</p>
      </div>

      {/* 시선 궤적 시각화 */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <h4 className="font-medium text-gray-900 mb-3">👁️ 시선 분포 분석</h4>
        <p className="text-sm text-gray-600 mb-4">
          면접 중 시선 포인트들의 분포를 시각화했습니다. 
          <span className="font-medium text-green-600"> 녹색 영역</span>은 캘리브레이션 기반 허용 범위이며, 
          <span className="font-medium text-blue-600"> 파란색 점</span>은 범위 내 시선, 
          <span className="font-medium text-red-600"> 빨간색 점</span>은 범위 외 시선을 나타냅니다.
        </p>
        <canvas
          ref={canvasRef}
          width={600}
          height={350}
          className="w-full border border-gray-300 rounded bg-gray-50"
        />
      </div>

      {/* 개선 팁 */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <h4 className="font-medium text-yellow-900 mb-2">💡 개선 팁</h4>
        <ul className="text-sm text-yellow-800 space-y-1">
          <li>• 면접관의 눈을 직접 바라보는 연습을 하세요</li>
          <li>• 긴장할 때 시선이 흔들리지 않도록 심호흡을 하세요</li>
          <li>• 카메라 렌즈를 면접관의 눈으로 생각하고 집중하세요</li>
          {result.allowed_range && rangeStats.rangeCompliancePercent < 70 && (
            <li className="font-medium">• 허용 범위 내에 시선을 유지하는 연습이 필요합니다 (현재 {rangeStats.rangeCompliancePercent}%)</li>
          )}
          {result.jitter_score < 60 && (
            <li className="font-medium">• 시선이 흔들리지 않도록 안정적인 자세를 유지하세요</li>
          )}
          <li>• 답변 중 잠깐의 시선 이동은 자연스럽지만, 너무 자주는 피하세요</li>
          <li>• 규칙적인 아이컨택 연습으로 자신감을 기르세요</li>
        </ul>
      </div>

      {/* 분석 정보 */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="font-medium text-gray-900 mb-3">ℹ️ 분석 정보</h4>
        <div className="grid grid-cols-2 gap-4 text-sm text-gray-600">
          <div>
            <span className="block font-medium">분석 시간:</span>
            <span>{result.analysis_duration.toFixed(1)}초</span>
          </div>
          <div>
            <span className="block font-medium">수집된 시선 포인트:</span>
            <span>{result.gaze_points.length}개</span>
          </div>
        </div>
      </div>

      {/* 액션 버튼 */}
      <div className="flex gap-4 justify-center">
        <button
          onClick={onRestart}
          className="bg-gradient-to-r from-blue-500 to-purple-500 text-white px-6 py-3 rounded-lg font-bold hover:shadow-lg hover:scale-105 transition-all"
        >
          🔄 다시 테스트하기
        </button>
        
        <button
          onClick={() => window.close()}
          className="bg-gray-500 text-white px-6 py-3 rounded-lg font-bold hover:bg-gray-600 transition-colors"
        >
          ✅ 완료
        </button>
      </div>
    </div>
  );
};

export default VideoGazeResult;