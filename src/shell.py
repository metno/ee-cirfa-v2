from subprocess import run
from loguru import logger

def run_cmd(cmd, workdir=None):
    if workdir is None:
        msg = f'Running command: {cmd}'
    else:
        msg = f'Running command in folder {workdir}: {cmd}'
    
    logger.debug(msg)
    run(cmd, shell=True, cwd=workdir)
