from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from functools import wraps
from ipaddress import IPv4Network, ip_network
import os
import socket
import threading
from typing import Any, Callable
from urllib.error import URLError
from urllib.request import Request, urlopen

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from .infrastructure.api.decorators import rate_limit
from .infrastructure.observability import get_logger


discovery_bp = Blueprint('discovery', __name__, url_prefix='/api/v1/discovery')
_log = get_logger(__name__)


@dataclass
class Endpoint:
    app_id: str
    hostname: str
    ip: str
    port: int
    username: str
    version: str
    trust_state: str
    source: str
    last_seen: str
    status: str


_REGISTRY: dict[str, Endpoint] = {}
_LOCK = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _identity() -> dict[str, str]:
    identity = get_jwt_identity()
    if isinstance(identity, dict):
        return {
            'username': str(identity.get('username', 'unknown')),
            'role': str(identity.get('role', 'writer')).lower(),
        }
    claims = get_jwt() or {}
    username = str(claims.get('username') or identity or 'unknown')
    role = str(claims.get('role') or 'writer').lower()
    return {'username': username, 'role': role}


def _require_roles(*allowed_roles: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    allowed = {role.lower() for role in allowed_roles}

    def _decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def _wrapper(*args: Any, **kwargs: Any):
            ident = _identity()
            if ident['role'] not in allowed:
                return jsonify({'error': 'Permission denied'}), 403
            return func(*args, **kwargs)

        return _wrapper

    return _decorator


def _check_discovery_token() -> bool:
    expected = (os.environ.get('DISCOVERY_SHARED_TOKEN', '') or '').strip()
    if not expected:
        return True
    provided = (request.headers.get('X-Discovery-Token', '') or '').strip()
    return provided == expected


def _default_scan_cidrs() -> list[str]:
    configured = (os.environ.get('DISCOVERY_SCAN_CIDRS', '') or '').strip()
    if configured:
        return [chunk.strip() for chunk in configured.split(',') if chunk.strip()]

    cidrs = []
    try:
        host_ip = socket.gethostbyname(socket.gethostname())
        if host_ip and not host_ip.startswith('127.'):
            network = ip_network(f'{host_ip}/24', strict=False)
            cidrs.append(str(network))
    except Exception:
        pass

    if not cidrs:
        cidrs.append('192.168.1.0/24')
    return cidrs


def _scan_ports() -> list[int]:
    raw = (os.environ.get('DISCOVERY_SCAN_PORTS', '5000,8080,8765') or '').strip()
    ports = []
    for chunk in raw.split(','):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            ports.append(int(chunk))
        except ValueError:
            continue
    return ports or [5000, 8080, 8765]


def _is_port_open(ip: str, port: int, timeout_seconds: float = 0.12) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout_seconds)
        return sock.connect_ex((ip, port)) == 0


def _probe_main_app(ip: str, port: int) -> tuple[bool, dict[str, Any]]:
    endpoint = f'http://{ip}:{port}/api/v1/client/discovery'
    req = Request(endpoint, method='GET')
    try:
        with urlopen(req, timeout=0.25) as response:
            body = response.read(4096).decode('utf-8', errors='ignore')
            if 'forensic-main-app' in body.lower() or 'forensic report' in body.lower():
                return True, {'probe': endpoint, 'response_preview': body[:200]}
    except (TimeoutError, URLError, OSError):
        pass
    return False, {'probe': endpoint}


def _register_endpoint(endpoint: Endpoint) -> None:
    with _LOCK:
        _REGISTRY[endpoint.app_id] = endpoint


def _active_scan() -> list[Endpoint]:
    found: list[Endpoint] = []
    max_hosts = int(os.environ.get('DISCOVERY_SCAN_MAX_HOSTS', '96'))
    ports = _scan_ports()

    seen_hosts = 0
    for cidr in _default_scan_cidrs():
        try:
            network = IPv4Network(cidr, strict=False)
        except ValueError:
            continue

        for host in network.hosts():
            if seen_hosts >= max_hosts:
                return found
            ip = str(host)
            seen_hosts += 1
            for port in ports:
                if not _is_port_open(ip, port):
                    continue

                is_main, details = _probe_main_app(ip, port)
                app_id = f'{ip}:{port}'
                endpoint = Endpoint(
                    app_id=app_id,
                    hostname=details.get('hostname', ip),
                    ip=ip,
                    port=port,
                    username=details.get('username', 'unknown'),
                    version=details.get('version', 'unknown'),
                    trust_state='pending',
                    source='active-scan-verified' if is_main else 'active-scan-candidate',
                    last_seen=_now_iso(),
                    status='online' if is_main else 'candidate',
                )
                _register_endpoint(endpoint)
                found.append(endpoint)
    return found


