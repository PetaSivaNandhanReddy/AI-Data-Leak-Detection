"""AES-GCM Cryptographic Security Lab view for LEAKGUARD.

Educational demonstration of Authenticated Encryption with Associated Data (AEAD)
using NIST SP 800-38D AES-256-GCM.

Core Concepts Demonstrated:
- Ephemeral 256-bit symmetric key generation (in-memory only).
- Unique 96-bit (12-byte) cryptographically secure nonces per encryption.
- Authenticated Associated Data (AAD) binding context without encryption.
- Tamper-evident authentication tag (128-bit) integrity verification.
- Active failure demonstrations: ciphertext bit-flipping and wrong-key decryption.
"""

from __future__ import annotations

import streamlit as st

from leakguard.crypto.aes_gcm import (
    AuthenticationFailedError,
    EncryptedPayload,
    decrypt_message,
    encrypt_message,
    generate_ephemeral_key,
    mask_key_preview,
    tamper_payload,
)

SAFE_SAMPLES = {
    "Security Alert": (
        "Security Alert [INC-8491]: Sensitive pattern detected in session stream. "
        "Automated quarantine protocol engaged."
    ),
    "Audit Log Receipt": (
        "Audit Log Receipt [RCPT-20261019-902]: Scan completed in 1.4ms. "
        "Zero raw input preserved. Findings: 2."
    ),
    "Diagnostic Telemetry": (
        "Diagnostic Telemetry [DIAG-501]: Local memory footprint: 48.2MB. "
        "Outbound network calls: 0. Egress: Denied."
    ),
}

DEFAULT_AAD = "context=leakguard_security_console;version=1.0;env=educational_demo"


def _init_lab_state() -> tuple[bytes, EncryptedPayload | None]:
    """Retrieve or initialize the ephemeral key and encrypted payload in session state."""
    if "sec_lab_key" not in st.session_state:
        st.session_state["sec_lab_key"] = generate_ephemeral_key()
    if "sec_lab_payload" not in st.session_state:
        st.session_state["sec_lab_payload"] = None
    if "sec_lab_is_tampered" not in st.session_state:
        st.session_state["sec_lab_is_tampered"] = False

    return st.session_state["sec_lab_key"], st.session_state["sec_lab_payload"]


