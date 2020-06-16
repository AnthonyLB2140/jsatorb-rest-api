# -----------------------------------------------------------------------------
# JSatOrb project: Dockerization of the JSatOrb GUI Angular server
# -----------------------------------------------------------------------------
# Python 3.7
# Anaconda (conda) 4.5.12
# -----------------------------------------------------------------------------

# Use miniconda 3 v4.5.12 base image 
FROM continuumio/miniconda3:4.5.12

# Copy the environment file in the container
COPY jsatorbenv.yml /tmp/jsatorbenv.yml

# Create the JSatOrb virtual environment
RUN conda env create -f /tmp/jsatorbenv.yml

# Add the environment activation into the user's bash script
RUN echo "source activate JSatOrbEnv" > ~/.bashrc

# -----------------------------------------------------------------------------
# [OREKIT_10.2_SNAPSHOT_ONLY] Activate the 2 lines below if the official Orekit 
# v10.2 is still not released yet.
COPY orekit-10.2-py37he1b5a44_0.tar.bz2 /tmp/orekit-10.2-py37he1b5a44_0.tar.bz2
RUN conda install -n JSatOrbEnv /tmp/orekit-10.2-py37he1b5a44_0.tar.bz2
# -----------------------------------------------------------------------------

# Add the JSatOrb's Anaconda environment binary folder into the PATH
ENV PATH /opt/conda/envs/JSatOrbEnv/bin:$PATH

# Set working dir
WORKDIR /app

# Create the REST API and the different backend parts folders.
RUN mkdir -p /app/jsatorb-visibility-service/src \
&&  mkdir -p /app/jsatorb-eclipse-service/src \
&&  mkdir -p /app/jsatorb-date-conversion/src \
&&  mkdir -p /app/jsatorb-common/src \
&&  mkdir -p /app/jsatorb-coverage-service/src \
&&  mkdir -p /app/jsatorb-rest-api/src

# -----------------------------------------------------------------------------
# Copy the different backend parts contents into the container.
# -----------------------------------------------------------------------------

# jsatorb-visibility-service
COPY ../jsatorb-visibility-service/src jsatorb-visibility-service/src
COPY ./orekit-data.zip jsatorb-visibility-service

# jsatorb-eclipse-service
COPY ../jsatorb-eclipse-service/src jsatorb-eclipse-service/src
COPY ./orekit-data.zip jsatorb-eclipse-service

# jsatorb-date-conversion
COPY ../jsatorb-date-conversion/src jsatorb-date-conversion/src
COPY ./orekit-data.zip jsatorb-date-conversion

# jsatorb-common
COPY ../jsatorb-common/src jsatorb-common/src
COPY ./orekit-data.zip jsatorb-common

# jsatorb-coverage-service
COPY ../jsatorb-coverage-service/src jsatorb-coverage-service/src
COPY ./orekit-data.zip jsatorb-coverage-service

# JSatOrb's REST API
COPY ./orekit-data.zip jsatorb-rest-api
COPY ./src jsatorb-rest-api/src

# Start the JSatOrb REST API
CMD [ "python", "./src/JSatOrbREST.py" ]
