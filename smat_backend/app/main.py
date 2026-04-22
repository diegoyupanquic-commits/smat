from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
import models
from database import engine, get_db

# CRITICAL: Creación automática de la BD y tablas al iniciar
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SMAT - Sistema de Monitoreo de Alerta Temprana",
    description="""
    API robusta para la gestión y monitoreo de desastres naturales.
    Permite la telemetría de sensores en tiempo real y el análisis de riesgos.
    
    **Entidades principales:**
    * **Estaciones:** Puntos de monitoreo físico.
    * **Lecturas:** Datos capturados por sensores.
    * **Riesgos:** Análisis de criticidad basado en umbrales.
    """,
    version="1.2.0",
    terms_of_service="http://unmsm.edu.pe/terms/",
    contact={
        "name": "Soporte Técnico SMAT - FISI",
        "url": "http://fisi.unmsm.edu.pe",
        "email": "desarrollo.smat@unmsm.edu.pe",
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
)

# --- Esquemas Pydantic ---
class EstacionCreate(BaseModel):
    id: int
    nombre: str
    ubicacion: str

class LecturaCreate(BaseModel):
    estacion_id: int
    valor: float

# --- Endpoints ---

# --- Endpoints POST Modificados para Lab 4.2 ---

@app.post(
    "/estaciones/",
    status_code=201,
    tags=["Gestión de Infraestructura"],
    summary="Registrar una nueva estación de monitoreo",
    description="Inserta una estación física (ej. río, volcán, zona sísmica) en la base de datos relacional del sistema SMAT."
)
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


@app.post(
    "/lecturas/",
    status_code=201,
    tags=["Telemetría de Sensores"],
    summary="Registrar una nueva lectura de sensor",
    description="Recibe un valor numérico y lo vincula a una estación existente. Si la estación no existe, devuelve un error 404."
)
def registrar_lectura(lectura: LecturaCreate, db: Session = Depends(get_db)):
    estacion = db.query(models.EstacionDB).filter(models.EstacionDB.id == lectura.estacion_id).first()
    if not estacion:
        raise HTTPException(status_code=404, detail="Estación no existe")

    nueva_lectura = models.LecturaDB(valor=lectura.valor, estacion_id=lectura.estacion_id)
    db.add(nueva_lectura)
    db.commit()
    return {"status": "Lectura guardada en DB"}

# --- Endpoints GET Modificados e Inclusión del Reto (Laboratorio 4.2) ---

@app.get(
    "/estaciones/{id}/riesgo",
    tags=["Análisis de Riesgo"],
    summary="Evaluar nivel de riesgo actual",
    description="""
    Analiza la última lectura recibida de una estación para determinar su estado crítico:
    - **NORMAL**: Valor menor o igual a 10.0.
    - **ALERTA**: Valor entre 10.1 y 20.0.
    - **PELIGRO**: Valor superior a 20.0.
    """,
    responses={
        200: {"description": "Cálculo de riesgo exitoso"},
        404: {"description": "La estación no existe en la base de datos"}
    }
)
def obtener_riesgo(id: int, db: Session = Depends(get_db)):
    estacion = db.query(models.EstacionDB).filter(models.EstacionDB.id == id).first()
    if not estacion:
        raise HTTPException(status_code=404, detail="Estación no encontrada")

    lecturas = db.query(models.LecturaDB).filter(models.LecturaDB.estacion_id == id).all()
    if not lecturas:
        return {"id": id, "nivel": "SIN DATOS", "valor": 0}

    ultima_lectura = lecturas[-1].valor
    nivel = "PELIGRO" if ultima_lectura > 20.0 else "ALERTA" if ultima_lectura > 10.0 else "NORMAL"
    return {"id": id, "valor": ultima_lectura, "nivel": nivel}


@app.get(
    "/estaciones/{id}/historial",
    tags=["Reportes Históricos"],
    summary="Obtener historial estadístico de lecturas",
    description="""
    Realiza una consulta SQL para recuperar todas las lecturas de una estación y calcula:
    1. **Lista de valores**: Historial completo de capturas.
    2. **Conteo total**: Cantidad de registros en la base de datos.
    3. **Promedio**: Media aritmética de los valores capturados (redondeado a 2 decimales).
    """,
    responses={
        200: {"description": "Historial y promedio calculados correctamente"},
        404: {"description": "ID de estación no encontrado"}
    }
)
def historial_y_promedio(id: int, db: Session = Depends(get_db)):
    estacion = db.query(models.EstacionDB).filter(models.EstacionDB.id == id).first()
    if not estacion:
        raise HTTPException(status_code=404, detail="Estación no encontrada")

    lecturas = db.query(models.LecturaDB).filter(models.LecturaDB.estacion_id == id).all()
    conteo = len(lecturas)
    promedio = sum(l.valor for l in lecturas) / conteo if conteo > 0 else 0.0
    lista_lecturas = [{"id": l.id, "valor": l.valor} for l in lecturas]

    return {
        "estacion_id": id,
        "lecturas": lista_lecturas,
        "conteo": conteo,
        "promedio": round(promedio, 2)
    }

# --- PUNTO 2 DEL RETO: Auditoría de Críticos ---
@app.get(
    "/reportes/criticos",
    tags=["Auditoría"],
    summary="Filtrar lecturas que superan el umbral",
    description="""
    Filtra las lecturas en el sistema que superan un valor crítico. 
    - **umbral**: Parámetro opcional. Si no se provee, el valor por defecto es 20.0.
    """
)
def obtener_criticos(umbral: float = Query(20.0, description="Valor mínimo para filtrar"), db: Session = Depends(get_db)):
    criticos = db.query(models.LecturaDB).filter(models.LecturaDB.valor > umbral).all()
    return {"umbral_aplicado": umbral, "total": len(criticos), "datos": criticos}

# --- PUNTO 3 DEL RETO: Stats / Resumen Ejecutivo ---
@app.get(
    "/estaciones/stats",
    tags=["Auditoría"],
    summary="Resumen ejecutivo del sistema",
    description="Proporciona un conteo global de estaciones y lecturas totales registradas en el SMAT."
)
def obtener_stats(db: Session = Depends(get_db)):
    return {
        "total_estaciones": db.query(models.EstacionDB).count(),
        "total_lecturas": db.query(models.LecturaDB).count(),
        "mensaje": "Resumen consolidado de infraestructura"
    }