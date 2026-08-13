import os
from dotenv import load_dotenv

load_dotenv()  

ARXIV_API_BASE_URL = "http://export.arxiv.org/api/query"

ARXIV_CATEGORIES = [
    "cs.LG",            # Machine Learning
    "cs.AI",            # Artificial Intelligence
    "cs.RO",            # Robotics
    "cond-mat.mes-hall",  # Semiconductor / Mesoscale Physics
    "physics.app-ph",   # Nanotech / Applied Physics
    "cs.AR",            # Embedded — Hardware Architecture
    "cs.SY",            # Embedded — Systems and Control
    "physics.med-ph",   # Radiotherapy / Medical Physics
]

ARXIV_LOOKBACK_HOURS = 24
ARXIV_PDF_URL_TEMPLATE = "https://arxiv.org/pdf/{arxiv_id}"
PDF_DOWNLOAD_TIMEOUT_SECONDS = 30
PDF_DOWNLOAD_DELAY_SECONDS = 1 


TOP_N_PAPERS = 30               
SIMILARITY_SOFT_THRESHOLD = 0.45  
CHUNK_SIZE = 700         
CHUNK_OVERLAP = 80        

MAX_CHUNKS_PER_QUERY = 7
MAX_TOKENS_PER_LLM_CALL = 4000
MAX_OUTPUT_TOKENS = 2500

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
LLM_MODEL_NAME = "gemini-1.5-flash"

RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 5   
RETENTION_DAYS = 7

RESEARCH_INTERESTS = (
    "Deep learning, neural network architectures, transformers, model efficiency, "
    "training optimization, representation learning, self-supervised learning. "
    "Machine learning algorithms, supervised and unsupervised learning, generative models. "
    "Artificial intelligence, reinforcement learning, multi-agent systems, autonomous decision-making. "
    "Robotics, robot perception, robotic control systems, motion planning, manipulation, "
    "sensor fusion, autonomous navigation. "
    "Semiconductor devices, semiconductor fabrication, transistor design, "
    "integrated circuits, chip architecture. "
    "Nanotechnology, nanoscale materials, nanofabrication, nanoelectronics, "
    "quantum dots, nanostructures. "
    "Embedded systems, hardware architecture, real-time systems, FPGA, "
    "microcontrollers, low-power computing, edge computing. "
    "Medical physics, radiotherapy, radiation treatment planning, dosimetry, "
    "medical imaging for treatment."
)

if RESEARCH_INTERESTS.startswith("TODO:"):
    import warnings
    warnings.warn(
        "RESEARCH_INTERESTS in settings.py is still the placeholder text — "
        "paper ranking will be meaningless until you replace it with your "
        "actual interests.",
        stacklevel=2,
    )

def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise EnvironmentError(
            f"Missing required environment variable: '{name}'. "
            f"Check that your .env file exists and defines {name}."
        )
    return value

SUPABASE_URL = _require_env("SUPABASE_URL")
SUPABASE_KEY = _require_env("SUPABASE_KEY")
GEMINI_API_KEY = _require_env("GEMINI_API_KEY")