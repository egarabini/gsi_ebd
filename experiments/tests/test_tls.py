import ssl
from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from experiments.identity_client.tls import tls_context


@pytest.fixture
def certificate(tmp_path):
    now=datetime.now(timezone.utc)
    ca_key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,"Unit test CA")])
    ca=(x509.CertificateBuilder().subject_name(name).issuer_name(name)
        .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True,path_length=None),critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()),critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),critical=False)
        .add_extension(x509.KeyUsage(digital_signature=False,content_commitment=False,key_encipherment=False,data_encipherment=False,key_agreement=False,key_cert_sign=True,crl_sign=True,encipher_only=False,decipher_only=False),critical=True)
        .sign(ca_key,hashes.SHA256()))
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    server=(x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,"fixture.test")]))
        .issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("fixture.test")]),critical=False)
        .add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()),critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),critical=False)
        .sign(ca_key,hashes.SHA256()))
    ca_path=tmp_path/"fixture-ca.pem"; ca_path.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    cert_path=tmp_path/"fixture-server.pem"; cert_path.write_bytes(server.public_bytes(serialization.Encoding.PEM))
    key_path=tmp_path/"fixture.key"; key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())); key_path.chmod(0o600)
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); context.load_cert_chain(cert_path,key_path)
    return str(ca_path),context


def handshake(client_context,server_context,hostname):
    ci,co,si,so=[ssl.MemoryBIO() for _ in range(4)]
    client=client_context.wrap_bio(ci,co,server_hostname=hostname)
    server=server_context.wrap_bio(si,so,server_side=True)
    client_done=server_done=False
    for _ in range(30):
        try: client.do_handshake(); client_done=True
        except ssl.SSLWantReadError: pass
        chunk=co.read()
        if chunk: si.write(chunk)
        try: server.do_handshake(); server_done=True
        except ssl.SSLWantReadError: pass
        chunk=so.read()
        if chunk: ci.write(chunk)
        if client_done and server_done: return
    raise AssertionError("Handshake not completed")


def test_e01_explicit_ca_verifies_chain_and_hostname(certificate):
    path,server=certificate; context=tls_context(path)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    handshake(context,server,"fixture.test")


def test_e01_unknown_ca_rejected(certificate):
    _,server=certificate
    with pytest.raises(ssl.SSLCertVerificationError): handshake(tls_context(),server,"fixture.test")


def test_e01_wrong_hostname_rejected_with_trusted_ca(certificate):
    path,server=certificate
    with pytest.raises(ssl.SSLCertVerificationError): handshake(tls_context(path),server,"wrong.test")


def test_e01_missing_ca_fails_closed(tmp_path):
    with pytest.raises(FileNotFoundError): tls_context(str(tmp_path/"missing.pem"))


def test_e01_explicit_ca_applied_to_authlib(certificate):
    from experiments.identity_client.app import create_app
    from experiments.identity_client.config import Settings
    path,server=certificate
    cfg=Settings(issuer="https://fixture.test",public_url="https://app.test/experimento",
        client_id="client",client_secret="",session_secret="s"*40,organization_id="org",
        project_id="project",environment="test",scopes="roles",organization_claim="org",
        roles_claim="roles",provisioning_org_header="x-org",ca_bundle=path)
    context=create_app(cfg).state.oidc_client.client_kwargs["verify"]
    assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
    handshake(context,server,"fixture.test")
