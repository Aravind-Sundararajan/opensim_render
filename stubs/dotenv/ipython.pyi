from .main import find_dotenv as find_dotenv, load_dotenv as load_dotenv
from IPython.core.magic import Magics, line_magic

class IPythonDotEnv(Magics):
    @line_magic
    def dotenv(self, line) -> None: ...

def load_ipython_extension(ipython) -> None: ...
