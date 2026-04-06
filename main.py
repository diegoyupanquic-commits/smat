from fastapi import FastAPI # Importación del framework

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "success", "plataforma": "UNMSM-FISI"}