import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory using pathlib (cross-platform, Windows-compatible)
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env if present
env_path = BASE_DIR / '.env'
if env_path.exists():
    load_dotenv(env_path)

# Data Directories
DATA_DIR = BASE_DIR / 'data'
RAW_DATA_DIR = DATA_DIR / 'raw'
SUBSAMPLE_DIR = DATA_DIR / 'subsample'
GOLDEN_DIR = DATA_DIR / 'golden'

# Output Directories
RESULTS_DIR = BASE_DIR / 'results'
REPORT_DIR = BASE_DIR / 'report'

# File Paths
SUBSAMPLE_FILE = SUBSAMPLE_DIR / 'apple_support_subsample.json'
GOLDEN_UNLABELLED_FILE = GOLDEN_DIR / 'golden_set_unlabelled.csv'
GOLDEN_LABELLED_FILE = GOLDEN_DIR / 'golden_set_labelled.json'
LABELLING_GUIDE_FILE = GOLDEN_DIR / 'LABELLING_GUIDE.md'
METRICS_JSON_FILE = RESULTS_DIR / 'metrics.json'
CONFUSION_MATRIX_FILE = RESULTS_DIR / 'confusion_matrix.png'
CALIBRATION_PLOT_FILE = RESULTS_DIR / 'confidence_calibration.png'

# Ensure directories exist
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
SUBSAMPLE_DIR.mkdir(parents=True, exist_ok=True)
GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# Fixed Random Seed for Deterministic Reproducibility
RANDOM_SEED = int(os.getenv('RANDOM_SEED', 42))

# Model Configs
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
