// =======================================================================================
// React 훅 및 주요 라이브러리 임포트
// =======================================================================================
import { useState, useEffect, useRef, useCallback } from 'react';
import './App.css'; // 애플리케이션 전반에 사용될 스타일시트

// =======================================================================================
// 이미지 에셋 임포트
// =======================================================================================
import image1 from './assets/Whisk_4bfd948033.jpg';
import image2 from './assets/Whisk_59d5cab285.jpg';
import image3 from './assets/Whisk_998640dfbb.jpg';
import imageFromFile from './assets/image.png';

// =======================================================================================
// VideoPlayer 컴포넌트: 면접관 또는 AI의 비디오(또는 텍스트)를 표시합니다.
// =======================================================================================
const VideoPlayer = ({ isActive, onFinished, displayText, imageSrc }) => {
  useEffect(() => {
    let timer;
    if (isActive) {
      timer = setTimeout(() => {
        onFinished();
      }, 5000);
    }
    return () => clearTimeout(timer);
  }, [isActive, onFinished]);

  return (
    <div className={`box video-player ${isActive ? 'active' : ''}`}>
      {imageSrc ? (
        <img src={imageSrc} alt="Video player placeholder" className="video-placeholder-image" />
      ) : (
        <div className="video-placeholder">{displayText || "Video Player"}</div>
      )}
    </div>
  );
};

