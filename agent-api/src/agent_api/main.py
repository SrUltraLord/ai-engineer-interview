from dotenv import load_dotenv

# Antes de crear la app: Settings.from_env() lee os.environ. No pisa variables ya exportadas.
load_dotenv()

from agent_api.adapters.inbound.http.app import create_app  # noqa: E402

app = create_app()
