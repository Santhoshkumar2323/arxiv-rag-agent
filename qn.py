from sentence_transformers import SentenceTransformer
from agent.prompts import FIXED_QUESTION

model = SentenceTransformer('all-MiniLM-L6-v2')
vector = model.encode(FIXED_QUESTION).tolist()
print(vector)