# No PythonAnywhere: apague o wsgi padrão e cole isto (troque SEU_USUARIO)
import sys
USERNAME = "SEU_USUARIO"
path = f"/home/{USERNAME}/LinuxSurvival"
if path not in sys.path:
    sys.path.append(path)
from app import app as application
