from pathlib import Path
import json
from tqdm import tqdm
from typing import List, Set, Dict
import pandas as pd
import datetime


def generate_keyword_variations(keywords: List[str]) -> Set[str]:
    """키워드의 모든 변형을 생성하는 함수"""
    variations = set()
    for keyword in keywords:
        variations.update(
            [
                keyword,
                keyword.lower(),
                keyword.upper(),
                keyword.replace(" ", ""),
                keyword.replace(" ", "").lower(),
                keyword.replace(" ", "").upper(),
            ]
        )
    return variations


def convert_timestamp_to_datetime(timestamp: int) -> str:
    """밀리초 타임스탬프를 datetime 문자열로 변환"""
    return datetime.datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")


def extract_tag_names(tag_list: List[dict]) -> str:
    """태그 리스트에서 이름만 추출하여 쉼표로 구분된 문자열로 반환"""
    return ",".join([tag["name"] for tag in tag_list])


def process_json_files(
    input_dir: Path,
    keywords: List[str],
    target_fields: List[str] = ["desc", "title"],
) -> List[dict]:
    """JSON 파일들을 처리하여 필터링된 데이터 리스트 반환"""

    json_files = list(input_dir.glob("*.json"))
    if not json_files:
        print(f"Warning: No JSON files found in {input_dir}")
        return []

    keyword_variations = generate_keyword_variations(keywords)
    filtered_data = []

    for json_file in tqdm(json_files, desc=f"Processing {input_dir.name}"):
        try:
            with json_file.open("r", encoding="utf-8") as f:
                data = json.load(f)

            # 키워드 검색
            found_keyword = False
            for field in target_fields:
                if field not in data:
                    continue

                text = data[field].lower()
                if any(variation.lower() in text for variation in keyword_variations):
                    found_keyword = True
                    break

            # 키워드가 발견되면 데이터 추출
            if found_keyword:
                row = {
                    "note_id": data.get("note_id", ""),
                    "title": data.get("title", ""),
                    "liked_count": data.get("interact_info", {}).get("liked_count", "0"),
                    "collected_count": data.get("interact_info", {}).get("collected_count", "0"),
                    "comment_count": data.get("interact_info", {}).get("comment_count", "0"),
                    "share_count": data.get("interact_info", {}).get("share_count", "0"),
                    "tags": extract_tag_names(data.get("tag_list", [])),
                    "time": convert_timestamp_to_datetime(data.get("time", 0)),
                    "last_update_time": convert_timestamp_to_datetime(data.get("last_update_time", 0)),
                    "user_id": data.get("user", {}).get("user_id", ""),
                    "user_nickname": data.get("user", {}).get("nickname", ""),
                    "desc": data.get("desc", ""),
                    "source_folder": input_dir.name,  # 출처 폴더 정보 추가
                }
                filtered_data.append(row)

        except json.JSONDecodeError:
            print(f"Error decoding JSON file: {json_file}")
        except Exception as e:
            print(f"Error processing file {json_file}: {str(e)}")

    return filtered_data


def main():
    # 폴더별 키워드 설정
    FOLDER_KEYWORDS = {
        "output/hotel_de_ggoodd": [
            "오뗄 드 꾸뜨",
            "hotel de ggoodd",
            "오뗄 드 꾸드",
            "서울 마포구 동교로46길 7 101호",
            "오뗄 뜨 꾸뜨",
            "오뗄 드 구뜨",
        ],
        "output/richard": [
            "리차드하우스",
            "richard haus",
            "서울 마포구 동교로46길 36",
        ],
        "output/hey_george": ["헤이죠지", "hey george", "서울 마포구 동교로46길 42-24"],
        "output/camelo": [
            "카멜로",
            "CAMELLO yeonnam",
            "서울 마포구 연희로1길 57 1.5층",
            "서울 마포구 연희로 1길 57 1.5층",
        ],
    }

    TARGET_FIELDS = ["desc", "title"]
    OUTPUT_CSV = Path("output/all_filtered_results.csv")

    all_filtered_data = []

    # 각 폴더별 처리
    for folder_path, keywords in FOLDER_KEYWORDS.items():
        input_dir = Path(folder_path)
        if not input_dir.exists():
            print(f"Warning: Directory not found - {input_dir}")
            continue

        filtered_data = process_json_files(input_dir=input_dir, keywords=keywords, target_fields=TARGET_FIELDS)
        all_filtered_data.extend(filtered_data)

        print(f"{input_dir.name}: {len(filtered_data)}개의 데이터가 필터링되었습니다.")

    # 전체 결과를 하나의 CSV 파일로 저장
    if all_filtered_data:
        df = pd.DataFrame(all_filtered_data)
        df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
        print(f"\n총 {len(all_filtered_data)}개의 데이터가 CSV 파일로 저장되었습니다.")
        print(f"CSV 파일 저장 위치: {OUTPUT_CSV}")
    else:
        print("\n필터링된 데이터가 없습니다.")


if __name__ == "__main__":
    main()
