from flask import Flask
import requests
import os
import logging
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# Включаем дебаг логирование
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.info("Инициализация трейсера...")

trace.set_tracer_provider(
    TracerProvider(
        resource=Resource.create({SERVICE_NAME: "service-a"})
    )
)

# Вместо UDP агента используем HTTP коллектор напрямую
jaeger_collector_url = os.environ.get(
    "JAEGER_COLLECTOR_URL",
    "http://simplest-collector.observability:14268/api/traces"
)
logger.info(f"Jaeger collector URL: {jaeger_collector_url}")

# Используем HTTP вместо UDP
jaeger_exporter = JaegerExporter(
    collector_endpoint=jaeger_collector_url,
)

# Экспортер в консоль (для отладки)
console_exporter = ConsoleSpanExporter()

# Добавляем оба экспортера
trace.get_tracer_provider().add_span_processor(
    SimpleSpanProcessor(jaeger_exporter)
)
trace.get_tracer_provider().add_span_processor(
    SimpleSpanProcessor(console_exporter)
)

logger.info("Добавлены SimpleSpanProcessor (Jaeger HTTP + Console)")

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

@app.route("/")
def create():
    logger.info("Обработка запроса /")
    with trace.get_tracer(__name__).start_as_current_span("create"):
        try:
            logger.info("Отправляем запрос к service-b")
            res = requests.get("http://service-b:8080")
            logger.info(f"Ответ от service-b: {res.status_code}")
            return res.text
        except Exception as e:
            logger.error(f"Ошибка при обращении к service-b: {str(e)}")
            return f"Error calling service-b: {str(e)}", 500