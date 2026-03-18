from fastapi import FastAPI, Request, HTTPException, Form, Depends, File, UploadFile
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import hashlib
import hmac
import os
import time
from datetime import datetime, timedelta
from sqlalchemy.exc import OperationalError

app = FastAPI(title="SISMA VPS HUB")

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Cambiar a DATABASE_URL de entorno si existe (Docker/Production)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'data', 'licenses.db')}")
STATIC_DIR = os.path.join(BASE_DIR, "static")
SECRET_KEY_HMAC = os.getenv("SECRET_KEY_HMAC", "SISMA_ULTRA_SECRET_KEY_2026").encode()
ADMIN_USER = os.getenv("ADMIN_USER", "santiago.salazar")
ADMIN_PASS = os.getenv("ADMIN_PASS", "Ssc841209*")
# URL Pública del HUB (para Coolify/Producción)
HUB_PUBLIC_URL = os.getenv("HUB_PUBLIC_URL", "http://localhost:10000")

# --- ENDPOINT DE CONFIGURACIÓN ---
@app.get("/api/admin/config/webhook")
async def get_webhook_config(request: Request):
    """Retorna la URL del Webhook para la sincronización con la App de Tierra."""
    # Detección dinámica: Si es localhost (default), usar el dominio desde el que se accede
    host = HUB_PUBLIC_URL
    if "localhost" in host:
        # Extraer el esquema (http/https) y el dominio del request actual
        scheme = request.url.scheme
        netloc = request.url.netloc
        host = f"{scheme}://{netloc}"
    
    return {
        "webhook_url": f"{host}/api/ops/sync",
        "hub_id": "SISMA-HUB-MASTER-01",
        "status": "Ready"
    }

# --- DATABASE ENGINE ---
def get_engine():
    """Crea el engine con lógica de reconexión para entornos Docker."""
    retries = 5
    while retries > 0:
        try:
            temp_engine = create_engine(
                DATABASE_URL,
                pool_pre_ping=True, # Verifica conexión antes de usarla
                pool_recycle=3600   # Recicla conexiones cada hora
            )
            # Probar conexión física
            with temp_engine.connect() as conn:
                return temp_engine
        except OperationalError:
            retries -= 1
            print(f"WARN: DB no lista. Reintentando en 5s... ({retries} intentos restantes)")
            time.sleep(5)
    
    # Si falla PostgreSQL catastróficamente, fallback silencioso a SQLite para asegurar arranque parcial
    if "postgresql" in DATABASE_URL:
        print("CRITICAL: Fallo total en PostgreSQL. Iniciando en modo EMERGENCIA (SQLite local).")
        sqlite_fallback = f"sqlite:///{os.path.join(BASE_DIR, 'data', 'emergency.db')}"
        return create_engine(sqlite_fallback)
    
    return create_engine(DATABASE_URL)

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- MODELOS ---
class License(Base):
    __tablename__ = "licenses"
    id = Column(Integer, primary_key=True, index=True)
    hwid = Column(String, unique=True, index=True)
    short_code = Column(String)
    status = Column(String, default="Pendiente")
    days_remaining = Column(Integer, default=0)
    expiration_date = Column(String)
    last_ip = Column(String)
    last_login = Column(String)
    hostname = Column(String)
    os_version = Column(String)
    cpu_model = Column(String)
    ram_total = Column(String)

class TrainingStat(Base):
    __tablename__ = "training_stats"
    id = Column(Integer, primary_key=True, index=True)
    epoch = Column(Integer)
    map50 = Column(Float)
    recall = Column(Float)
    loss = Column(Float)
    timestamp = Column(String)
    status = Column(String)

class TacticalModel(Base):
    __tablename__ = "tactical_models"
    id = Column(Integer, primary_key=True, index=True)
    project = Column(String, index=True)
    filename = Column(String)
    version = Column(String)
    file_hash = Column(String)
    timestamp = Column(String)
    raw_effort = Column(Integer)

