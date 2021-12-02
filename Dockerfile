FROM continuumio/miniconda3:latest

WORKDIR /tmp

RUN apt-get update \
 && apt-get install -y unzip zip

RUN wget -O /tmp/snap_install.sh http://step.esa.int/downloads/7.0/installers/esa-snap_sentinel_unix_7_0.sh \
 && chmod +x snap_install.sh \
 && ./snap_install.sh -q \
 && rm snap_install.sh

ENV PATH="/opt/snap/bin:${PATH}"
ENV LD_LIBRARY_PATH=".:${LD_LIBRARY_PATH}"
ENV MODEL_FOLDER="/tmp/model"

RUN echo '-Xmx8192m' >> /opt/snap/bin/gpt.vmoptions \
 && echo '-Xms2048m' >> /opt/snap/bin/gpt.vmoptions

RUN conda install gdal

# Two options here w.r.t. the model
# It can either be copied into ./model on the local machine before building
# or it can be bind-mounted into /work/model after building the machine
COPY src /tmp
RUN mkdir /workdir
WORKDIR /workdir

RUN pip install -r /tmp/requirements.txt

ENTRYPOINT ["python", "/tmp/run.py"]
