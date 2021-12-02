from loguru import logger
from shell import run_cmd
import pathlib

script_folder = pathlib.Path(__file__).parent.resolve()
snap_graph_folder = script_folder / 'snap_graphs'

def make_snap_feature(graph_file, original_path, output_path, *extra_args):
    if output_path.exists():
        logger.debug(f'Already exists: {output_path}')
        return

    cmd = f'gpt {snap_graph_folder / graph_file} -PinFile={original_path} -PoutFile={output_path} ' + ' '.join(extra_args)
    run_cmd(cmd)

def create_features(original_path, feature_folder):
    original_path = pathlib.Path(original_path).absolute()
    feature_folder = pathlib.Path(feature_folder)
    logger.debug(f'Creating features for product: {original_path}')

    make_snap_feature("HH_db.xml", original_path, feature_folder / "HH_db.dim")
    make_snap_feature("HV_db.xml", original_path, feature_folder / "HV_db.dim")
    make_snap_feature("IA.xml", original_path, feature_folder / "IA.dim")
    make_snap_feature("landmask.xml", original_path, feature_folder / "landmask.dim")

def put_metadata_back(feature_folder):
    run_cmd(
        'gpt Merge -SmasterProduct=HH_db.dim -PgeographicError=NaN -t merged.dim HH_db.dim labels.hdr',
        workdir=feature_folder,
    )