class Operator(Base):
    __tablename__ = "operators"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    full_name = Column(String)
    assigned_hwid = Column(String)  # NULL significa que se vinculará en el primer login
    expiration_date = Column(String) # Fecha límite de uso
    role = Column(String, default="operator")
    status = Column(String, default="Activo") # Activo, Inactivo, Caducado

class FlightLog(Base):
    __tablename__ = "flight_logs"
    id = Column(Integer, primary_key=True, index=True)
    operator_id = Column(Integer, ForeignKey("operators.id"))
    start_time = Column(String)
    end_time = Column(String)
    detections = Column(Integer)
    success_rate = Column(Float)
    comments = Column(Text)

class ModelVault(Base):
    __tablename__ = "model_vault"
    id = Column(Integer, primary_key=True, index=True)
    version = Column(String)
    filename = Column(String)
    sha256_hash = Column(String, unique=True, index=True)
    status = Column(String, default="Avalado")
    upload_date = Column(String)

class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True, index=True)
    operator_id = Column(Integer, ForeignKey("operators.id"))
    type = Column(String)
    content = Column(Text)
    timestamp = Column(String)
    status = Column(String, default="Pendiente")

# Crear tablas
Base.metadata.create_all(bind=engine)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- MONTAR FRONTEND ---
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- ENDPOINTS API ---
@app.get("/api/health")
def health():
    return {"status": "online", "server": "SISMA VPS"}

@app.get("/api/data/licenses")
async def api_licenses(db: Session = Depends(get_db)):
    rows = db.query(License).order_by(License.last_login.desc()).all()
    return rows

@app.get("/api/data/training")
async def api_training(db: Session = Depends(get_db)):
    rows = db.query(TrainingStat).order_by(TrainingStat.epoch.desc()).limit(50).all()
    return rows

@app.get("/api/data/vault")
async def api_vault(db: Session = Depends(get_db)):
    rows = db.query(ModelVault).order_by(ModelVault.upload_date.desc()).all()
    return rows

@app.get("/api/admin/operators/list")
async def list_operators(db: Session = Depends(get_db)):
    return db.query(Operator).all()

@app.post("/api/admin/operators/add")
async def add_operator(
    username: str = Form(...), 
    password: str = Form(...), 
    full_name: str = Form(...), 
    days: int = Form(30),
    db: Session = Depends(get_db)
):
    try:
        exp = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        new_op = Operator(
            username=username, 
            password=password, 
            full_name=full_name, 
            assigned_hwid=None, # Se vincula en el primer login
            expiration_date=exp
        )
        db.add(new_op)
        db.commit()
    except Exception:
        db.rollback()
        return RedirectResponse(url="/admin/dashboard?error=user_exists", status_code=303)
    return RedirectResponse(url="/admin/dashboard#personal", status_code=303)

@app.post("/api/admin/operators/update_time")
async def update_op_time(op_id: int = Form(...), days: int = Form(...), db: Session = Depends(get_db)):
    op = db.query(Operator).filter(Operator.id == op_id).first()
    if op:
        exp = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        op.expiration_date = exp
        op.status = "Activo"
        db.commit()
    return RedirectResponse(url="/admin/dashboard#personal", status_code=303)

