FROM python:3.12-slim

# from https://docs.streamlit.io/deploy/tutorials/docker#create-a-dockerfile

WORKDIR /valencianow

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

ADD requirements.txt requirements.txt

RUN python -m pip install -r requirements.txt

ADD ui/ ui/

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "ui/src/valencianow/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
