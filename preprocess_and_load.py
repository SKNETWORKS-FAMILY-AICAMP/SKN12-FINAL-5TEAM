import json
import os
import re
from tqdm import tqdm

# --------------------------------------------------------------------------
# 1. 설정 (Configuration)
# --------------------------------------------------------------------------

# 데이터 경로 (os.path.join 사용, 절대 경로)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TRAINING_DATA_PATH = os.path.join(BASE_DIR, '01-1.정식개방데이터', 'Training', '02.라벨링데이터')
VALIDATION_DATA_PATH = os.path.join(BASE_DIR, '01-1.정식개방데이터', 'Validation', '02.라벨링데이터')
OUTPUT_FILE_PATH = os.path.join(BASE_DIR, 'preprocessed_data.json')

# 전처리 파라미터
MIN_SENTENCE_LENGTH = 5  # 이 길이 미만의 문장은 필터링

# 제거할 추임새 및 습관어 목록 (정규식으로 구성)
# 주의: 단어 경계(\b)를 사용하여 부분 일치를 방지 (예: '그'가 '그림'에서 삭제되는 것을 방지)
FILLER_WORDS_PATTERN = re.compile(
    r'\b(음|아|어|그|저|뭐랄까|그러니까|사실|그냥|약간|일단|아무튼|솔직히|어떻게 보면|좀|너무|글쎄요|있잖아요|뭐라고 해야 할까|노력하는 편입니다|잘 모르겠지만)\b'
)

# 제거할 불필요한 기호 목록
SYMBOL_PATTERN = re.compile(r'[\"()[\\].,?!...]{2,}') # 2번 이상 반복되는 기호
WHITESPACE_PATTERN = re.compile(r'\s+') # 중복 공백

# --------------------------------------------------------------------------
# 2. 전처리 함수 (Preprocessing Functions)
# --------------------------------------------------------------------------

def remove_fillers(text):
    """추임새 및 습관어를 제거합니다."""
    return FILLER_WORDS_PATTERN.sub('', text).strip()

def remove_symbols(text):
    """불필요한 기호를 제거합니다."""
    return SYMBOL_PATTERN.sub(' ', text)

def normalize_whitespace(text):
    """중복 공백 및 앞뒤 공백을 정리합니다."""
    return WHITESPACE_PATTERN.sub(' ', text).strip()

# def correct_spelling(text):
#     """(선택 사항) 맞춤법을 교정합니다."""
#     # 필요 시 `py-hanspell` 설치 후 주석 해제하여 사용
#     # from hanspell import spell_checker
#     # try:
#     #     spelled_sent = spell_checker.check(text)
#     #     return spelled_sent.checked
#     # except:
#     #     return text # 에러 발생 시 원문 반환
#     return text

def preprocess_text(text):
    """정의된 파이프라인에 따라 텍스트를 전처리합니다."""
    if not isinstance(text, str):
        return ""
    
    # 1. 추임새 및 습관어 제거
    text = remove_fillers(text)
    # 2. 불필요한 기호 제거
    text = remove_symbols(text)
    # 3. 공백 정리
    text = normalize_whitespace(text)
    # 4. (선택) 맞춤법 교정
    # text = correct_spelling(text)
    
    return text

# --------------------------------------------------------------------------
# 3. 메인 로직 (Main Logic)
# --------------------------------------------------------------------------

def get_all_file_paths(directory_paths):
    """모든 JSON 파일 경로를 재귀적으로 찾습니다."""
    file_paths = []
    for path in directory_paths:
        if not os.path.exists(path):
            print(f"경로가 존재하지 않습니다: {path}")
            continue
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith('.json'):
                    file_paths.append(os.path.join(root, file))
    return file_paths

def main():
    """전체 전처리 과정을 실행하고 결과를 파일로 저장합니다."""
    print("면접 음성 텍스트 데이터 전처리를 시작합니다.")
    
    # 1. 데이터 로딩
    all_json_files = get_all_file_paths([TRAINING_DATA_PATH, VALIDATION_DATA_PATH])
    if not all_json_files:
        print("오류: 지정된 경로에서 JSON 파일을 찾을 수 없습니다.")
        return

    print(f"총 {len(all_json_files)}개의 파일을 발견했습니다. 전처리를 진행합니다...")
    
    processed_data = []
    
    for file_path in tqdm(all_json_files, desc="전처리 진행 중"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError as e:
                    print(f"JSON 디코딩 오류: {file_path}: {e}")
                    continue
                # 2. 원본 텍스트 추출
                raw_question = data.get('dataSet', {}).get('question', {}).get('raw', {}).get('text', "")
                raw_answer = data.get('dataSet', {}).get('answer', {}).get('raw', {}).get('text', "")
                # 3. 전처리 적용
                clean_question = preprocess_text(raw_question)
                clean_answer = preprocess_text(raw_answer)
                # 4. 유효성 검사 (Null, 빈 문자열, 최소 길이)
                if not clean_question or not clean_answer:
                    continue
                if len(clean_question) < MIN_SENTENCE_LENGTH or len(clean_answer) < MIN_SENTENCE_LENGTH:
                    continue
                # 5. 최종 데이터 구조화
                file_id = os.path.basename(file_path).split('.')[0]
                processed_data.append({
                    "id": file_id,
                    "question": clean_question,
                    "answer": clean_answer
                })
        except FileNotFoundError:
            print(f"파일을 찾을 수 없습니다: {file_path}")
        except Exception as e:
            print(f"알 수 없는 오류 발생 {file_path}: {e}")

    print(f"전처리 완료. 총 {len(processed_data)}개의 유효한 데이터가 처리되었습니다.")

    # 6. 전처리된 데이터를 JSON 파일로 저장
    with open(OUTPUT_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(processed_data, f, ensure_ascii=False, indent=4)
        
    print(f"전처리된 데이터가 '{OUTPUT_FILE_PATH}' 파일로 저장되었습니다.")

    # 7. 전/후 예시 출력
    if processed_data:
        print("\n--- 전/후 처리 예시 ---")
        example_id = processed_data[0]['id']
        # 원본 파일을 다시 읽어와서 비교
        example_raw_path = os.path.join(TRAINING_DATA_PATH, example_id + '.json')
        if not os.path.exists(example_raw_path):
            example_raw_path = os.path.join(VALIDATION_DATA_PATH, example_id + '.json')
        if os.path.exists(example_raw_path):
            try:
                with open(example_raw_path, 'r', encoding='utf-8') as f:
                    raw_example = json.load(f)
                    print(f"원본 답변: {raw_example['dataSet']['answer']['raw']['text']}")
                    print(f"전처리 후 답변: {processed_data[0]['answer']}")
            except Exception as e:
                print(f"예시 파일 처리 중 오류: {e}")
        else:
            print("예시 파일 경로를 찾을 수 없어 전/후 비교를 생략합니다.")


if __name__ == '__main__':
    main()
