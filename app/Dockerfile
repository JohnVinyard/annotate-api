FROM ubuntu:16.04

EXPOSE 8000

RUN apt-get update
RUN apt-get install wget bzip2 -y

RUN echo 'export PATH=/opt/conda/bin:$PATH' > /etc/profile.d/conda.sh \
    && wget https://repo.continuum.io/miniconda/Miniconda3-4.3.21-Linux-x86_64.sh \
    && /bin/bash /Miniconda3-4.3.21-Linux-x86_64.sh -b -p /opt/conda \
    && rm /Miniconda3-4.3.21-Linux-x86_64.sh

ENV PATH /opt/conda/bin:$PATH

RUN pip install falcon gunicorn pymongo

COPY *.py remote/

CMD gunicorn app:application \
    --bind 0.0.0.0:8000 --workers 4 --max-requests 1000 \
    --max-requests-jitter 150 --reload --chdir remote/