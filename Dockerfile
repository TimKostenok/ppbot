FROM python:3.11
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade -r requirements.txt
COPY ./ /app/
CMD ["python3", "main.py"]