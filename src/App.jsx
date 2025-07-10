import { useState, useEffect, useRef, useCallback } from 'react';
import './App.css';

// 동영상 플레이어 컴포넌트
const VideoPlayer = ({ isActive, onFinished, displayText }) => {
  // 비디오 재생 로직 제거
  useEffect(() => {
    let timer;
    if (isActive) {
      timer = setTimeout(() => {
        onFinished();
      }, 5000); // 5초 후 실행
    }
    return () => clearTimeout(timer);
  }, [isActive, onFinished]);

  return (
    <div className={`box video-player ${isActive ? 'active' : ''}`}>
      <div className="video-placeholder">{displayText || "Video Player"}</div>
    </div>
  );
};

// 웹캠 컴포넌트
const Webcam = ({ isActive, setTranscript, onEndAnswer }) => {
  const videoRef = useRef(null);
  const audioStreamRef = useRef(null);
  const recognitionRef = useRef(null);
  const [remainingTime, setRemainingTime] = useState(30); // 30초 제한

  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const dataArrayRef = useRef(null);
  const silenceTimerRef = useRef(null);
  const SILENCE_THRESHOLD = 0.03; // 침묵 임계값 (0.0 ~ 1.0)
  const SILENCE_DURATION = 3000; // 침묵 지속 시간 (3초)
  
  const isActiveRef = useRef(isActive);

  useEffect(() => {
    isActiveRef.current = isActive;
  }, [isActive]);

  // 타이머 로직
  useEffect(() => {
    let timerInterval;
    if (isActive) {
      setRemainingTime(30);
      timerInterval = setInterval(() => {
        setRemainingTime(prevTime => {
          if (prevTime <= 1) {
            clearInterval(timerInterval);
            onEndAnswer();
            return 0;
          }
          return prevTime - 1;
        });
      }, 1000);
    } else {
      clearInterval(timerInterval);
    }

    return () => clearInterval(timerInterval);
  }, [isActive, onEndAnswer]);

  useEffect(() => {
    const getMedia = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
        audioStreamRef.current = stream;

        audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
        const source = audioContextRef.current.createMediaStreamSource(stream);
        analyserRef.current = audioContextRef.current.createAnalyser();
        analyserRef.current.fftSize = 256;
        dataArrayRef.current = new Uint8Array(analyserRef.current.frequencyBinCount);
        source.connect(analyserRef.current);

        const detectSilence = () => {
          if (!analyserRef.current) return;
          analyserRef.current.getByteTimeDomainData(dataArrayRef.current);
          let sumSquares = 0;
          for (const amplitude of dataArrayRef.current) {
            sumSquares += (amplitude / 128.0 - 1.0) ** 2;
          }
          const rms = Math.sqrt(sumSquares / dataArrayRef.current.length);

          if (rms < SILENCE_THRESHOLD) {
            if (!silenceTimerRef.current) {
              silenceTimerRef.current = setTimeout(() => {
                if (isActiveRef.current) {
                  onEndAnswer();
                }
              }, SILENCE_DURATION);
            }
          } else {
            if (silenceTimerRef.current) {
              clearTimeout(silenceTimerRef.current);
              silenceTimerRef.current = null;
            }
          }
          requestAnimationFrame(detectSilence);
        };
        requestAnimationFrame(detectSilence);

      } catch (err) {
        console.error("미디어 접근 오류:", err);
      }
    };

    getMedia();

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = true;
      recognitionRef.current.interimResults = true;
      recognitionRef.current.lang = 'ko-KR';

      recognitionRef.current.onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          } else {
            interimTranscript += event.results[i][0].transcript;
          }
        }
        setTranscript(finalTranscript + interimTranscript);
      };

      recognitionRef.current.onerror = (event) => console.error("Speech recognition error:", event.error);

      recognitionRef.current.onend = (event) => {
        if (isActive) {
          recognitionRef.current.start(); // 자동 재시작 활성화
        }
      };
    } else {
      console.warn("Web Speech API not supported in this browser.");
    }

    return () => {
      if (audioStreamRef.current) {
        audioStreamRef.current.getTracks().forEach(track => track.stop());
      }
      if (videoRef.current) {
        videoRef.current.srcObject = null; // 비디오 요소 소스 해제
      }
      if (recognitionRef.current) recognitionRef.current.stop();
      if (audioContextRef.current) audioContextRef.current.close();
      clearTimeout(silenceTimerRef.current);
    };
  }, [setTranscript, onEndAnswer]);

  useEffect(() => {
    if (recognitionRef.current) {
      if (isActive) {
        setTranscript('');
        recognitionRef.current.start();
      } else {
        recognitionRef.current.stop();
      }
    }
  }, [isActive, setTranscript]);

  return (
    <div className={`box webcam ${isActive ? 'active' : ''}`}>
      <video ref={videoRef} autoPlay playsInline muted className="webcam-video"></video>
      {isActive && <div className="microphone-indicator">마이크 활성화됨</div>}
      {isActive && <div className="remaining-time">남은 시간: {remainingTime}초</div>}
    </div>
  );
};

