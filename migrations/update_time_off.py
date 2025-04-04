from app import create_app, db
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('app')

app = create_app()
with app.app_context():
    # Create a new table with the desired schema
    db.engine.execute('''
        CREATE TABLE IF NOT EXISTS time_off_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            caregiver_id INTEGER NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            reason VARCHAR(200),
            category VARCHAR(50) NOT NULL DEFAULT 'vacation',
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (caregiver_id) REFERENCES caregivers (id)
        )
    ''')
    
    # Copy existing data without the reason column
    db.engine.execute('''
        INSERT INTO time_off_new (id, caregiver_id, start_date, end_date)
        SELECT id, caregiver_id, start_date, end_date FROM time_off
    ''')
    
    # Drop the old table
    db.engine.execute('DROP TABLE IF EXISTS time_off')
    
    # Rename the new table to the original name
    db.engine.execute('ALTER TABLE time_off_new RENAME TO time_off')
    
    logger.info("Migration completed successfully") 