from email.message import EmailMessage
from datetime import timedelta
import logging
import os
import smtplib
import time

from flask import Flask, jsonify, request
from flask_caching import Cache
from flask_cors import CORS
from flask_jwt_extended import JWTManager, get_jwt_identity, jwt_required
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from flask_wtf.csrf import CSRFProtect

from .auth_bp import auth_bp
from .cases_bp import cases_bp
from .dashboard_bp import dashboard_bp
from .peer_review_bp import peer_review_bp
from .reports_bp import reports_bp
from .server_view_bp import server_view_bp
from .discovery_bp import discovery_bp
from .legal_template_library_bp import legal_template_library_bp
from .users_bp import users_bp, supervisor_bp
from .models import db
from .infrastructure.api.decorators import rate_limit
from .infrastructure.middleware import register_request_logging
from .infrastructure.observability import (
    bind_request_id,
    configure_logging,
    generate_prometheus_text,
    get_logger,
    get_metrics,
)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _required_env(name: str) -> str | None:
    value = os.environ.get(name, '').strip()
    return value or None


def send_feature_request_email(feature_request: dict, authenticated_user: str):
    smtp_host = _required_env('SMTP_HOST')
    recipient = _required_env('FEATURE_REQUEST_TO_EMAIL')
    sender = _required_env('SMTP_FROM_EMAIL')
    if not smtp_host or not recipient or not sender:
        raise RuntimeError(
            'Missing SMTP configuration. Set SMTP_HOST, SMTP_FROM_EMAIL, and FEATURE_REQUEST_TO_EMAIL.'
        )

    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_username = os.environ.get('SMTP_USERNAME', '').strip()
    smtp_password = os.environ.get('SMTP_PASSWORD', '')
    use_tls = os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true'
    use_ssl = os.environ.get('SMTP_USE_SSL', 'false').lower() == 'true'

    feature = feature_request.get('feature', {})
    user = feature_request.get('user', {})
    system = feature_request.get('system', {})

    message = EmailMessage()
    message['Subject'] = f"Feature Request: {feature.get('title', 'Untitled request')}"
    message['From'] = sender
    message['To'] = recipient
    message.set_content(
        '\n'.join(
            [
                'Feature Request from FuDog Labs Forensic Report Suite',
                '',
                f"Submitted: {feature_request.get('timestamp', '')}",
                f"Authenticated User: {authenticated_user}",
                f"Reported User: {user.get('username', '')} ({user.get('role', '')})",
                f"System: {system.get('os', '')}, Python {system.get('python', '')}, PyQt5 {system.get('pyqt5', '')}",
                '',
                f"Priority: {feature.get('priority', '')}",
                f"Title: {feature.get('title', '')}",
                '',
                'Description:',
                feature.get('description', ''),
                '',
                'Benefits:',
                feature.get('benefits', ''),
                '',
                'Use Cases:',
                feature.get('use_cases', ''),
                '',
                'Configuration:',
                str(feature_request.get('config', 'Not included')),
            ]
        )
    )

    smtp_class = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
    with smtp_class(smtp_host, smtp_port, timeout=20) as smtp_client:
        smtp_client.ehlo()
        if use_tls and not use_ssl:
            smtp_client.starttls()
            smtp_client.ehlo()
        if smtp_username:
            smtp_client.login(smtp_username, smtp_password)
        smtp_client.send_message(message)


