# Example of using a model trained on Hops from the Polar TEP

# Creating the Docker container

# Publishing the model
To publish the model you will need a development machine on the PolarTEP.
Start the machine and connect to the machine via VPN and then SSH according to the instructions in the PolarTEP documentation.

You will need to either include the model in `src/model` or mount the the model to `/tmp/model` in the docker container at run time.

Build the machine

    cd ee-cirfa-v2 
    docker build -t ee-cirfa-v2 .

Publish the processor using the `publish` script on the development machine

    publish $(pwd)


# Running outside PolarTEP

    cd ee-cirfa-v2
    docker build -t ee-cirfa-v2 .

The satellite image to be processed will need to be mounted into the container at run time using `-v` and then the location where it is mounted is used as an argument to the docker container entrypoint. If the model was not built into the docker container, this can also be mounted at run time.

    docker run -v /path/to/local/image.zip:/workdir/image.zip -v /path/to/local/model:/tmp/model ee-cirfa-v2:0.1 /workdir/image.zip

Example:

    docker run -v ~/data/ARCSAR_TTX/S1A_EW_GRDM_1SDH_20191228T063938_20191228T064042_030545_037F8B_D990.zip:/work/S1A_EW_GRDM_1SDH_20191228T063938_20191228T064042_030545_037F8B_D990.zip -v $PWD/../model:/work/model alistaire/ee-cirfa-v2:0.1 /work/S1A_EW_GRDM_1SDH_20191228T063938_20191228T064042_030545_037F8B_D990.zip

# See examples

https://github.com/logicalclocks/hops-examples/tree/extremeearth/notebooks/extremeearth

https://hub.docker.com/ukhydrographicoffice/esa-snap7-snappy

ukhydrographicoffice/esa-snap7-snappy
