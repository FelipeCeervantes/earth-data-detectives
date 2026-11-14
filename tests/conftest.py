"""Configuración común de pytest."""


def pytest_configure(config):
    config.addinivalue_line("markers", "red: prueba que necesita internet (NASA POWER). Sáltala con -m 'not red'.")
