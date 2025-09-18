FROM python:3.12-slim 
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy app + templates/static
COPY app.py .
COPY templates ./templates
# (add this if you later add a static/ folder)
# COPY static ./static

EXPOSE 8080
CMD ["python", "app.py"]
