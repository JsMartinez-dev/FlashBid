from fastapi import FastAPI
from local_dev.websocket import router

app = FastAPI(title="FlashBid WebSocket gateway")
app.include_router(router)
