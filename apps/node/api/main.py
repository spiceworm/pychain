from fastapi import FastAPI

from v1 import router as v1_router


def create_app():
    api = FastAPI()

    api.include_router(v1_router, prefix="/api/v1")

    return api


app = create_app()
