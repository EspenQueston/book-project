# -*- coding: utf-8 -*-
"""Verifies PawaPay's RFC-9421 HTTP Message Signatures on incoming callbacks.

PawaPay signs callbacks (deposits/payouts/refunds webhooks) with an EC-P256
key once "Signed Callbacks" is enabled in the Dashboard, sending:
  - Content-Digest   sha-256=:<base64>: or sha-512=:<base64>:
  - Signature-Date    ISO-8601 timestamp
  - Signature-Input   sig-pp=("@method" "@authority" "@path" ...);
                      alg="ecdsa-p256-sha256";keyid="HTTP_EC_P256_KEY:1";
                      created=...;expires=...
  - Signature         sig-pp=:<base64 DER-encoded ECDSA signature>:

Verification (see https://docs.pawapay.io/using_the_api#signatures):
  1. Recompute the Content-Digest from the raw request body and compare.
  2. Rebuild the "signature base" from the covered components named in
     Signature-Input, using the *actual* header/derived-component values
     from this request.
  3. Verify the base against PawaPay's public key (fetched from
     GET {base_url}/public-key/http, keyed by `id`, cached in-process).

No third-party "http-message-signatures" dependency — PawaPay's covered
component set is small and fixed, so a focused parser is simpler and easier
to audit than a generic RFC 8941 structured-field-values implementation.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import re
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_PUBLIC_KEYS_CACHE = {'keys': {}, 'fetched_at': 0.0}
_PUBLIC_KEYS_TTL_SECONDS = 24 * 60 * 60  # PawaPay's signing keys rotate rarely.

_CONTENT_DIGEST_RE = re.compile(r'([a-zA-Z0-9\-]+)=:([^:]*):')
_SIG_VALUE_RE = re.compile(r'([a-zA-Z0-9\-]+)=:([^:]*):')
# Signature-Input, e.g.:
#   sig-pp=("@method" "@authority" "@path" "signature-date" "content-digest"
#   "content-type");alg="ecdsa-p256-sha256";keyid="HTTP_EC_P256_KEY:1";
#   created=1714657551;expires=1714657611
_SIG_INPUT_RE = re.compile(
    r'([a-zA-Z0-9\-]+)=\(([^)]*)\)(;.*)?$'
)


class SignatureVerificationError(Exception):
    """Raised for any step of callback verification that fails."""


def _fetch_public_keys(force=False):
    """Return {keyid: pem_string}, refreshing from PawaPay at most once per TTL."""
    now = time.time()
    if not force and _PUBLIC_KEYS_CACHE['keys'] and (now - _PUBLIC_KEYS_CACHE['fetched_at']) < _PUBLIC_KEYS_TTL_SECONDS:
        return _PUBLIC_KEYS_CACHE['keys']

    base_url = getattr(settings, 'PAWAPAY_BASE_URL', 'https://api.sandbox.pawapay.io').rstrip('/')
    token = getattr(settings, 'PAWAPAY_API_TOKEN', '')
    url = f'{base_url}/public-key/http'
    try:
        resp = requests.get(
            url,
            headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json'},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        keys = {item['id']: item['key'] for item in data if item.get('id') and item.get('key')}
        if keys:
            _PUBLIC_KEYS_CACHE['keys'] = keys
            _PUBLIC_KEYS_CACHE['fetched_at'] = now
        return keys
    except Exception as exc:
        logger.warning('PawaPay: failed to fetch public keys from %s: %s', url, exc)
        return _PUBLIC_KEYS_CACHE['keys']  # serve stale cache rather than hard-fail


def _parse_labeled_value(header_value, expected_label=None):
    """Parse `label=:BASE64:` (Content-Digest / Signature) → (label, raw_bytes)."""
    m = _SIG_VALUE_RE.search(header_value or '')
    if not m:
        raise SignatureVerificationError(f'Could not parse labeled value: {header_value!r}')
    label, b64 = m.group(1), m.group(2)
    if expected_label and label != expected_label:
        raise SignatureVerificationError(f'Unexpected label {label!r}, expected {expected_label!r}')
    return label, base64.b64decode(b64)


def _parse_signature_input(header_value):
    """Parse Signature-Input into (label, [components], params_dict, raw_params_str)."""
    m = _SIG_INPUT_RE.match((header_value or '').strip())
    if not m:
        raise SignatureVerificationError(f'Could not parse Signature-Input: {header_value!r}')
    label = m.group(1)
    components_raw = m.group(2)
    components = re.findall(r'"([^"]+)"', components_raw)
    params_str = m.group(3) or ''
    params = {}
    for key, quoted_val, bare_val in re.findall(r';\s*([a-zA-Z0-9\-]+)=(?:"([^"]*)"|([^;]+))', params_str):
        params[key] = quoted_val if quoted_val else bare_val
    # Everything after the label's '=' — i.e. "(...);alg=...;keyid=..." verbatim —
    # is what gets echoed back as the @signature-params component value.
    raw_params = header_value[header_value.index('=') + 1:].strip()
    return label, components, params, raw_params


def verify_callback_signature(request):
    """Verify a PawaPay callback request's RFC-9421 signature.

    Returns (verified: bool, detail: str). `verified=False` with a detail
    string covers both "signature present but invalid" and "no signature
    headers at all" (e.g. Signed Callbacks not yet enabled in the Dashboard)
    — callers decide whether absence is acceptable via
    settings.PAWAPAY_REQUIRE_SIGNED_CALLBACKS.
    """
    headers = request.headers
    signature_header = headers.get('Signature')
    signature_input_header = headers.get('Signature-Input')
    content_digest_header = headers.get('Content-Digest')

    if not signature_header or not signature_input_header:
        return False, 'no Signature/Signature-Input headers present'

    try:
        # 1. Content-Digest integrity check (if present — PawaPay always sends it
        #    when signing, but don't assume the exact algorithm).
        if content_digest_header:
            algo, digest_bytes = _parse_labeled_value(content_digest_header)
            algo_norm = algo.lower().replace('sha-', 'sha')
            hasher = {'sha256': hashlib.sha256, 'sha512': hashlib.sha512}.get(algo_norm)
            if not hasher:
                return False, f'unsupported Content-Digest algorithm: {algo}'
            computed = hasher(request.body or b'').digest()
            if computed != digest_bytes:
                return False, 'Content-Digest does not match request body'

        # 2. Parse Signature-Input to know which components were signed, and
        #    which key/algorithm/validity window to use.
        label, components, params, raw_params = _parse_signature_input(signature_input_header)
        alg = (params.get('alg') or '').lower()
        keyid = params.get('keyid') or ''
        if alg != 'ecdsa-p256-sha256':
            return False, f'unsupported signature algorithm: {alg or "(none)"}'

        expires = params.get('expires')
        if expires:
            try:
                if time.time() > float(expires):
                    return False, 'signature has expired'
            except ValueError:
                pass

        # 3. Rebuild the signature base from THIS request's actual values —
        #    never trust a value carried in the payload itself.
        lines = []
        for comp in components:
            comp_lower = comp.lower()
            if comp_lower == '@method':
                value = request.method.upper()
            elif comp_lower == '@authority':
                value = request.get_host()
            elif comp_lower == '@path':
                value = request.path
            else:
                value = headers.get(comp)
                if value is None:
                    return False, f'missing covered header: {comp}'
            lines.append(f'"{comp_lower}": {value}')
        lines.append(f'"@signature-params": {raw_params}')
        signature_base = '\n'.join(lines).encode('utf-8')

        # 4. Extract the raw signature bytes and verify against PawaPay's key.
        _, signature_bytes = _parse_labeled_value(signature_header, expected_label=label)

        public_keys = _fetch_public_keys()
        pem = public_keys.get(keyid)
        if not pem:
            public_keys = _fetch_public_keys(force=True)
            pem = public_keys.get(keyid)
        if not pem:
            return False, f'unknown keyid: {keyid}'

        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives.serialization import load_pem_public_key
        from cryptography.exceptions import InvalidSignature

        public_key = load_pem_public_key(pem.encode('utf-8'))
        try:
            public_key.verify(signature_bytes, signature_base, ec.ECDSA(hashes.SHA256()))
        except InvalidSignature:
            return False, 'signature does not match'

        return True, 'ok'
    except SignatureVerificationError as exc:
        return False, str(exc)
    except Exception as exc:  # never let a parsing bug crash the webhook
        logger.exception('PawaPay callback signature verification error: %s', exc)
        return False, f'verification error: {exc}'
