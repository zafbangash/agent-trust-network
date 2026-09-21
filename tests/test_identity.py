# tests/test_identity.py
from agentframe import identity as idmod

def test_agent_id_format_and_stability():
    a = idmod.Identity.generate()
    assert a.agent_id.startswith("ag:")
    assert len(a.agent_id) == 3 + 16          # "ag:" + 16 chars
    assert a.agent_id == idmod.agent_id_from_pubkey(a.pub_raw)

def test_sign_then_verify_roundtrip():
    a = idmod.Identity.generate()
    msg = b"hello"
    sig = a.sign(msg)
    assert idmod.verify(a.pub_b64, msg, sig) is True

def test_verify_rejects_tampered_message():
    a = idmod.Identity.generate()
    sig = a.sign(b"hello")
    assert idmod.verify(a.pub_b64, b"HELLO", sig) is False

def test_verify_rejects_other_key():
    a, b = idmod.Identity.generate(), idmod.Identity.generate()
    sig = a.sign(b"hello")
    assert idmod.verify(b.pub_b64, b"hello", sig) is False

def test_id_is_derived_from_pubkey_only():
    a = idmod.Identity.generate()
    assert idmod.agent_id_from_pubkey(a.pub_raw) == a.agent_id

def test_save_then_load_preserves_identity(tmp_path):
    a = idmod.Identity.generate()
    p = tmp_path / "agent.pem"
    a.save(str(p))
    loaded = idmod.Identity.load(str(p))
    assert loaded.agent_id == a.agent_id
    sig = loaded.sign(b"x")
    assert idmod.verify(a.pub_b64, b"x", sig) is True

def test_saved_key_file_is_owner_only(tmp_path):
    import os

    a = idmod.Identity.generate()
    p = tmp_path / "agent.pem"
    a.save(str(p))

    if os.name == "posix":
        import stat
        mode = stat.S_IMODE(p.stat().st_mode)
        assert mode == 0o600
    else:
        # NTFS has no POSIX mode bits; the real guarantee is the ACL
        # Identity.save() rewrites via _restrict_to_owner_windows(), so
        # verify that directly: exactly one ACE, full control, current user.
        import ntsecuritycon as con
        import win32api
        import win32security

        sd = win32security.GetFileSecurity(
            str(p), win32security.DACL_SECURITY_INFORMATION
        )
        dacl = sd.GetSecurityDescriptorDacl()
        assert dacl.GetAceCount() == 1
        ace = dacl.GetAce(0)
        ace_mask, ace_sid = ace[1], ace[2]
        assert ace_mask == con.FILE_ALL_ACCESS
        user_sid, _, _ = win32security.LookupAccountName("", win32api.GetUserName())
        assert ace_sid == user_sid
