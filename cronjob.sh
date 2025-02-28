#!/bin/bash

source ~/ENV/miniconda3/etc/profile.d/conda.sh

# 원하는 Conda 환경 활성화
conda activate py310

# Python 스크립트 실행 및 로그 기록 (로그 파일 경로와 이름 지정)
python ${HOME}/PRJ/xhs/sync_notion.py |& tee ${HOME}/PRJ/xhs/log/sync_notion_$(date +\%Y-\%m-\%d).log 2>&1