@discovery_bp.route('/heartbeat', methods=['POST'])
@rate_limit(limit=360, window_seconds=60, strategy='ip')
def heartbeat():
    if not _check_discovery_token():
        return jsonify({'error': 'Unauthorized discovery token'}), 401

    payload = request.get_json(silent=True) or {}
    app_id = str(payload.get('app_id') or '').strip()
    hostname = str(payload.get('hostname') or request.remote_addr or '').strip()
    ip = str(payload.get('ip') or request.remote_addr or '').strip()
    port = int(payload.get('port') or 0)
    username = str(payload.get('username') or 'unknown').strip()
    version = str(payload.get('version') or 'unknown').strip()

    if not app_id:
        app_id = f'{hostname}:{port or 0}'
    if not hostname:
        hostname = app_id

    endpoint = Endpoint(
        app_id=app_id,
        hostname=hostname,
        ip=ip,
        port=port,
        username=username,
        version=version,
        trust_state=str(payload.get('trust_state') or 'pending'),
        source='heartbeat',
        last_seen=_now_iso(),
        status='online',
    )
    _register_endpoint(endpoint)

    return jsonify({'message': 'Heartbeat accepted', 'app_id': app_id})


@discovery_bp.route('/endpoints', methods=['GET'])
@jwt_required()
@_require_roles('admin', 'supervisor')
@rate_limit(limit=240, window_seconds=60, strategy='user_or_ip')
def list_endpoints():
    query = (request.args.get('q', '') or '').strip().lower()
    with _LOCK:
        endpoints = list(_REGISTRY.values())

    rows = []
    for endpoint in endpoints:
        row = asdict(endpoint)
        if query and not (
            query in row['app_id'].lower()
            or query in row['hostname'].lower()
            or query in row['ip'].lower()
            or query in row['username'].lower()
        ):
            continue
        rows.append(row)

    rows.sort(key=lambda item: (item['status'] != 'online', item['hostname']))
    ident = _identity()
    _log.info('discovery_endpoints_listed', extra={'actor': ident['username'], 'role': ident['role'], 'count': len(rows)})
    return jsonify({'count': len(rows), 'rows': rows})


@discovery_bp.route('/scan', methods=['POST'])
@jwt_required()
@_require_roles('admin', 'supervisor')
@rate_limit(limit=20, window_seconds=60, strategy='user_or_ip')
def scan_network():
    ident = _identity()
    _log.info('discovery_scan_started', extra={'actor': ident['username'], 'role': ident['role']})
    found = _active_scan()
    _log.info('discovery_scan_completed', extra={'actor': ident['username'], 'found': len(found)})
    return jsonify({'message': 'Scan completed', 'found': len(found), 'rows': [asdict(endpoint) for endpoint in found]})


@discovery_bp.route('/trust/<string:app_id>', methods=['PUT'])
@jwt_required()
@_require_roles('admin')
@rate_limit(limit=90, window_seconds=60, strategy='user_or_ip')
def update_trust(app_id: str):
    ident = _identity()
    payload = request.get_json(silent=True) or {}
    trust_state = str(payload.get('trust_state') or '').strip().lower()
    if trust_state not in {'trusted', 'pending', 'untrusted'}:
        return jsonify({'error': 'trust_state must be trusted, pending, or untrusted'}), 400

    with _LOCK:
        endpoint = _REGISTRY.get(app_id)
        if not endpoint:
            return jsonify({'error': 'Endpoint not found'}), 404
        endpoint.trust_state = trust_state
        endpoint.last_seen = _now_iso()

    _log.info('discovery_trust_updated', extra={'actor': ident['username'], 'app_id': app_id, 'trust_state': trust_state})
    return jsonify({'message': 'Trust state updated', 'app_id': app_id, 'trust_state': trust_state})
