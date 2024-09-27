from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict
import typing_extensions

from ngen.config.init_config.topmodel import Topmodel, TopModelParams, TopModelSubcat
from ngen.config.path_pair import PathPair

if TYPE_CHECKING:
    from typing import Any

    from pydantic import BaseModel

    from ngen.config_gen.hook_providers import HookProvider


class _HistPair(TypedDict):
    frequency: float
    v: float


class TopmodelHooks:
    def __init__(self):
        self.data = {}
        self.subcats = {}
        self.params = {}
        self.divide_id: str = ""

    def _defaults(self) -> None:
        self._default_init_config()
        self._default_subcats()
        self._default_params()

    def hydrofabric_linked_data_hook(
        self, version: str, divide_id: str, data: dict[str, Any]
    ) -> None:
        self.divide_id = divide_id

        # params
        self.params["subcat"] = f"Extracted study basin: {divide_id}"
        self.subcats["subcat"] = f"Extracted study basin: {divide_id}"
        # from: https://github.com/ajkhattak/basin_workflow/blob/ac8de7a7fcbb3d002d8967e81d3e89c23bf0e99a/basin_workflow/generate_files/configuration.py#L409C19-L409C95
        self.data["title"] = f"Extracted study basin: {divide_id}"

        twi: str | list[_HistPair] = data["twi"]
        if isinstance(twi, str):
            twi: list[_HistPair] = json.loads(twi)

        # subcats
        # NOTE: not sure about these; need to ask Ahmad
        # frequency, value
        dist_area_lnaotb = [f["frequency"] for f in twi]
        lnaotb = [f["v"] for f in twi]
        self.subcats["dist_area_lnaotb"] = dist_area_lnaotb
        self.subcats["lnaotb"] = lnaotb
        self.subcats["num_topodex_values"] = len(dist_area_lnaotb)

        # TODO: refactor; this is redundant
        width_dist: str | list[_HistPair] = data["width_dist"]
        if isinstance(width_dist, str):
            width_dist: list[_HistPair] = json.loads(width_dist)

        cum_dist_area_with_dist = [f["frequency"] for f in width_dist]
        dist_from_outlet = [f["v"] for f in width_dist]
        self.subcats["cum_dist_area_with_dist"] = cum_dist_area_with_dist
        self.subcats["dist_from_outlet"] = dist_from_outlet
        self.subcats["num_channels"] = len(dist_from_outlet)

    def build(self) -> BaseModel:
        assert (
            self.divide_id != ""
        ), "`divide_id` must not have been provided correctly in `hydrofabric_linked_data_hook`"

        # apply defaults
        self._defaults()

        # create inner `subcat` and `params` pydantic model instances and
        # create PathPair objects that bind them to a filename.
        # See overriden `TopmodelWriteInnerConfigs` class for how these
        # instances get written to disk.
        subcat_path = Path(f"subcat_{self.divide_id}.dat")
        params_path = Path(f"params_{self.divide_id}.dat")
        subcat = TopModelSubcat.parse_obj(self.subcats)
        params = TopModelParams.parse_obj(self.params)
        self.data["subcat"] = PathPair[TopModelSubcat].with_object(
            subcat, path=subcat_path
        )
        self.data["params"] = PathPair[TopModelParams].with_object(
            params, path=params_path
        )
        return TopmodelWriteInnerConfigs.parse_obj(self.data)

    def visit(self, hook_provider: HookProvider) -> None:
        hook_provider.provide_hydrofabric_linked_data(self)

    def _default_init_config(self) -> None:
        self.data["stand_alone"] = 0

    def _default_subcats(self) -> None:
        # subcats
        self.subcats["num_sub_catchments"] = 1
        self.subcats["imap"] = 0

        # NOTE: may want to enable this (1) on for debugging purposes
        self.subcats["yes_print_output"] = 0

        # `twi_dist_4`
        self.subcats["area"] = 1
        # TODO: should this always be 1? b.c. NextGen / HF?
        # self.subcats["num_channels"] = 1

    def _default_params(self) -> None:
        # from: https://github.com/ajkhattak/basin_workflow/blob/ac8de7a7fcbb3d002d8967e81d3e89c23bf0e99a/basin_workflow/generate_files/configuration.py#L409C19-L409C95
        self.params["szm"] = 0.032
        self.params["t0"] = 5.0
        self.params["td"] = 50.0
        self.params["chv"] = 3600.0
        self.params["rv"] = 3600.0
        self.params["srmax"] = 0.05
        self.params["q0"] = 0.0000328
        self.params["sr0"] = 0.002
        self.params["infex"] = 0
        self.params["xk0"] = 1.0
        self.params["hf"] = 0.02
        self.params["dth"] = 0.1


class TopmodelWriteInnerConfigs(Topmodel):
    @typing_extensions.override
    def to_file(self, p: Path, *_) -> None:
        # this is something like: f"subcat_{self.divide_id}.dat"
        self.subcat = self.subcat.with_path(p.parent / Path(self.subcat))
        self.params = self.params.with_path(p.parent / Path(self.params))
        assert self.subcat.write(), f"failed to write subcat: {Path(self.subcat)}"
        assert self.params.write(), f"failed to write params: {Path(self.params)}"

        # TODO: fix file name; should be nwis loc id
        vm_root = Path("/home/ec2-user/configs/REPLACE/")
        self.subcat = vm_root / Path(self.subcat.name)
        self.params = vm_root / Path(self.params.name)
        super().to_file(p)


if __name__ == "__main__":
    import geopandas as gpd
    import pandas as pd

    from ngen.config_gen.file_writer import DefaultFileWriter
    from ngen.config_gen.generate import generate_configs
    from ngen.config_gen.hook_providers import DefaultHookProvider

    hf_file = "/Users/austinraney/github/lynker/benchmark/hf_v211_01105000.gpkg"
    hf_lnk_file = "/Users/austinraney/github/lynker/benchmark/model-attributes_benchmark_2_1_1.parquet"

    hf: gpd.GeoDataFrame = gpd.read_file(hf_file, layer="divides")
    hf_lnk_data: pd.DataFrame = pd.read_parquet(hf_lnk_file)
    target = "cat-9494"
    hf = hf[hf["divide_id"] == target]
    hf_lnk_data = hf_lnk_data[hf_lnk_data["divide_id"] == target]

    hook_provider = DefaultHookProvider(hf=hf, hf_lnk_data=hf_lnk_data)
    file_writer = DefaultFileWriter("./config/")

    generate_configs(
        hook_providers=hook_provider,
        hook_objects=[TopmodelHooks],
        file_writer=file_writer,
    )
