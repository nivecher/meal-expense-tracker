FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Create a volume for the database
VOLUME /app/instance

EXPOSE 5000

# Initialize the database and run the application
CMD ["sh", "-c", "flask init-db && flask run --host=0.0.0.0"] 