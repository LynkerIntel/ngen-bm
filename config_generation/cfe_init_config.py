from __future__ import annotations
import geopandas as gpd
import pandas as pd
from pathlib import Path
import json

from ngen.config_gen.file_writer import DefaultFileWriter
from ngen.config_gen.hook_providers import DefaultHookProvider
from ngen.config_gen.generate import generate_configs
from ngen.config.init_config.cfe import CFE as CFEConfig

from ngen.config_gen.models.cfe import Cfe
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


class CFEConfigExtra(CFEConfig):
    class Config(CFEConfig.Config):
        extra = "allow"


class CfeCommon(Cfe):
    nsubsteps_nash_surface: int

    def hydrofabric_linked_data_hook(
        self, version: str, divide_id: str, data: dict[str, Any]
    ) -> None:
        super().hydrofabric_linked_data_hook(version, divide_id, data)
        if "N_nash_surface" in data:
            self.data["N_nash_surface"] = data["N_nash_surface"]
        else:
            self.data["N_nash_surface"] = 2

        if "K_nash_surface" in data:
            self.data["K_nash_surface"] = data["K_nash_surface"]
        else:
            self.data["K_nash_surface"] = 0.83089

        giuh = data["giuh"]  # type: ignore
        if isinstance(giuh, str):
            giuh = json.loads(giuh)
        giuh = [f["frequency"] for f in giuh]
        self.data["giuh_ordinates"] = giuh

        # Quick fix -- gw_Zmax from NWM params is *most likely* in units of mm
        # but max_gw_storage needs to be in meters, so do the conversion here.
        self.data["max_gw_storage"].value = self.data["max_gw_storage"].value/1000.0

        # the primary gw outlet coefficient (baseflow)
        # cgw from WRF-Hydro NWM is in "m^3/s" which is interestingly
        # 0.005 everywhere
        # We need to rescale this to m/hr
        # Hydrofabic v2.1.1 conus areasqkm distribution is
        """
        mean         14.129473
        std         166.396737
        min           0.000235
        25%           4.565701
        50%           7.337700
        75%          11.065949
        max       65014.294940
        """
        # Since the min and max here are well outside the idealized size (3-10 sqkm), we will use
        # the inter qualitle values for calibration range, and the median for default here
        cgs = self.data['cgw'].value
        cgs = cgs/(7.337700*1000*1000) # now we have m/s, I think, converting sq things to flat is hard
        cgs = cgs*3600 # m/hr
        self.data['cgw'].value = cgs


    def build(self):
        self.data["soil_layer_depths"] = ",".join(
            (str(x) for x in [0.1, 0.4, 1.0, 2.0])
        )
        self.data["max_rootzone_layer"] = 2
        self.data["aet_rootzone"] = False  # NO SMP

        # FIXME does this need updated in the backend CFE???
        self.data["retention_depth_nash_surface"] = 0.001

        # TODO/FIXME self.data['giuh_ordinates']

        # TODO not in Cfe class right now...
        self.data["nsubsteps_nash_surface"] = 10

        # TODO related to GIUH ordiantes...

        # This array length should be the N_nash_storage
        self.data["nash_storage_surface"] = ",".join((str(x) for x in [0.0, 0.0]))

        self.data["surface_runoff_scheme"] = "NASH_CASCADE"

        # This array length should be the N_nash_storage
        self.data["nash_storage_subsurface"] = ",".join((str(x) for x in [0.0, 0.0]))
        self.data["K_nash_subsurface"] = 0.03

        # TODO: not sure what this should be (ask ahmad)
        self.data["N_nash_subsurface"] = 2

        return CFEConfigExtra(__root__=self.data)


# Copied from noahmp SOILPARM.TBL
# indexed by STAS soil type
tension_inflection = [
    0.009,
    0.010,
    0.009,
    0.010,
    0.012,
    0.013,
    0.014,
    0.015,
    0.016,
    0.015,
    0.016,
    0.017,
    0.012,
    0.001,
    0.017,
    0.017,
    0.017,
    0.015,
    0.009,
]

free_water_shape = [
    0.05,
    0.08,
    0.09,
    0.25,
    0.15,
    0.18,
    0.20,
    0.22,
    0.23,
    0.25,
    0.28,
    0.30,
    0.26,
    0.00,
    1.00,
    1.00,
    1.00,
    0.35,
    0.15,
]

tension_water_shape = [
    0.05,
    0.08,
    0.09,
    0.25,
    0.15,
    0.18,
    0.20,
    0.22,
    0.23,
    0.25,
    0.28,
    0.30,
    0.26,
    0.00,
    1.00,
    1.00,
    1.00,
    0.35,
    0.15,
]


class CfeX(CfeCommon):
    def hydrofabric_linked_data_hook(
        self, version: str, divide_id: str, data: dict[str, object]
    ) -> None:
        super().hydrofabric_linked_data_hook(version, divide_id, data)
        # Look up xinanjiang params based on soil type
        soil_type = data["ISLTYP"]
        self.data["a_xinanjiang_inflection_point_parameter"] = tension_inflection[
            soil_type
        ]
        self.data["b_xinanjiang_shape_parameter"] = tension_water_shape[soil_type]
        self.data["x_xinanjiang_shape_parameter"] = free_water_shape[soil_type]
        self.data["urban_decimal_fraction"] = 0.0

    def build(self):
        self.data["surface_partitioning_scheme"] = "Xinanjiang"
        self.data["surface_water_partitioning_scheme"] = "Xinanjiang"
        return super().build()


class CfeShaake(CfeCommon):
    def build(self):
        self.data["surface_partitioning_scheme"] = "Schaake"
        self.data["surface_water_partitioning_scheme"] = "Schaake"
        return super().build()


if __name__ == "__main__":
    import sys

    gpkg = sys.argv[1]
    # basin_id = '1022500'
    # or pass local file paths instead
    # hf_file = f"s3://lynker-spatial/hydrofabric/v20.1/camels/Gage_{basin_id}.gpkg"
    hf_file = gpkg
    hf_lnk_file = "s3://lynker-spatial/hydrofabric/v20.1/model_attributes.parquet"

    hf: gpd.GeoDataFrame = gpd.read_file(hf_file, layer="divides")

    hf_lnk_data: pd.DataFrame = pd.read_parquet(hf_lnk_file)

    hf_lnk_data = hf_lnk_data[hf_lnk_data["divide_id"].isin(hf["divide_id"])]

    hook_provider = DefaultHookProvider(hf=hf, hf_lnk_data=hf_lnk_data)
    # files will be written to ./config
    file_writer = DefaultFileWriter("./config/")

    param_table_dir = Path("./params").resolve()

    generate_configs(
        hook_providers=hook_provider,
        hook_objects=[CfeShaake, CfeX],
        file_writer=file_writer,
    )
