import json
import glob
import os

def is_valid_id(id_str):
    """
    ID가 유효한지 검사하는 함수
    
    Args:
        id_str (str): 검사할 ID 문자열
        
    Returns:
        bool: 유효한 ID이면 True, 아니면 False
    """
    VALID_ID_LENGTH = 24  # "675bc154000000000103dbfa" 길이
    return isinstance(id_str, str) and len(id_str) == VALID_ID_LENGTH

def parse_xiaohongshu_urls(json_file_path):
    """
    JSON 파일에서 xiaohongshu URL 리스트를 생성하는 함수
    
    Args:
        json_file_path (str): JSON 파일 경로
        
    Returns:
        list: URL 문자열 리스트
    """
    try:
        # JSON 파일 읽기
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        # URL 리스트 생성
        urls = []
        invalid_ids = []
        base_url = "https://www.xiaohongshu.com/explore"
        
        # items 리스트를 순회하면서 URL 생성
        for item in data['data']['items']:
            if 'id' in item and 'xsec_token' in item:
                if is_valid_id(item['id']):
                    url = f"{base_url}/{item['id']}?xsec_token={item['xsec_token']}&xsec_source=pc_search&source=web_search_result_notes"
                    urls.append(url)
                else:
                    invalid_ids.append(item['id'])
        
        if invalid_ids:
            print(f"Warning: 유효하지 않은 ID {len(invalid_ids)}개를 발견했습니다:")
            for invalid_id in invalid_ids[:5]:  # 처음 5개만 출력
                print(f"- {invalid_id}")
            if len(invalid_ids) > 5:
                print(f"... 외 {len(invalid_ids) - 5}개")
        
        return urls
    
    except FileNotFoundError:
        print(f"Error: 파일을 찾을 수 없습니다 - {json_file_path}")
        return []
    except json.JSONDecodeError:
        print(f"Error: JSON 파일 형식이 올바르지 않습니다 - {json_file_path}")
        return []
    except KeyError as e:
        print(f"Error: JSON 구조에서 필요한 키를 찾을 수 없습니다 - {e}")
        return []

def save_urls_to_file(urls, output_file_path):
    """
    URL 리스트를 파일로 저장하는 함수
    
    Args:
        urls (list): URL 문자열 리스트
        output_file_path (str): 저장할 파일 경로
    """
    try:
        # 출력 디렉토리가 없으면 생성
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
        
        with open(output_file_path, 'w', encoding='utf-8') as file:
            json.dump({"urls": urls}, file, indent=2, ensure_ascii=False)
        print(f"URLs가 성공적으로 저장되었습니다: {output_file_path}")
    except Exception as e:
        print(f"Error: 파일 저장 중 오류가 발생했습니다 - {e}")

if __name__ == "__main__":
    # import 폴더 경로 설정
    import_dir = "import"
    output_dir = "export"
    
    # import 폴더가 없으면 생성
    if not os.path.exists(import_dir):
        os.makedirs(import_dir)
        print(f"'{import_dir}' 폴더가 생성되었습니다.")
        print(f"JSON 파일을 '{import_dir}' 폴더에 넣어주세요.")
        exit()
    
    # import 폴더의 모든 JSON 파일 찾기
    json_files = glob.glob(os.path.join(import_dir, "*.json"))
    
    if not json_files:
        print(f"'{import_dir}' 폴더에 JSON 파일이 없습니다.")
        exit()
    
    all_urls = []
    
    # 각 JSON 파일 처리
    for json_file in json_files:
        print(f"\n{os.path.basename(json_file)} 처리 중...")
        urls = parse_xiaohongshu_urls(json_file)
        if urls:
            print(f"{os.path.basename(json_file)}에서 {len(urls)}개의 URL을 찾았습니다.")
            all_urls.extend(urls)
    
    # 중복 URL 제거
    all_urls = list(dict.fromkeys(all_urls))
    
    # 결과 출력 및 저장
    if all_urls:
        print(f"\n총 {len(all_urls)}개의 고유한 URL이 생성되었습니다.")
        output_file_path = os.path.join(output_dir, "urls.json")
        save_urls_to_file(all_urls, output_file_path)
