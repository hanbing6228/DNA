from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from vcf_parser import parse_vcf

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "running"}

@app.post("/upload")
async def upload(file: UploadFile):
    data = await file.read()
    result = parse_vcf(data)
    return result
