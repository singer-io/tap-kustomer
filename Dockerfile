FROM python:3.8.1

RUN groupadd -g 1001 -r tap-kustomer &&\
    useradd -u 1001 -r -g tap-kustomer -d \/home/tap-kustomer -s /sbin/nologin tap-kustomer

RUN mkdir /home/tap-kustomer && \
    chown -R tap-kustomer:tap-kustomer /home/tap-kustomer

#COPY requirements_dev.txt /
#RUN pip install -r /requirements_dev.txt
COPY . /app
WORKDIR /app

COPY catalog.json /home/tap-kustomer/kustomer-catalog.json

RUN pip install .

USER tap-kustomer
CMD sh get-config.sh && tap-kustomer --config /home/tap-kustomer/kustomer-config.json --state kustomer-state.json --catalog catalog.json | target-stitch --config /home/singer-dialpad/stitch-config.json