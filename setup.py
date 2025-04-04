from setuptools import setup, find_packages

setup(
    name="group_home_scheduler",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'Flask==2.0.1',
        'Flask-SQLAlchemy==2.5.1',
        'python-dateutil==2.8.2',
        'SQLAlchemy==1.4.46',
        'Werkzeug==2.2.3',
        'gunicorn==21.2.0',
        'python-dotenv==1.0.0',
        'google-api-python-client==2.86.0',
        'google-auth-httplib2==0.1.0',
        'google-auth-oauthlib==1.0.0'
    ],
) 