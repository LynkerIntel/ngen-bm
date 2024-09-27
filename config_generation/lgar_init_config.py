from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

from ngen.config.init_config.lgar import Lgar
from ngen.config.init_config.utils import FloatUnitPair

if TYPE_CHECKING:
    from typing import Any

    from pydantic import BaseModel

    from ngen.config_gen.hook_providers import HookProvider


class LgarTmp(Lgar):
    class Config(Lgar.Config):
        extra = "allow"  # type: ignore


class LgarHooks:
    def __init__(self, soil_params_file: Path):
        self.data = {}
        self.data["soil_params_file"] = soil_params_file

    def _defaults(self) -> None:
        # NOTE: I think we can ignore this?
        # self.data["forcing_file"]: Optional[Path]

        self.data["timestep"] = FloatUnitPair(value=3600, unit="s")
        self.data["forcing_resolution"] = FloatUnitPair(value=3600, unit="s")
        # NOTE: not sure if I can ignore this or not. going to make it super
        # long for now
        self.data["endtime"] = FloatUnitPair(value=1000000000, unit="d")

        # TODO: could not use anything in the hf to derive these parameters
        self.data["initial_psi"] = FloatUnitPair(value=2000.0, unit="cm")
        self.data["wilting_point_psi"] = FloatUnitPair(value=15495, unit="cm")

        # NOTE: I think this is unused unless coupled with sft
        self.data["soil_z"] = [42]

        # single 200 cm soil horizon
        self.data["layer_thickness"] = [200]
        # NOTE: toggle if not calibrating
        self.data["calib_params"] = True
        self.data["verbosity"] = "none"
        self.data["sft_coupled"] = False
        self.data["use_closed_form_G"] = False

        self.data["ponded_depth_max"] = 2.0
        # NOM STATS
        self.data["max_valid_soil_types"] = 12

        # NOTE: not in pydantic model
        self.data["adaptive_timestep"] = "true"
        self.data["field_capacity_psi"] = "340.9[cm]"

    def hydrofabric_linked_data_hook(
        self, version: str, divide_id: str, data: dict[str, Any]
    ) -> None:
        giuh: str | list[_HistPair] = data["giuh"] # type: ignore
        if isinstance(giuh, str):
            giuh = json.loads(giuh)
        giuh = [f["frequency"] for f in giuh]
        self.data["giuh_ordinates"] = giuh
        layer_soil_type = data["ISLTYP"]
        if layer_soil_type > 12:
            warnings.warn(
                "Invalid LGAR soil type. Lgar will returns input_precip = ouput_Qout.",
                RuntimeWarning,
            )
        self.data["layer_soil_type"] = [layer_soil_type]

    def build(self) -> BaseModel:
        # apply defaults
        self._defaults()
        return LgarTmp.parse_obj(self.data)

    def visit(self, hook_provider: HookProvider) -> None:
        hook_provider.provide_hydrofabric_linked_data(self)


if __name__ == "__main__":
    import geopandas as gpd
    import pandas as pd

    from ngen.config_gen.file_writer import DefaultFileWriter
    from ngen.config_gen.generate import generate_configs
    from ngen.config_gen.hook_providers import DefaultHookProvider

    hf_file = "/Users/austinraney/github/lynker/benchmark/hf_v211_03366500.gpkg"
    hf_lnk_file = "/Users/austinraney/github/lynker/benchmark/model-attributes_benchmark_2_1_1.parquet"

    hf: gpd.GeoDataFrame = gpd.read_file(hf_file, layer="divides")
    hf_lnk_data: pd.DataFrame = pd.read_parquet(hf_lnk_file)

    hf_lnk_data = hf_lnk_data[hf_lnk_data["divide_id"].isin(hf["divide_id"])]
    hook_provider = DefaultHookProvider(hf=hf, hf_lnk_data=hf_lnk_data)
    file_writer = DefaultFileWriter("./config/")

    def lgar_hooks():
        return LgarHooks(Path("/home/ec2-user/params/vG_params_stat_nom_ordered.dat"))

    generate_configs(
        hook_providers=hook_provider,
        hook_objects=[lgar_hooks],
        file_writer=file_writer,
    )
