import subprocess
import os

def convert_mpp_to_json(mpp_path):
    """
    Convierte un archivo .mpp a .json usando mpxj-examples.jar y sus dependencias
    """
    if not mpp_path.endswith('.mpp'):
        raise ValueError("Debe proporcionar un archivo .mpp válido.")

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib'))
    classpath = os.pathsep.join([os.path.join(base_dir, jar) for jar in os.listdir(base_dir) if jar.endswith('.jar')])
    json_path = os.path.splitext(mpp_path)[0] + ".json"

    command = [
        'java', '-cp', classpath, 'net.sf.mpxj.sample.MpxjConvert',
        '-f', mpp_path, '-o', json_path
    ]

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Error ejecutando mpxj: {result.stderr}")
    return json_path
