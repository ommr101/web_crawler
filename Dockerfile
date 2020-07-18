FROM python:3.7.0-alpine3.7
WORKDIR /web_crawler
ADD . /web_crawler
RUN pip install -r requirements.txt
CMD ["python","main.py"]
