FROM python:3.8

WORKDIR /code

COPY requirements.txt /code/requirements.txt

RUN pip3 install -r requirements.txt

COPY . /code/

CMD ["python3", "bot.py"]
