# Key NextGen Components

## ngen-cal
Commit id [bb311029c5a1959628fa22c109016140d3997bd5](https://github.com/NOAA-OWP/ngen-cal/commit/bb311029c5a1959628fa22c109016140d3997bd5) used from https://github.com/NOAA-OWP/ngen-cal

## ngen
Commit id [230929ac40586434b771ce4d8eb74dbab9158bf4](https://github.com/NOAA-OWP/ngen/commit/230929ac40586434b771ce4d8eb74dbab9158bf4) used from https://github.com/NOAA-OWP/ngen/

Relevant Build Options:
```sh
-DNGEN_WITH_SQLITE:=On -DNETCDF_ACTIVE:=On -DBMI_C_LIB_ACTIVE:=On -DBMI_FORTRAN_ACTIVE:=On -DNGEN_ACTIVATE_PYTHON:=On -DNGEN_ACTIVATE_ROUTING:=On -DUDUNITS_ACTIVE:=On -DUDUNITS_QUIET:=On
```

## Model Formulations Used
All formulations were built for ngen/framework use.

### Sloth
Commit id [48cd8082878fdb8a6f0e2337a5b375be5b71384c](https://github.com/NOAA-OWP/SLoTH/commit/48cd8082878fdb8a6f0e2337a5b375be5b71384c) used from https://github.com/NOAA-OWP/SLoTH

### Noah-Owp-Modular
Commit id [0abb891b48b043cc626c4e4bbd0efe54ad357fe1](https://github.com/NOAA-OWP/noah-owp-modular/commit/0abb891b48b043cc626c4e4bbd0efe54ad357fe1) used from https://github.com/NOAA-OWP/noah-owp-modular

### CFE
Commit id [29231c4004b13882145c2e75fcbe2506a592478c](https://github.com/NOAA-OWP/cfe/commit/29231c4004b13882145c2e75fcbe2506a592478c) used from https://github.com/NOAA-OWP/cfe/

### Topmodel
Commit id [ebd24a4b45123991217835fe6808d71cd1d5104c](https://github.com/NOAA-OWP/topmodel/commit/ebd24a4b45123991217835fe6808d71cd1d5104c) used from https://github.com/NOAA-OWP/topmodel/

### Lasam/Lgar
Commit id [fe0f2245a283c884f81da5d1c4be5b14de514d4d](https://github.com/NOAA-OWP/LGAR-C/commit/fe0f2245a283c884f81da5d1c4be5b14de514d4d) used from https://github.com/NOAA-OWP/LGAR-C/

### t-route
Commit id [eed1f8ad34604f1ee971e57a3226164bb135d86a](https://github.com/NOAA-OWP/t-route/commit/eed1f8ad34604f1ee971e57a3226164bb135d86a) used from https://github.com/NOAA-OWP/t-route

# Transient dependencies with potential impact

## hypy
Commit id [d6a6d1a0881fc0ff448d718e7798e4cbe1cf7f77](https://github.com/NOAA-OWP/hypy/commit/d6a6d1a0881fc0ff448d718e7798e4cbe1cf7f77) used from https://github.com/NOAA-OWP/hypy/

## hydrotools
Pypi version 2.2.2

## Python
Version 3.9.16

>[!NOTE]
> See [python_freeze.txt](python_freeze.txt) for full list of python environment