def render_security_lab() -> None:
    """Render the AES-GCM Security Lab interactive view."""
    st.title("🔐 AES-GCM Security Lab")
    st.markdown(
        "Interactive cryptographic demonstration of **Authenticated Encryption with Associated "
        "Data (AEAD)** using modern **AES-256-GCM** (NIST SP 800-38D)."
    )

    # -------------------------------------------------------------------------
    # Educational Disclaimer & Legacy Architecture Notice
    # -------------------------------------------------------------------------
    st.markdown(
        """
        <div class="leakguard-banner" style="margin-bottom: 1rem;">
            <strong>⚠️ Educational Cryptography Lab Notice</strong><br>
            This interactive sandbox demonstrates symmetric authenticated encryption and
            cryptographic integrity protection. It is an educational tool and
            <strong>not a production key management service (KMS)</strong>.
            All keys are ephemeral, held strictly in memory, and discarded upon session reset.
            <strong>Never enter live credentials or production secrets here.</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("ℹ️ Architecture Note: Why AES-GCM instead of Legacy RSA-2048 / EAX?"):
        st.markdown(
            """
            The legacy prototype notebook used PyCryptodome to create an RSA-2048 + AES-EAX hybrid
            envelope, storing hardcoded PEM keys on disk without key rotation or authenticated
            associated data.

            In the **LEAKGUARD rebuild**, the unauthenticated legacy RSA approach was
            **intentionally dropped** in favor of standard **AES-256-GCM** (NIST SP 800-38D):
            - **Authenticated Encryption (AEAD):** Provides both confidentiality and ciphertext
              integrity in a single unified primitive with a 128-bit authentication tag.
            - **Associated Data (AAD):** Cryptographically binds contextual metadata (e.g., audit
              record IDs, schema version) to the ciphertext without encrypting the metadata itself.
            - **Nonce Invariant:** Every encryption uses a fresh, random 96-bit nonce ($2^{96}$
              entropy) to prevent replay attacks and catastrophic XOR stream key reuse.
            """
        )

    key, payload = _init_lab_state()

    # -------------------------------------------------------------------------
    # 1. Ephemeral Key Management
    # -------------------------------------------------------------------------
    st.markdown("### 1. Ephemeral Key State")
    k_col1, k_col2 = st.columns([7, 3])
    with k_col1:
        st.markdown(f"**Active Ephemeral Key:** `{mask_key_preview(key)}`")
        st.caption(
            "Cryptographically secure 256-bit key generated in memory via os.urandom. "
            "The full key is never logged or exposed in the UI."
        )
    with k_col2:
        if st.button("🔄 Rotate Ephemeral Key", use_container_width=True):
            st.session_state["sec_lab_key"] = generate_ephemeral_key()
            st.session_state["sec_lab_payload"] = None
            st.session_state["sec_lab_is_tampered"] = False
            st.rerun()

    st.markdown("---")

    # -------------------------------------------------------------------------
    # 2. Safe Payload Selection & Encryption
    # -------------------------------------------------------------------------
    st.markdown("### 2. Encryption with Authenticated Associated Data (AAD)")

    p_col1, p_col2 = st.columns(2)
    with p_col1:
        selected_sample_name = st.selectbox(
            "Select Safe Synthetic Payload:",
            options=list(SAFE_SAMPLES.keys()),
            index=0,
            help="Free-form secret entry is disabled to prevent accidental credential leakage.",
        )
        sample_plaintext = SAFE_SAMPLES[selected_sample_name]
        st.text_area(
            "Plaintext Message to Encrypt:",
            value=sample_plaintext,
            height=100,
            disabled=True,
            help="Pre-configured safe synthetic text.",
        )

    with p_col2:
        aad_input = st.text_input(
            "Authenticated Associated Data (AAD):",
            value=DEFAULT_AAD,
            help="Cleartext metadata authenticated alongside the message. Any alteration to AAD "
            "causes decryption to fail even if the ciphertext is untouched.",
        )
        st.caption(
            "AAD is authenticated into the 128-bit tag but transmitted in cleartext. "
            "Useful for protocol headers, routing IDs, and audit timestamps."
        )

    if st.button("🔒 Encrypt with AES-256-GCM", type="primary", use_container_width=True):
        fresh_payload = encrypt_message(sample_plaintext, key, associated_data=aad_input)
        st.session_state["sec_lab_payload"] = fresh_payload
        st.session_state["sec_lab_is_tampered"] = False
        payload = fresh_payload
        st.success("Message successfully encrypted with fresh 96-bit random nonce!")

    # -------------------------------------------------------------------------
    # 3. Ciphertext Inspection & Integrity Envelope
    # -------------------------------------------------------------------------
    if payload is not None:
        st.markdown("---")
        st.markdown("### 3. Cryptographic Envelope Breakdown")

        is_tampered = st.session_state.get("sec_lab_is_tampered", False)
        if is_tampered:
            st.warning("⚠️ **Notice:** This payload has been tampered with (bit flipped in memory).")

        env_dict = payload.to_dict()
        e_col1, e_col2, e_col3 = st.columns(3)
        with e_col1:
            st.markdown("**Nonce (96 bits / 12 bytes):**")
            st.code(env_dict["nonce_hex"], language="text")
        with e_col2:
            st.markdown("**Auth Tag (128 bits / 16 bytes):**")
            st.code(env_dict["tag_hex"], language="text")
        with e_col3:
            st.markdown("**Ciphertext Length:**")
            st.code(f"{len(payload.raw_ciphertext)} bytes (AES-256)", language="text")

        st.markdown("**Base64 Ciphertext:**")
        st.code(env_dict["ciphertext_b64"], language="text")

        # ---------------------------------------------------------------------
        # 4. Decryption & Tamper Verification Demos
        # ---------------------------------------------------------------------
        st.markdown("---")
        st.markdown("### 4. Decryption & Tamper-Evident Verification")

        act_col1, act_col2, act_col3 = st.columns(3)

        with act_col1:
            if st.button("🔓 Decrypt with Valid Key", use_container_width=True):
                try:
                    decrypted_text = decrypt_message(payload, key)
                    st.success("✅ **Decryption & Tag Verification Succeeded!**")
                    st.code(decrypted_text, language="text")
                except AuthenticationFailedError as exc:
                    st.error(f"⛔ **Authentication Failed:** {exc}")

        with act_col2:
            if st.button(
                "💥 Tamper Ciphertext (Flip 1 Bit)",
                use_container_width=True,
                help="Flip a single bit in the ciphertext to simulate data corruption or MITM.",
            ):
                tampered = tamper_payload(payload, byte_index=0)
                st.session_state["sec_lab_payload"] = tampered
                st.session_state["sec_lab_is_tampered"] = True
                st.rerun()

        with act_col3:
            if st.button(
                "🔑 Decrypt with Wrong Key",
                use_container_width=True,
                help="Attempt decryption using a different randomly generated 256-bit key.",
            ):
                wrong_key = generate_ephemeral_key()
                try:
                    decrypt_message(payload, wrong_key)
                    st.error("Unexpected success: Decryption should have failed!")
                except AuthenticationFailedError as exc:
                    st.error(
                        "⛔ **Tag Verification Failed (Expected):** Decryption with an "
                        "incorrect cryptographic key was rejected. AES-GCM guarantees that "
                        f"wrong keys produce no decrypted output.\n\n*Error:* {exc}"
                    )

        if is_tampered:
            st.info(
                "ℹ️ **Tampering Demonstration Active:** A single bit in ciphertext was flipped. "
                "Click **'🔓 Decrypt with Valid Key'** above to verify that AES-GCM's "
                "authentication tag immediately detects the modification and rejects the payload."
            )


if __name__ == "__main__" or "streamlit" in __name__:
    render_security_lab()
