import logging

log = logging.getLogger(__name__)


def configure_app_insights(connection_string: str | None) -> bool:
    """Envía logs (incluido `agent_api.audit`) a Application Insights vía OpenTelemetry.

    Requiere el extra `azure` (azure-monitor-opentelemetry). Sin cadena de conexión no hace nada.
    """
    if not connection_string:
        return False
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
    except ImportError:
        log.warning("APPLICATIONINSIGHTS_CONNECTION_STRING definida pero falta el extra 'azure'")
        return False
    configure_azure_monitor(connection_string=connection_string, logger_name="agent_api")
    return True