def create_app() -> Flask:
    app = Flask(__name__)

    jwt_secret = os.environ.get('JWT_SECRET')
    if not jwt_secret or len(jwt_secret) < 32:
        raise RuntimeError(
            'CRITICAL: JWT_SECRET environment variable not set or too short (min 32 chars). '
            'Set JWT_SECRET in .env or environment variables before running server.'
        )

    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///server.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = jwt_secret
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', jwt_secret)
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=12)
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=7)
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PREFERRED_URL_SCHEME'] = 'https'
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['WTF_CSRF_TIME_LIMIT'] = None
    app.config['WTF_CSRF_SSL_STRICT'] = True
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'max_overflow': 20,
    }
    app.config['CACHE_DEFAULT_TIMEOUT'] = 300
    app.config['RATE_LIMIT_ENABLED'] = os.environ.get('RATE_LIMIT_ENABLED', 'true').lower() == 'true'

    try:
        app.config['CACHE_TYPE'] = 'redis'
        app.config['CACHE_REDIS_HOST'] = os.environ.get('REDIS_HOST', 'localhost')
        app.config['CACHE_REDIS_PORT'] = int(os.environ.get('REDIS_PORT', 6379))
        app.config['CACHE_REDIS_DB'] = int(os.environ.get('REDIS_DB', 0))
    except Exception:
        app.config['CACHE_TYPE'] = 'simple'

    db.init_app(app)
    JWTManager(app)
    csrf = CSRFProtect(app)
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=['200 per day', '50 per hour'],
        storage_uri=os.environ.get('RATELIMIT_STORAGE_URI', 'memory://'),
    )
    limiter.init_app(app)
    Cache(app)

    CORS(
        app,
        origins=os.environ.get('CORS_ORIGINS', 'http://localhost:5000,https://localhost:5000').split(','),
        supports_credentials=True,
        allow_headers=['Content-Type', 'Authorization'],
        expose_headers=['Content-Type', 'Authorization'],
    )

    Talisman(
        app,
        force_https=True,
        strict_transport_security=True,
        strict_transport_security_max_age=31536000,
        strict_transport_security_include_subdomains=True,
        content_security_policy={
            'default-src': "'self'",
            'script-src': "'self'",
            'style-src': "'self'",
            'img-src': "'self' data:",
            'font-src': "'self'",
        },
        content_security_policy_nonce_in=['script-src', 'style-src'],
    )

    configure_logging(level=logging.INFO, output_file='logs/server.log')
    log = get_logger(__name__)
    metrics = get_metrics()
    metrics_token = os.environ.get('METRICS_TOKEN', '')
    log.info('Server startup')

    app.register_blueprint(auth_bp)
    app.register_blueprint(cases_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(peer_review_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(server_view_bp)
    app.register_blueprint(discovery_bp)
    app.register_blueprint(legal_template_library_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(supervisor_bp)

    # API endpoints rely on bearer tokens rather than browser form CSRF tokens.
    csrf.exempt(auth_bp)
    csrf.exempt(cases_bp)
    csrf.exempt(dashboard_bp)
    csrf.exempt(peer_review_bp)
    csrf.exempt(reports_bp)
    csrf.exempt(server_view_bp)
    csrf.exempt(discovery_bp)
    csrf.exempt(legal_template_library_bp)
    csrf.exempt(users_bp)
    csrf.exempt(supervisor_bp)

    register_request_logging(app)

    @app.before_request
    def _before_request() -> None:
        rid = request.headers.get('X-Request-ID') or None
        bind_request_id(rid)
        request._start_time = time.perf_counter()
        metrics.increment('http.requests', tags={'method': request.method, 'endpoint': request.path})

    @app.after_request
    def _after_request(response):
        from .infrastructure.observability import current_request_id

        elapsed_ms = (time.perf_counter() - getattr(request, '_start_time', time.perf_counter())) * 1000
        metrics.histogram('http.latency_ms', elapsed_ms, tags={'method': request.method, 'status': str(response.status_code)})
        response.headers['X-Request-ID'] = current_request_id()
        return response

    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({'status': 'ok', 'version': '1.3'}), 200

    @app.route('/metrics', methods=['GET'])
    def prometheus_metrics():
        if metrics_token:
            auth = request.headers.get('Authorization', '')
            if not auth.startswith('Bearer ') or auth[len('Bearer '):] != metrics_token:
                return jsonify({'error': 'Unauthorized'}), 401
        text = generate_prometheus_text(metrics)
        return text, 200, {'Content-Type': 'text/plain; version=0.0.4; charset=utf-8'}

    @app.route('/feature_requests', methods=['POST'])
    @jwt_required()
    @rate_limit(limit=20, window_seconds=60, strategy='user_or_ip')
    def submit_feature_request():
        current_user = get_jwt_identity()
        payload = request.get_json(silent=True)
        if not payload:
            return jsonify({'error': 'No data provided'}), 400

        feature = payload.get('feature') or {}
        title = str(feature.get('title', '')).strip()
        description = str(feature.get('description', '')).strip()
        if not title or not description:
            return jsonify({'error': 'Feature title and description are required'}), 400

        try:
            send_feature_request_email(payload, str(current_user))
            log.info('Feature request emailed successfully', extra={'user': current_user})
            return jsonify({'message': 'Feature request emailed successfully'}), 200
        except RuntimeError as error:
            log.warning('Feature request email not configured', extra={'error': str(error)})
            return jsonify({'error': str(error)}), 503
        except Exception as error:
            log.exception('Feature request email failed', extra={'error': str(error)})
            return jsonify({'error': 'Feature request delivery failed'}), 500

    with app.app_context():
        db.create_all()

    @app.errorhandler(400)
    def bad_request(error):
        log.warning('Bad request', extra={'error': str(error)})
        return jsonify({'error': 'Bad request'}), 400

    @app.errorhandler(401)
    def unauthorized(error):
        log.warning('Unauthorized access', extra={'error': str(error)})
        return jsonify({'error': 'Unauthorized'}), 401

    @app.errorhandler(403)
    def forbidden(error):
        log.warning('Forbidden access', extra={'error': str(error)})
        return jsonify({'error': 'Forbidden'}), 403

    @app.errorhandler(404)
    def not_found(error):
        log.warning('Not found', extra={'error': str(error)})
        return jsonify({'error': 'Not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        log.error('Internal server error', extra={'error': str(error)})
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

    return app


app = create_app()


def run() -> None:
    log = get_logger(__name__)
    log.info('Secure Forensic Case Management Server starting...')
    log.info('Database configured', extra={'db': app.config['SQLALCHEMY_DATABASE_URI']})

    is_production = os.environ.get('FLASK_ENV', 'production').lower() == 'production'
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

    if is_production and debug_mode:
        log.warning('Running in PRODUCTION with DEBUG=True. This is a security risk!')
    elif is_production:
        log.info('Running in PRODUCTION mode (debug disabled)')
    else:
        log.info('Running in DEVELOPMENT mode')

    tls_enabled = os.environ.get('TLS_ENABLED', 'True').lower() == 'true'
    if is_production and not tls_enabled:
        log.warning('Production mode but TLS_ENABLED=False. HTTPS is required for security!')

    ssl_context = None
    if tls_enabled:
        cert_path = os.environ.get('TLS_CERT_PATH')
        key_path = os.environ.get('TLS_KEY_PATH')
        if cert_path and key_path and os.path.exists(cert_path) and os.path.exists(key_path):
            ssl_context = (cert_path, key_path)
            log.info('Using TLS certificates', extra={'cert_path': cert_path})
        elif is_production:
            log.warning('TLS_ENABLED but certificate paths not configured!')

    app.run(
        host=os.environ.get('SERVER_HOST', '0.0.0.0'),
        port=int(os.environ.get('SERVER_PORT', 5000)),
        debug=debug_mode and not is_production,
        ssl_context=ssl_context,
    )
