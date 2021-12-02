# Example of using a model trained on Hops from the Polar TEP

# Creating the Docker container

# Publishing the model
To publish the model you will need a development machine on the PolarTEP.
Start the machine and connect to the machine via VPN and then SSH according to the instructions in the PolarTEP documentation.

Build the machine

    cd ee-hops-polartep-in-memory
    docker build -t ee-hops-polartep-in-memory .

Publish the processor using the `publish` script on the development machine

    publish $(pwd)

/srv/PTEP-testdata/S1-EW-GRDM/S1A_EW_GRDM_1SDH_20160802T100634_20160802T100734_012420_01362B_5FC9.SAFE.zip

# See example

https://github.com/logicalclocks/hops-examples/tree/extremeearth/notebooks/extremeearth

https://hub.docker.com/ukhydrographicoffice/esa-snap7-snappy

ukhydrographicoffice/esa-snap7-snappy
