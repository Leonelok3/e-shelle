import os
import numpy as np
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_embedding(text: str):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text[:8000]
    )
    return response.data[0].embedding

def semantic_match(cv_text: str, offer_text: str):
    if not cv_text or not offer_text:
        return 0

    emb_cv = np.array(get_embedding(cv_text))
    emb_offer = np.array(get_embedding(offer_text))

    similarity = np.dot(emb_cv, emb_offer) / (
        np.linalg.norm(emb_cv) * np.linalg.norm(emb_offer)
    )

    score = int(similarity * 100)
    return max(0, min(score, 100))
