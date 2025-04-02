# GH Scheduler

A Flask-based web application for managing caregiver schedules and shifts.

## Features

- Calendar view of weekly schedules
- Hourly view of shifts
- Caregiver management
- Shift assignment and removal
- Error handling and logging

## Setup

1. Clone the repository:
```bash
git clone https://github.com/akhils0810/GHScheduler.git
cd GHScheduler
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Deployment on Render

1. Create a new account on [Render](https://render.com) if you don't have one
2. Click "New +" and select "Web Service"
3. Connect your GitHub repository
4. Configure the service:
   - Name: `gh-scheduler` (or your preferred name)
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn wsgi:app`
   - Add the following environment variables:
     - `FLASK_ENV=production`
     - `SECRET_KEY=your-secret-key-here`
     - `DATABASE_URL=your-postgresql-url` (Render will provide this automatically)

5. Click "Create Web Service"

The application will be deployed and available at `https://your-app-name.onrender.com`

## Project Structure

- `app.py`: Main application file
- `models.py`: Database models
- `routes.py`: Route handlers
- `config.py`: Configuration settings
- `templates/`: HTML templates
- `static/`: Static files (CSS, JS)
- `wsgi.py`: WSGI entry point for production
- `Procfile`: Process file for Render deployment

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 