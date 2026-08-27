from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.routes import shops, queue, appointments, analytics, predictions
from app.database import get_db_connection, execute_query
import os

app = FastAPI(
    title="BarberFlow API",
    description="Backend services for discovery, queue scheduling, analytics, and predictions.",
    version="1.0.0"
)

# Enable CORS for frontend local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for the portfolio application demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handling for sqlite errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {str(exc)}"}
    )

# Register routes
app.include_router(shops.router)
app.include_router(queue.router)
app.include_router(appointments.router)
app.include_router(analytics.router)
app.include_router(predictions.router)

@app.get("/api/health")
def health_check():
    """
    Verifies database connection and checks if ML model files are generated on disk.
    """
    db_ok = False
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1;")
        conn.close()
        db_ok = True
    except Exception:
        pass
        
    models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'models')
    models = {
        "demand_model": os.path.exists(os.path.join(models_dir, 'demand_model.pkl')),
        "waiting_time_model": os.path.exists(os.path.join(models_dir, 'waiting_time_model.pkl')),
        "noshow_model": os.path.exists(os.path.join(models_dir, 'noshow_model.pkl'))
    }
    
    return {
        "status": "healthy" if db_ok else "unhealthy",
        "database_connected": db_ok,
        "models_status": models
    }

@app.get("/")
def read_root():
    return {
        "message": "Welcome to the BarberFlow API platform.",
        "docs_url": "/docs",
        "health_check": "/api/health"
    }

@app.get("/api/explorer/{table_name}")
def explore_table(table_name: str):
    valid_tables = ["shops", "services", "customers", "appointments", "visits", "availability", "reviews"]
    if table_name not in valid_tables:
        raise HTTPException(status_code=400, detail="Invalid table name")
        
    # Get columns metadata
    cols_meta = execute_query(f"PRAGMA table_info({table_name});")
    columns = [{"name": c["name"], "type": c["type"]} for c in cols_meta]
    
    # Get rows (limit 25)
    rows = execute_query(f"SELECT * FROM {table_name} LIMIT 25;")
    
    # Get total count
    count_res = execute_query(f"SELECT COUNT(*) as count FROM {table_name};", fetch_all=False)
    total_rows = count_res["count"] if count_res else 0
    
    return {
        "columns": columns,
        "rows": rows,
        "total_rows": total_rows
    }

