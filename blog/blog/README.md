# Market Analysis Blog Automation

This project automatically collects market data, analyzes it using DeepSeek AI, and posts the analysis to a Naver blog.

## Setup

1. Create conda environment:
```bash
conda env create -f environment.yml
```

2. Activate environment:
```bash
conda activate blog
```

3. Run the script:
```bash
python src/main.py
```

## Configuration

- Edit `config/config.yaml` for customizing data collection and blog posting settings
- Environment variables are stored in `.env` file

## Features

- Collects market data from Yahoo Finance
- Analyzes market trends using DeepSeek AI
- Automatically posts analysis to Naver blog
- Scheduled execution at market close
