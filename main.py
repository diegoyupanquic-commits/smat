from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import models
from database import engine, get_db

# CRITICAL: Creación automática de la BD y tablas al iniciar
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="SMAT Persistente UNMSM")

# --- Esquemas Pydantic ---
class EstacionCreate(BaseModel):
    id: int
    nombre: str
    ubicacion: str

class LecturaCreate(BaseModel):
    estacion_id: int
    valor: float

# --- Endpoints ---

@app.post("/estaciones/", status_code=201)
def crear_estacion(estacion: EstacionCreate, db: Session = Depends(get_db)):
    # Validar si ya existe
    existe = db.query(models.EstacionDB).filter(models.EstacionDB.id == estacion.id).first()
    if existe:
        raise HTTPException(status_code=400, detail="El ID de la estación ya existe")
        
    nueva_estacion = models.EstacionDB(id=estacion.id, nombre=estacion.nombre, ubicacion=estacion.ubicacion)
    db.add(nueva_estacion)
    db.commit()
    db.refresh(nueva_estacion)
    return {"msj": "Estación guardada en DB", "data": nueva_estacion}

@app.post("/lecturas/", status_code=201)
def registrar_lectura(lectura: LecturaCreate, db: Session = Depends(get_db)):
    estacion = db.query(models.EstacionDB).filter(models.EstacionDB.id == lectura.estacion_id).first()
    if not estacion:
        raise HTTPException(status_code=404, detail="Estación no existe")

    nueva_lectura = models.LecturaDB(valor=lectura.valor, estacion_id=lectura.estacion_id)
    db.add(nueva_lectura)
    db.commit()
    return {"status": "Lectura guardada en DB"}

@app.get("/estaciones/{id}/riesgo")
def obtener_riesgo(id: int, db: Session = Depends(get_db)):
    estacion = db.query(models.EstacionDB).filter(models.EstacionDB.id == id).first()
    if not estacion:
        raise HTTPException(status_code=404, detail="Estación no encontrada")

    lecturas = db.query(models.LecturaDB).filter(models.LecturaDB.estacion_id == id).all()
    if not lecturas:
        return {"id": id, "nivel": "SIN DATOS", "valor": 0}

    ultima_lectura = lecturas[-1].valor
    if ultima_lectura > 20.0:
        nivel = "PELIGRO"
    elif ultima_lectura > 10.0:
        nivel = "ALERTA"
    else:
        nivel = "NORMAL"

    return {"id": id, "valor": ultima_lectura, "nivel": nivel}

# RETO LABORATIORIO 2 Y 3: Historial y Promedio desde SQL
@app.get("/estaciones/{id}/historial")
def historial_y_promedio(id: int, db: Session = Depends(get_db)):
    estacion = db.query(models.EstacionDB).filter(models.EstacionDB.id == id).first()
    if not estacion:
        raise HTTPException(status_code=404, detail="Estación no encontrada")

    # Consulta SQL mediante SQLAlchemy
    lecturas = db.query(models.LecturaDB).filter(models.LecturaDB.estacion_id == id).all()
    
    conteo = len(lecturas)
    if conteo == 0:
        promedio = 0.0
    else:
        promedio = sum(l.valor for l in lecturas) / conteo

    # Formateo de respuesta
    lista_lecturas = [{"id": l.id, "valor": l.valor} for l in lecturas]

    return {
        "estacion_id": id,
        "lecturas": lista_lecturas,
        "conteo": conteo,
        "promedio": round(promedio, 2)
    }