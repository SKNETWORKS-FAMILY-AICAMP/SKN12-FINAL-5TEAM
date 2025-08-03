/**
 * STT/TTS 기능을 위한 유틸리티 함수들
 * Web Speech API 기반 구현
 */

// 브라우저 호환성 체크
export const checkSpeechSupport = () => {
  const hasSTT = 'SpeechRecognition' in window || 'webkitSpeechRecognition' in window;
  const hasTTS = 'speechSynthesis' in window;
  return { hasSTT, hasTTS };
};

// STT 설정 타입
export interface STTConfig {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
}

// STT 이벤트 콜백 타입
export interface STTCallbacks {
  onResult: (transcript: string, isFinal: boolean) => void;
  onError: (error: string) => void;
  onStart: () => void;
  onEnd: () => void;
}

// TTS 설정 타입
export interface TTSConfig {
  lang: string;
  rate: number;
  pitch: number;
  volume: number;
  voice?: SpeechSynthesisVoice;
}

// STT 클래스
export class SpeechToText {
  private recognition: SpeechRecognition | null = null;
  private isListening = false;

  constructor(private config: STTConfig, private callbacks: STTCallbacks) {
    this.initializeRecognition();
  }

  private initializeRecognition() {
    const { hasSTT } = checkSpeechSupport();
    if (!hasSTT) {
      this.callbacks.onError('STT를 지원하지 않는 브라우저입니다. Chrome을 사용해주세요.');
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || (window as any).webkitSpeechRecognition;
    this.recognition = new SpeechRecognition();

    // 설정 적용
    this.recognition.lang = this.config.lang;
    this.recognition.continuous = this.config.continuous;
    this.recognition.interimResults = this.config.interimResults;
    this.recognition.maxAlternatives = this.config.maxAlternatives;

    // 이벤트 핸들러 설정
    this.recognition.onstart = () => {
      this.isListening = true;
      this.callbacks.onStart();
    };

    this.recognition.onend = () => {
      this.isListening = false;
      this.callbacks.onEnd();
    };

    this.recognition.onresult = (event: SpeechRecognitionEvent) => {
      let finalTranscript = '';
      let interimTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript;
        } else {
          interimTranscript += transcript;
        }
      }

      if (finalTranscript) {
        this.callbacks.onResult(finalTranscript, true);
      } else if (interimTranscript) {
        this.callbacks.onResult(interimTranscript, false);
      }
    };

    this.recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      this.callbacks.onError(`음성 인식 오류: ${event.error}`);
    };
  }

  start() {
    if (!this.recognition) {
      this.callbacks.onError('음성 인식이 초기화되지 않았습니다.');
      return;
    }

    if (this.isListening) {
      console.log('이미 음성 인식이 실행 중입니다.');
      return;
    }

    try {
      this.recognition.start();
    } catch (error) {
      this.callbacks.onError('음성 인식 시작 실패');
    }
  }

  stop() {
    if (this.recognition && this.isListening) {
      this.recognition.stop();
    }
  }

  abort() {
    if (this.recognition) {
      this.recognition.abort();
    }
  }

  getIsListening() {
    return this.isListening;
  }
}

// TTS 클래스
export class TextToSpeech {
  private synthesis: SpeechSynthesis;
  private currentUtterance: SpeechSynthesisUtterance | null = null;
  private voices: SpeechSynthesisVoice[] = [];

  constructor(private config: TTSConfig) {
    this.synthesis = window.speechSynthesis;
    this.loadVoices();

    // 음성 목록이 로드되면 다시 시도
    if (speechSynthesis.onvoiceschanged !== undefined) {
      speechSynthesis.onvoiceschanged = () => {
        this.loadVoices();
      };
    }
  }

  private loadVoices() {
    this.voices = this.synthesis.getVoices();
  }

  // 한국어 음성 목록 가져오기
  getKoreanVoices(): SpeechSynthesisVoice[] {
    return this.voices.filter(voice => voice.lang.startsWith('ko'));
  }

  // 특정 이름의 음성 찾기
  findVoiceByName(name: string): SpeechSynthesisVoice | undefined {
    return this.voices.find(voice => voice.name.includes(name));
  }

