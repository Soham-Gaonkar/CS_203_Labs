from flask import Flask, render_template, request, redirect, url_for, flash
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider , StatusCode
from opentelemetry.sdk.trace.export import BatchSpanProcessor,ConsoleSpanExporter
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.trace import SpanKind
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from time import perf_counter
import logging
import json
import os
import time

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
console_exporter = ConsoleSpanExporter()

# Metrics Setup
metric_reader = PeriodicExportingMetricReader(ConsoleMetricExporter(),export_interval_millis= 15000)
meter_provider = MeterProvider(metric_readers=[metric_reader])
meter = meter_provider.get_meter('meter') # global meter instance

total_requests_counter = meter.create_counter('total_requests_index',description= 'Total number of requests', unit='1')
exception_counter = meter.create_counter('exceptions_index',description= 'Total number of exceptions', unit='1')
processing_time_histogram = meter.create_histogram(name = 'request_processing_time_index',description = 'Time taken to process requests',unit = 'ms')

# FlaskInstrumentor().instrument_app(app)

# Json - python structured logging
class Json_Formatter(logging.Formatter):
    def format(self, record):
        log_record = {
            'timestamp': time.time(),
            'level': record.levelname,
            'message': record.getMessage(),
            'logger_name': record.name,
        }
        print(json.dumps(log_record)) # Print the log record to the console
        return json.dumps(log_record)

# Logging Setup
handler = logging.FileHandler('app.log')
handler.setFormatter(Json_Formatter())
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

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

def record_processing_time(histogram, route_name, start_time):
    """Record request processing time."""
    processing_time = (perf_counter() - start_time) * 1000
    histogram.record(processing_time, {route_name: f"/{route_name}"})

def log_event(logger, event_name, **kwargs):
    """Log structured events."""
    log_data = {"event": event_name , "user_ip": request.remote_addr, **kwargs}
    logger.info(log_data)

def start_span(span_name):
    """Start a span with the given name."""
    return tracer.start_as_current_span(span_name)

def set_span_attributes(span):
    """Set common attributes for a span"""
    span.set_attribute("http.method", request.method)
    span.set_attribute("http.url", request.url)
    span.set_attribute("user.ip", request.remote_addr)


def handle_exception_logging(error):
    """Helper function to handle and log exceptions."""
    exception_counter.add(1)
    logger.exception({
        'event': 'Unhandled_exception',
        'error_type': type(error).__name__,
        'error_message': str(error),
        'path': request.path,
        'user_ip': request.remote_addr
    })

# ROUTES
@app.route('/')
def index():
    total_requests_counter.add(1,{"index": "/"})
    start_time = perf_counter()

    with start_span("index") as span:
        span.set_status(StatusCode.OK)
        span.add_event('Course Info Page Loaded')
        set_span_attributes(span)
        log_event(logger, "Index_page_loaded")
    
    # record_processing_time(processing_time_histogram, "index", start_time)
    return render_template('index.html')

@app.route('/catalog')
def course_catalog():
    total_requests_counter.add(1, {"catalog": "/catalog"})
    start_time = perf_counter()

    with start_span("course-catalog") as span:
        try:
            courses = load_courses()
            span.add_event('Courses loaded')
        except Exception as error:
            span.set_status(StatusCode.ERROR)
            span.add_event('Error loading courses'+str(error))
            handle_exception_logging(error)
            log_event(logger, "Error_loading_courses")
            return render_template('error.html', error_message="There was an issue loading the course catalog. Please try again later."), 500
            
        span.set_status(StatusCode.OK)
        set_span_attributes(span)
        span.set_attribute("courses.count", len(courses))
        log_event(logger, "Course_catalog_loaded", courses_count=len(courses))
        record_processing_time(processing_time_histogram, "catalog", start_time)
        return render_template('course_catalog.html', courses=courses)


@app.route('/add_course', methods=['GET', 'POST'])
def add_course():
    start_time = perf_counter()
    total_requests_counter.add(1, {"add_course": "/add_course"})

    log_event(logger, "Add_course_page_loaded")

    if request.method == 'POST':
        with start_span("add-course") as span:
            try:
                set_span_attributes(span)
                
                # Validate the form data
                if not validate_form_data(request.form):
                    log_event(logger, 'Form_validation_failed')
                    return redirect(url_for('add_course'))

                course = {
                    key: request.form[key]
                    for key in ['code', 'name', 'instructor', 'semester', 'schedule', 'classroom', 'prerequisites', 'grading', 'description']
                }

                save_courses(course)
                flash(f"Course '{course['name']}' added successfully!", "success")

                # Log the course addition details
                log_event(logger, 'Course_added', course_name=course['name'])
                span.add_event(f"Course '{course['name']}' added successfully")
                span.set_status(StatusCode.OK)

                span.set_attribute("course.code", course['code'])
                span.set_attribute("course.name", course['name'])
                span.set_status(StatusCode.OK)
            except Exception as error:
                span.set_status(StatusCode.ERROR)
                span.add_event('Error adding course'+str(error))
                handle_exception_logging(error)
                log_event(logger, 'Error_adding_course')
                flash("An unexpected error occurred. Please try again later.", "danger")
        return redirect(url_for('course_catalog'))

    record_processing_time(processing_time_histogram, "add_course", start_time)
    return render_template('add_course.html')


@app.route('/course/<code>')
def course_details(code):
    start_time = perf_counter()
    total_requests_counter.add(1, {"course_code": f"/course/{code}"})

    with start_span("course-details") as span:
        set_span_attributes(span)
        span.set_attribute("course.code", code)
        try:
            courses = load_courses()
            course = next((course for course in courses if course['code'] == code), None)
            if not course:
                span.set_status(StatusCode.ERROR)
                span.add_event(f"No course found with code '{code}'")
                flash(f"No course found with code '{code}'.", "error")
                log_event(logger, 'Course_not_found', course_code=code)
                return redirect(url_for('course_catalog'))

            log_event(logger, 'Course_details_loaded')
            span.set_status(StatusCode.OK)
            span.add_event(f"Course '{course['name']}' details loaded")

        except Exception as error:
            handle_exception_logging(error)
            log_event(logger, 'Error_loading_course_details')
            flash("An unexpected error occurred. Please try again later.", "danger")
            span.set_status(StatusCode.ERROR)
            span.add_event('Error loading course details'+str(error))

            return redirect(url_for('course_catalog'))

    record_processing_time(processing_time_histogram, "course_details", start_time)
    return render_template('course_details.html', course=course)


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

@app.errorhandler(404)
def page_not_found(e):
    with tracer.start_as_current_span("404-error-handler", kind=SpanKind.INTERNAL) as span:
        span.set_status(StatusCode.ERROR)  # Set status to ERROR
        span.set_attribute("http.status_code", 404)
        span.set_attribute("error.message", str(e))
        handle_exception_logging(e)  # Log the error
        log_event(logger, 'Page_not_found')  # Structured logging for the event

    return render_template('error.html',error_message = 'Page Not Found',error_description =  "The page you are looking for does not exist. Please check the URL and try again."
), 404


if __name__ == '__main__':
    app.run(debug=True)