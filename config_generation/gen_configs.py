from __future__ import annotations

import contextlib
import os
import subprocess
from pathlib import Path

import geopandas as gpd
import pandas as pd
from ngen.config_gen.generate import BuilderVisitableFn, generate_configs
from ngen.config_gen.hook_providers import DefaultHookProvider

targets = [
    "01105000",
    "01391500",
    "01509000",
    "01643000",
    "02299950",
    "023177483",
    "02421000",
    "02481880",
    "03050000",
    "03217500",
    "03366500",
    "03574500",
    "04112850",
    "04231000",
    "04282000",
    "05061000",
    "05455500",
    "06218500",
    "06469400",
    "06921720",
    "07103700",
    "07187000",
    "07311500",
    "08010000",
    "08020700",
    "08070500",
    "08159000",
    "09112500",
    "09504420",
    "10011500",
    "11147500",
    "11264500",
    "11532500",
    "12048000",
    "12358500",
    "14301000",
]

# change these to fit your needs
PARENT_DIR = Path(__file__).parent
STATIC_DATA = PARENT_DIR / "static"
HF_DIR = PARENT_DIR / "hydrofabric"
HF_LNK_FILE = PARENT_DIR / "model-attributes_benchmark_2_1_1.parquet"


def main() -> int:
    # for target in targets:
    import tempfile

    parent_dir = Path(__file__).resolve().parent
    archive_output = parent_dir / "all_configs.tar.gz"

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        with pushd(root):
            configs_dir = Path(".") / "configs"
            configs_dir.mkdir()

            ret = 0
            for target in targets:
                try:
                    gen_config(configs_dir, HF_DIR, target)
                except Exception as e:
                    ret = 1
                    print(f"failed to generate {target}\n{e!s}")

            subprocess.check_call(f"cp -r {STATIC_DATA!s} {configs_dir!s}", shell=True)
            subprocess.check_call(f"tar czf {archive_output!s} {configs_dir!s}", shell=True)

    return ret


def gen_config(root: Path, hf_dir: Path, target: str):
    hf_file = hf_dir / f"hf_v211_{target}.gpkg"

    hf: gpd.GeoDataFrame = gpd.read_file(hf_file, layer="divides")
    hf_lnk_data: pd.DataFrame = pd.read_parquet(HF_LNK_FILE)
    hf_lnk_data = hf_lnk_data[hf_lnk_data["divide_id"].isin(hf["divide_id"])]

    hooks = {
        "cfe_s_config": cfe_s(),
        "cfe_x_config": cfe_x(),
        "topmodel_config": topmodel(),
        "nom_config": nom(),
        "lasam_config": lasam(),
    }
    output_dir = root / Path(f"hf_v211_{target}")
    for hook in hooks.values():
        hook_provider = DefaultHookProvider(hf=hf, hf_lnk_data=hf_lnk_data)
        file_writer = file_writer_with_output_dir(output_dir)
        generate_configs(
            hook_providers=hook_provider,
            hook_objects=[hook],
            file_writer=file_writer,
        )
    update_topmodel_configs(output_dir, target)


@contextlib.contextmanager
def pushd(p: Path):
    assert p.is_dir()
    pwd = os.getcwd()
    os.chdir(str(p))
    yield
    os.chdir(pwd)


def update_topmodel_configs(input_dir: Path, nwis_id: str):
    assert input_dir.is_dir()
    with pushd(input_dir):
        import subprocess

        import platform
        if platform.system() == "Linux":
            sed_cmd = "sed"
        else:
            sed_cmd = "gsed"

        subprocess.check_call(
            f"find . -name 'Topmodel_*' -type f |  xargs -I {{}} {sed_cmd} -i 's/REPLACE/hf_v211_{nwis_id}/' {{}}",
            shell=True,
        )


from ngen.config_gen.file_writer import _get_file_extension, _get_serializer


def file_writer_with_output_dir(output_dir: Path):
    if output_dir.exists() and not output_dir.is_dir():
        assert False, f"output_dir exists and is not a directory: {output_dir!s}"
    output_dir.mkdir(parents=True, exist_ok=True)

    def writer(id: str | Literal["global"], data: BaseModel):
        class_name = data.__class__.__name__

        if isinstance(data, WriterData):
            class_name = data.name or class_name
            ext = data.ext or _get_file_extension(data.data)
            data = data.data
        else:
            ext = _get_file_extension(data)

        output_file = output_dir / f"{class_name}_{id}.{ext}"
        serializer = _get_serializer(data)
        serializer(output_file)

    return writer


from dataclasses import dataclass


@dataclass
class WriterData:
    data: BaseModel
    name: str | None = None
    ext: str | None = None


def with_name(name: str, bldr):
    def build(self):
        return WriterData(data=bldr(self), name=name)

    return build


def cfe_s() -> BuilderVisitableFn:
    import cfe_init_config

    subclass = type("CfeShaakeCustomName", (cfe_init_config.CfeShaake,), {})
    subclass.build = with_name("CFE_NASH_S", subclass.build)

    return subclass


def cfe_x() -> BuilderVisitableFn:
    import cfe_init_config

    subclass = type("CfeXCustomName", (cfe_init_config.CfeX,), {})
    subclass.build = with_name("CFE_NASH_X", subclass.build)

    return subclass


def topmodel() -> BuilderVisitableFn:
    import topmodel_init_config

    subclass = type("Topmodel", (topmodel_init_config.TopmodelHooks,), {})
    bld = subclass.build

    def build(self):
        data = bld(self)
        return WriterData(data=data, name="Topmodel", ext="dat")

    subclass.build = build

    return subclass


def nom() -> BuilderVisitableFn:
    from functools import partial

    import nom_cfe_pet

    return partial(
        nom_cfe_pet.NoahOWP,
        start_time="201610010000",
        end_time="202109300000",
        parameter_dir=Path("/home/ec2-user/configs/static/"),
    )


def lasam() -> BuilderVisitableFn:
    import lgar_init_config

    def lgar_hooks():
        return lgar_init_config.LgarHooks(
            Path("/home/ec2-user/configs/static/vG_params_stat_nom_ordered.dat")
        )

    return lgar_hooks


if __name__ == "__main__":
    raise SystemExit(main())
