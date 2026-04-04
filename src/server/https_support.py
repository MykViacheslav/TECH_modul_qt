from __future__ import annotations

import json
import socket
import ssl
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


@dataclass(frozen=True)
class HttpsMaterial:
    cert_file: Path
    key_file: Path
    ca_file: Path
    ca_key_file: Path
    meta_file: Path
    https_url: str
    ca_install_hint: str


def detect_primary_ip() -> str:
    """
    Best-effort discovery of the LAN IP that tablet clients should use.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            if ip and ip != "0.0.0.0":
                return ip
    except OSError:
        pass
    return "127.0.0.1"


def ensure_https_material(base_dir: Path, host: str = "0.0.0.0", port: int = 8443) -> HttpsMaterial:
    https_dir = base_dir / "https"
    https_dir.mkdir(parents=True, exist_ok=True)

    ca_key_file = https_dir / "TECH_modul_CA.key.pem"
    ca_file = https_dir / "TECH_modul_CA.crt"
    cert_file = https_dir / "TECH_modul_server.crt"
    key_file = https_dir / "TECH_modul_server.key.pem"
    meta_file = https_dir / "TECH_modul_https_meta.json"

    primary_ip = detect_primary_ip()
    target_host = primary_ip if host == "0.0.0.0" else host
    hostname = "TECH_modul.local"

    if _needs_refresh(meta_file, cert_file, key_file, ca_file, ca_key_file, target_host):
        _write_https_material(
            ca_key_file=ca_key_file,
            ca_file=ca_file,
            cert_file=cert_file,
            key_file=key_file,
            target_host=target_host,
            hostname=hostname,
        )
        meta_file.write_text(
            json.dumps(
                {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "host": host,
                    "target_host": target_host,
                    "port": port,
                    "hostname": hostname,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    https_url = f"https://{target_host}:{port}/kiosk-time"
    hint = f"Skopiuj certyfikat CA na tablet: {ca_file}"
    return HttpsMaterial(
        cert_file=cert_file,
        key_file=key_file,
        ca_file=ca_file,
        ca_key_file=ca_key_file,
        meta_file=meta_file,
        https_url=https_url,
        ca_install_hint=hint,
    )


def build_ssl_context(cert_file: Path, key_file: Path) -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=str(cert_file), keyfile=str(key_file))
    return context


def _needs_refresh(meta_file: Path, cert_file: Path, key_file: Path, ca_file: Path, ca_key_file: Path, target_host: str) -> bool:
    if not (meta_file.exists() and cert_file.exists() and key_file.exists() and ca_file.exists() and ca_key_file.exists()):
        return True
    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
    except Exception:
        return True
    if str(meta.get("target_host", "")).strip() != str(target_host).strip():
        return True
    try:
        cert = x509.load_pem_x509_certificate(cert_file.read_bytes())
    except Exception:
        return True
    try:
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        san_values = set()
        for value in san:
            if isinstance(value, x509.DNSName):
                san_values.add(value.value)
            elif isinstance(value, x509.IPAddress):
                san_values.add(str(value.value))
    except Exception:
        return True
    return target_host not in san_values and "127.0.0.1" not in san_values


def _write_https_material(
    *,
    ca_key_file: Path,
    ca_file: Path,
    cert_file: Path,
    key_file: Path,
    target_host: str,
    hostname: str,
) -> None:
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "PL"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "TECH_modul"),
            x509.NameAttribute(NameOID.COMMON_NAME, "TECH_modul Local CA"),
        ]
    )
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_subject)
        .issuer_name(ca_subject)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(x509.KeyUsage(
            digital_signature=False,
            content_commitment=False,
            key_encipherment=False,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=True,
            crl_sign=True,
            encipher_only=False,
            decipher_only=False,
        ), critical=True)
        .sign(private_key=ca_key, algorithm=hashes.SHA256())
    )

    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server_subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "PL"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "TECH_modul"),
            x509.NameAttribute(NameOID.COMMON_NAME, "TECH_modul Kiosk"),
        ]
    )

    san_entries = []
    for candidate in {target_host, hostname, "localhost", "127.0.0.1"}:
        candidate = str(candidate or "").strip()
        if not candidate:
            continue
        try:
            san_entries.append(x509.IPAddress(ip_address(candidate)))
        except ValueError:
            san_entries.append(x509.DNSName(candidate))

    server_cert = (
        x509.CertificateBuilder()
        .subject_name(server_subject)
        .issuer_name(ca_cert.subject)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=825))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName(san_entries), critical=False)
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .sign(private_key=ca_key, algorithm=hashes.SHA256())
    )

    ca_key_file.write_bytes(
        ca_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    ca_file.write_bytes(ca_cert.public_bytes(serialization.Encoding.PEM))
    key_file.write_bytes(
        server_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    cert_file.write_bytes(server_cert.public_bytes(serialization.Encoding.PEM))
