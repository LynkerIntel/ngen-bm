# Becnchamrking the NextGen Framework

This repository contains configurations, templates, and some code used for running initial benchmarks of four different NextGen Formulations.

# Getting Started

We will assume a valid ngen build exists, see [build](build.md) for details on the model engine and formulation builds used for this effort.

Activate the `ngen venv`, with the vairous python dependencies noted in the build notes.

```sh
source <path_to_ngen_venv>/bin/activate
```

# Data sources
All required data for the benchmarking can currently be found on the `s3://ngen-bm` bucket.  These can also be extracted from an archive for use, provided the relevant inputs described below are available.

Key inputs are
### hydrofabric
This directory contains NextGen Hydrofabric v2.1.1 geopackage domains for each of the benchmark locations.

### basin_info
@snowhydrology TODO

### forcing

The forcing data used to run the models, must contain at least the calibration and validation time periods.  This work used AORC data with a simple weighted average downsampling to each hydrofabric divide.  The netcdf ngen supported format was used.

>[!NOTE]
> The unit attribute for `APCP_surface` is *intentionally* wrong, and is set to `mm/hr` to allow the model engine to do unit conversions of the precip on behalf of models which assume the mass flux is equivalent to `mm/hr`.

# Generate additaional basin attributes
The GIUH (Geomorphological Instantaneous Unit Hydrograph) and Nash Cascade Surface parameters are obtained using an R-based workflow [here](https://github.com/ajkhattak/basin_workflow/). These parameters can be computed using the following steps:
  - Clone `git clone https://github.com/ajkhattak/basin_workflow`
  - Setup `workflow_dir`, `output_dir`, `gpkg_model_params` in the configureation file [here](https://github.com/ajkhattak/basin_workflow/blob/master/basin_workflow/configs/config_workflow.yaml)
  - from terminal run `python <path_to_basin_workflow_repo>/basin_workflow/main.py -gpkg`

**Note 1** The workflow requires installation of `hydrofabric` and other required packages. The script has been designed to configure most of the required packages, however, if a package is missing the user should install it manually.

**Note 2** The script can be run directly from RStudio too.

# Generate ngen bmi configuration files

The [`gen_configs.py`](./config_generation/gen_configs.py) script can generate `init_config` configuration files for the 4 NextGen benchmark formulations.
Configuration files are written to a gzipped tar archive with the name `all_configs.tar.gz` in the parent directory of `gen_configs.py`.
The archive file has a directory structure that looks as follows:

```
configs
└── hf_v211_01105000
    ├── CFE_NASH_S_cat-9459.ini
    ├── CFE_NASH_X_cat-9459.ini
    ├── LgarTmp_cat-9459.ini
    ├── NoahOWP_cat-9459.namelist
    ├── Topmodel_cat-9459.dat
    ├── params_cat-9459.dat
    └── subcat_cat-9459.dat
```

The archive has a single root directory, `config`, and subdirectories for each gage in the exercise.
Each subdirectory contains `init_config` configuration files for each aforementioned bmi module.

Configuration file fields are populated from either default values, hydrofabric `model-attributes`, or hydrofabric `divides` information.
These mappings are captured programmatically in the `./config_generation/*_init config.py` python modules.

The data requirements of `gen_configs.py` are:
    - basin scale hydrofabrics; expected to be located in `./config_generation/hydrofabrics/` and follow the naming convention `hf_v211_01105000.gpkg`.
    - exercise scale hydrofabric model-attributes information; expected to be located at`./config_generation/model-attributes_benchmark_2_1_1.parquet`
    - NOM and LASAM static parameter tables; expected to be located in `./config_generation/static`

# Use realization and configuration templates

This reposotiry contains realization, ngen-cal, and t-route templates which are used to produce the calibration results.

## Realization Templates
Copy the formulation realization template to calibrate, e.g.

`realizations/nom_cfe_nash_s.json` to your working directory, and modify the following template strings

- CONFIG_DIR : the directory which bmi configuration files are stored.
- HYDROFAB_INPUT : the hydrofabric geopackage name prefix, e.g. `hf_211_<location>`

>[!NOTE] 
>These realizations assumes
> BMI libs are located in `/lib`
> Forcing data is under `/home/ec2-user/local_data/forcing/1979_to_2024/`
> and
> Routing configuration files are under `/home/ec2-user/`

Each of these paths may need adjusted in each realization based on your environment and setup.

## Configuration Templates

Next you need to pick the ngen-cal configuration template based on the formulation to run and copy it to your working directory, e.g.

`templates/nom_cfe_nash_s_template.yaml`

In this template file, you will need to modify the following template strings

- WORKDIR_INPUT : The name of a working directory to hold the calibration results in, this MUST be an absolute path!
- NGEN_INPUT : Absolute path to the `ngen` model engine binary
- REALIZATION_INPUT : Path to the realization setup in the previous step
- GPKG_INPUT: Hydrofabric geopackage (needs to be the same location configured in the realization step)
- EVAL_FEAT_INPUT: The hydrofabric identifier of the waterbody coinciding with the downstream gage where evaluation will occur, e.g. `wb-012345`.  Note this information is in the basin_info data for the benchmarking excercise.

## Routing Configuration

Finally, copy both `templates/routing_template.yaml` and `templates/routing_validation_template.yaml` to your working directory and edit the following template string in each file

- GPKG_INPUT : The hydrofabric geopackage input for the location

# Run the calibration experiment

With all the files created in the current working dir and their template strings updated accordingly, simply run `ngen-cal`

```sh
python -m ngen.cal <config.yaml>
```
where `<config.yaml>` is the ngen-cal config created from the formulation template, e.g. `cfe_nash_s_template.yaml`

>[!NOTE]
> The plugins directory of this repository MUST be in the same working directory where `ngen-cal` is launched from!