@app.post("/api/ops/login")
async def operator_login(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    username = data.get("username")
    password = data.get("password")
    hwid = data.get("hwid")
    
    op = db.query(Operator).filter(Operator.username == username, Operator.password == password).first()
    if not op:
        return {"status": "Error", "message": "Credenciales inválidas."}
    
    # 1. Validar Estado
    if op.status != "Activo":
        return {"status": "Error", "message": f"Cuenta {op.status}"}
    
    # 2. Validar Tiempo
    exp_dt = datetime.strptime(op.expiration_date, "%Y-%m-%d %H:%M:%S")
    if datetime.now() > exp_dt:
        op.status = "Caducado"
        db.commit()
        return {"status": "Error", "message": "Licencia de operador caducada."}
    
    # 3. Ciclo de Identificación (Vinculación HWID)
    if op.assigned_hwid is None:
        op.assigned_hwid = hwid
        db.commit()
        return {"status": "Success", "message": "Equipo vinculado correctamente.", "token": "OP_TOKEN_LITE"}
    
    if op.assigned_hwid != hwid:
        return {"status": "Error", "message": "Este usuario está vinculado a otro equipo."}
        
    return {"status": "Success", "message": "Acceso concedido.", "token": "OP_TOKEN_READY"}

@app.post("/api/admin/operators/delete")
async def delete_operator(op_id: int = Form(...), db: Session = Depends(get_db)):
    op = db.query(Operator).filter(Operator.id == op_id).first()
    if op:
        db.delete(op)
        db.commit()
    return RedirectResponse(url="/admin/dashboard#personal", status_code=303)

@app.post("/api/admin/vault/add")
async def add_model_to_vault(
    version: str = Form(...), 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    vault_dir = os.path.join(BASE_DIR, "data", "vault")
    if not os.path.exists(vault_dir):
        os.makedirs(vault_dir)
    
    file_path = os.path.join(vault_dir, file.filename)
    sha256_hash = hashlib.sha256()
    
    # Guardar archivo y calcular hash simultáneamente
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
        sha256_hash.update(content)
    
    final_hash = sha256_hash.hexdigest()
    
    try:
        new_model = ModelVault(
            version=version, 
            filename=file.filename, 
            sha256_hash=final_hash, 
            upload_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        db.add(new_model)
        db.commit()
    except Exception:
        db.rollback()
        return RedirectResponse(url="/admin/dashboard?error=hash_exists", status_code=303)
        
    return RedirectResponse(url="/admin/dashboard#vault", status_code=303)

@app.get("/api/ops/vault/download/{model_id}")
async def download_model(model_id: int, db: Session = Depends(get_db)):
    model = db.query(ModelVault).filter(ModelVault.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Archivo no encontrado en la bóveda.")
    
    file_path = os.path.join(BASE_DIR, "data", "vault", model.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="El binario físico no existe en el servidor.")
        
    return FileResponse(path=file_path, filename=model.filename, media_type='application/octet-stream')

@app.post("/api/sync/metrics")
async def sync_metrics(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    new_stat = TrainingStat(
        epoch=data.get("epoch"), map50=data.get("map50"), recall=data.get("recall"), 
        loss=data.get("loss"), timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        status=data.get("status"), raw_effort=data.get("raw_effort")
    )
    db.add(new_stat)
    db.commit()
    return {"status": "synchronized"}

@app.post("/api/verify")
async def verify(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    hwid = data.get("hwid")
    short_code = data.get("short_code")
    metadata = data.get("metadata", {})
    ip = request.client.host
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    license = db.query(License).filter(License.hwid == hwid).first()

    if not license:
        license = License(
            hwid=hwid, short_code=short_code, status='Pendiente', last_ip=ip, last_login=now,
            hostname=metadata.get("hostname"), os_version=metadata.get("os_version"),
            cpu_model=metadata.get("cpu"), ram_total=metadata.get("ram")
        )
        db.add(license)
        db.commit()
        return {"status": "Pendiente", "message": "Equipo en espera de activacion."}

    # Actualizar telemetría
    license.last_ip = ip
    license.last_login = now
    license.hostname = metadata.get("hostname")
    license.os_version = metadata.get("os_version")
    license.cpu_model = metadata.get("cpu")
    license.ram_total = metadata.get("ram")
    db.commit()

    if license.status != "Activo":
        return {"status": license.status, "message": f"Acceso {license.status}"}

    # Token firmado
    res_data = f"{hwid}|{license.status}|{license.expiration_date}"
    sig = hmac.new(SECRET_KEY_HMAC, res_data.encode(), hashlib.sha256).hexdigest()
    
    return {"status": "Aceptado", "expiration": license.expiration_date, "signature": sig}

@app.post("/api/models/verify")
async def verify_model(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    model_hash = data.get("sha256")
    model = db.query(ModelVault).filter(ModelVault.sha256_hash == model_hash, ModelVault.status == 'Avalado').first()
    if model:
        return {"status": "Avalado", "version": model.version}
    return {"status": "No Autorizado", "message": "Firma del modelo no coincide con el registro oficial."}

@app.post("/api/ops/flight_log")
async def register_flight(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    new_log = FlightLog(
        operator_id=data.get("op_id"), start_time=data.get("start"), end_time=data.get("end"),
        detections=data.get("detections"), success_rate=data.get("rate"), comments=data.get("comments")
    )
    db.add(new_log)
    db.commit()
    return {"status": "success", "message": "Bitácora sincronizada."}

@app.post("/api/ops/feedback")
async def register_feedback(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    new_feedback = Feedback(
        operator_id=data.get("op_id"), type=data.get("type"), content=data.get("content"),
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    db.add(new_feedback)
    db.commit()
    return {"status": "success", "message": "Informe enviado."}

# --- RUTAS WEB ---
@app.get("/", response_class=HTMLResponse)
async def landing():
    try:
        with open(os.path.join(STATIC_DIR, "index.html"), "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"<h1>Error 404</h1><p>Archivo base no encontrado en {STATIC_DIR}</p>"

@app.get("/admin", response_class=HTMLResponse)
async def admin_login():
    try:
        with open(os.path.join(STATIC_DIR, "admin", "index.html"), "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Error 404</h1><p>Login de administracion no disponible.</p>"

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def dashboard_view():
    try:
        with open(os.path.join(STATIC_DIR, "admin", "dashboard.html"), "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Error 404</h1><p>Dashboard de administracion no disponible.</p>"

@app.get("/operator/dashboard", response_class=HTMLResponse)
async def op_dashboard_view():
    try:
        with open(os.path.join(STATIC_DIR, "operator", "dashboard.html"), "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Error 404</h1><p>Dashboard de operador no disponible.</p>"

@app.post("/admin/action")
async def action(id: int = Form(...), act: str = Form(...), days: int = Form(30), db: Session = Depends(get_db)):
    license = db.query(License).filter(License.id == id).first()
    if not license:
        return RedirectResponse(url="/admin/dashboard", status_code=303)
    
    if act == "on":
        exp = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        license.status = 'Activo'
        license.expiration_date = exp
        license.days_remaining = days
    else:
        license.status = 'Inactivo'
    
    db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=303)

# --- GESTIÓN DE MODELOS TÁCTICOS ---
@app.post("/api/ops/models/upload")
async def upload_tactical_model(
    file: UploadFile = File(...),
    project: str = Form("SISMA_GEN"),
    hash: str = Form(""),
    db: Session = Depends(get_db)
):
    """Recibe modelos desde el SISMA-TRAINER."""
    models_dir = os.path.join(STATIC_DIR, "models")
    if not os.path.exists(models_dir):
        os.makedirs(models_dir)
    
    file_path = os.path.join(models_dir, file.filename)
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    
    # Registrar en DB
    new_model = TacticalModel(
        project=project,
        filename=file.filename,
        version=datetime.now().strftime("%Y%m%d.%H%M"),
        file_hash=hash,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    db.add(new_model)
    db.commit()
    return {"status": "Uploaded", "version": new_model.version}

@app.get("/api/ops/models/latest/{project}")
async def get_latest_model(project: str, db: Session = Depends(get_db)):
    """Informa a la App de Tierra sobre el último modelo disponible."""
    model = db.query(TacticalModel).filter(TacticalModel.project == project).order_by(TacticalModel.id.desc()).first()
    if not model:
        raise HTTPException(status_code=404, detail="No models found")
    
    return {
        "version": model.version,
        "filename": model.filename,
        "hash": model.file_hash,
        "url": f"/static/models/{model.filename}"
    }

if __name__ == "__main__":
    import uvicorn
    # Puerto 10000 solicitado para el VPS
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