  // 면접관별 음성 설정
  getInterviewerVoice(type: 'hr' | 'tech' | 'collaboration'): SpeechSynthesisVoice | undefined {
    const koreanVoices = this.getKoreanVoices();
    
    if (koreanVoices.length === 0) return undefined;

    switch (type) {
      case 'hr':
        // 인사 면접관은 여성 음성 선호
        return koreanVoices.find(voice => voice.name.includes('Female')) || koreanVoices[0];
      case 'tech':
        // 기술 면접관은 남성 음성 선호
        return koreanVoices.find(voice => voice.name.includes('Male')) || koreanVoices[1] || koreanVoices[0];
      case 'collaboration':
        // 협업 면접관은 중성적인 음성
        return koreanVoices[2] || koreanVoices[0];
      default:
        return koreanVoices[0];
    }
  }

  speak(text: string, customConfig?: Partial<TTSConfig>): Promise<void> {
    return new Promise((resolve, reject) => {
      console.log('🔊 TTS speak 호출:', { 
        textLength: text.length, 
        text: text.substring(0, 100),
        hasCustomConfig: !!customConfig
      });
      
      if (!text.trim()) {
        console.log('⚠️ 빈 텍스트로 인해 TTS 건너뜀');
        resolve();
        return;
      }

      // 현재 재생 중인 음성 중지
      this.stop();

      const utterance = new SpeechSynthesisUtterance(text);
      const finalConfig = { ...this.config, ...customConfig };
      
      console.log('🎛️ TTS 설정:', finalConfig);

      // 설정 적용
      utterance.lang = finalConfig.lang;
      utterance.rate = finalConfig.rate;
      utterance.pitch = finalConfig.pitch;
      utterance.volume = finalConfig.volume;
      
      if (finalConfig.voice) {
        utterance.voice = finalConfig.voice;
      }

      // 이벤트 핸들러
      utterance.onstart = () => {
        console.log('✅ TTS 재생 시작됨');
      };
      
      utterance.onend = () => {
        console.log('✅ TTS 재생 완료됨');
        this.currentUtterance = null;
        resolve();
      };

      utterance.onerror = (event) => {
        console.error('❌ TTS 재생 오류:', event.error);
        this.currentUtterance = null;
        reject(new Error(`TTS 오류: ${event.error}`));
      };

      this.currentUtterance = utterance;
      console.log('🎤 speechSynthesis.speak() 호출');
      this.synthesis.speak(utterance);
    });
  }

  // 면접관 질문 읽기 (타입별 다른 음성)
  speakAsInterviewer(text: string, interviewerType: 'hr' | 'tech' | 'collaboration'): Promise<void> {
    console.log('🎯 speakAsInterviewer 호출:', { text: text.substring(0, 50), interviewerType });
    const voice = this.getInterviewerVoice(interviewerType);
    console.log('🎵 선택된 음성:', voice?.name || '기본 음성');
    return this.speak(text, { voice });
  }

  // AI 지원자 답변 읽기 (구별되는 음성으로)
  speakAsAICandidate(text: string): Promise<void> {
    console.log('🤖 speakAsAICandidate 호출:', { text: text.substring(0, 50) });
    const aiVoice = this.getAICandidateVoice();
    console.log('🎵 AI 지원자 음성:', aiVoice?.name || '기본 음성');
    return this.speak(text, { 
      voice: aiVoice,
      rate: 0.95,    // 약간 빠르게
      pitch: 0.95    // 약간 낮은 톤
    });
  }

  // AI 지원자 전용 음성 선택
  getAICandidateVoice(): SpeechSynthesisVoice | undefined {
    const koreanVoices = this.getKoreanVoices();
    
    if (koreanVoices.length === 0) return undefined;

    // AI 지원자는 중성적이고 젊은 느낌의 음성 선호
    const preferredVoice = koreanVoices.find(voice => 
      voice.name.includes('Seoyeon') || 
      voice.name.includes('Female') ||
      voice.name.includes('Young')
    );
    
    return preferredVoice || koreanVoices[0];
  }

