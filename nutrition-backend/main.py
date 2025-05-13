from fastapi import FastAPI
from dotenv import load_dotenv
import os
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")
load_dotenv()
app = FastAPI()

@app.get("/")
def root():
    return {"api_key_loaded": bool(os.getenv("OPENAI_API_KEY"))}

