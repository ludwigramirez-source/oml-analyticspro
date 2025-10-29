import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from starlette.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Create the main app without a prefix
app = FastAPI(
    title="OmniLeads Analytics API",
    description="API REST para análisis de datos de OmniLeads",
    version="2.0.0"
)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {
        "message": "OmniLeads Analytics API",
        "version": "2.0.0",
        "status": "running"
    }


@api_router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "postgresql"
    }

# Configure logging FIRST
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add CORS middleware BEFORE routing
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],  # Allow all origins for development
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the router in the main app
app.include_router(api_router)

# Include Analytics router
try:
    from analytics.routes.analytics_routes import router as analytics_router
    app.include_router(analytics_router)
    logger.info("Analytics module loaded successfully")
except Exception as e:
    logger.warning(f"Analytics module not loaded: {e}")

# Include Debug router (temporal)
try:
    from analytics.routes.debug_routes import router as debug_router
    app.include_router(debug_router)
    logger.info("Debug module loaded successfully")
except Exception as e:
    logger.warning(f"Debug module not loaded: {e}")
