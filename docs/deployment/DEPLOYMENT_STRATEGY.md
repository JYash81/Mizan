# Deployment strategy

Build the React application for static hosting on Hostinger. Deploy FastAPI only to a Python-compatible hosting environment; Hostinger Business shared hosting must not be assumed to run FastAPI. Configure a MySQL/MariaDB URL through protected environment variables, use private object storage for future uploads/artifacts, and add external compute providers only through provider adapters. No production database is contacted by this repository's automated tests.
