from fastapi import FastAPI
from app.routers import product_description_generator
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(product_description_generator.router, prefix="/product", tags=["Product Generation"])



@app.get("/")
async def test_api():
    return {"message": "FastAPI is working! for product description"}