from flask import Flask, render_template, request, redirect, url_for, flash
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.trace import SpanKind
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from time import perf_counter
import logging
import json
import os
import time

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# Flask App Initialization
app = Flask(__name__)
app.secret_key = 'secret' 
COURSE_FILE = 'course_catalog.json'

# OpenTelemetry Setup
resource = Resource.create({"service.name": "course-catalog-service"})

trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

jaeger_exporter = JaegerExporter(agent_host_name="localhost",agent_port=6831,)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)

# Metrics Setup
metric_reader = PeriodicExportingMetricReader(ConsoleMetricExporter())
meter_provider = MeterProvider(metric_readers=[metric_reader])
meter = meter_provider.get_meter("course-catalog-service")

total_requests_counter = meter.create_counter(
    name="total_requests_index",
    description="Total number of requests",
    unit="1",
)

exception_counter = meter.create_counter(
    name="exceptions_index",
    description="Total number of exceptions",
    unit="1",
)

processing_time_histogram = meter.create_histogram(
    name="request_processing_time",
    description="Time taken to process requests",
    unit="ms"
)

FlaskInstrumentor().instrument_app(app)


# Utility Functions
def load_courses():
    """Load courses from the JSON file."""
    if not os.path.exists(COURSE_FILE):
        return []
    with open(COURSE_FILE, 'r') as file:
        return json.load(file)


def save_courses(data):
    """Save new course data to the JSON file."""
    courses = load_courses()
    courses.append(data) 
    with open(COURSE_FILE, 'w') as file:
        json.dump(courses, file, indent=4)

def validate_form_data(form_data):
    """Validate the form data."""
    required_fields = ['code', 'name', 'instructor']
    for field in required_fields:
        if not form_data.get(field).strip():
            flash(f"Field '{field}' is required.", "error")
            logger.warning({
                'event': 'Form_validation_warning',
                'missing_field': field,
                'user_ip': request.remote_addr
            })
            return False
    return True

# ROUTES
@app.route('/')
def index():
    total_requests_counter.add(1,{"index": "/"})
    start_time = perf_counter()
    with tracer.start_as_current_span("index", kind=SpanKind.SERVER) as span:
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", request.url)
        span.set_attribute("user.ip", request.remote_addr)
        logger.info({
            'event':'Index_page_loaded',
            'user_ip': request.remote_addr,
        })
    processing_time_histogram.record((perf_counter() - start_time)*1000, {"index": "/"})
    return render_template('index.html')

@app.route('/catalog')
def course_catalog():
    total_requests_counter.add(1,{"catalog": "/catalog"})
    start_time = perf_counter()
    with tracer.start_as_current_span("course-catalog", kind=SpanKind.SERVER) as span:
        courses = load_courses()
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", request.url)
        span.set_attribute("user.ip", request.remote_addr)
        span.set_attribute("courses.count", len(courses))

        logger.info({
            'event':'Course_catalog_loaded',
            'courses_count': len(courses),
            'user_ip': request.remote_addr,
        })
    processing_time_histogram.record((perf_counter() - start_time)*1000, {"catalog": "/"})
    return render_template('course_catalog.html', courses=courses)


@app.route('/add_course', methods=['GET', 'POST'])
def add_course():
    start_time = perf_counter()
    logger.info({
        'event':'Add_course_page_loaded',
        'user_ip': request.remote_addr,
    })
    total_requests_counter.add(1,{"add_course": "/add_course"})
    if request.method == 'POST':
        with tracer.start_as_current_span("add-course", kind=SpanKind.SERVER) as span:
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", request.url)
            span.set_attribute("user.ip", request.remote_addr)

            # Validate the form data
            if not validate_form_data(request.form):
                logger.warning({
                    'event':'Form_validation_failed',
                    'user_ip': request.remote_addr
                })
                return redirect(url_for('add_course'))

            course = { key : request.form[key] for key in ['code', 'name', 'instructor','semester','schedule','classroom','prerequisites','grading','description'] }
            save_courses(course)
            flash(f"Course '{course['name']}' added successfully!", "success")
            span.set_attribute("course.code", course['code'])
            span.set_attribute("course.name", course['name'])
            
            
            logger.info({
                'event':'Course_added',
                'course_name': course['name'],
                'user_ip': request.remote_addr,
            })

        return redirect(url_for('course_catalog'))
    processing_time_histogram.record((perf_counter() - start_time)*1000, {"add_course": "/"})
    return render_template('add_course.html')

@app.route('/course/<code>')
def course_details(code):
    start_time = perf_counter()
    total_requests_counter.add(1,{"course_code": "/course/<code>"})
    with tracer.start_as_current_span("course-details", kind=SpanKind.SERVER) as span:
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", request.url)
        span.set_attribute("user.ip", request.remote_addr)
        span.set_attribute("course.code", code)

        courses = load_courses()
        course = next((course for course in courses if course['code'] == code), None)
        
        if not course:
            flash(f"No course found with code '{code}'.", "error")
            logger.error({
                'event':'Course_not_found',
                'course_code': code,
                'user_ip': request.remote_addr
            })
            return redirect(url_for('course_catalog'))
        
        logger.info({
            'event':'Course_details_loaded',
        })
    processing_time_histogram.record((perf_counter() - start_time)*1000, {"course_details": "/"})
    return render_template('course_details.html', course=course)


# ERROR HANDLING
@app.errorhandler(404)
def page_not_found(error):
    exception_counter.add(1)
    logger.error({
        'event': 'Page_not_found',
        'path': request.path,
        'user_ip': request.remote_addr
    })
    return render_template(
        'error.html',
        error_type="404 - Page Not Found",
        error_message="Oops! The page you are looking for doesn't exist.",
        description="Sorry, we couldn't find what you're looking for."
    ), 404


@app.errorhandler(500)
def internal_server_error(error):
    exception_counter.add(1)
    logger.exception({
        'event': 'Internal_server_error',
        'path': request.path,
        'user_ip': request.remote_addr
    })
    return render_template(
        'error.html',
        error_type="500 - Server Error",
        error_message="Oops! Something went wrong.",
        description="Please try refreshing the page or come back later."
    ), 500


@app.errorhandler(Exception)
def handle_exception(error):
    exception_counter.add(1)
    logger.exception({
        'event': 'Unhandled_exception',
        'error_type': type(error).__name__,
        'error_message': str(error),
        'path': request.path,
        'user_ip': request.remote_addr
    })
    return render_template(
        'error.html',
        error_type="Unexpected Error",
        error_message="Something went wrong.",
        description="Please try again later or contact support."
    ), 500

# CUSTOM 
@app.route("/manual-trace")
def manual_trace():
    # Start a span manually for custom tracing
    with tracer.start_as_current_span("manual-span", kind=SpanKind.SERVER) as span:
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", request.url)
        span.add_event("Processing request")
        return "Manual trace recorded!", 200

@app.route("/auto-instrumented")
def auto_instrumented():
    # Automatically instrumented via FlaskInstrumentor
    return "This route is auto-instrumented!", 200


if __name__ == '__main__':
    app.run(debug=True)