// App 컴포넌트
function App() {
  const [interviewState, setInterviewState] = useState('idle');
  const [activePlayerIndex, setActivePlayerIndex] = useState(null);
  const [activeTtsPlayerIndex, setActiveTtsPlayerIndex] = useState(null);
  const [aiAnswer, setAiAnswer] = useState('');
  const [transcript, setTranscript] = useState(''); // 사용자의 답변 텍스트
  const [currentQuestion, setCurrentQuestion] = useState(''); // 현재 사용자가 답변 중인 질문
  const audioRef = useRef(new Audio('https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3'));

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
      console.error("TTS error:", event.error);
      setActiveTtsPlayerIndex(null);
      if (onEndCallback) onEndCallback();
    };
    window.speechSynthesis.speak(utterance);
  };

  const handleEndAnswer = useCallback(() => {
    if (interviewState !== 'answering') return;

    console.log("handleEndAnswer called. Saving user's answer.");
    
    // 사용자 답변 로그 저장
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
    .then(data => console.log('User log saved:', data.message))
    .catch(err => console.error('Error saving user log:', err));

    setInterviewState('feedbackAndChunsikIntro');
    setActivePlayerIndex(null);
  }, [interviewState, currentQuestion, transcript]);

  useEffect(() => {
    console.log("interviewState changed to:", interviewState);
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
            })
            .then(logRes => logRes.json())
            .then(logData => console.log('Chunsik log save status:', logData.message))
            .catch(logError => console.error('Error saving chunsik log:', logError));

            speakTTS(chunsikAnswer, 3, () => {
              setInterviewState('subsequentQuestion');
            });
          })
          .catch(error => {
            console.error("Error fetching AI answer:", error);
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
    console.log("handleStart called.");
    // 기존 로그 파일 초기화 요청
    fetch('/api/clear_log', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })
    .then(res => res.json())
    .then(data => console.log('Log clear status:', data.message))
    .catch(err => console.error('Error clearing log:', err));

    setInterviewState('initialQuestion');
  };
  const handleStop = () => {
    console.log("handleStop called.");
    setInterviewState('idle');
    setActivePlayerIndex(null);
    setActiveTtsPlayerIndex(null);
    setAiAnswer(''); // 춘식이 답변 초기화
    setTranscript(''); // 사용자 답변 초기화
    setCurrentQuestion(''); // 현재 질문 초기화
    window.speechSynthesis.cancel(); // 혹시 재생 중인 TTS가 있다면 중지
  };

  return (
    <div className="app-container">
      <div className="row">
        <VideoPlayer isActive={activeTtsPlayerIndex === 0} onFinished={() => {}} />
        <VideoPlayer 
          isActive={activePlayerIndex === 1 || activeTtsPlayerIndex === 1} 
          onFinished={() => {}} 
          displayText={currentQuestion}
        />
        <VideoPlayer isActive={false} onFinished={() => {}} />
      </div>
      <div className="row">
        {interviewState !== 'idle' && (
          <Webcam 
            isActive={interviewState === 'answering'} 
            setTranscript={setTranscript}
            onEndAnswer={handleEndAnswer}
          />
        )}
        {interviewState === 'idle' && (
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
        />
      </div>
    </div>
  );
}

export default App;