  stop() {
    console.log('🔇 TTS stop() 호출 - 강제 정리 시작');
    
    // 현재 재생 중인 utterance가 있으면 중단
    if (this.currentUtterance) {
      console.log('🛑 현재 utterance 중단');
      this.currentUtterance.onend = null; // 이벤트 핸들러 제거
      this.currentUtterance.onerror = null;
      this.currentUtterance = null;
    }
    
    // speechSynthesis 전체 중단
    if (this.synthesis.speaking || this.synthesis.pending) {
      console.log('🔇 speechSynthesis.cancel() 호출');
      this.synthesis.cancel();
    }
    
    // 추가적인 강제 정리 (브라우저별 호환성)
    try {
      // Chrome, Edge 등에서 때때로 필요한 추가 정리
      if (this.synthesis.paused) {
        this.synthesis.resume();
        this.synthesis.cancel();
      }
    } catch (error) {
      console.warn('⚠️ TTS 추가 정리 중 오류 (무시 가능):', error);
    }
  }

  // 페이지 새로고침/닫기 시 강제 정리용 메서드
  forceStop() {
    console.log('💥 TTS forceStop() 호출 - 모든 음성 강제 중단');
    
    this.stop();
    
    // 전역 speechSynthesis도 강제 정리
    try {
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
        // 일부 브라우저에서는 여러 번 호출이 필요할 수 있음
        setTimeout(() => {
          if (window.speechSynthesis.speaking) {
            window.speechSynthesis.cancel();
          }
        }, 10);
      }
    } catch (error) {
      console.warn('⚠️ 전역 speechSynthesis 정리 실패 (무시 가능):', error);
    }
  }

  pause() {
    if (this.synthesis.speaking) {
      this.synthesis.pause();
    }
  }

  resume() {
    if (this.synthesis.paused) {
      this.synthesis.resume();
    }
  }

  isSpeaking(): boolean {
    return this.synthesis.speaking;
  }

  isPaused(): boolean {
    return this.synthesis.paused;
  }
}

// 기본 설정
export const DEFAULT_STT_CONFIG: STTConfig = {
  lang: 'ko-KR',
  continuous: true,
  interimResults: true,
  maxAlternatives: 1,
};

export const DEFAULT_TTS_CONFIG: TTSConfig = {
  lang: 'ko-KR',
  rate: 0.9,
  pitch: 1.0,
  volume: 1.0,
};

// 면접관 타입별 TTS 설정
export const INTERVIEWER_TTS_CONFIGS: Record<string, Partial<TTSConfig>> = {
  hr: { rate: 0.85, pitch: 1.1 }, // 인사: 약간 높은 톤, 천천히
  tech: { rate: 0.9, pitch: 0.9 }, // 기술: 약간 낮은 톤, 보통 속도
  collaboration: { rate: 0.95, pitch: 1.0 }, // 협업: 보통 톤, 약간 빠르게
};

// 편의 함수들
export const createSTT = (callbacks: STTCallbacks, config?: Partial<STTConfig>) => {
  const finalConfig = { ...DEFAULT_STT_CONFIG, ...config };
  return new SpeechToText(finalConfig, callbacks);
};

export const createTTS = (config?: Partial<TTSConfig>) => {
  const finalConfig = { ...DEFAULT_TTS_CONFIG, ...config };
  return new TextToSpeech(finalConfig);
};

// 질문 카테고리에 따른 면접관 타입 매핑
export function mapQuestionCategoryToInterviewer(category: any): 'hr' | 'tech' | 'collaboration' {
  let catStr = "";
  if (typeof category === "number") {
    // 백엔드 enum 값에 따라 매핑 (예시: 1=hr, 2=tech, 3=collaboration)
    if (category === 1) catStr = "hr";
    else if (category === 2) catStr = "tech";
    else if (category === 3) catStr = "collaboration";
    else catStr = "hr";
  } else if (typeof category === "string") {
    catStr = category.toLowerCase();
  } else {
    catStr = "hr";
  }

  if (catStr.includes("hr") || catStr.includes("인사") || catStr.includes("자기소개") || catStr.includes("지원동기")) return "hr";
  if (catStr.includes("tech") || catStr.includes("기술")) return "tech";
  if (catStr.includes("collaboration") || catStr.includes("협업")) return "collaboration";
  return "hr";
}