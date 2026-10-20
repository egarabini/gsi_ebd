import ssl


def tls_context(ca_bundle=""):
    # Explicit trust never weakens certificate or hostname verification.
    return ssl.create_default_context(cafile=ca_bundle or None)
