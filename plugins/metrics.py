from __future__ import annotations

import typing

from ngen.cal import hookimpl
from hydrotools.metrics.metrics import *
import numpy as np
import pandas as pd
from pathlib import Path

#from download_nwm_streamflow import

if typing.TYPE_CHECKING:
    from datetime import datetime
    from ngen.cal.meta import JobMeta
    from ngen.cal.model import ModelExec
    from hypy.nexus import Nexus

class ComputeMetrics:
    def __init__(self) -> None:
        self.sim: pd.Series | None = None
        self.obs: pd.Series | None = None
        self.first_iteration: bool = True
        self.save_obs_nwm: bool = True
        self.eval_range: tuple[datetime, datetime] | None = None
        self.out_file: Path = Path("metrics.parquet")

    def ngen_cal_model_configure(self, config: ModelExec) -> None:
        self.eval_range = config.eval_params._eval_range

    @hookimpl(wrapper=True)
    def ngen_cal_model_observations(
        self,
        nexus: Nexus,
        start_time: datetime,
        end_time: datetime,
        simulation_interval: pd.Timedelta,
    ) -> typing.Generator[None, pd.Series, pd.Series]:
        # In short, all registered `ngen_cal_model_observations` hooks run
        # before `yield` and the results are sent as the result to `yield`
        # NOTE: DO NOT MODIFY `obs`
        obs = yield
        if self.first_iteration and obs is None:
           self.first_iteration = False
           return None
        assert isinstance(obs, pd.Series), f"expected pd.Series, got {type(obs)!r}"
        self.obs = obs
        return obs

    @hookimpl(wrapper=True)
    def ngen_cal_model_output(
        self, id: str | None
    ) -> typing.Generator[None, pd.Series, pd.Series]:
        # In short, all registered `ngen_cal_model_output` hooks run
        # before `yield` and the results are sent as the result to `yield`
        # NOTE: DO NOT MODIFY `sim`
        sim = yield
        if self.first_iteration and sim is None:
           self.first_iteration = False
           return None
        assert isinstance(sim, pd.Series), f"expected pd.Series, got {type(sim)!r}"
        self.sim = sim
        return sim

    @hookimpl
    def ngen_cal_model_iteration_finish(self, iteration: int, info: JobMeta) -> None:
        if self.sim is None:
            return None
        assert self.sim is not None, "make sure `ngen_cal_model_output` was called"
        assert (
            self.obs is not None
        ), "make sure `ngen_cal_model_observations` was called"

        out_dir: Path = info.workdir/"model_outputs"
        out_dir.mkdir(exist_ok=True)

        # index: hourly datetime
        # columns: `obs_flow` and `sim_flow`; units m^3/s
        funcs = {
            "mean_absolute_error": mean_error,
            "mean_squared_error": mean_squared_error,
            "root_mean_squared_error": root_mean_squared_error,
            "volumetric_efficiency": volumetric_efficiency,
            "nash_sutcliffe_efficiency": nash_sutcliffe_efficiency,
            "coefficient_of_persistence": coefficient_of_persistence,
            "coefficient_of_extrapolation": coefficient_of_extrapolation,
            "kling_gupta_efficiency": kling_gupta_efficiency,
        }

        def failure_all_nan():
            return pd.Series(
                data=[np.nan for _ in funcs.keys()], index=funcs.keys()
            )

        if self.sim.empty or self.obs.empty:
            print(
                f"{'SIM' if self.sim.empty else 'OBS'} DATAFRAME IS EMPTY. SETTING ALL METRICS TO NP.NAN"
            )
            metrics = failure_all_nan()
            self.update_metrics(info, metrics, iteration)
            return

        df = pd.merge(self.sim, self.obs, left_index=True, right_index=True)

        if df.empty:
            print("MERGED DATAFRAME IS EMPTY. SETTING ALL METRICS TO NP.NAN")
            metrics = failure_all_nan()
            self.update_metrics(info, metrics, iteration)
            return

        if self.eval_range:
            df = df.between_time(self.eval_range[0], self.eval_range[1])

        metrics = pd.Series(index=funcs.keys())
        for f in funcs.keys():
            try:
                metrics[f] = funcs[f](df["obs_flow"], df["sim_flow"])
            except Exception as e:
                metrics[f] = np.nan
                print(
                    f"FAILED TO COMPUTE METRIC {f}. Setting metric value to np.nan for iteration {iteration}. Metric raised {e}"
                )

        self.update_metrics(info, metrics, iteration)

        model_file = f"sim_obs_{iteration}.parquet"
        df.to_parquet(out_dir/model_file)

    def update_metrics(self, info, metrics, iteration):
        out_dir: Path = info.workdir/"model_outputs"
        out_dir.mkdir(exist_ok=True)
        metric_file: Path = out_dir / self.out_file

        if metric_file.exists():
            metric_df = pd.read_parquet(metric_file)
        else:
            metric_df = pd.DataFrame(index=metrics.index)

        metric_df[iteration] = metrics

        metric_df.to_parquet(metric_file)