import os
import subprocess
from pathlib import Path

HERE = os.path.dirname(__file__)
RESOURCES_DIR = Path(f"{HERE}/resources")

CLONE_CONFIGS = {
    # ACCESS-OM2, branch: release-1deg_jra55_ryf
    "om2-1deg": {
        "repo_url": "https://github.com/ACCESS-NRI/access-om2-configs.git",
        "branch": "release-1deg_jra55_ryf",
        "file_list": [
            "manifests/",
            "config.yaml",
            "accessom2.nml",
            "metadata.yaml",
            "LICENSE",
        ],
        "commit": "3537bca",
    },
    # ACCESS-OM2, branch: dev-025deg_jra55_iaf_bgc
    "om2-025deg": {
        "repo_url": "https://github.com/ACCESS-NRI/access-om2-configs.git",
        "branch": "dev-025deg_jra55_iaf_bgc",
        "file_list": [
            "manifests/",
            "config.yaml",
            "accessom2.nml",
            "metadata.yaml",
            "LICENSE",
        ],
        "commit": "bf3f0e2",
    },
    # ACCESS-OM3, branch: dev-MC_100km_jra_ryf
    "om3-100km": {
        "repo_url": "https://github.com/ACCESS-NRI/access-om3-configs.git",
        "branch": "dev-MC_100km_jra_ryf",
        "file_list": ["manifests/", "config.yaml", "nuopc.runconfig"],
        "commit": "9071557",
    },
    # ACCESS-OM3, branch: dev-MCW_100km_jra_ryf
    "om3-100km-wav": {
        "repo_url": "https://github.com/ACCESS-NRI/access-om3-configs.git",
        "branch": "dev-MCW_100km_jra_ryf",
        "file_list": ["manifests/", "config.yaml", "nuopc.runconfig", "wav_in"],
        "commit": "d7a19b4",
    },
    # ACCESS-ESM1.5, branch: release-preindustrial+concentrations
    "esm1p5-prein": {
        "repo_url": "https://github.com/ACCESS-NRI/access-esm1.5-configs.git",
        "branch": "release-preindustrial+concentrations",
        "file_list": [
            "manifests/",
            "ice/",
            "atmosphere/",
            "config.yaml",
            "metadata.yaml",
        ],
        "commit": "1e9f8ec",
    },
    # ACCESS-ESM1.6, branch: dev-amip
    "esm1p6-amip": {
        "repo_url": "https://github.com/ACCESS-NRI/access-esm1.6-configs.git",
        "branch": "dev-amip",
        "file_list": ["config.yaml"],
        "commit": "a875585",
    },
    # ACCESS-ESM1.6, branch: dev-preindustrial+concentrations
    "esm1p6-prein": {
        "repo_url": "https://github.com/ACCESS-NRI/access-esm1.6-configs.git",
        "branch": "dev-preindustrial+concentrations",
        "file_list": ["config.yaml"],
        "commit": "946134f",
    },
}


def clone_config_repo(config_name, config_dir):
    """Clone necessary config files from a designated branch of a git repository.
    Parameters:
    ----------
    config_name (str): model and branch of the config to clone, which should be a key of CLONE_CONFIGS
    config_dir (Path): the directory to clone the config files into

    Returns:
    ----------
    branch (str): branch name where the config files are cloned from
    """
    branch = CLONE_CONFIGS[config_name]["branch"]

    # Clone the repository with no checkout
    clone_cmd = f"git clone --filter=blob:none --no-checkout {CLONE_CONFIGS[config_name]['repo_url']} {config_dir.name}"
    try:
        subprocess.run(clone_cmd, cwd=config_dir.parent, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error cloning repository: {e}")
        raise

    # Set up sparse checkout to only get the necessary files from the specified branch
    # reset to the specific commit for version control
    cmds = [
        "git sparse-checkout init --no-cone",
        f"git sparse-checkout set {' '.join(CLONE_CONFIGS[config_name]['file_list'])}",
        f"git checkout {branch}",
        f"git reset --hard {CLONE_CONFIGS[config_name]['commit']}",
    ]
    try:
        for cmd in cmds:
            subprocess.run(cmd, cwd=config_dir, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error setting up sparse checkout: {e}")
        raise

    return branch
