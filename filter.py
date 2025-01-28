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
) -> tuple[List[dict], List[dict]]:
    """JSON 파일들을 처리하여 필터링된 데이터와 필터링되지 않은 데이터 리스트 반환"""

    json_files = list(input_dir.glob("*.json"))
    if not json_files:
        print(f"Warning: No JSON files found in {input_dir}")
        return [], []

    keyword_variations = generate_keyword_variations(keywords)
    filtered_data = []
    unfiltered_data = []

    for json_file in tqdm(json_files, desc=f"Processing {input_dir.name}"):
        try:
            with json_file.open("r", encoding="utf-8") as f:
                data = json.load(f)

            # 데이터 행 생성을 키워드 검색 전에 수행
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
                "source_folder": input_dir.name,
            }

            # 키워드 검색
            found_keyword = False
            for field in target_fields:
                if field not in data:
                    continue

                text = data[field].lower()
                if any(variation.lower() in text for variation in keyword_variations):
                    found_keyword = True
                    break

            # 키워드 발견 여부에 따라 적절한 리스트에 추가
            if found_keyword:
                filtered_data.append(row)
            else:
                unfiltered_data.append(row)

        except json.JSONDecodeError:
            print(f"Error decoding JSON file: {json_file}")
        except Exception as e:
            print(f"Error processing file {json_file}: {str(e)}")

    return filtered_data, unfiltered_data


def create_tag_histogram(filtered_data: List[dict]) -> pd.DataFrame:
    """태그 빈도수를 계산하여 DataFrame으로 반환"""
    all_tags = []
    for row in filtered_data:
        if row["tags"]:
            tags = row["tags"].split(",")
            all_tags.extend(tags)

    tag_counts = pd.Series(all_tags).value_counts().reset_index()
    tag_counts.columns = ["tag_name", "frequency"]
    return tag_counts


def main():
    # 폴더별 키워드 설정
    FOLDER_KEYWORDS = {
        "output/신촌고기창고": ["신촌 고기 창고", "서울 서대문구 연세로7길 34-4", "新村烤肉仓库"],
        "output/장군닭갈비": [
            "서울 서대문구 연세로9길 7",
            "장군 닭갈비 신촌점",
            "신촌 장군 닭갈비",
            "장군닭갈비 신촌점",
            "서대문구 연세로9길 7",
            "장군닭갈비 新村",
        ],
        "output/김덕후의곱창조": [
            "서울 서대문구 연세로7안길 18",
            "연세로7안길 18",
            "김덕후의 곱창조 신촌",
            "신촌 김덕후의 곱창조",
            "김덕후의 곱창조 신촌점",
            "김덕후의곱창조 신촌점",
        ],
    }

    TARGET_FIELDS = ["desc", "title"]
    OUTPUT_CSV = Path("output/all_filtered_results.csv")
    TAG_HISTOGRAM_CSV = Path("output/tag_histograms.csv")
    UNFILTERED_CSV = Path("output/all_unfiltered_results.csv")

    all_filtered_data = []
    all_unfiltered_data = []
    folder_tag_histograms = {}

    # 각 폴더별 처리
    for folder_path, keywords in FOLDER_KEYWORDS.items():
        input_dir = Path(folder_path)
        if not input_dir.exists():
            print(f"Warning: Directory not found - {input_dir}")
            continue

        filtered_data, unfiltered_data = process_json_files(
            input_dir=input_dir, keywords=keywords, target_fields=TARGET_FIELDS
        )
        all_filtered_data.extend(filtered_data)
        all_unfiltered_data.extend(unfiltered_data)

        # 폴더별 태그 히스토그램 생성
        folder_name = input_dir.name
        tag_histogram = create_tag_histogram(filtered_data)
        tag_histogram["source_folder"] = folder_name
        folder_tag_histograms[folder_name] = tag_histogram

        print(f"{folder_name}: {len(filtered_data)}개의 데이터가 필터링되었습니다.")
        print(f"{folder_name}: {len(unfiltered_data)}개의 데이터가 필터링되지 않았습니다.")

    # 필터링된/되지 않은 데이터를 각각의 CSV 파일로 저장
    if all_filtered_data:
        df_filtered = pd.DataFrame(all_filtered_data)
        df_filtered.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
        print(f"\n총 {len(all_filtered_data)}개의 필터링된 데이터가 CSV 파일로 저장되었습니다.")
        print(f"필터링된 CSV 파일 저장 위치: {OUTPUT_CSV}")

    if all_unfiltered_data:
        df_unfiltered = pd.DataFrame(all_unfiltered_data)
        df_unfiltered.to_csv(UNFILTERED_CSV, index=False, encoding="utf-8-sig")
        print(f"총 {len(all_unfiltered_data)}개의 필터링되지 않은 데이터가 CSV 파일로 저장되었습니다.")
        print(f"필터링되지 않은 CSV 파일 저장 위치: {UNFILTERED_CSV}")

    # 태그 히스토그램 CSV 저장
    if folder_tag_histograms:
        all_histograms = pd.concat(folder_tag_histograms.values(), ignore_index=True)
        all_histograms.to_csv(TAG_HISTOGRAM_CSV, index=False, encoding="utf-8-sig")
        print(f"태그 히스토그램이 저장되었습니다: {TAG_HISTOGRAM_CSV}")
    else:
        print("\n필터링된 데이터가 없습니다.")


if __name__ == "__main__":
    main()
