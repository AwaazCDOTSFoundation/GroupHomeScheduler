from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize SQLAlchemy
db = SQLAlchemy()

def create_app():
    try:
        logger.debug("Starting application creation...")
        app = Flask(__name__)
        
        # Load configuration
        from .config import Config
        app.config.from_object(Config)
        
        # Initialize database
        db.init_app(app)
        
        # Import models here to avoid circular imports
        from .models import Caregiver, Shift
        
        with app.app_context():
            logger.debug("Creating database tables...")
            db.create_all()
            
            # Initialize caregivers if none exist
            if Caregiver.query.count() == 0:
                logger.debug("Initializing caregivers...")
                from .config import ShiftConfig
                for name in ShiftConfig.CAREGIVERS:
                    caregiver = Caregiver(name=name)
                    db.session.add(caregiver)
                db.session.commit()
                logger.debug(f"Added {len(ShiftConfig.CAREGIVERS)} caregivers")
        
        # Register blueprints
        from .routes import views
        app.register_blueprint(views)
        
        logger.debug("Application creation completed successfully")
        return app
    except Exception as e:
        logger.error(f"Error creating application: {str(e)}")
        raise

# Create the application instance
app = create_app() 