// =======================================================================================
// Webcam 컴포넌트 (최종 수정 버전): 오디오 스트림 복제 및 상태 관리 강화
// =======================================================================================
const Webcam = ({ isInterviewing, isAnswering, setTranscript, onEndAnswer }) => {
  const videoRef = useRef(null);
  const recognitionRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const audioContextRef = useRef(null);
  const silenceTimerRef = useRef(null);
  
  const [remainingTime, setRemainingTime] = useState(30);
  const [isListening, setIsListening] = useState(false);

  // Props를 ref에 담아 useEffect 의존성 문제를 회피합니다.
  const onEndAnswerRef = useRef(onEndAnswer);
  useEffect(() => { onEndAnswerRef.current = onEndAnswer; }, [onEndAnswer]);

  const setTranscriptRef = useRef(setTranscript);
  useEffect(() => { setTranscriptRef.current = setTranscript; }, [setTranscript]);

  // 미디어 장치 설정 및 해제
  useEffect(() => {
    const setupMedia = async () => {
      console.log("미디어 장치 설정을 시작합니다.");
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        mediaStreamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }

        // 1. 음성 인식을 위한 SpeechRecognition 설정
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRecognition) {
          const recognition = new SpeechRecognition();
          recognition.continuous = true;
          recognition.interimResults = true;
          recognition.lang = 'ko-KR';

          recognition.onstart = () => {
            console.log("음성 인식이 시작되었습니다.");
            setIsListening(true);
          };
          recognition.onend = () => {
            console.log("음성 인식이 종료되었습니다.");
            setIsListening(false);
          };
          recognition.onresult = (event) => {
            let finalTranscript = '';
            let interimTranscript = '';
            for (let i = event.resultIndex; i < event.results.length; ++i) {
              if (event.results[i].isFinal) {
                finalTranscript += event.results[i][0].transcript;
              } else {
                interimTranscript += event.results[i][0].transcript;
              }
            }
            setTranscriptRef.current(finalTranscript + interimTranscript);
          };
          recognition.onerror = (event) => {
            console.error("음성 인식 오류:", event.error);
            if (event.error !== 'no-speech') {
              setTranscriptRef.current(`오류: ${event.error}`);
            }
          };
          recognitionRef.current = recognition;
        } else {
          console.warn("이 브라우저에서는 음성 인식을 지원하지 않습니다.");
          setTranscriptRef.current("음성 인식을 지원하지 않습니다.");
        }

        // 2. 침묵 감지를 위한 AudioContext 설정 (스트림 복제 사용)
        const audioStreamForSilence = stream.clone();
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        if (audioContext.state === 'suspended') await audioContext.resume();
        const source = audioContext.createMediaStreamSource(audioStreamForSilence);
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        source.connect(analyser);
        audioContextRef.current = { audioContext, analyser, dataArray, stream: audioStreamForSilence };
        console.log("오디오 스트림을 복제하여 침묵 감지를 설정했습니다.");

      } catch (err) {
        console.error("미디어 장치 설정 중 오류 발생:", err);
        setTranscriptRef.current(`미디어 오류: ${err.name}`);
      }
    };

    const cleanupMedia = () => {
      console.log("미디어 장치를 정리합니다.");
      if (recognitionRef.current) {
        recognitionRef.current.stop();
        recognitionRef.current = null;
      }
      if (audioContextRef.current) {
        audioContextRef.current.stream.getTracks().forEach(track => track.stop());
        audioContextRef.current.audioContext.close();
        audioContextRef.current = null;
      }
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach(track => track.stop());
        mediaStreamRef.current = null;
      }
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
    };

    if (isInterviewing) {
      setupMedia();
    } else {
      cleanupMedia();
    }
    return cleanupMedia;
  }, [isInterviewing]);

  // 답변 상태(isAnswering)에 따라 기능 제어
  useEffect(() => {
    if (!isAnswering) {
      if (recognitionRef.current && isListening) {
        recognitionRef.current.stop();
      }
      return;
    }

    // 답변이 시작되면, 음성 인식이 실행 중이 아니라면 시작
    if (recognitionRef.current && !isListening) {
      setTranscriptRef.current('');
      recognitionRef.current.start();
    }

    // 답변 시간 타이머 설정
    setRemainingTime(30);
    const timerInterval = setInterval(() => {
      setRemainingTime(prev => {
        if (prev <= 1) {
          clearInterval(timerInterval);
          console.log("시간 초과로 답변을 종료합니다.");
          onEndAnswerRef.current();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    // 침묵 감지 로직
    let silenceFrameId;
    const SILENCE_THRESHOLD = 0.01;
    const SILENCE_DURATION = 3000;

    const detectSilence = () => {
      if (!audioContextRef.current) {
        silenceFrameId = requestAnimationFrame(detectSilence);
        return;
      }
      const { analyser, dataArray } = audioContextRef.current;
      analyser.getByteTimeDomainData(dataArray);
      const sumSquares = dataArray.reduce((acc, amp) => acc + ((amp / 128.0) - 1.0) ** 2, 0);
      const rms = Math.sqrt(sumSquares / dataArray.length);

      if (rms < SILENCE_THRESHOLD) {
        if (!silenceTimerRef.current) {
          silenceTimerRef.current = setTimeout(() => {
            console.log("침묵이 감지되어 답변을 종료합니다.");
            onEndAnswerRef.current();
          }, SILENCE_DURATION);
        }
      } else {
        clearTimeout(silenceTimerRef.current);
        silenceTimerRef.current = null;
      }
      silenceFrameId = requestAnimationFrame(detectSilence);
    };
    
    silenceFrameId = requestAnimationFrame(detectSilence);

    return () => {
      clearInterval(timerInterval);
      cancelAnimationFrame(silenceFrameId);
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    };
  }, [isAnswering, isListening]);

  return (
    <div className={`box webcam ${isAnswering ? 'active' : ''}`}>
      <video ref={videoRef} autoPlay playsInline muted className="webcam-video"></video>
      {isAnswering && <div className="microphone-indicator">마이크 활성화됨</div>}
      {isAnswering && <div className="remaining-time">남은 시간: {remainingTime}초</div>}
    </div>
  );
};

// =======================================================================================
// App 컴포넌트: 애플리케이션의 최상위 컴포넌트
// =======================================================================================
function App() {
  const [interviewState, setInterviewState] = useState('idle');
  const [activePlayerIndex, setActivePlayerIndex] = useState(null);
  const [activeTtsPlayerIndex, setActiveTtsPlayerIndex] = useState(null);
  const [aiAnswer, setAiAnswer] = useState('');
  const [transcript, setTranscript] = useState('');
  const [currentQuestion, setCurrentQuestion] = useState('');

  const speakTTS = (text, playerIndex, onEndCallback) => {
    if (!text) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'ko-KR';
    utterance.onstart = () => setActiveTtsPlayerIndex(playerIndex);
    utterance.onend = () => {
      setActiveTtsPlayerIndex(null);
      if (onEndCallback) onEndCallback();
    };
    utterance.onerror = (event) => {
      console.error("TTS 재생 오류:", event.error);
      setActiveTtsPlayerIndex(null);
      if (onEndCallback) onEndCallback();
    };
    window.speechSynthesis.speak(utterance);
  };

  const handleEndAnswer = useCallback(() => {
    if (interviewState !== 'answering') return;
    console.log("handleEndAnswer가 호출되었습니다. 사용자 답변을 서버에 저장합니다.");
    
    fetch('/api/save_log', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        who: '사용자',
        question: currentQuestion,
        answer: transcript
      })
    })
    .then(res => res.json())
    .then(data => console.log('사용자 로그 저장 성공:', data.message))
    .catch(err => console.error('사용자 로그 저장 중 오류 발생:', err));

    setInterviewState('feedbackAndChunsikIntro');
    setActivePlayerIndex(null);
  }, [interviewState, currentQuestion, transcript]);

  useEffect(() => {
    console.log("면접 상태가 다음으로 변경됨:", interviewState);
    if (['initialQuestion', 'feedbackAndChunsikIntro', 'subsequentQuestion'].includes(interviewState)) {
      window.speechSynthesis.cancel();

      if (interviewState === 'initialQuestion') {
        const question = '자기소개 해주세요.';
        setCurrentQuestion(question);
        setActivePlayerIndex(1);
        speakTTS(question, 1, () => {
          setInterviewState('answering');
          setActivePlayerIndex(null);
        });
      } else if (interviewState === 'feedbackAndChunsikIntro') {
        setAiAnswer('');
        const questionToChunsik = '춘식씨 자기소개 해주세요.';
        
        speakTTS(`잘 들었습니다. ${questionToChunsik}`, 1, () => {
          fetch('/api/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: questionToChunsik })
          })
          .then(res => res.json())
          .then(data => {
            const chunsikAnswer = data.answer;
            setAiAnswer(chunsikAnswer);

            fetch('/api/save_log', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ who: '춘식이', question: questionToChunsik, answer: chunsikAnswer })
            });

            speakTTS(chunsikAnswer, 3, () => {
              setInterviewState('subsequentQuestion');
            });
          })
          .catch(error => {
            console.error("AI 답변을 가져오는 중 오류 발생:", error);
            const fallbackAnswer = "죄송합니다. 지금은 답변하기 어렵습니다.";
            setAiAnswer(fallbackAnswer);
            speakTTS(fallbackAnswer, 3, () => setInterviewState('subsequentQuestion'));
          });
        });
      } else if (interviewState === 'subsequentQuestion') {
        const question = '다음 질문입니다. 답변해주세요.';
        setCurrentQuestion(question);
        setActivePlayerIndex(1);
        speakTTS(question, 1, () => {
          setInterviewState('answering');
          setActivePlayerIndex(null);
        });
      }
    }
  }, [interviewState]);

  const handleStart = () => {
    console.log("handleStart가 호출되었습니다.");
    fetch('/api/clear_log', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })
    .then(res => res.json())
    .then(data => console.log('로그 초기화 상태:', data.message))
    .catch(err => console.error('로그 초기화 중 오류 발생:', err));
    setInterviewState('initialQuestion');
  };

  const handleStop = () => {
    console.log("handleStop가 호출되었습니다.");
    setInterviewState('idle');
    setActivePlayerIndex(null);
    setActiveTtsPlayerIndex(null);
    setAiAnswer('');
    setTranscript('');
    setCurrentQuestion('');
    window.speechSynthesis.cancel();
  };

  return (
    <div className="app-container">
      <div className="row">
        <VideoPlayer isActive={activeTtsPlayerIndex === 0} onFinished={() => {}} imageSrc={image1} />
        <VideoPlayer 
          isActive={activePlayerIndex === 1 || activeTtsPlayerIndex === 1} 
          onFinished={() => {}} 
          displayText={currentQuestion}
          imageSrc={image2}
        />
        <VideoPlayer isActive={false} onFinished={() => {}} imageSrc={image3} />
      </div>
      <div className="row">
        {interviewState !== 'idle' ? (
          <Webcam 
            isInterviewing={interviewState !== 'idle'}
            isAnswering={interviewState === 'answering'}
            setTranscript={setTranscript}
            onEndAnswer={handleEndAnswer}
          />
        ) : (
          <div className="box webcam">
            <div className="video-placeholder">웹캠 비활성화됨</div>
          </div>
        )}
        <div className="button-container">
          <button onClick={handleStart} disabled={interviewState !== 'idle'}>면접 시작</button>
          <button onClick={handleEndAnswer} disabled={interviewState !== 'answering'}>대답 종료</button>
          <button onClick={handleStop}>면접 종료</button>
          <div className="transcript-display">사용자 답변: {transcript}</div>
        </div>
        <VideoPlayer 
          isActive={activeTtsPlayerIndex === 3} 
          onFinished={() => {}} 
          displayText={interviewState === 'feedbackAndChunsikIntro' ? (aiAnswer || '생각 중...') : 'Video Player'}
          imageSrc={imageFromFile}
        />
      </div>
    </div>
  );
}

export default App;