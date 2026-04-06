from fastapi import FastAPI

app = FastAPI(title="Ecosistema Digital UNMSM")

@app.get("/")
def read_root():
    return {"message": "Bienvenido al Ecosistema Multiplataforma", "status": "online"}

@app.get("/health")
def health_check():
    return {"check": "Servicios Cloud operativos"}