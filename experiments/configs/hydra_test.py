import hydra
from omegaconf import DictConfig, OmegaConf
from hydra.core.hydra_config import HydraConfig
import os

@hydra.main(config_path=".", config_name="experiment_config",version_base=None)
def test_sweep(cfg: DictConfig) -> None:
    """
    A simple test function to verify the Hydra sweep configuration.
    It prints the composed configuration for each run.
    """
    # Get the job number from the Hydra runtime configuration.
    # This is a useful way to see which job is currently running in the sweep.
    job_num = HydraConfig.get().job.num
    print(f"--- Running Job {job_num} ---")
    
    # Print the full, resolved configuration for this specific job.
    # This is the key part of the test, as it shows you exactly what Hydra
    # has composed for each run.
    print(OmegaConf.to_yaml(cfg, resolve=True))
    
    # You can also access specific parameters to verify their values
    print(f"token_limit: {cfg["general_config"]["token_limit"]}")
    print(f"generic_type_allowance: {cfg.general_config.generic_type_allowance}")
    print(f"priming: {cfg.general_config.priming}")
    print("\n")
    logs = OmegaConf.to_yaml(cfg, resolve=True)
    with open("h_results.txt","w") as f:
        f.write(logs)
    


@hydra.main(config_path=".", config_name="experiment_config", version_base=None)
def main(cfg: DictConfig):
    print("Config loaded:", cfg)


if __name__ == "__main__":
    # To run this in sweep mode from your terminal, navigate to the directory
    # containing this file and your 'configs' directory and run:
    # python test_sweep.py -m
    # test_sweep()
    test_sweep()
